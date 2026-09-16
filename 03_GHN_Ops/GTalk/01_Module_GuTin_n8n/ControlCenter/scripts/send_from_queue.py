# -*- coding: utf-8 -*-
"""
scripts/send_from_queue.py — Gửi tin nhắn GTalk từ hàng đợi RP_Queue (GitHub Actions / Script).

Luồng xử lý:
1. Đọc ô _Control_Center!B4 từ Google Sheet.
   - Nếu B4 != "DONE" -> Thoát ngay lập tức (exit 0).
2. Ghi _Control_Center!B5 = "RUNNING", C5 = timestamp.
3. Đọc tab RP_Queue -> Lọc các dòng có cột G (status) = "PENDING".
4. Gửi mẫu tin đầu tiên cho Admin (mã NV 3049378) để kiểm duyệt.
5. Với mỗi tin PENDING:
   - Đọc cột D (ma_nv) + cột F (noi_dung).
   - Gọi GTalk API gửi tin (qua GuTin_Theo_MaNV/gtalk_bulk_sender.py).
   - Nghỉ 1.5 giây giữa các tin để tránh rate-limit.
   - Ghi nhận trạng thái SENT / FAILED, timestamp gửi và chi tiết lỗi.
6. Cập nhật kết quả vào tab RP_Queue.
7. Ghi log vào vùng Log của _Control_Center (dòng 83+).
8. Ghi _Control_Center!B5 = "DONE", C5 = timestamp.
9. Gửi tin tổng kết cho Admin (3049378).
"""

import os
import sys
import io
import json
import time
from datetime import datetime

# UTF-8 encoding fix for Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

# Add module path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "GuTin_Theo_MaNV"))

try:
    from GuTin_Theo_MaNV import gtalk_bulk_sender as gs
except ImportError:
    try:
        import gtalk_bulk_sender as gs
    except ImportError:
        gs = None

from google.oauth2 import service_account
from googleapiclient.discovery import build

# CẤU HÌNH HỆ THỐNG
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg")
ADMIN_ID = os.environ.get("ADMIN_GTALK_ID", "3049378")
SLEEP_INTERVAL = 1.5


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _dot_id_str():
    return datetime.now().strftime("%Y-%m-%d_%H")


def get_sheets_service():
    """Khởi tạo Google Sheets API client từ env var hoặc file json cục bộ."""
    key_json = os.environ.get("GOOGLE_KEY_JSON")
    key_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    local_fallback = os.path.join(r"E:\GHN\AntiGravity\Khua_Ho_Tro\05_TaiLieu_Note\Keys\ghn-sheets-automation-90e4499c91ec.json")

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    if key_json and key_json.strip():
        try:
            info = json.loads(key_json)
            creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
            return build("sheets", "v4", credentials=creds)
        except Exception as e:
            print(f"[WARN] Không parse được GOOGLE_KEY_JSON: {e}")

    if key_file and os.path.exists(key_file):
        creds = service_account.Credentials.from_service_account_file(key_file, scopes=scopes)
        return build("sheets", "v4", credentials=creds)

    if os.path.exists(local_fallback):
        creds = service_account.Credentials.from_service_account_file(local_fallback, scopes=scopes)
        return build("sheets", "v4", credentials=creds)

    raise RuntimeError("Không tìm thấy Google Service Account credentials (GOOGLE_KEY_JSON hoặc file key)")


def load_oa_credentials():
    """Đọc GTALK_OA_TOKEN từ env hoặc file .env."""
    token = os.environ.get("GTALK_OA_TOKEN")
    if not token and gs is not None:
        try:
            return gs._load_oa_token()
        except Exception:
            pass

    if token:
        if ":" not in token:
            raise ValueError("GTALK_OA_TOKEN phải có định dạng 'oa_id:oa_secret'")
        oa_id = token.split(":", 1)[0]
        return oa_id, token

    raise RuntimeError("Không tìm thấy biến môi trường GTALK_OA_TOKEN")


def send_gtalk_direct(oa_id, oa_token, ma_nv, content):
    """Gửi 1 tin text hoặc template card qua GTalk OA API."""
    if gs is None:
        return False, "Thiếu module gtalk_bulk_sender"

    ma_nv_str = str(ma_nv).strip()
    channel_id, err = gs.create_direct_channel(oa_id, oa_token, ma_nv_str)
    if not channel_id:
        return False, f"Lỗi tạo kênh 1-1 ({ma_nv_str}): {err}"

    # Kiểm tra xem content có phải JSON template card hay không
    content_trimmed = content.strip() if isinstance(content, str) else ""
    if content_trimmed.startswith("{") and content_trimmed.endswith("}"):
        try:
            payload = json.loads(content_trimmed)
            tpl_id = payload.get("templateId", "1")
            short_msg = payload.get("shortMessage", "Thông báo vận hành")
            data = payload.get("data", {})
            msg_id, serr, _ = gs.send_template_message(oa_id, oa_token, channel_id, tpl_id, short_msg, data)
            if msg_id:
                return True, msg_id
            return False, f"Lỗi gửi card template: {serr}"
        except Exception:
            pass  # Fallback to normal text send

    # Gửi text Markdown chuẩn
    msg_id, serr, _ = gs.send_message(oa_id, oa_token, channel_id, content)
    if msg_id:
        return True, msg_id
    return False, f"Lỗi gửi text: {serr}"


def append_control_center_log(svc, timestamp, dot_id, step, status, count, detail):
    """Ghi log vào vùng _Control_Center!A83:F132."""
    try:
        res = svc.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="_Control_Center!A83:F132"
        ).execute()
        vals = res.get("values", [])
        
        target_row = 83 + len(vals)
        for i, row in enumerate(vals):
            if not row or not any(row):
                target_row = 83 + i
                break
        if target_row > 132:
            target_row = 83

        svc.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=f"_Control_Center!A{target_row}:F{target_row}",
            valueInputOption="USER_ENTERED",
            body={
                "values": [[
                    timestamp,
                    dot_id,
                    step,
                    status,
                    str(count),
                    str(detail)[:450]
                ]]
            }
        ).execute()
    except Exception as e:
        print(f"[WARN] Ghi log _Control_Center thất bại: {e}")


def main():
    print(f"[{_now_str()}] === BẮT ĐẦU CHU KỲ GỬI TIN GTALK (send_from_queue.py) ===")
    svc = get_sheets_service()

    # 1. Kiểm tra cờ B4 (GAS)
    res_flag = svc.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range="_Control_Center!B4"
    ).execute()
    b4_val = ""
    if res_flag.get("values") and res_flag["values"][0]:
        b4_val = str(res_flag["values"][0][0]).strip().upper()

    print(f"[{_now_str()}] Trạng thái cờ _Control_Center!B4: '{b4_val}'")
    if b4_val != "DONE":
        print(f"[{_now_str()}] ⏹ B4 != 'DONE' (GAS chưa xử lý xong đợt mới). Dừng quy trình an toàn.")
        sys.exit(0)

    # 2. Cập nhật B5 = RUNNING
    start_ts = _now_str()
    dot_id = _dot_id_str()
    svc.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range="_Control_Center!B5:D5",
        valueInputOption="USER_ENTERED",
        body={"values": [["RUNNING", start_ts, "Đang gửi tin từ hàng đợi RP_Queue..."]]}
    ).execute()

    try:
        # Load OA token
        oa_id, oa_token = load_oa_credentials()
        print(f"[{_now_str()}] ✓ Đã tải OA Token (oaId: {oa_id})")

        # 3. Đọc tab RP_Queue
        res_queue = svc.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range="RP_Queue!A1:J"
        ).execute()
        rows = res_queue.get("values", [])

        if len(rows) <= 1:
            print(f"[{_now_str()}] ℹ Tab RP_Queue rỗng hoặc chỉ có header. Không có tin cần gửi.")
            svc.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range="_Control_Center!B5:D5",
                valueInputOption="USER_ENTERED",
                body={"values": [["DONE", _now_str(), "Không có tin nào trong queue"]]}
            ).execute()
            append_control_center_log(svc, _now_str(), dot_id, "3. Gửi GTalk", "OK", 0, "Hàng đợi rỗng")
            sys.exit(0)

        hdr = [str(c).strip().lower() for c in rows[0]]
        ci = {c: idx for idx, c in enumerate(hdr)}

        # Xác định vị trí các cột
        col_status = ci.get("status", 6)
        col_manv = ci.get("ma_nv", 3)
        col_ten = ci.get("ten", 4)
        col_noidung = ci.get("noi_dung", 5)
        col_ts_gui = ci.get("timestamp_gui", 8)
        col_loi = ci.get("loi", 9)
        col_dotid = ci.get("dot_id", 0)

        # Lọc danh sách PENDING
        pending_items = []
        for row_idx, r in enumerate(rows[1:], start=2):
            status = r[col_status].strip().upper() if len(r) > col_status and r[col_status] else ""
            if status == "PENDING":
                ma_nv = r[col_manv].strip() if len(r) > col_manv else ""
                ten = r[col_ten].strip() if len(r) > col_ten else ""
                noi_dung = r[col_noidung] if len(r) > col_noidung else ""
                r_dot = r[col_dotid].strip() if len(r) > col_dotid else dot_id
                pending_items.append({
                    "row_num": row_idx,
                    "ma_nv": ma_nv,
                    "ten": ten,
                    "noi_dung": noi_dung,
                    "dot_id": r_dot
                })

        total_pending = len(pending_items)
        print(f"[{_now_str()}] 📋 Tìm thấy {total_pending} tin PENDING trong RP_Queue.")

        if total_pending == 0:
            svc.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range="_Control_Center!B5:D5",
                valueInputOption="USER_ENTERED",
                body={"values": [["DONE", _now_str(), "0 tin PENDING"]]}
            ).execute()
            append_control_center_log(svc, _now_str(), dot_id, "3. Gửi GTalk", "OK", 0, "Không có tin PENDING")
            sys.exit(0)

        # 4. Gửi mẫu tin đầu tiên cho Admin kiểm duyệt
        first_item = pending_items[0]
        preview_text = (
            f"🔍 *[KIỂM DUYỆT ĐỢT {first_item['dot_id']}] Mẫu tin gửi AM/Trợ lý đầu tiên*\n"
            f"👤 Người nhận mẫu: *{first_item['ten']}* (`{first_item['ma_nv']}`)\n\n"
            f"{first_item['noi_dung']}"
        )
        print(f"[{_now_str()}] 📤 Đang gửi mẫu tin đầu tiên cho Admin ({ADMIN_ID})...")
        send_gtalk_direct(oa_id, oa_token, ADMIN_ID, preview_text)
        time.sleep(1.0)

        # 5. Gửi từng tin trong hàng đợi
        sent_count = 0
        failed_count = 0
        updates = []

        for idx, item in enumerate(pending_items, start=1):
            ma_nv = item["ma_nv"]
            ten = item["ten"]
            noi_dung = item["noi_dung"]
            row_num = item["row_num"]

            if not ma_nv or not ma_nv.isdigit():
                err_msg = "Mã NV không hợp lệ"
                print(f"[{_now_str()}] ({idx}/{total_pending}) ❌ Bỏ qua {ten} — {err_msg}")
                updates.append({
                    "row": row_num,
                    "status": "FAILED",
                    "timestamp_gui": _now_str(),
                    "loi": err_msg
                })
                failed_count += 1
                continue

            print(f"[{_now_str()}] ({idx}/{total_pending}) 🚀 Gửi tới: {ten} ({ma_nv})...")
            ok, res_detail = send_gtalk_direct(oa_id, oa_token, ma_nv, noi_dung)

            if ok:
                sent_count += 1
                updates.append({
                    "row": row_num,
                    "status": "SENT",
                    "timestamp_gui": _now_str(),
                    "loi": ""
                })
                print(f"[{_now_str()}] ({idx}/{total_pending}) ✅ Gửi thành công tới {ten} ({ma_nv})")
            else:
                failed_count += 1
                updates.append({
                    "row": row_num,
                    "status": "FAILED",
                    "timestamp_gui": _now_str(),
                    "loi": str(res_detail)
                })
                print(f"[{_now_str()}] ({idx}/{total_pending}) ❌ Gửi thất bại tới {ten} ({ma_nv}): {res_detail}")

            time.sleep(SLEEP_INTERVAL)

        # 6. Ghi cập nhật trạng thái vào RP_Queue
        print(f"[{_now_str()}] 💾 Đang cập nhật trạng thái {len(updates)} dòng lên RP_Queue...")
        batch_data = []
        for u in updates:
            row_n = u["row"]
            batch_data.append({
                "range": f"RP_Queue!G{row_n}",
                "values": [[u["status"]]]
            })
            batch_data.append({
                "range": f"RP_Queue!I{row_n}:J{row_n}",
                "values": [[u["timestamp_gui"], u["loi"]]]
            })

        if batch_data:
            # Dùng batchUpdate để ghi đồng loạt
            svc.spreadsheets().values().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={
                    "valueInputOption": "USER_ENTERED",
                    "data": batch_data
                }
            ).execute()

        # 7. Ghi B5 = DONE
        end_ts = _now_str()
        summary_msg = f"Đã gửi: {sent_count}/{total_pending} tin (Lỗi: {failed_count})"
        svc.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range="_Control_Center!B5:D5",
            valueInputOption="USER_ENTERED",
            body={"values": [["DONE", end_ts, summary_msg]]}
        ).execute()

        # 8. Ghi Log vào _Control_Center
        log_status = "OK" if failed_count == 0 else "PARTIAL"
        append_control_center_log(svc, end_ts, dot_id, "3. Gửi GTalk", log_status, f"{sent_count}/{total_pending}", summary_msg)

        # 9. Gửi báo cáo tổng kết cho Admin
        admin_summary = (
            f"📊 *[TỔNG KẾT GỬI TIN GTALK — {end_ts}]*\n\n"
            f"• Đợt chạy: *{dot_id}*\n"
            f"• Tổng số tin trong queue: *{total_pending}*\n"
            f"• Gửi thành công: *{sent_count}* ✅\n"
            f"• Thất bại: *{failed_count}* ❌\n\n"
            f"📈 Trạng thái đợt: *{log_status}*\n"
            f"👉 Xem chi tiết tại: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/"
        )
        print(f"[{_now_str()}] 📤 Đang gửi tổng kết cho Admin ({ADMIN_ID})...")
        send_gtalk_direct(oa_id, oa_token, ADMIN_ID, admin_summary)

        print(f"[{_now_str()}] === HOÀN TẤT CHU KỲ GỬI TIN GTALK: {summary_msg} ===")

    except Exception as e:
        err_ts = _now_str()
        err_str = str(e)
        print(f"[{err_ts}] ❌ LỖI HỆ THỐNG TRONG QUÁ TRÌNH GỬI: {err_str}")
        try:
            svc.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID,
                range="_Control_Center!B5:D5",
                valueInputOption="USER_ENTERED",
                body={"values": [["FAILED", err_ts, err_str[:300]]]}
            ).execute()
            append_control_center_log(svc, err_ts, dot_id, "3. Gửi GTalk", "FAILED", 0, err_str)
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
