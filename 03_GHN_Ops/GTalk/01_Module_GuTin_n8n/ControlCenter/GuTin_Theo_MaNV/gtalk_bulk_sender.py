# -*- coding: utf-8 -*-
"""
gtalk_bulk_sender.py — Gửi tin nhắn GTalk OA hàng loạt theo Mã NV từ Google Sheet.

Luồng (theo tài liệu chuẩn gtalk-integration-docs.md):
  1. Đọc Google Sheet (cột Mã NV + Nội dung) bằng Service Account ghn-sheet-bot
  2. Chỉ lấy những dòng Chưa gửi (Trạng thái trống)   → chống gửi trùng
  3. Với mỗi Mã NV:
       a. Tạo kênh 1-1 bằng identity (Section 12 create-server-direct-channel)
       b. Tra userId bằng channelId vừa tạo (Section 19 get-user-id-by-identity)
       c. Gửi tin (Section 3 text / Section 4 template) — tùy cột Loại tin
  4. Chỉ ghi "ĐÃ GỬI" khi API trả errorCode=success; lỗi thì ghi "LỖI" + chi tiết
  5. Ghi lại: Trạng thái, Chi tiết, Gửi lúc, Mã gửi (chống trùng)

Cách chạy:
  python gtalk_bulk_sender.py --help        # xem hướng dẫn
  python gtalk_bulk_sender.py --dry-run     # chạy thử, KHÔNG gửi thật
  python gtalk_bulk_sender.py               # chạy thật
"""

import os
import sys
import io
import json
import time
import argparse
import hashlib
from datetime import datetime

# ---------- Xuất tiếng Việt chuẩn trên Windows ----------
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

# Đọc thư viện mềm dẻo
try:
    import requests
except ImportError:
    requests = None

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    HAS_GSHEET = True
except ImportError:
    HAS_GSHEET = False

# ============================================================
# CẤU HÌNH (có thể sửa, hoặc đưa vào .env)
# ============================================================
WORKSPACE = r"E:\GHN\AntiGravity\Khua_Ho_Tro"

# Spreadsheet nguồn (do anh Khoa tạo)
SPREADSHEET_ID = os.environ.get(
    "GTALK_SHEET_ID",
    "15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg",
)
SHEET_TAB = "Sheet1"

# Key file của Service Account ghn-sheet-bot
KEY_FILE = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.join(WORKSPACE, "05_TaiLieu_Note", "Keys",
                 "ghn-sheets-automation-90e4499c91ec.json"),
)

# OA Token = "username:password" (phần trước dấu : là oaId)
# Đọc từ .env của Automate_Sheets_Gtalk
_OA_TOKEN = None
_OA_ID = None


def _load_oa_token():
    """Đọc GTALK_OA_TOKEN từ .env của Automate_Sheets_Gtalk. KHÔNG log token."""
    global _OA_TOKEN, _OA_ID
    if _OA_TOKEN is not None:
        return _OA_ID, _OA_TOKEN
    env_path = os.path.join(WORKSPACE, "03_GHN_Ops", "GTalk",
                            "Automate_Sheets_Gtalk", ".env")
    token = None
    # ƯU TIÊN đọc từ file .env (tránh env bị che trong môi trường tương tác)
    if os.path.exists(env_path):
        for line in open(env_path, encoding="utf-8", errors="ignore"):
            s = line.strip()
            if s.startswith("GTALK_OA_TOKEN="):
                token = s.split("=", 1)[1].strip()
                break
    # fallback: biến môi trường (chỉ khi file .env không có)
    if not token:
        token = os.environ.get("GTALK_OA_TOKEN")
    if not token:
        raise SystemExit("[LỖI] Không tìm thấy GTALK_OA_TOKEN trong .env")
    if ":" not in token:
        raise SystemExit("[LỖI] OA token phải có dạng username:password")
    _OA_TOKEN, _OA_ID = token, token.split(":", 1)[0]
    return _OA_ID, _OA_TOKEN


def _base_url():
    """Môi trường gửi: prod mặc định, có thể dùng test."""
    env = os.environ.get("GTALK_ENV", "prod").lower()
    return ("https://mbff.ghn.vn" if env == "prod"
            else "https://test-api.mbff.ghn.tech")


# ============================================================
# GOOGLE SHEETS
# ============================================================
_sheets = None


def _get_sheets():
    global _sheets
    if _sheets is None:
        if not HAS_GSHEET:
            raise SystemExit(
                "[LỖI] Thiếu thư viện. Cài: pip install google-auth google-api-python-client requests")
        if not os.path.exists(KEY_FILE):
            raise SystemExit(f"[LỖI] Không tìm thấy key file: {KEY_FILE}")
        creds = service_account.Credentials.from_service_account_file(
            KEY_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        _sheets = build("sheets", "v4", credentials=creds)
    return _sheets


def read_rows():
    """Đọc toàn bộ sheet, trả về header + các dòng dữ liệu."""
    svc = _get_sheets()
    rng = f"'{SHEET_TAB}'!A1:H"
    res = svc.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=rng).execute()
    values = res.get("values", [])
    if not values:
        raise SystemExit("[LỖI] Sheet rỗng (chưa có header?)")
    return values[0], values[1:]


def write_status_updates(updates):
    """Ghi hàng loạt (Trạng thái, Chi tiết, Gửi lúc, Mã gửi) cho nhiều dòng.

    updates: list mỗi phần tử là dict {row, status, detail, sent_at, sent_id}.
    """
    if not updates:
        return
    svc = _get_sheets()
    data = []
    for u in updates:
        row = u["row"]
        values = [[u.get("status", ""), u.get("detail", ""),
                   u.get("sent_at", ""), u.get("sent_id", "")]]
        rng = f"'{SHEET_TAB}'!E{row}:H{row}"
        data.append({"range": rng, "values": values})
    svc.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={"valueInputOption": "RAW", "data": data}).execute()


# ============================================================
# GTALK API
# ============================================================
def _api(method, endpoint, body):
    """Gọi REST API mbff, trả dict response chuẩn."""
    if requests is None:
        raise SystemExit("[LỖI] Thiếu requests. Cài: pip install requests")
    url = _base_url() + endpoint
    headers = {"Content-Type": "application/json"}
    r = requests.request(method, url, json=body, headers=headers, timeout=40)
    try:
        return r.json()
    except Exception:
        return {"errorCode": "http_error", "error": {"errorMessage": f"HTTP {r.status_code}"}}


def _load_channel_cache():
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gtalk_channels.json")
    try:
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_channel_cache(cache):
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gtalk_channels.json")
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=1)
    except Exception:
        pass

def create_direct_channel(oa_id, oa_token, ma_nv):
    """Section 12: tạo kênh 1-1 bằng Mã NV (identity). Trả channelId. Có cơ chế cache cục bộ giúp giảm tải API và tăng tốc gửi tin gấp đôi."""
    ma_nv_str = str(ma_nv).strip()
    cache = _load_channel_cache()
    if ma_nv_str in cache:
        return cache[ma_nv_str], None

    body = {
        "oaId": oa_id,
        "oaToken": oa_token,
        "identity": {"identityChannel": 1, "identityId": ma_nv_str},
    }
    res = _api("POST", "/api/gtalk/create-server-direct-channel", body)
    if res.get("errorCode") == "success" and res.get("data"):
        cid = res["data"].get("channelId")
        if cid:
            cache[ma_nv_str] = cid
            _save_channel_cache(cache)
        return cid, None
    return None, res.get("error", {}).get("errorMessage", res.get("errorCode"))


def get_user_id_by_identity(oa_id, oa_token, channel_id, ma_nv):
    """Section 19: tra userId từ Mã NV dựa trên channel. Trả userId (hoặc None)."""
    body = {
        "oaId": oa_id,
        "oaToken": oa_token,
        "channelId": str(channel_id),
        "identityChannel": 1,
        "identityId": str(ma_nv),
    }
    res = _api("POST", "/api/gtalk/get-user-id-by-identity", body)
    if res.get("errorCode") == "success" and res.get("data"):
        return res["data"].get("userId"), None
    return None, res.get("error", {}).get("errorMessage", res.get("errorCode"))


def send_message(oa_id, oa_token, channel_id, text, is_template=False,
                 mentioned_user_ids=None):
    """Gửi tin (text / template). Phiên bản mở rộng:
    - is_template=True  -> Section 4 template card
    - mentioned_user_ids -> Section 3 @mention (list userId string), top-level
    Trả (globalMsgId, error, clientMsgId).
    """
    client_msg_id = str(int(time.time() * 1000))
    # Tự động phát hiện cấu trúc JSON của Mẫu thẻ (Card template)
    if not is_template:
        if text.strip().startswith("{") and text.strip().endswith("}"):
            try:
                json.loads(text)
                is_template = True
            except Exception:
                pass

    if is_template:
        # Card có nút — text có thể là JSON {templateId, shortMessage, data}
        try:
            tpl = json.loads(text)
            content = {
                "template": {
                    "templateId": str(tpl.get("templateId", "1")),
                    "shortMessage": tpl.get("shortMessage", ""),
                    "data": json.dumps(
                        tpl.get("data", {}), ensure_ascii=False),
                },
                "parseMode": "PLAIN_TEXT",
            }
        except Exception:
            content = {
                "template": {
                    "templateId": "1",
                    "shortMessage": text,
                    "data": json.dumps(
                        {"title": text, "content": text}, ensure_ascii=False),
                },
                "parseMode": "PLAIN_TEXT",
            }
    else:
        content = {"text": text, "parseMode": "MARKDOWN"}

    body = {
        "channelId": str(channel_id),
        "clientMsgId": client_msg_id,
        "content": content,
        "oaToken": oa_token,
    }
    # @mention: interaction là field TOP-LEVEL (sibling của content), userId là string
    if mentioned_user_ids:
        body["interaction"] = {
            "mentionedUserIds": [str(u) for u in mentioned_user_ids]
        }

    res = _api("POST", "/api/gtalk/send-message", body)
    if res.get("errorCode") == "success":
        return res.get("data", {}).get("globalMsgId", client_msg_id), None, client_msg_id
    return None, res.get("error", {}).get("errorMessage", res.get("errorCode")), client_msg_id


# ============================================================
# UPLOAD FILE/ẢNH/VIDEO (Section 5-9)
# ============================================================

def upload_file(oa_id, oa_token, channel_id, file_path):
    """Luồng 3 bước gửi file: initiate-upload -> PUT S3 -> complete-upload.

    Returns (fileId, width, height, error). Hỗ trợ ảnh/file/video.
    """
    import mimetypes
    if not os.path.exists(file_path):
        return None, None, None, f"Không tìm thấy file: {file_path}"

    file_size = os.path.getsize(file_path)
    fname = os.path.basename(file_path)
    mime, _ = mimetypes.guess_type(fname)
    mime = mime or "application/octet-stream"

    # metadata ảnh/video (tùy chọn) - đo kích thước nếu là ảnh
    meta = ""
    if mime.startswith("image/"):
        try:
            from PIL import Image
            with Image.open(file_path) as im:
                w, h = im.size
                meta = json.dumps({"width": w, "height": h})
        except Exception:
            meta = ""

    # Bước 1: initiate-upload
    body = {
        "ChannelId": str(channel_id),
        "FileName": fname,
        "FileSize": str(file_size),
        "MimeType": mime,
        "Metadata": meta,
        "oaToken": oa_token,
    }
    res = _api("POST", "/api/gtalk/initiate-upload", body)
    if res.get("errorCode") != "success" or not res.get("data"):
        return (None, None, None,
                f"Initiate thất bại: {res.get('error', {}).get('errorMessage', res.get('errorCode'))}")
    pu = res["data"]
    presigned_url = pu.get("PresignedURL")
    presigned_thumb = pu.get("PresignedThumbURL") or presigned_url
    upload_id = pu.get("UploadId")

    # Bước 2: PUT lên S3 (không cần auth header, credentials nằm trong URL)
    headers = {"Content-Type": mime}
    try:
        with open(file_path, "rb") as f:
            r = requests.put(presigned_url, data=f.read(),
                             headers=headers, timeout=120)
        if r.status_code not in (200, 201):
            return (None, None, None, f"Upload S3 thất bại HTTP {r.status_code}")
    except Exception as e:
        return (None, None, None, f"Upload S3 lỗi: {e}")

    # Bước 3: complete-upload
    res2 = _api("POST", "/api/gtalk/complete-upload",
                {"oaToken": oa_token, "UploadId": upload_id})
    if res2.get("errorCode") != "success":
        return (None, None, None,
                f"Complete thất bại: {res2.get('error', {}).get('errorMessage', res2.get('errorCode'))}")
    fid = res2.get("data", {}).get("Id")

    # lấy kích thước ảnh nếu là ảnh đã đo
    w = h = None
    if meta:
        try:
            m = json.loads(meta)
            w, h = m.get("width"), m.get("height")
        except Exception:
            pass
    return fid, w, h, None


def send_attachment(oa_id, oa_token, channel_id, file_path, caption=""):
    """Sau khi upload xong, gửi message kèm file/ảnh/video."""
    import mimetypes
    fid, w, h, err = upload_file(oa_id, oa_token, channel_id, file_path)
    if err:
        return None, err, None

    fname = os.path.basename(file_path)
    mime, _ = mimetypes.guess_type(fname)
    mime = mime or "application/octet-stream"
    file_size = os.path.getsize(file_path)

    client_msg_id = str(int(time.time() * 1000))
    if mime and mime.startswith("image/"):
        item = {"image": {"fileId": fid, "width": w or 680, "height": h or 453}}
    elif mime and mime.startswith("video/"):
        item = {"video": {"fileId": fid, "width": w or 1280, "height": h or 720,
                          "duration": 0}}
    else:
        item = {"file": {"fileId": fid, "fileName": fname,
                         "mimeType": mime, "fileSize": file_size}}
    content = {"attachment": {"caption": caption or "", "items": [item]}, "parseMode": "PLAIN_TEXT"}

    body = {"channelId": str(channel_id), "clientMsgId": client_msg_id,
            "content": content, "oaToken": oa_token}
    res = _api("POST", "/api/gtalk/send-message", body)
    if res.get("errorCode") == "success":
        return res.get("data", {}).get("globalMsgId", client_msg_id), None, client_msg_id
    return None, res.get("error", {}).get("errorMessage", res.get("errorCode")), client_msg_id


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Gửi tin GTalk OA hàng loạt theo Mã NV từ Google Sheet.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Chạy thử: đọc sheet, KHÔNG gửi thật, không ghi sheet.")
    parser.add_argument("--ma-nv", type=str, default=None,
                        help="Chỉ gửi 1 mã NV cụ thể (test).")
    parser.add_argument("--template", action="store_true",
                        help="Gửi dạng template card thay vì text.")
    args = parser.parse_args()

    oa_id, oa_token = _load_oa_token()
    print(f"[i] OA_ID: {oa_id}   Môi trường: {_base_url()}")
    if args.dry_run:
        print("[i] CHẾ ĐỘ DRY-RUN: sẽ KHÔNG gửi thật, không ghi sheet.")

    header, rows = read_rows()
    # định vị cột theo header
    idx = {c: i for i, c in enumerate(header)}
    def col(cname): return idx.get(cname)
    i_ma = col("Mã NV")
    i_nd = col("Nội dung")
    i_tt = col("Trạng thái")
    i_loai = col("Loại tin")
    if i_ma is None or i_nd is None:
        raise SystemExit("[LỖI] Sheet thiếu cột 'Mã NV' hoặc 'Nội dung' (kiểm tra header)")

    results = []
    for i, row in enumerate(rows):
        gsheet_row = i + 2  # dòng dữ liệu bắt đầu từ dòng 2
        for _ in range(len(row), 8):
            row.append("")  # pad đủ 8 cột
        ma_nv = (row[i_ma] or "").strip()
        noi_dung = (row[i_nd] or "").strip()
        trang_thai = (row[i_tt] or "").strip() if i_tt is not None else ""
        loai_tin = (row[i_loai] or "").strip().upper() if i_loai is not None else ""

        if not ma_nv and not noi_dung:
            continue  # dòng trống
        if args.ma_nv and ma_nv != args.ma_nv:
            continue  # lọc theo --ma-nv
        if trang_thai and trang_thai.upper() in ("ĐÃ GỬI", "SENT", "DONE"):
            print(f"  - Bỏ qua dòng {gsheet_row} ({ma_nv}): đã gửi trước đó")
            continue  # chống gửi trùng
        if trang_thai and trang_thai.upper() in ("LỖI", "FAILED", "FAIL"):
            # vẫn xử lý lại dòng lỗi
            pass

        print(f"\n[+] Dòng {gsheet_row} | Mã NV={ma_nv}")
        if not ma_nv:
            # thiếu mã NV -> chỉ status thiếu thông tin
            results.append({"row": gsheet_row, "status": "LỖI",
                            "detail": "Thiếu Mã NV"})
            continue

        if args.dry_run:
            print(f"    [DRY] dòng {gsheet_row} | Loại={loai_tin or 'TEXT'} | {ma_nv}: {noi_dung[:60]}")
            continue

        # 1) Tạo kênh bằng Mã NV
        channel_id, err = create_direct_channel(oa_id, oa_token, ma_nv)
        if not channel_id:
            print(f"    [LỖI] Tạo kênh thất bại: {err}")
            results.append({"row": gsheet_row, "status": "LỖI", "detail": f"Tạo kênh: {err}"})
            continue

        # 2) Tra userId (để mention / kiểm tra đúng người)
        user_id, uerr = get_user_id_by_identity(oa_id, oa_token, channel_id, ma_nv)

        # 3) Gửi tin theo Loại tin
        msg_id = None
        serr = ""
        client_id = str(int(time.time() * 1000))
        if loai_tin == "MENTION":
            msg_id, serr, client_id = send_message(
                oa_id, oa_token, channel_id, noi_dung,
                mentioned_user_ids=[user_id] if user_id else None)
        elif loai_tin in ("IMAGE", "FILE", "VIDEO"):
            msg_id, serr, client_id = send_attachment(
                oa_id, oa_token, channel_id, noi_dung.strip('"'),
                caption="")
        elif loai_tin == "TEMPLATE":
            msg_id, serr, client_id = send_message(
                oa_id, oa_token, channel_id, noi_dung, is_template=True)
        else:
            # mặc định: text thường
            msg_id, serr, client_id = send_message(
                oa_id, oa_token, channel_id, noi_dung)

        if msg_id:
            print(f"    [OK] {loai_tin or 'TEXT'} tới {ma_nv} (userId={user_id}) msg={msg_id}")
            results.append({
                "row": gsheet_row, "status": "ĐÃ GỬI",
                "detail": f"{loai_tin or 'TEXT'} userId={user_id or '?'} msg={msg_id}",
                "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "sent_id": hashlib.sha1(f"{ma_nv}:{client_id}".encode()).hexdigest()[:16],
            })
        else:
            print(f"    [LỖI] Gửi thất bại: {serr}")
            results.append({"row": gsheet_row, "status": "LỖI", "detail": f"Gửi: {serr}"})

        # Delay giữa các tin để tránh bị spam/block
        time.sleep(1.5)

    if args.dry_run:
        print(f"\n[i] DRY-RUN xong — duyệt {len(results)} dòng hợp lệ, chưa gửi gì.")
        return

    # ghi kết quả theo lô
    write_status_updates(results)
    ok = sum(1 for r in results if r.get("status", "").endswith("GỬI"))
    fail = sum(1 for r in results if r.get("status") == "LỖI")
    print("\n" + "=" * 50)
    print(f"HOÀN THÀNH: {ok} đã gửi, {fail} lỗi ({len(results)} dòng xử lý)")
    print("=" * 50)


if __name__ == "__main__":
    main()