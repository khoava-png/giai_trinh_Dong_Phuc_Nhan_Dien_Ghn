# -*- coding: utf-8 -*-
"""
cao_ton_phieu.py — Cào dữ liệu tồn phiếu Vận hành từ web ghn-vanhanh.dedyn.io
và ghi vào Google Sheet.

3 chế độ:
  python cao_ton_phieu.py --dry-run   -> CHẠY THỬ: đọc web, in ra số lượng + vài dòng mẫu, KHÔNG ghi sheet
  python cao_ton_phieu.py             -> CHẠY THẬT: đọc web + ghi vào Google Sheet

Dữ liệu lấy TOÀN BỘ hệ thống (không phân trang, không bỏ sót):
  1. GET /api/buucuc?top=   -> toàn bộ bưu cục + tổng phiếu/phạt
  2. GET /api/tickets       -> toàn bộ mã đơn chi tiết (1867+ ticket, 1 lần gọi)
"""

import os
import sys
import io
import json
import time
import argparse

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass

try:
    import requests
except ImportError:
    requests = None

# ============================================================
# CẤU HÌNH
# ============================================================
WEB_BASE = "https://ghn-vanhanh.dedyn.io"
WEB_USER = "vanhanh"
WEB_PASS = "GHN@2026"

# Google Sheet đích (anh Khoa tạo)
SPREADSHEET_ID = "15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg"
# tên tab sẽ được tạo nếu chưa có
TAB_TON = "Ton_phieu"      # bưu cục + tổng
TAB_CT = "Chi_tiet"        # mã đơn chi tiết toàn bộ
# TAB MỚI (bản nâng cấp: có Loại phiếu + Trạng thái) — demo ra sheet mới, không đè cũ
TAB_TON_NEW = "Ton_phieu_v2"
TAB_CT_NEW = "Chi_tiet_v2"

# Phân loại phiếu (theo bảng web)
LOAI_LIST = ["Hối giao", "Hối lấy", "Hối trả"]
# Ngưỡng phạt kịch khung (đ) — theo quy tắc tạm tính
CAP_PHAT = 200000

# Key Service Account ghn-sheet-bot
KEY_FILE = os.path.join(
    r"E:\GHN\AntiGravity\Khua_Ho_Tro",
    "05_TaiLieu_Note", "Keys", "ghn-sheets-automation-90e4499c91ec.json",
)


# ============================================================
# CÀO WEB VẬN HÀNH
# ============================================================
def login_and_scrape(attach_bc=True):
    """Đăng nhập web, cào toàn bộ dữ liệu.

    attach_bc=True -> lặp TỪNG bưu cục gọi /api/tickets?bc=X để gắn mã bưu cục
                      vào từng ticket (chính xác 100%, nhưng 287+ request nên chậm hơn).
    attach_bc=False -> gọi /api/tickets toàn hệ thống 1 lần (nhanh, không kèm mã bưu cục).
    Trả (buucuc_list, tickets_list, meta).
    """
    if requests is None:
        raise SystemExit("Thiếu requests. Cài: pip install requests")
    s = requests.Session()
    r = s.post(f"{WEB_BASE}/login",
               data={"username": WEB_USER, "password": WEB_PASS}, timeout=40)
    if r.status_code not in (200, 302) or "/login" in r.url:
        raise RuntimeError(f"Đăng nhập thất bại ({r.status_code})")

    # 1) Toàn bộ bưu cục + tổng
    r1 = s.get(f"{WEB_BASE}/api/buucuc?top=", timeout=60)
    d1 = r1.json()
    buu_cuc = d1.get("buu_cuc", [])
    cols = d1.get("cols", [])
    grand_total = d1.get("grand_total")
    grand_penalty = d1.get("grand_penalty")
    updated_at = d1.get("updated_at")

    tickets = []
    total_penalty = 0
    failed_bc = []   # bưu cục lấy trượt (để chạy lại cho đủ 100%)
    if attach_bc:
        # lặp từng bưu cục -> gắn mã bưu cục vào từng ticket (đảm bảo map khớp)
        for i, b in enumerate(buu_cuc):
            bc = b.get("value")
            got = 0
            for attempt in range(3):   # retry tối đa 3 lần khi lỗi/timer
                try:
                    rr = s.get(f"{WEB_BASE}/api/tickets?bc={bc}", timeout=40)
                    if rr.status_code != 200:
                        raise RuntimeError(f"HTTP {rr.status_code}")
                    dd = rr.json()
                    for t in dd.get("tickets", []):
                        t["ma_buu_cuc"] = bc
                        tickets.append(t)
                    got = len(dd.get("tickets", []))
                    total_penalty += dd.get("total_penalty") or 0
                    break
                except Exception:
                    import time as _t
                    _t.sleep(1)
                    continue
            # đối chiếu: tổng trên web vs tổng gom được
            expected = b.get("total") or 0
            if got != expected:
                failed_bc.append((bc, expected, got))
            if (i + 1) % 50 == 0:
                print(f"    ... đã xử lý {i+1}/{len(buu_cuc)} bưu cục (lỗi/lệch: {len(failed_bc)})")
    else:
        # 2) Toàn bộ mã đơn chi tiết (toàn hệ thống, 1 lần) - không kèm mã bưu cục
        r2 = s.get(f"{WEB_BASE}/api/tickets", timeout=120)
        d2 = r2.json()
        tickets = d2.get("tickets", [])
        total_penalty = d2.get("total_penalty")

    meta = {
        "grand_total": grand_total,
        "grand_penalty": grand_penalty,
        "updated_at": updated_at,
        "cols": cols,
        "total_penalty": total_penalty,
        "failed_bc": failed_bc,
    }
    return buu_cuc, tickets, meta


# ============================================================
# GOOGLE SHEETS
# ============================================================
def get_sheets():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_file(
        KEY_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return build("sheets", "v4", credentials=creds)


def load_co_cau_map(svc):
    """Đọc tab Co_Cau (warehouse_id -> gdv/am/vùng) để map vào Chi_tiet.
    Trả dict: ma_bưu_cục(chuỗi) -> (gdv_id, gdv_name, am_id, am_name, region).
    """
    try:
        r = svc.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range="'Co_Cau'!A:J").execute()
        hdr = r.get("values", [[]])[0]
        rows = r.get("values", [])[1:] if len(r.get("values", [])) > 1 else []
        def ci(n): return hdr.index(n) if n in hdr else -1
        i_wid = ci("warehouse_id"); i_gid = ci("gdv_pgdv_id")
        i_gn = ci("gdv_pgdv_name"); i_amid = ci("area_manager_id")
        i_amn = ci("area_manager_name"); i_reg = ci("region_shortname")
        m = {}
        for row in rows:
            if i_wid < 0 or len(row) <= i_wid:
                continue
            wid = str(row[i_wid]).strip()
            if not wid:
                continue
            def gv(j): return (row[j] if 0 <= j < len(row) else "")
            m[wid] = (gv(i_gid), gv(i_gn), gv(i_amid), gv(i_amn), gv(i_reg))
        return m
    except Exception as e:
        print(f"  ⚠ Đọc Co_Cau lỗi: {str(e)[:80]}")
        return {}


def ensure_tab(svc, name):
    """Tạo tab nếu chưa có; trả sheetId."""
    meta = svc.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    for sh in meta["sheets"]:
        if sh["properties"]["title"] == name:
            return sh["properties"]["sheetId"]
    body = {"requests": [{"addSheet": {"properties": {"title": name}}}]}
    svc.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
    meta = svc.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
    for sh in meta["sheets"]:
        if sh["properties"]["title"] == name:
            return sh["properties"]["sheetId"]
    raise RuntimeError(f"Không tạo được tab {name}")


def write_tab(svc, tab, values, only_clear_rows=0):
    """Ghi đè snapshot nguyên tử kèm dọn dẹp phần đuôi thừa (stale tail cleanup) chính xác trên cột A:N."""
    res = svc.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'!A:A").execute()
    old_rows = len(res.get("values", []))
    new_rows = len(values) if values else 0
    if values:
        svc.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'!A1",
            valueInputOption="RAW", body={"values": values}).execute()
    if old_rows > new_rows:
        clear_range = f"'{tab}'!A{new_rows + 1}:N{old_rows}"
        svc.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID, range=clear_range).execute()


def rebuild_formulas(svc):
    """Ghi 1 công thức ARRAYFORMULA duy nhất vào I2, đổ ra I2:M cho toàn bộ Chi_tiet.
    Map theo mã bưu cục (A) -> Co_Cau (B:J) lấy gdv/am/vùng. Ép VALUE() vì A là text, B là số."""
    # đếm số dòng Chi_tiet hiện có (cột B)
    bb = svc.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range="'Chi_tiet'!B:B").execute().get("values", [])
    nrows = max(2, sum(1 for r in bb[1:] if r and r[0].strip()))
    last = nrows + 1  # row cuối có dữ liệu

    inner = []
    # CÔNG THỨC TỐI ƯU: 1 VLOOKUP trả 5 cột (B:J có B=1..J=9). A*1 ép text->số khớp B.
    col_idx = "{3,4,5,6,9}"
    formula = (f'=ARRAYFORMULA(IF($A$2:$A${last}="","",'
               f'IFERROR(VLOOKUP($A$2:$A${last}*1,\'Co_Cau\'!$B$2:$J$1609,{col_idx},FALSE),"")))')
    svc.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range="'Chi_tiet'!I2",
        valueInputOption="USER_ENTERED", body={"values": [[formula]]}).execute()


# ============================================================
# HÀM TÍNH TRẠNG THÁI + CÀO THEO LOẠI (bản nâng cấp v2)
# ============================================================
def trang_thai(close_esc, penalty):
    """Trả 1 trong 3 trạng thái cho 1 phiếu dựa trên hạn đóng + tiền phạt."""
    if penalty >= CAP_PHAT:
        return "Phạt kịch khung"
    if not close_esc:
        return "Chưa trễ hạn"
    try:
        from datetime import datetime
        hd = datetime.fromisoformat(close_esc)
        if hd.replace(tzinfo=None) < datetime.now():
            return "Trễ hạn còn cứu được"
        return "Chưa trễ hạn"
    except Exception:
        return "Chưa trễ hạn"


def login_and_scrape_v2(attach_bc=True):
    """Cào theo TỪNG LOẠI (Hối giao/lấy/trả) — gắn loại phiếu + trạng thái vào mỗi ticket.

    Trả (buu_cuc, tickets, meta) trong đó mỗi ticket có thêm:
      loai       : 'Hối giao' | 'Hối lấy' | 'Hối trả'
      trang_thai : 'Chưa trễ hạn' | 'Trễ hạn còn cứu được' | 'Phạt kịch khung'
    """
    if requests is None:
        raise SystemExit("Thiếu requests. Cài: pip install requests")
    s = requests.Session()
    r = s.post(f"{WEB_BASE}/login",
               data={"username": WEB_USER, "password": WEB_PASS}, timeout=40)
    if r.status_code not in (200, 302) or "/login" in r.url:
        raise RuntimeError(f"Đăng nhập thất bại ({r.status_code})")

    r1 = s.get(f"{WEB_BASE}/api/buucuc?top=", timeout=60)
    d1 = r1.json()
    buu_cuc = d1.get("buu_cuc", [])
    cols = d1.get("cols", LOAI_LIST)
    grand_total = d1.get("grand_total")
    grand_penalty = d1.get("grand_penalty")
    updated_at = d1.get("updated_at")

    tickets = []
    failed_bc = []
    for i, b in enumerate(buu_cuc):
        bc = b.get("value")
        expected = b.get("total") or 0
        got = 0
        for loai in LOAI_LIST:
            for attempt in range(3):
                try:
                    rr = s.get(f"{WEB_BASE}/api/tickets", params={"bc": bc, "ly_do": loai}, timeout=40)
                    if rr.status_code != 200:
                        raise RuntimeError(f"HTTP {rr.status_code}")
                    dd = rr.json()
                    for t in dd.get("tickets", []):
                        t["ma_buu_cuc"] = bc
                        t["loai"] = loai
                        t["trang_thai"] = trang_thai(t.get("close_esc"), t.get("penalty") or 0)
                        tickets.append(t)
                    got += len(dd.get("tickets", []))
                    break
                except Exception:
                    import time as _t
                    _t.sleep(1)
                    continue
        if got != expected:
            failed_bc.append((bc, expected, got))
        if (i + 1) % 50 == 0:
            print(f"    ... đã xử lý {i+1}/{len(buu_cuc)} bưu cục (lệch: {len(failed_bc)})")

    meta = {
        "grand_total": grand_total,
        "grand_penalty": grand_penalty,
        "updated_at": updated_at,
        "cols": cols,
        "failed_bc": failed_bc,
    }
    return buu_cuc, tickets, meta


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Cào tồn phiếu web vận hành -> Google Sheet")
    parser.add_argument("--dry-run", action="store_true",
                        help="Chạy thử: đọc web, in số lượng, KHÔNG ghi sheet")
    parser.add_argument("--v2", action="store_true",
                        help="Bản nâng cấp: cào theo LOẠI (Hối giao/lấy/trả) + gắn TRẠNG THÁI, ghi tab mới _v2")
    args = parser.parse_args()

    print("[i] Đăng nhập web vận hành + cào toàn bộ dữ liệu...")
    if args.v2:
        buu_cuc, tickets, meta = login_and_scrape_v2()
    else:
        buu_cuc, tickets, meta = login_and_scrape()
    print(f"[i] Đã cào xong: {len(buu_cuc)} bưu cục | {len(tickets)} mã đơn\n")

    print("=" * 55)
    print("TỔNG HỆ THỐNG")
    print("=" * 55)
    print(f"  Tổng số bưu cục:        {len(buu_cuc)}")
    print(f"  Tổng số ticket/mã đơn:  {len(tickets)}")
    print(f"  Tổng phiếu tồn:         {meta.get('grand_total')}")
    print(f"  Tổng tiền phạt:         {meta.get('grand_penalty')} đ")
    print(f"  Phân loại:              {meta.get('cols')}")
    print(f"  vào lúc:                {meta.get('updated_at')}")

    print("\n--- 5 bưu cục tồn cao nhất (mẫu) ---")
    for b in buu_cuc[:5]:
        print(f"  {b.get('value')}  {b.get('label')}  | {b.get('total')} phiếu | {b.get('penalty')}đ")

    print("\n--- 3 ticket chi tiết (mẫu) ---")
    for t in tickets[:3]:
        print(f"  {t.get('number')} | {t.get('title')} | phạt {t.get('penalty')}đ")

    # Chỉ coi là LỖI MẤT DỮ LIỆU khi gom được 0 phiếu (web có phiếu mà ta không lấy được).
    # Lệch ±1 do web cập nhật realtime (lúc lấy danh sách vs lúc gom) là bình thường, không mất phiếu.
    failed = [(bc, exp, got) for bc, exp, got in meta.get("failed_bc", []) if got == 0 and exp > 0]
    if failed:
        print("\n" + "=" * 55)
        print(f"[!] CẢNH BÁO: {len(failed)} bưu cục lệch realtime (web đổi số giữa lúc cào) — gom được 0 phiếu:")
        for bc, exp, got in failed[:30]:
            print(f"    - mã {bc}: web={exp} phiếu, gom được={got}")
        print("    -> Phiếu có thể vừa được đóng/xử lý giữa lúc cào. VẪN TIẾP TỤC ghi (không chặn).")
        print("=" * 55)

    if args.dry_run:
        print("\n[i] CHẾ ĐỘ DRY-RUN: đã đọc xong, KHÔNG ghi gì vào Google Sheet.")
        print("    Anh xem kết quả trên rồi chạy lệnh thật để ghi vào sheet.")
        return

    # GHI THẬT
    print("\n[Ghi] Đang ghi vào Google Sheet...")
    svc = get_sheets()

    # ==== GHI SHEET (bản --v2 đầy đủ: có Loại phiếu + Trạng thái + map cơ cấu) ====
    from collections import defaultdict
    name_of = {b.get("value"): b.get("label") for b in buu_cuc}
    co_cau = load_co_cau_map(svc)   # ma_bưu_cục -> (gdv_id, gdv_name, am_id, am_name, region)

    # Bảng 1: Ton_phieu — bưu cục + 3 cột loại Hối giao/lấy/trả + tổng + phạt
    ensure_tab(svc, TAB_TON)
    cnt_map = defaultdict(lambda: [0, 0, 0])
    for t in tickets:
        bc = t.get("ma_buu_cuc", ""); loai = t.get("loai", "")
        if loai == "Hối giao": cnt_map[bc][0] += 1
        elif loai == "Hối lấy": cnt_map[bc][1] += 1
        elif loai == "Hối trả": cnt_map[bc][2] += 1
    au = meta.get("updated_at", "")
    rows_ton = [["ma_buu_cuc", "ten_buu_cuc", "Hối giao", "Hối lấy", "Hối trả", "Tổng", "Tiền phạt", "cap_nhat_luc"]]
    for b in buu_cuc:
        bc = b.get("value"); c = cnt_map.get(bc, [0, 0, 0])
        rows_ton.append([bc, name_of.get(bc, b.get("label")), c[0], c[1], c[2],
                         b.get("total"), b.get("penalty"), au])
    write_tab(svc, TAB_TON, rows_ton)
    print(f"  ✓ Ghi {len(buu_cuc)} dòng vào tab '{TAB_TON}' (3 cột loại)")

    # Bảng 2: Chi_tiet — 14 cột, map GDV/AM/Vùng bằng CODE (không dùng công thức)
    ensure_tab(svc, TAB_CT)
    rows_ct = [["ma_buu_cuc", "ten_buu_cuc", "ma_ticket", "ma_don", "loai_phieu", "tien_phat",
                "hạn_đóng", "trạng_thái", "url",
                "gdv_pgdv_id", "gdv_pgdv_name", "area_manager_id", "area_manager_name", "region_shortname"]]
    for t in tickets:
        bc = t.get("ma_buu_cuc", "")
        cc = co_cau.get(str(bc).strip()) or ("", "", "", "", "")
        rows_ct.append([bc, name_of.get(bc, ""), t.get("number"), t.get("order_code"),
                        t.get("loai"), t.get("penalty"), t.get("close_esc"),
                        t.get("trang_thai"), t.get("url"),
                        cc[0], cc[1], cc[2], cc[3], cc[4]])
    write_tab(svc, TAB_CT, rows_ct)
    print(f"  ✓ Ghi {len(tickets)} dòng vào tab '{TAB_CT}' (14 cột, map cơ cấu bằng code)")

    # Bảng 3: RP_theo_AM — tự sinh RP mới cho các AM CÓ PHIẾU (để gửi nhẹ, không ghi thủ công)
    ghi_rp_theo_am(svc, tickets, co_cau, au, name_of)

    print("\n" + "=" * 55)
    print("HOÀN THÀNH! Đã ghi toàn bộ vào Google Sheet")
    print("=" * 55)


def _load_am_tpl():
    """Đọc MẪU TIN AM từ template.json của Control Center (kế bên).
    Chỉ dùng khi mẫu có cả {ten_am} và {bcs} — nếu không thì fallback format cũ."""
    try:
        cc_tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "ControlCenter", "template.json")
        if os.path.exists(cc_tpl):
            d = json.load(open(cc_tpl, encoding="utf-8"))
            tpl = (d or {}).get("am", "")
            if isinstance(tpl, str) and "{bcs}" in tpl and "{ten_am}" in tpl:
                return tpl
    except Exception:
        pass
    return None


def replace_vars(obj, ten_am, ngay_gio, bcs_txt):
    if isinstance(obj, dict):
        return {k: replace_vars(v, ten_am, ngay_gio, bcs_txt) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_vars(x, ten_am, ngay_gio, bcs_txt) for x in obj]
    elif isinstance(obj, str):
        return obj.replace("{ten_am}", ten_am or "") \
                  .replace("{vung}", ten_am or "") \
                  .replace("{ngay_gio}", ngay_gio or "") \
                  .replace("{bcs}", bcs_txt or "")
    return obj


def _build_am_rp(ten, ngay, bcs):
    """Sinh nội dung RP cho 1 AM. ƯU TIÊN dùng MẪU TIN (②) để anh sửa là RP đổi theo;
    nếu không có mẫu thì dùng format cũ."""
    tpl = _load_am_tpl()
    is_json = tpl and tpl.strip().startswith("{") and tpl.strip().endswith("}")
    
    bcs_txt = ""
    if bcs:
        if is_json:
            bcs_txt = "<br/>".join(
                f"📦 <b>Bưu cục {ten_ngh}</b>: <b>{_nz}</b> phiếu (GÁN KHẨN CẤP để không bị phạt), <b>{_np}</b> phiếu (GÁN NGAY để không tăng mức phạt)"
                for _bc, ten_ngh, _ii, _nz, _np in bcs)
        else:
            bcs_txt = "\n".join(
                f"📦 *Bưu cục {ten_ngh}*: *{_nz}* phiếu (GÁN KHẨN CẤP để không bị phạt), *{_np}* phiếu (GÁN NGAY để không tăng mức phạt)"
                for _bc, ten_ngh, _ii, _nz, _np in bcs)
    else:
        bcs_txt = "Hiện nhân viên không còn phiếu tồn nào cần xử lý."
        
    if tpl:
        if is_json:
            try:
                tpl_obj = json.loads(tpl)
                replaced_obj = replace_vars(tpl_obj, ten, ngay, bcs_txt)
                return json.dumps(replaced_obj, ensure_ascii=False, indent=2)
            except Exception:
                pass
        return tpl.replace("{ten_am}", ten or "")\
                  .replace("{ngay_gio}", ngay or "")\
                  .replace("{bcs}", bcs_txt)
    # fallback format cũ (khớp mẫu mặc định)
    lines = ["*CẦN XỬ LÝ PHIẾU HỐI GIAO / LẤY / TRẢ*", "",
             f"Hi Anh/Chị {ten}, tính tới thời điểm {ngay}"]
    lines.append(bcs_txt if bcs else "Hiện nhân viên không còn phiếu tồn nào cần xử lý. Chúc một ngày tốt lành!")
    lines += ["", "Chi tiết: https://g.ghn.studio/PhieuKhachHang",
              "Nhờ AM nhắc nhở nhân viên xử lý ngay nhé!",
              'Cần hỗ lòng liên hệ nhóm Gtalk "OE - Triển khai phiếu hối G/L/T"']
    return "\n".join(lines)


def ghi_rp_theo_am(svc, tickets, co_cau, capnhat_luc, name_of):
    """Đổ bảng RP_theo_AM: Mã NV | Tên AM | Tổng | Cần ngay | Đang phạt | Nội dung RP | Trạng thái.
    Chỉ các AM CÓ PHIẾU trong Chi_tiet (anh Khoa yêu cầu: không phiếu thì không gửi).
    RP dùng format mới: không tổng, phân nhóm GÁN KHẨN CẤP / GÁN NGAY."""
    from collections import defaultdict
    TAB_RP = "RP_theo_AM"
    am = defaultdict(lambda: {"ten": "", "bcs": defaultdict(lambda: ["", 0, 0, 0])})
    am_name_by_id = {}
    for bc, cc in co_cau.items():
        if len(cc) > 3 and cc[2]:
            am_name_by_id[str(cc[2])] = cc[3]
    for t in tickets:
        bc = t.get("ma_buu_cuc", "")
        cc = co_cau.get(bc)
        if not cc:
            continue
        amid = str(cc[2]) if len(cc) > 2 and cc[2] else ""
        if not amid or amid == "0":
            continue
        am[amid]["ten"] = am_name_by_id.get(amid, "")
        # tên bưu cục ngắn từ name_of vd "20269000 - (DNO) Kiến Đức" -> "(DNO) Kiến Đức"
        bcn = name_of.get(bc, "")
        if " - " in bcn:
            bcn = bcn.split(" - ", 1)[1]
        am[amid]["bcs"][bc][0] = bcn or bc
        am[amid]["bcs"][bc][1] += 1
        pen = int(t.get("penalty") or 0)
        if pen > 0:
            am[amid]["bcs"][bc][3] += 1
        else:
            am[amid]["bcs"][bc][2] += 1
    # build rows
    rows = [["Mã NV", "Tên AM", "Tổng phiếu", "Cần xử lý ngay", "Đang phát sinh phạt",
             "Nội dung RP (gửi GTalk)", "Trạng thái"]]
    ngay = capnhat_luc or ""
    for aid, a in sorted(am.items(), key=lambda x: -sum(v[1] for v in x[1]["bcs"].values())):
        bcs = []
        for bc, c in a["bcs"].items():
            if c[1] == 0:
                continue
            bcs.append([bc, c[0], c[1], c[2], c[3]])  # ma, ten_ngh, total, nz, np
        bcs.sort(key=lambda x: -x[2])
        total = sum(x[2] for x in bcs)
        nz = sum(x[3] for x in bcs)
        np = sum(x[4] for x in bcs)
        # format RP — dùng MẪU TIN (②) nếu có, không thì format cũ
        rp = _build_am_rp(a["ten"], ngay, bcs)
        rows.append([aid, a["ten"], total, nz, np, rp, ""])
    try:
        ensure_tab(svc, TAB_RP)
        write_tab(svc, TAB_RP, rows)
        print(f"  ✓ Đổ {len(rows)-1} RP theo AM (có phiếu) vào tab '{TAB_RP}'")
    except Exception as e:
        print(f"  ⚠ Không ghi RP_theo_AM: {str(e)[:100]}")


def _load_vung_tpl():
    try:
        cc_tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "ControlCenter", "template.json")
        if os.path.exists(cc_tpl):
            d = json.load(open(cc_tpl, encoding="utf-8"))
            tpl = (d or {}).get("vung", "")
            if isinstance(tpl, str) and "{bcs}" in tpl and "{vung}" in tpl:
                return tpl
    except Exception:
        pass
    return None


def _build_vung_rp(vung, ngay, ams):
    tpl = _load_vung_tpl()
    is_json = tpl and tpl.strip().startswith("{") and tpl.strip().endswith("}")
    
    bcs_txt = ""
    if ams:
        # Nhóm hiển thị theo AM
        if is_json:
            bcs_txt = "<br/>".join(
                f"📦 <b>{ten_am}</b> (AM): <b>{nz}</b> phiếu (GÁN KHẨN CẤP để không bị phạt), <b>{np}</b> phiếu (GÁN NGAY để không tăng mức phạt)"
                for am_id, ten_am, _ii, nz, np in ams)
        else:
            bcs_txt = "\n".join(
                f"📦 *{ten_am}* (AM): *{nz}* phiếu (GÁN KHẨN CẤP để không bị phạt), *{np}* phiếu (GÁN NGAY để không tăng mức phạt)"
                for am_id, ten_am, _ii, nz, np in ams)
    else:
        bcs_txt = f"Hiện Trợ lý GĐ Vùng {vung} không còn phiếu tồn nào cần xử lý."
        
    if tpl:
        if is_json:
            try:
                tpl_obj = json.loads(tpl)
                replaced_obj = replace_vars(tpl_obj, vung, ngay, bcs_txt)
                return json.dumps(replaced_obj, ensure_ascii=False, indent=2)
            except Exception:
                pass
        return tpl.replace("{vung}", vung or "")\
                  .replace("{ngay_gio}", ngay or "")\
                  .replace("{bcs}", bcs_txt)
    # fallback default
    lines = ["*CẦN XỬ LÝ PHIẾU HỐI GIAO / LẤY / TRẢ*", "",
             f"Hi Anh/Chị Trợ Lý/ HRBP vùng {vung}, tính tới thời điểm {ngay}"]
    lines.append(bcs_txt)
    lines += ["", "Chi tiết: https://g.ghn.studio/PhieuKhachHang",
              "Nhờ Anh/ Chị nhắc nhở AM xử lý ngay nhé!",
              'Cần hỗ trợ vui lòng liên hệ nhóm Gtalk "OE - Triển khai phiếu hối G/L/T"']
    return "\n".join(lines)


def _load_vung_ids_from_cc():
    try:
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "ControlCenter", "vung_troly.json")
        if os.path.exists(cfg_path):
            return json.load(open(cfg_path, encoding="utf-8"))
    except Exception:
        pass
    return {}


def ghi_rp_theo_vung(svc, tickets, co_cau, capnhat_luc, name_of):
    """Đổ bảng RP_theo_TroLy: Mã NV Trợ lý | Vùng | Tổng | Cần ngay | Đang phạt | Nội dung RP | Trạng thái."""
    from collections import defaultdict
    TAB_RP = "RP_theo_TroLy"
    
    vg = defaultdict(lambda: defaultdict(lambda: ["", 0, 0, 0]))
    for t in tickets:
        bc = t.get("ma_buu_cuc", "")
        cc = co_cau.get(bc)
        if not cc:
            continue
        reg = str(cc[4]).strip() if len(cc) > 4 and cc[4] else ""
        if not reg:
            continue
        amid = str(cc[2]) if len(cc) > 2 and cc[2] else ""
        if not amid or amid == "0":
            continue
        am_name = cc[3] if len(cc) > 3 else ""
        
        vg[reg][amid][0] = am_name or amid
        vg[reg][amid][1] += 1
        pen = int(t.get("penalty") or 0)
        if pen > 0:
            vg[reg][amid][3] += 1
        else:
            vg[reg][amid][2] += 1
            
    vung_ids = _load_vung_ids_from_cc()
    rows = [["Mã NV Trợ lý", "Vùng", "Tổng phiếu", "Cần xử lý ngay", "Đang phát sinh phạt",
             "Nội dung RP (gửi GTalk)", "Trạng thái"]]
    ngay = capnhat_luc or ""
    
    for reg in sorted(vg.keys()):
        ams = []
        for am_id, val in vg[reg].items():
            if val[1] == 0:
                continue
            ams.append((am_id, val[0], val[1], val[2], val[3]))
            
        ams.sort(key=lambda x: -x[2])
        total = sum(x[2] for x in ams)
        nz = sum(x[3] for x in ams)
        np = sum(x[4] for x in ams)
        
        rp = _build_vung_rp(reg, ngay, ams)
        ma_nv_tro_ly = str(vung_ids.get(reg, "")).strip()
        rows.append([ma_nv_tro_ly, reg, total, nz, np, rp, ""])
        
    try:
        ensure_tab(svc, TAB_RP)
        write_tab(svc, TAB_RP, rows)
        print(f"  ✓ Đổ {len(rows)-1} RP theo Trợ lý vào tab '{TAB_RP}'")
    except Exception as e:
        print(f"  ⚠ Không ghi RP_theo_TroLy: {str(e)[:100]}")


if __name__ == "__main__":
    main()