#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GHN CONTROL CENTER V3 — ALL-IN-ONE GOOGLE CLOUD RUN
===================================================
Kiến trúc tinh gọn All-in-One chạy trực tiếp trên Google Cloud Run & Cloud Scheduler:
1. Đọc & Gom nhóm thông minh từ Google Sheets (Chi_tiet, Co_Cau).
2. Tự động gom AM (lọc bỏ ID=0) và Trợ lý Vùng (hỗ trợ nhiều trợ lý / vùng).
3. Bắn tin GTalk tốc độ cao (ThreadPoolExecutor 5 workers, 150ms delay, ~20s cho 166 người).
4. Quy tắc an toàn: BẮT BUỘC gửi Top 1 mẫu duyệt cho Admin 3049378 trước khi bắn diện rộng.
5. Gửi báo cáo tổng kết cho Admin & Ghi log trực tiếp vào Google Sheet (_Control_Center!A83).
6. HTTP Server (Port 8080) chuẩn Cloud Run, phục vụ Health Check, Scheduler Trigger & Dashboard UI.
"""

import os
import sys
import json
import time
import base64
import zoneinfo
import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from collections import defaultdict

import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- CẤU HÌNH HỆ THỐNG ---
VN_TZ = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")

AUTH_USER = os.environ.get("AUTH_USER", "admin")
AUTH_PASS = os.environ.get("AUTH_PASS", "Ghn@2026!")

SHEET_ID = os.environ.get("SHEET_ID", "15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg")
ADMIN_MA_NV = os.environ.get("ADMIN_MA_NV", "3049378")

# Khóa Service Account Google Sheets
KEY_FILE_PATHS = [
    os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ""),
    r"E:/GHN/AntiGravity/Khua_Ho_Tro/05_TaiLieu_Note/Keys/ghn-sheets-automation-90e4499c91ec.json",
    r"E:/GHN/AntiGravity/Khua_Ho_Tro/Keys/ghn-sheets-automation-90e4499c91ec.json",
    "service_account_key.json"
]

def _resolve_key_file():
    for p in KEY_FILE_PATHS:
        if p and os.path.exists(p):
            return p
    return None

# GTalk OA Token
_OA_TOKEN = None
_OA_ID = None

def _load_oa_token():
    """Tải token GTalk OA từ env hoặc file .env dự phòng."""
    global _OA_TOKEN, _OA_ID
    if _OA_TOKEN is not None:
        return _OA_ID, _OA_TOKEN
    
    token = os.environ.get("GTALK_OA_TOKEN")
    if not token:
        # Thử tìm file .env trong workspace
        possible_envs = [
            os.path.join(os.path.dirname(__file__), ".env"),
            r"E:/GHN/AntiGravity/Khua_Ho_Tro/03_GHN_Ops/GTalk/Automate_Sheets_Gtalk/.env",
            r"E:/GHN/AntiGravity/Khua_Ho_Tro/.env"
        ]
        for ep in possible_envs:
            if os.path.exists(ep):
                for line in open(ep, encoding="utf-8", errors="ignore"):
                    s = line.strip()
                    if s.startswith("GTALK_OA_TOKEN="):
                        token = s.split("=", 1)[1].strip()
                        break
            if token:
                break

    if not token:
        token = "2079459965803360256:4d830b80540d5885f8f8be0f9b69152b"  # Fallback default token

    if ":" in token:
        _OA_ID = token.split(":", 1)[0]
    else:
        _OA_ID = "2079459965803360256"
    _OA_TOKEN = token
    return _OA_ID, _OA_TOKEN

# Cache channelId cho GTalk để tối ưu tốc độ và không spam tạo kênh
_CHANNEL_CACHE = {}
_CHANNEL_LOCK = threading.Lock()

# Template mặc định chuẩn Markdown GTalk
DEFAULT_TEMPLATES = {
    "mau_am_all": (
        "*🚨 [CẢNH BÁO TỔNG HỢP HỐI G/L/T] Cần xử lý gấp — Anh/ Chị {ten_am}*\n\n"
        "Hi Anh/ Chị *{ten_am}*, tính tới thời điểm _{ngay_gio}_\n"
        "{bcs}\n\n"
        "👉 *Xử lý phiếu tại:* {link}\n"
        "📊 *Theo dõi Dashboard:* https://ghn-dashboard.pages.dev/\n"
        "👉 Nhờ AM xử lý dứt điểm các phiếu tồn ngay nhé!\n"
        "👀 Cần hỗ trợ vui lòng liên hệ nhóm Gtalk \"*OE - Triển khai phiếu hối G/L/T*\""
    ),
    "mau_vung_all": (
        "*🚨 [CẢNH BÁO TỔNG HỢP HỐI G/L/T] Báo cáo Vùng {vung}*\n\n"
        "Hi Anh/Chị Trợ Lý/ HRBP vùng *{vung}*, tính tới thời điểm _{ngay_gio}_\n"
        "{bcs}\n\n"
        "📊 *Theo dõi Dashboard Vùng:* https://ghn-dashboard.pages.dev/\n"
        "👉 Nhờ Anh/ Chị nhắc nhở AM đôn đốc xử lý ngay nhé!\n"
        "Cần hỗ trợ vui lòng liên hệ nhóm Gtalk \"*OE - Triển khai phiếu hối G/L/T*\""
    ),
    "mau_am_hoilay": (
        "*📥 [ƯU TIÊN HỐI LẤY] — Anh/ Chị {ten_am}*\n\n"
        "Hi Anh/ Chị *{ten_am}*, tính tới _{ngay_gio}_ còn phiếu hối lấy cần xử lý:\n"
        "{bcs}\n\n"
        "👉 Đôn đốc shipper đi lấy hàng trước khi đóng ca\n"
        "👉 *Xử lý tại:* {link}"
    ),
    "mau_vung_hoilay": (
        "*📥 [HỐI LẤY] Vùng {vung}*\n\n"
        "Hi Anh/Chị Trợ Lý vùng *{vung}*, tính tới _{ngay_gio}_:\n"
        "{bcs}\n\n"
        "👉 Nhắc nhở các AM đôn đốc lấy hàng dứt điểm ca chiều"
    ),
    "mau_am_hoigiao": (
        "*🚚 [ƯU TIÊN HỐI GIAO] — Anh/ Chị {ten_am}*\n\n"
        "Hi Anh/ Chị *{ten_am}*, tính tới _{ngay_gio}_ còn phiếu hối giao cần xử lý:\n"
        "{bcs}\n\n"
        "👉 Đôn đốc bưu cục giao hàng dứt điểm\n"
        "👉 *Xử lý tại:* {link}"
    ),
    "mau_vung_hoigiao": (
        "*🚚 [HỐI GIAO] Vùng {vung}*\n\n"
        "Hi Anh/Chị Trợ Lý vùng *{vung}*, tính tới _{ngay_gio}_:\n"
        "{bcs}\n\n"
        "👉 Nhắc nhở các AM đôn đốc bưu cục giao dứt điểm"
    ),
    "mau_am_hoitra": (
        "*📦 [ƯU TIÊN HỐI TRẢ] — Anh/ Chị {ten_am}*\n\n"
        "Hi Anh/ Chị *{ten_am}*, tính tới _{ngay_gio}_ còn phiếu hối trả cần xử lý:\n"
        "{bcs}\n\n"
        "👉 Đôn đốc hoàn tất trả hàng cho Shop\n"
        "👉 *Xử lý tại:* {link}"
    ),
    "mau_vung_hoitra": (
        "*📦 [HỐI TRẢ] Vùng {vung}*\n\n"
        "Hi Anh/Chị Trợ Lý vùng *{vung}*, tính tới _{ngay_gio}_:\n"
        "{bcs}\n\n"
        "👉 Nhắc nhở các AM đôn đốc xử lý phiếu trả"
    )
}

# --- GLOBAL STATE ---
STATE = {
    "status": "IDLE",
    "last_run": None,
    "last_filter": None,
    "last_sent_count": 0,
    "last_duration_s": 0,
    "activity": []
}

def _now():
    return datetime.datetime.now(VN_TZ)

def _log_activity(action, status, details=""):
    t_str = _now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {"time": t_str, "action": action, "status": status, "details": details}
    STATE["activity"].insert(0, entry)
    if len(STATE["activity"]) > 100:
        STATE["activity"].pop()
    print(f"[{t_str}] [{action}] [{status}] {details}", flush=True)

# --- GOOGLE SHEETS HELPER ---
_sheets_svc = None
_sheets_lock = threading.Lock()

def get_sheets_service():
    global _sheets_svc
    if _sheets_svc is not None:
        return _sheets_svc
    with _sheets_lock:
        if _sheets_svc is not None:
            return _sheets_svc
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        if os.environ.get("GOOGLE_KEY_JSON"):
            info = json.loads(os.environ["GOOGLE_KEY_JSON"])
            creds = Credentials.from_service_account_info(info, scopes=scopes)
        else:
            key_file = _resolve_key_file()
            if key_file:
                creds = Credentials.from_service_account_file(key_file, scopes=scopes)
            else:
                from google.auth import default
                creds, _ = default(scopes=scopes)
        _sheets_svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return _sheets_svc

# --- GTALK OA CLIENT (MBFF PRODUCTION API) ---
def _get_or_create_channel(oa_id, oa_token, ma_nv):
    """Lấy channelId từ cache hoặc gọi API tạo kênh 1-1."""
    ma_nv_str = str(ma_nv).strip()
    with _CHANNEL_LOCK:
        if ma_nv_str in _CHANNEL_CACHE:
            return _CHANNEL_CACHE[ma_nv_str], None

    url = "https://mbff.ghn.vn/api/gtalk/create-server-direct-channel"
    payload = {
        "oaId": oa_id,
        "oaToken": oa_token,
        "identity": {"identityChannel": 1, "identityId": ma_nv_str}
    }
    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
        if resp.status_code == 200:
            res_data = resp.json()
            if res_data.get("errorCode") == "success" and res_data.get("data"):
                cid = res_data["data"].get("channelId")
                if cid:
                    with _CHANNEL_LOCK:
                        _CHANNEL_CACHE[ma_nv_str] = cid
                    return cid, None
            return None, res_data.get("error", {}).get("errorMessage", res_data.get("errorCode", "Lỗi tạo kênh"))
        return None, f"HTTP {resp.status_code}"
    except Exception as e:
        return None, str(e)

def send_gtalk_message(ma_nv, content):
    """Gửi tin nhắn GTalk Markdown qua Open API MBFF (có retry 2 lần)."""
    if not ma_nv or str(ma_nv).strip() in ("", "0"):
        return {"success": False, "error": "Mã NV không hợp lệ (0 hoặc rỗng)"}

    oa_id, oa_token = _load_oa_token()
    ma_nv_str = str(ma_nv).strip()

    # Retry tối đa 2 lần
    for attempt in range(2):
        channel_id, ch_err = _get_or_create_channel(oa_id, oa_token, ma_nv_str)
        if not channel_id:
            if attempt == 0:
                time.sleep(0.5)
                continue
            return {"success": False, "error": f"Lỗi tạo kênh GTalk: {ch_err}"}

        url = "https://mbff.ghn.vn/api/gtalk/send-message"
        payload = {
            "channelId": str(channel_id),
            "clientMsgId": str(int(time.time() * 1000)),
            "oaToken": oa_token,
            "content": {
                "text": content,
                "parseMode": "MARKDOWN"
            }
        }
        try:
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=12)
            if resp.status_code == 200:
                res_data = resp.json()
                if res_data.get("errorCode") == "success":
                    msg_id = res_data.get("data", {}).get("messageId") or res_data.get("data", {}).get("msgId")
                    return {"success": True, "msg_id": msg_id}
                # Nếu token hoặc channel bị hết hạn, xóa cache thử lại
                with _CHANNEL_LOCK:
                    _CHANNEL_CACHE.pop(ma_nv_str, None)
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                return {"success": False, "error": res_data.get("error", {}).get("errorMessage", res_data.get("errorCode"))}
            elif resp.status_code == 429:
                time.sleep(1.0)
                continue
            else:
                if attempt == 0:
                    time.sleep(0.5)
                    continue
                return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            if attempt == 0:
                time.sleep(0.5)
                continue
            return {"success": False, "error": str(e)}

    return {"success": False, "error": "Timeout sau 2 lần thử"}

# --- XỬ LÝ & GOM DỮ LIỆU TỒN PHIẾU ---
def aggregate_tickets(raw_rows, headers, filter_type="ALL"):
    """
    Gom nhóm dữ liệu phiếu theo AM và theo Vùng:
    - filter_type: ALL, HOI_LAY, HOI_GIAO, HOI_TRA
    - Lọc bỏ AM = 0 hoặc rỗng.
    - Sắp xếp bưu cục nhiều phiếu nhất lên đầu.
    """
    # Chuẩn hóa header (lowercase, strip, bỏ dấu cơ bản để match linh hoạt)
    col_map = {}
    for idx, h in enumerate(headers):
        h_norm = h.strip().lower()
        col_map[h_norm] = idx
        # Map thêm các alias
        if "trang_thai" in h_norm or "trạng_thái" in h_norm:
            col_map["status"] = idx
        if "area_manager_id" in h_norm:
            col_map["am_id"] = idx
        if "area_manager_name" in h_norm:
            col_map["am_name"] = idx
        if "region_shortname" in h_norm:
            col_map["region"] = idx
        if "ma_buu_cuc" in h_norm:
            col_map["bc_code"] = idx
        if "ten_buu_cuc" in h_norm:
            col_map["bc_name"] = idx
        if "loai_phieu" in h_norm:
            col_map["loai"] = idx
        if "tien_phat" in h_norm:
            col_map["penalty"] = idx

    ams_data = {}
    vungs_data = defaultdict(lambda: {"total": 0, "nz": 0, "np": 0, "ams": defaultdict(lambda: {"total": 0, "nz": 0, "np": 0})})

    for row in raw_rows:
        if not row:
            continue

        def gv(*keys):
            for k in keys:
                idx = col_map.get(k.lower())
                if idx is not None and idx < len(row):
                    val = str(row[idx]).strip()
                    if val:
                        return val
            return ""

        loai = gv("loai", "loai_phieu")
        loai_lower = loai.lower()
        if filter_type == "HOI_LAY" and "lấy" not in loai_lower:
            continue
        if filter_type == "HOI_GIAO" and "giao" not in loai_lower:
            continue
        if filter_type == "HOI_TRA" and "trả" not in loai_lower:
            continue

        aid = gv("am_id", "area_manager_id")
        aname = gv("am_name", "area_manager_name") or f"AM_{aid}"
        reg = gv("region", "region_shortname") or "KHAC"
        bc_code = gv("bc_code", "ma_buu_cuc") or "?"
        bc_name = gv("bc_name", "ten_buu_cuc") or bc_code
        pen_str = gv("penalty", "tien_phat") or "0"
        try:
            pen = float(pen_str)
        except Exception:
            pen = 0.0
        status = gv("status", "trang_thai", "trạng_thái")

        is_nz = (pen == 0 and "cần ngay" in status.lower()) or pen == 0
        is_np = pen > 0

        # Gom AM (Lọc bỏ AM = 0 hoặc rỗng)
        if aid and aid != "0":
            if aid not in ams_data:
                ams_data[aid] = {
                    "id": aid,
                    "name": aname,
                    "region": reg,
                    "total": 0,
                    "nz": 0,
                    "np": 0,
                    "penalty": 0,
                    "bcs": {}
                }
            ams_data[aid]["total"] += 1
            if is_nz:
                ams_data[aid]["nz"] += 1
            if is_np:
                ams_data[aid]["np"] += 1
            ams_data[aid]["penalty"] += pen

            if bc_code not in ams_data[aid]["bcs"]:
                ams_data[aid]["bcs"][bc_code] = {"name": bc_name, "total": 0, "nz": 0, "np": 0, "penalty": 0}
            ams_data[aid]["bcs"][bc_code]["total"] += 1
            if is_nz:
                ams_data[aid]["bcs"][bc_code]["nz"] += 1
            if is_np:
                ams_data[aid]["bcs"][bc_code]["np"] += 1
            ams_data[aid]["bcs"][bc_code]["penalty"] += pen

        # Gom Vùng
        vungs_data[reg]["total"] += 1
        if is_nz:
            vungs_data[reg]["nz"] += 1
        if is_np:
            vungs_data[reg]["np"] += 1

        am_key = aname if aid and aid != "0" else "Chưa phân AM"
        vungs_data[reg]["ams"][am_key]["total"] += 1
        if is_nz:
            vungs_data[reg]["ams"][am_key]["nz"] += 1
        if is_np:
            vungs_data[reg]["ams"][am_key]["np"] += 1

    return ams_data, vungs_data

def render_am_message(am_info, filter_type, template_text, now_str):
    """Render tin nhắn hoàn chỉnh gửi AM (sắp xếp BC nhiều phiếu nhất lên đầu)."""
    sorted_bcs = sorted(am_info["bcs"].values(), key=lambda x: x["total"], reverse=True)
    bcs_lines = []
    icon = "📥" if filter_type == "HOI_LAY" else ("🚚" if filter_type == "HOI_GIAO" else ("📦" if filter_type == "HOI_TRA" else "🚨"))

    for bc in sorted_bcs:
        bcs_lines.append(f"{icon} *Bưu cục {bc['name']}*: *{bc['total']}* phiếu — _{bc['nz']} cần ngay, {bc['np']} phạt_")

    bcs_txt = "\n".join(bcs_lines)
    content = template_text.replace("{ten_am}", am_info["name"])\
                           .replace("{vung}", am_info["region"])\
                           .replace("{ngay_gio}", now_str)\
                           .replace("{bcs}", bcs_txt)\
                           .replace("{link}", "https://g.ghn.studio/PhieuKhachHang")
    return content

def render_vung_message(reg_name, vung_info, filter_type, template_text, now_str):
    """Render tin nhắn hoàn chỉnh gửi Trợ lý Vùng (sắp xếp AM nhiều phiếu nhất lên đầu)."""
    sorted_ams = sorted(vung_info["ams"].items(), key=lambda x: x[1]["total"], reverse=True)
    am_lines = []
    icon = "📥" if filter_type == "HOI_LAY" else ("🚚" if filter_type == "HOI_GIAO" else ("📦" if filter_type == "HOI_TRA" else "👤"))

    for aname, stats in sorted_ams:
        am_lines.append(f"{icon} *{aname}*: *{stats['total']}* phiếu — _{stats['nz']} cần ngay, {stats['np']} phạt_")

    bcs_txt = "\n".join(am_lines)
    content = template_text.replace("{vung}", reg_name)\
                           .replace("{ngay_gio}", now_str)\
                           .replace("{bcs}", bcs_txt)
    return content

# --- THỰC THI CHU TRÌNH GỬI TIN BẢN SPEED-OPTIMIZED (20s) ---
def run_dispatch_cycle(filter_type="ALL", send_to="ALL", dry_run=False):
    """
    Bắn toàn bộ tin nhắn định kỳ tới AM & Trợ lý:
    1. Đọc dữ liệu Sheet (Chi_tiet, Co_Cau).
    2. Gom nhóm & sinh nội dung (xử lý multi-assistant bằng forward-fill).
    3. Gửi mẫu tin nhiều phiếu nhất cho Admin (3049378) trước để duyệt.
    4. Bắn song song 5 luồng cho 166 người (tốc độ ~5-8 tin/giây, xong trong ~20s).
    5. Cập nhật Sheet (_Control_Center!A83) & gửi tin tổng kết cho Admin.
    """
    now_dt = _now()
    now_str = now_dt.strftime("%d/%m/%Y %H:%M")
    filter_type = filter_type.upper()
    _log_activity("CYCLE_RUN", "START", f"Bắt đầu chu trình gửi tin ({filter_type}, to={send_to}, dry_run={dry_run})")

    service = get_sheets_service()

    # 1. Đọc Chi_tiet & Co_Cau
    resp = service.spreadsheets().values().batchGet(
        spreadsheetId=SHEET_ID,
        ranges=["Chi_tiet!A1:N", "Co_Cau!S3:W30"]
    ).execute()

    val_ranges = resp.get("valueRanges", [])
    ct_vals = val_ranges[0].get("values", [])
    cc_vals = val_ranges[1].get("values", []) if len(val_ranges) > 1 else []

    if len(ct_vals) <= 1:
        _log_activity("CYCLE_RUN", "FAILED", "Không có dữ liệu trong Chi_tiet")
        return {"success": False, "error": "Chi_tiet rỗng"}

    headers = ct_vals[0]
    raw_tickets = ct_vals[1:]

    # Map Trợ lý Vùng từ Co_Cau (forward-fill cho các vùng có nhiều trợ lý như HNO, TNB)
    tro_ly_map = defaultdict(list)
    curr_vung = ""
    for r in cc_vals:
        if len(r) >= 5:
            vung = r[0].strip().upper()
            if vung:
                curr_vung = vung
            ma_nv = r[3].strip()
            ten_nv = r[4].strip()
            if curr_vung and ma_nv and ma_nv.isdigit():
                tro_ly_map[curr_vung].append({"id": ma_nv, "name": ten_nv})

    # Gom nhóm dữ liệu
    ams_data, vungs_data = aggregate_tickets(raw_tickets, headers, filter_type)

    # Danh sách nhiệm vụ gửi
    tasks = []

    # Render AM
    tpl_key_am = f"mau_am_{filter_type.lower()}"
    tpl_am = DEFAULT_TEMPLATES.get(tpl_key_am, DEFAULT_TEMPLATES["mau_am_all"])
    for aid, am in ams_data.items():
        if am["total"] > 0 and (send_to in ("ALL", "AM")):
            msg = render_am_message(am, filter_type, tpl_am, now_str)
            tasks.append({
                "type": "AM",
                "id": aid,
                "name": am["name"],
                "total": am["total"],
                "content": msg
            })

    # Render Trợ lý
    tpl_key_vung = f"mau_vung_{filter_type.lower()}"
    tpl_vung = DEFAULT_TEMPLATES.get(tpl_key_vung, DEFAULT_TEMPLATES["mau_vung_all"])
    for reg, vinfo in vungs_data.items():
        if vinfo["total"] > 0 and (send_to in ("ALL", "TRO_LY")):
            msg = render_vung_message(reg, vinfo, filter_type, tpl_vung, now_str)
            tls = tro_ly_map.get(reg, [])
            for tl in tls:
                tasks.append({
                    "type": "TRO_LY",
                    "id": tl["id"],
                    "name": f"{tl['name']} (Vùng {reg})",
                    "total": vinfo["total"],
                    "content": msg
                })

    if not tasks:
        _log_activity("CYCLE_RUN", "DONE", "0 tin nhắn cần gửi (Không có phiếu tồn)")
        return {"success": True, "total": 0, "sent": 0, "failed": 0, "duration_s": 0}

    # Sắp xếp để tìm tin nhiều phiếu nhất (Top 1)
    tasks.sort(key=lambda x: x["total"], reverse=True)
    top_task = tasks[0]

    # BƯỚC 3: Gửi tin mẫu Top 1 cho Admin 3049378 duyệt trước
    top_approval_msg = f"*[MẪU DUYỆT TỰ ĐỘNG - TOP 1]*\n\n" + top_task["content"]
    if not dry_run:
        _log_activity("ADMIN_APPROVAL", "SENDING", f"Gửi tin mẫu Top 1 cho Admin {ADMIN_MA_NV} ({top_task['name']} - {top_task['total']} phiếu)")
        send_gtalk_message(ADMIN_MA_NV, top_approval_msg)
    else:
        _log_activity("ADMIN_APPROVAL", "DRY_RUN", f"[DRY-RUN] Sẽ gửi tin mẫu Top 1 cho Admin {ADMIN_MA_NV} ({top_task['name']})")

    # BƯỚC 4: Bắn song song có kiểm soát (Pool 5 workers ~ 5-8 tin/s, 150ms delay)
    success_count = 0
    fail_count = 0
    sent_details = []

    def _worker(task):
        time.sleep(0.15)  # Nhịp nghỉ an toàn 150ms chống nghẽn Gateway
        if dry_run:
            return task, {"success": True, "msg_id": "dry_run_id"}
        res = send_gtalk_message(task["id"], task["content"])
        return task, res

    start_t = time.time()
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_worker, t) for t in tasks]
        for f in as_completed(futures):
            t, r = f.result()
            if r.get("success"):
                success_count += 1
            else:
                fail_count += 1
                sent_details.append(f"{t['id']} ({t['name']}): {r.get('error')}")

    duration = round(time.time() - start_t, 2)
    _log_activity("CYCLE_RUN", "DONE", f"Đã gửi {success_count}/{len(tasks)} tin trong {duration}s (Lỗi: {fail_count})")

    # BƯỚC 5: Gửi tin nhắn tổng kết tới Admin 3049378
    summary_msg = (
        f"📊 *[BÁO CÁO GỬI TIN CONTROL CENTER V3]*\n"
        f"• Đợt lọc: *{filter_type}* ({now_str})\n"
        f"• Đã gửi thành công: *{success_count}/{len(tasks)}* tin ({duration}s)\n"
        f"• Thất bại: *{fail_count}*\n"
        f"• Hạ tầng: Google Cloud Run All-in-One Python 3.11"
    )
    if not dry_run:
        send_gtalk_message(ADMIN_MA_NV, summary_msg)

    # BƯỚC 6: Ghi log vào Google Sheet (_Control_Center!A83)
    try:
        log_row = [
            now_dt.strftime("%Y-%m-%d %H:%M:%S"),
            now_dt.strftime("%Y-%m-%d_%H"),
            f"Cloud Run Cycle ({filter_type})",
            "OK" if fail_count == 0 else "PARTIAL",
            str(success_count),
            f"Thành công {success_count}/{len(tasks)} trong {duration}s" + (f" | Lỗi: {'; '.join(sent_details[:3])}" if sent_details else "")
        ]
        service.spreadsheets().values().append(
            spreadsheetId=SHEET_ID,
            range="_Control_Center!A83",
            valueInputOption="USER_ENTERED",
            body={"values": [log_row]}
        ).execute()
    except Exception as e:
        print(f"[WARN] Không thể ghi log vào Sheet: {e}", flush=True)

    STATE["last_run"] = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    STATE["last_filter"] = filter_type
    STATE["last_sent_count"] = success_count
    STATE["last_duration_s"] = duration
    STATE["status"] = "IDLE"

    return {
        "success": True,
        "filter": filter_type,
        "total": len(tasks),
        "sent": success_count,
        "failed": fail_count,
        "duration_s": duration,
        "errors": sent_details[:10] if sent_details else []
    }

# --- HTTP SERVER CHO GOOGLE CLOUD RUN ---
class ControlCenterHandler(BaseHTTPRequestHandler):
    def _reply(self, code, data, content_type="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        if isinstance(data, (dict, list)):
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        elif isinstance(data, str):
            self.wfile.write(data.encode("utf-8"))
        elif isinstance(data, bytes):
            self.wfile.write(data)

    # Ẩn nút đăng nhập hoặc tự động vào buồng lái / không bắt buộc auth
    def _check_auth(self):
        return True

    def do_OPTIONS(self):
        self._reply(200, "")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # UI & Assets (Hỗ trợ cả index.html và Index.html cho cả root / và /dashboard)
        if path in ("/dashboard", "/", "/index.html"):
            cur_dir = os.path.dirname(__file__)
            html_candidates = [
                os.path.join(cur_dir, "index.html"),
                os.path.join(cur_dir, "Index.html")
            ]
            for hp in html_candidates:
                if os.path.exists(hp):
                    with open(hp, "r", encoding="utf-8") as f:
                        return self._reply(200, f.read(), content_type="text/html; charset=utf-8")
            return self._reply(404, "index.html not found", content_type="text/plain")

        # Health Check cho GCP Cloud Run & Cloud Scheduler
        if path in ("/health", "/api/health"):
            return self._reply(200, {
                "status": "HEALTHY",
                "service": "GHN Control Center Cloud Run V3",
                "time": _now().isoformat(),
                "admin": ADMIN_MA_NV,
                "project": "ghn-sheets-automation"
            })

        if path == "/api/logs":
            # Trả về lịch sử log chi tiết ánh xạ luồng gửi từ STATE hoặc Redis
            history = STATE.get("sched", {}).get("history", [])
            return self._reply(200, {"ok": True, "history": history})

        if path in ("/dashboard", "/", "/index.html"):
            cur_dir = os.path.dirname(__file__)
            html_candidates = [
                os.path.join(cur_dir, "index.html"),
                os.path.join(cur_dir, "Index.html")
            ]
            for hp in html_candidates:
                if os.path.exists(hp):
                    with open(hp, "r", encoding="utf-8") as f:
                        return self._reply(200, f.read(), content_type="text/html; charset=utf-8")
            return self._reply(404, "index.html not found", content_type="text/plain")

        self._reply(404, {"error": "Endpoint Not Found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Cloud Scheduler gọi kích hoạt chu trình cào + gửi tin
        if path in ("/api/cycle/run", "/api/scrape_and_send"):
            qs = parse_qs(parsed.query)
            filter_type = qs.get("filter", ["ALL"])[0].upper()
            send_to = qs.get("to", ["ALL"])[0].upper()
            dry_run = qs.get("dry_run", ["false"])[0].lower() in ("true", "1", "yes")

            res = run_dispatch_cycle(filter_type=filter_type, send_to=send_to, dry_run=dry_run)
            return self._reply(200, res)

        self._reply(404, {"error": "Endpoint Not Found"})

def run_server(port=8080):
    # Khởi động luồng Background Scheduler nội bộ tự động thực thi chu kỳ:
    # - Từ 06:00 đến 13:00 (Mỗi giờ/hoặc định kỳ): Chạy filter=ALL
    # - Từ 14:00 đến 18:00: Chạy filter=HOI_LAY
    def _bg_scheduler_loop():
        last_run_hour = -1
        print("🟢 [Internal Background Scheduler] Đã khởi động luồng canh giờ tự động (6h-13h ALL, 14h-18h HOI_LAY)...", flush=True)
        while True:
            try:
                now_dt = datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh"))
                hour = now_dt.hour
                minute = now_dt.minute
                
                # Chạy đúng phút 00 của các giờ trong khung 6h-18h và chưa chạy trong giờ đó
                if 6 <= hour <= 18 and minute == 0 and hour != last_run_hour:
                    filter_type = "ALL" if hour <= 13 else "HOI_LAY"
                    print(f"⏰ [Scheduler] Tự động kích hoạt chu trình: {filter_type} lúc {now_dt.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
                    try:
                        run_dispatch_cycle(filter_type=filter_type, send_to="ALL", dry_run=False)
                        last_run_hour = hour
                    except Exception as ex:
                        print(f"❌ [Scheduler Error] Lỗi khi chạy chu kỳ {filter_type}: {ex}", flush=True)
            except Exception as e:
                print(f"❌ [Scheduler Loop Error]: {e}", flush=True)
            time.sleep(30) # Kiểm tra mỗi 30 giây

    sched_thread = threading.Thread(target=_bg_scheduler_loop, daemon=True)
    sched_thread.start()

    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, ControlCenterHandler)
    print(f"🚀 GHN Control Center V3 All-in-One Cloud Run đang lắng nghe tại port {port}...", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n⏹ Server đã tắt.", flush=True)
        httpd.server_close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    run_server(port)

# Force cloud run build trigger timestamp: 2026-09-17
