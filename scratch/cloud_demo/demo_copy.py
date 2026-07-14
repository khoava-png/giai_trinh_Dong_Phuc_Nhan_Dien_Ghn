"""
Demo: Copy du lieu tu SOURCE (Phase_1) sang DEST (file nhap)
Dung chung cho ca GitHub Actions va Cloud Function
"""
import os, sys
from datetime import datetime, timezone, timedelta

import gspread
from google.oauth2.service_account import Credentials

# Load .env cho local test (GH Actions/Cloud Function se set env truc tiep)
try:
    from dotenv import load_dotenv
    env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    load_dotenv(env_file)
except ImportError:
    pass  # dotenv khong co tren cloud runner

# === CONFIG ===
SOURCE_ID = "10L3suSlF0h-3bWIesdlKiFcGxr19QvVY7URqjOL3zzs"
SOURCE_SHEET = "Phase_1"

DEST_ID = "14aIefWIIstbV8c_5OoxOuMbnlSHTHAUexIx039SAztU"
DEST_SHEET = "Demo_Copy_Phase1"  # Se tao moi

VIETNAM_TZ = timezone(timedelta(hours=7))


def get_client():
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not set in .env or environment")
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds)


def main():
    t0 = datetime.now(VIETNAM_TZ)
    print(f"[{t0:%H:%M:%S}] START: Copy SOURCE -> DEST")

    client = get_client()

    # Step 1: Doc SOURCE
    print("[1/4] Reading SOURCE...")
    src = client.open_by_key(SOURCE_ID)
    ws_src = src.worksheet(SOURCE_SHEET)
    data = ws_src.get_all_values()
    print(f"  Read {len(data)} rows from '{SOURCE_SHEET}'")

    # Step 2: Chuan bi DEST sheet
    print(f"[2/4] Preparing DEST sheet '{DEST_SHEET}'...")
    dst = client.open_by_key(DEST_ID)
    try:
        old = dst.worksheet(DEST_SHEET)
        dst.del_worksheet(old)
    except gspread.exceptions.WorksheetNotFound:
        pass
    ws_dst = dst.add_worksheet(title=DEST_SHEET, rows=max(len(data), 100), cols=26)
    print(f"  Sheet '{DEST_SHEET}' created")

    # Step 3: Ghi du lieu
    print(f"[3/4] Writing {len(data)} rows...")
    ws_dst.update(f"A1:Z{len(data)}", data)
    print("  Done!")

    # Step 4: Format co ban
    print("[4/4] Formatting header...")
    ws_dst.format("A1:Z1", {
        "backgroundColor": {"red": 0.1, "green": 0.3, "blue": 0.5},
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}, "fontSize": 10},
    })
    ws_dst.freeze(rows=2)
    
    # Format row 2 (sub-header) khac mau
    if len(data) > 1:
        ws_dst.format("A2:Z2", {
            "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.95},
            "textFormat": {"bold": True, "fontSize": 9},
        })

    elapsed = (datetime.now(VIETNAM_TZ) - t0).total_seconds()
    print(f"[{datetime.now(VIETNAM_TZ):%H:%M:%S}] DONE! {len(data)} rows in {elapsed:.1f}s")
    print(f"  URL: https://docs.google.com/spreadsheets/d/{DEST_ID}/edit#gid={ws_dst.id}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
