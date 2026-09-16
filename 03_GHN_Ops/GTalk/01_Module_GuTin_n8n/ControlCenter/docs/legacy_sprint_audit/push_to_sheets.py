import os
import gspread
from google.oauth2.service_account import Credentials

# Cấu hình kết nối Google Sheets
SPREADSHEET_ID = "15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg"
KEY_PATH = r"E:\GHN\AntiGravity\Khua_Ho_Tro\03_GHN_Ops\GTalk\01_Module_GuTin_n8n\ControlCenter_Deploy\ghn-sheets-key.json"

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_file(KEY_PATH, scopes=scope)
client = gspread.authorize(creds)

print("Đang mở Google Sheet...")
sheet = client.open_by_key(SPREADSHEET_ID)

# Danh sách 7 tab chuẩn Lean Template
required_tabs = {
    "00_CONFIG": [
        ["key", "value", "description"],
        ["scheduler_enabled", "TRUE", "Bật/tắt tự động gửi tin nhắn"],
        ["dry_run", "TRUE", "Chế độ giả lập (không gọi API GTalk thật)"],
        ["am_l1_hours", "08:30, 14:00", "Khung giờ gửi L1 cho Area Manager"],
        ["am_l2_hours", "11:00, 16:30", "Khung giờ gửi L2 cho Area Manager"],
        ["vung_l1_hours", "09:00, 15:00", "Khung giờ gửi L1 cho Vùng"],
        ["vung_l2_hours", "11:30, 17:00", "Khung giờ gửi L2 cho Vùng"],
        ["allowed_weekdays", "1,2,3,4,5,6", "Các ngày trong tuần được phép chạy (Thứ 2 - Thứ 6/7)"]
    ],
    "01_RAW_CHI_TIET": [
        ["snapshot_id", "updated_at", "ma_don_hang", "ma_buu_cuc", "trang_thai", "nguoi_xu_ly"],
        ["SNAP_INIT", "2026-09-15 00:00:00", "GHN000000", "SGN000", "Khoi tao", "System"]
    ],
    "02_CO_CAU": [
        ["ma_buu_cuc", "ten_buu_cuc", "area_manager_id", "ten_am", "vung"],
        ["SGN123", "BC Quan 1", "AM001", "Tran Van B", "Mien Nam"],
        ["HAN456", "BC Cau Giay", "AM002", "Le Van C", "Mien Bac"]
    ],
    "03_DATA_ENRICHED": [
        ["enriched_data"],
        ['=ARRAYFORMULA(IF(\'01_RAW_CHI_TIET\'!A2:A="", "", VLOOKUP(\'01_RAW_CHI_TIET\'!D2:D, \'02_CO_CAU\'!A:E, {2,3,4,5}, FALSE)))']
    ],
    "04_RP_SUMMARY": [
        ["RP_AM & RP_VUNG QUERIES"],
        ['=QUERY(\'03_DATA_ENRICHED\'!A:Z, "SELECT Col3, Col4, COUNT(Col1), SUM(Col5) WHERE Col3 IS NOT NULL GROUP BY Col3, Col4 LABEL Col3 \'AM ID\', Col4 \'Ten AM\', COUNT(Col1) \'Tong Don\'", 1)']
    ],
    "05_SEND_QUEUE_LOG": [
        ["queue_id", "snapshot_id", "created_at", "recipient_type", "recipient_id", "message_type", "status", "sent_at", "error"],
        ["Q_INIT", "SNAP_INIT", "2026-09-15 00:00:00", "AM", "AM001", "INIT", "SENT", "2026-09-15 00:00:01", ""]
    ],
    "06_SYSTEM_STATE": [
        ["metric", "value", "description"],
        ["last_scrape", "2026-09-15 00:00:00", "Thời điểm Python cập nhật RAW gần nhất"],
        ["current_snapshot", "SNAP_INIT", "ID snapshot hiện tại"],
        ["raw_row_count", "1", "Tổng số dòng dữ liệu thô"],
        ["formula_ready", "TRUE", "Trạng thái công thức đã tính toán xong không lỗi"],
        ["last_scheduler_tick", "2026-09-15 00:00:00", "Lần chạy Apps Script gần nhất"],
        ["last_error", "", "Lỗi hệ thống gần nhất"]
    ]
}

existing_worksheets = {ws.title: ws for ws in sheet.worksheets()}

for tab_name, rows in required_tabs.items():
    if tab_name in existing_worksheets:
        print(f"Cập nhật tab {tab_name}...")
        ws = existing_worksheets[tab_name]
        ws.clear()
        ws.update(rows)
    else:
        print(f"Tạo mới tab {tab_name}...")
        ws = sheet.add_worksheet(title=tab_name, rows=100, cols=20)
        ws.update(rows)

print("Đã đẩy toàn bộ cấu trúc 7 tab Lean Template lên Google Sheet thành công!")
