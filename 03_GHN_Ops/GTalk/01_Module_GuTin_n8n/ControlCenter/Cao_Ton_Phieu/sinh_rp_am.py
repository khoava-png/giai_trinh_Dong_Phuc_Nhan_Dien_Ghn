# -*- coding: utf-8 -*-
"""
sinh_rp_am.py — Sinh báo cáo RP "CẦN XỬ LÝ PHIẾU HỐI GIAO/LẤY/TRẢ" theo từng AM
và ghi vào Sheet1 (bảng gửi GTalk) để chạy gtalk_bulk_sender.py.

- Đọc tab Chi_tiet (đã có Loại phiếu + Trạng thái + area_manager_id/name)
- Gom theo AM (mã = area_manager_id = Mã NV gửi GTalk)
- Phiếu KHÔNG có AM (id trống/0) -> BỎ QUA theo yêu cầu
- Sinh RP theo template, 1 dòng/AM trong Sheet1: Mã NV + Nội dung

Cách chạy:
  python sinh_rp_am.py --dry-run   # xem trước các AM + RP mẫu, KHÔNG ghi
  python sinh_rp_am.py             # ghi nội dung RP xuống Sheet1 (cột E 'Nội dung' để trống)
"""
import os, sys, io, argparse
from datetime import datetime
from collections import defaultdict, Counter

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass

WORKSPACE = r"E:\GHN\AntiGravity\Khua_Ho_Tro"
SPREADSHEET_ID = "15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg"
TAB_SRC = "Chi_tiet"      # nguồn: phiếu tồn (có loại + trạng thái + AM)
TAB_DST = "Sheet1"        # đích: bảng gửi GTalk
KEY_FILE = os.path.join(WORKSPACE, "05_TaiLieu_Note", "Keys",
                        "ghn-sheets-automation-90e4499c91ec.json")
LINK_XL = "https://g.ghn.studio/PhieuKhachHang"


def _sheets():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_file(
        KEY_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return build("sheets", "v4", credentials=creds)


def build_rp(ten_am, ngaygio, tt_counts, bc_counts):
    """Sinh nội dung RP theo template của anh Khoa."""
    def line(so, label):
        s = f"{so} {label}\n"
        if so:
            s += "(" + ", ".join(
                f"{bc} :{n}" for bc, n in
                sorted(bc_counts[label].items(), key=lambda x: -x[1])) + ")\n"
        return s
    lines = [
        f"CẦN XỬ LÝ PHIẾU HỐI GIAO/LẤY/TRẢ — AM {ten_am}",
        f"Dear sếp {ten_am},",
        f"tính tới thời điểm {ngaygio}",
        "",
        "Nhà mình còn",
        line(tt_counts.get("Chưa trễ hạn", 0), "Chưa trễ hạn"),
        line(tt_counts.get("Trễ hạn còn cứu được", 0), "Trễ hạn còn cứu được"),
        line(tt_counts.get("Phạt kịch khung", 0), "Phạt kịch khung"),
        f"chi tiết vui lòng xử lý tại {LINK_XL}",
        "",
        "Nhờ Sếp nhắc liền nhân viên xử lý nhé!",
        'Cần hỗ trợ vui lòng liên hệ nhóm Gtalk "OE - Triển khai phiếu hối giao lấy trả"',
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Xem trước RP mẫu, KHÔNG ghi sheet")
    args = parser.parse_args()

    svc = _sheets()
    r = svc.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"'{TAB_SRC}'!A:N").execute()
    hdr = r["values"][0]; rows = r["values"][1:]

    def ci(name): return hdr.index(name) if name in hdr else -1
    def gv(row, i): return (row[i] if i >= 0 and len(row) > i else "")
    i_amid, i_am, i_tt, i_bc, i_bcn = (
        ci("area_manager_id"), ci("area_manager_name"), ci("trạng_thái"),
        ci("ma_buu_cuc"), ci("ten_buu_cuc"))

    am = defaultdict(lambda: {"ten": "", "tt": Counter(), "bc_tt": defaultdict(Counter)})
    skipped = 0
    for row in rows:
        amid = gv(row, i_amid) or "0"
        if amid in ("", "0"):
            skipped += 1
            continue
        tt = gv(row, i_tt) or "Chưa trễ hạn"
        bc = gv(row, i_bc) or gv(row, i_bcn) or "?"
        a = am[amid]
        a["ten"] = gv(row, i_am) or ""
        a["tt"][tt] += 1
        a["bc_tt"][tt][bc] += 1

    ngaygio = datetime.now().strftime("%d/%m/%Y %H:%M")

    print(f"[i] Gom theo AM: {len(am)} AM | phiếu bỏ qua (thiếu AM): {skipped}")
    print("=" * 60)

    # Xem trước mẫu 3 AM lớn nhất
    top = sorted(am.items(), key=lambda x: -sum(x[1]["tt"].values()))[:4]
    for aid, a in top:
        total = sum(a["tt"].values())
        print(f"\n--- AM {aid} ({a['ten']}) — {total} phiếu ---")
        rp = build_rp(a["ten"], ngaygio, a["tt"], a["bc_tt"])
        print(rp)
        print("-" * 60)

    if args.dry_run:
        print(f"\n[i] DRY-RUN: xem {len(am)} AM phía trên — chưa ghi gì vào Sheet1.")
        return

    # Ghi xuống Sheet1: Mã NV = amid, Nội dung = RP (chỉ ghi cột A và E, để trống trạng thái)
    # Đọc Sheet1 hiện có trước
    rd = svc.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=f"'{TAB_DST}'!A:E").execute()
    dhdr = rd.get("values", [[]])[0]
    drows = rd.get("values", [])[1:]
    di_nv = dhdr.index("Mã NV") if "Mã NV" in dhdr else 0
    di_nd = dhdr.index("Nội dung") if "Nội dung" in dhdr else 1

    # Xóa nội dung cũ cột Nội dung (E) toàn bộ
    svc.spreadsheets().values().batchClear(
        spreadsheetId=SPREADSHEET_ID,
        body={"ranges": [f"'{TAB_DST}'!E2:E1000"]}).execute()

    updates = []
    written = 0
    # Ghi từng AM: dùng dòng trống đầu tiên, hoặc nối vào
    start = 500
    for i, (aid, a) in enumerate(am.items()):
        rp = build_rp(a["ten"], ngaygio, a["tt"], a["bc_tt"])
        b = 500 + i + 1  # dùng vùng 501 trở đi để không đụng dữ liệu anh đang có
        updates.append({"range": f"'{TAB_DST}'!A{b}:B{b}",
                        "values": [[aid, rp]]})
        written += 1
    if updates:
        svc.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"valueInputOption": "RAW", "data": updates}).execute()
    print(f"\n[i] Đã ghi {written} AM xuống Sheet1 (vùng A{B+1}:B{B+written+1}). Chạy gtalk_bulk_sender.py để gửi.")


if __name__ == "__main__":
    main()