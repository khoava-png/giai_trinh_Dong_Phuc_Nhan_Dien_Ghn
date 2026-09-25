# -*- coding: utf-8 -*-
"""
scripts/deploy_dashboard.py — Đọc dữ liệu từ Google Sheets, sinh file HTML và chuẩn bị thư mục _site để deploy Cloudflare Pages.

Luồng:
1. Đọc Google Sheet tab Chi_tiet, Ton_phieu, RP_theo_AM.
2. Build data dictionary chứa toàn bộ tồn phiếu realtime.
3. Thay thế `var RAW = {...};` trong file template dashboard/index.html.
4. Xuất file index.html và copy toàn bộ assets (video, image) vào thư mục `_site/`.
"""

import os
import sys
import io
import re
import json
import shutil
from datetime import datetime

# UTF-8 encoding fix for Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

from google.oauth2 import service_account
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")
TEMPLATE_HTML = os.path.join(DASHBOARD_DIR, "index.html")
SITE_DIR = os.path.join(BASE_DIR, "_site")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg")


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


def read_sheet_tab(svc, tab_name):
    """Đọc dữ liệu 1 tab, trả về header + rows."""
    try:
        res = svc.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"'{tab_name}'!A:ZZ"
        ).execute()
        values = res.get("values", [])
        if not values:
            return [], []
        return values[0], values[1:]
    except Exception as e:
        print(f"[WARN] Không đọc được tab '{tab_name}': {e}")
        return [], []


def pad_row(row, length):
    while len(row) < length:
        row.append("")
    return row


def build_dashboard_data(ch_hdr, ch_rows, t_hdr, t_rows, rp_hdr, rp_rows):
    """
    Delegate build logic trực tiếp sang dashboard_sync._build_raw để đảm bảo
    chỉ duy nhất 1 single source of truth cho dashboard build logic.
    """
    import dashboard_sync as dsync
    cached = {
        "hdr": ch_hdr,
        "rows": ch_rows,
        "ton_hdr": t_hdr,
        "ton_rows": t_rows,
        "source_updated_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }
    # Validate và build
    raw_html = dsync._build_raw(cached)
    m = re.search(r"var RAW = (\{.*?\});", raw_html, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    return {}


def replace_raw_in_html(template_html_content, data_obj):
    """Thay thế `var RAW = {...};` trong file HTML."""
    new_json = json.dumps(data_obj, ensure_ascii=False, separators=(",", ":"))
    pattern = re.compile(r'var RAW = \{.*?\};', re.DOTALL)
    new_html, count = pattern.subn('var RAW = ' + new_json + ';', template_html_content, count=1)
    if count == 0:
        raise RuntimeError("Không tìm thấy biến 'var RAW = {...};' trong file template!")
    return new_html


def main():
    print("=== BẮT ĐẦU BUILD DASHBOARD TĨNH CHO CLOUDFLARE PAGES ===")
    if not os.path.exists(TEMPLATE_HTML):
        raise FileNotFoundError(f"Không tìm thấy file template dashboard: {TEMPLATE_HTML}")

    svc = get_sheets_service()

    # Đọc dữ liệu các tab
    ch_hdr, ch_rows = read_sheet_tab(svc, "Chi_tiet")
    t_hdr, t_rows = read_sheet_tab(svc, "Ton_phieu")
    rp_hdr, rp_rows = read_sheet_tab(svc, "RP_theo_AM")

    print(f"✓ Đã đọc {len(ch_rows)} dòng Chi_tiet, {len(t_rows)} dòng Ton_phieu, {len(rp_rows)} dòng RP_theo_AM")

    # Xây dựng cấu trúc dữ liệu
    data_obj = build_dashboard_data(ch_hdr, ch_rows, t_hdr, t_rows, rp_hdr, rp_rows)
    print(f"✓ Đã tổng hợp dữ liệu: {data_obj['total']} phiếu tồn, tổng phạt: {data_obj['total_phat']:,}đ")

    # Đọc template và chèn data
    with open(TEMPLATE_HTML, "r", encoding="utf-8") as f:
        template_content = f.read()

    rendered_html = replace_raw_in_html(template_content, data_obj)

    # Chuẩn bị thư mục _site
    os.makedirs(SITE_DIR, exist_ok=True)

    # Ghi index.html vào _site
    site_index_path = os.path.join(SITE_DIR, "index.html")
    with open(site_index_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)
    print(f"✓ Đã xuất file HTML tĩnh -> {site_index_path}")

    # Copy các file media/assets từ dashboard/ vào _site/
    for item in os.listdir(DASHBOARD_DIR):
        if item.endswith((".mp4", ".png", ".jpg", ".jpeg", ".svg", ".css", ".js", ".ico", ".webm")):
            src = os.path.join(DASHBOARD_DIR, item)
            dst = os.path.join(SITE_DIR, item)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                print(f"  + Đã copy asset: {item}")

    print("=== HOÀN TẤT BUILD THƯ MỤC _site SẴN SÀNG CHO WRANGLER DEPLOY ===")


if __name__ == "__main__":
    main()
