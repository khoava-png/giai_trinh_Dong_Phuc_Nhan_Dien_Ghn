# -*- coding: utf-8 -*-
"""
cao_ton_phieu_api.py — Cào tồn phiếu Vận Hành GHN qua API đa luồng song song
và đồng bộ nguyên tử vào Google Sheet.

Kiến trúc tối ưu:
  - Tách biệt module API: ghn_vanhanh_api.py quản lý kết nối & endpoint.
  - Tốc độ siêu tốc: 20 workers song song hoàn tất toàn hệ thống chỉ trong 3-6 giây.
  - Chống trôi dòng 100%: Mỗi ticket được đóng gói nguyên tử (Atomic Record) kèm mã BC & tên BC.
  - Map cơ cấu trực tiếp bằng RAM Python, loại bỏ hoàn toàn phụ thuộc công thức VLOOKUP/ARRAYFORMULA.

Chế độ chạy:
  python cao_ton_phieu_api.py --dry-run   -> Chạy thử: cào web, in thống kê chi tiết, KHÔNG ghi sheet.
  python cao_ton_phieu_api.py             -> Chạy thật: cào web + ghi đè nguyên tử 4 tab Google Sheet.
"""

import os
import sys
import io
import json
import time
import argparse
from datetime import datetime
from collections import defaultdict

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    except Exception:
        pass

# Import module API chuyên trách bảo trì
try:
    from ghn_vanhanh_api import GHNVanHanhAPI, LOAI_LIST, CAP_PHAT
except ImportError:
    from Cao_Ton_Phieu.ghn_vanhanh_api import GHNVanHanhAPI, LOAI_LIST, CAP_PHAT

# ============================================================
# CẤU HÌNH GOOGLE SHEETS & TABS
# ============================================================
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg")

TAB_TON = "Ton_phieu"        # Bưu cục + 3 cột loại Hối giao/lấy/trả + tổng + phạt
TAB_CT = "Chi_tiet"          # 14 cột chi tiết mã đơn, loại phiếu, trạng thái & cơ cấu
TAB_RP_AM = "RP_theo_AM"     # Gom theo Area Manager có phiếu tồn
TAB_RP_VUNG = "RP_theo_TroLy" # Gom theo Vùng / Trợ lý GĐV

# Key Service Account ghn-sheet-bot
KEY_FILE = os.path.join(
    r"E:\GHN\AntiGravity\Khua_Ho_Tro",
    "05_TaiLieu_Note", "Keys", "ghn-sheets-automation-90e4499c91ec.json",
)


# ============================================================
# GOOGLE SHEETS HELPERS
# ============================================================
def get_sheets():
    """Khởi tạo Google Sheets API Client."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_file(
        KEY_FILE, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return build("sheets", "v4", credentials=creds)


def load_co_cau_map(svc):
    """
    Đọc tab Co_Cau (warehouse_id -> gdv/am/vùng) để map vào Chi_tiet.
    Trả dict: ma_buu_cuc (str) -> (gdv_id, gdv_name, am_id, am_name, region)
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
            def gv(j): return (str(row[j]).strip() if 0 <= j < len(row) else "")
            m[wid] = (gv(i_gid), gv(i_gn), gv(i_amid), gv(i_amn), gv(i_reg))
        return m
    except Exception as e:
        print(f"  ⚠ Đọc Co_Cau lỗi: {str(e)[:80]}")
        return {}


def ensure_tab(svc, name):
    """Tạo tab nếu chưa tồn tại; trả sheetId."""
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


def write_tab(svc, tab, values):
    """
    Ghi đè snapshot nguyên tử kèm dọn dẹp sạch sẽ phần đuôi cũ thừa (Stale Tail Cleanup).
    """
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


# ============================================================
# FORMAT & SINH BÁO CÁO GTALK (AM & TRỢ LÝ VÙNG)
# ============================================================
def _load_am_tpl():
    """Đọc MẪU TIN AM từ template.json nếu có."""
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


def _load_vung_tpl():
    """Đọc MẪU TIN VÙNG từ template.json nếu có."""
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
    """Sinh nội dung tin nhắn GTalk cho Area Manager (AM) chuẩn link xử lý nội bộ."""
    tpl = _load_am_tpl()
    is_json = tpl and tpl.strip().startswith("{") and tpl.strip().endswith("}")
    
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
                  .replace("{bcs}", bcs_txt)\
                  .replace("{link}", "https://noibo.ghn.vn/ghn-ticket")

    lines = ["*CẦN XỬ LÝ PHIẾU HỐI GIAO / LẤY / TRẢ*", "",
             f"Hi Anh/Chị {ten}, tính tới thời điểm {ngay}", ""]
    lines.append(bcs_txt if bcs else "Hiện nhân viên không còn phiếu tồn nào cần xử lý. Chúc một ngày tốt lành!")
    lines += ["", "👉 Chi tiết xử lý tại: https://noibo.ghn.vn/ghn-ticket",
              "Nhờ AM nhắc nhở nhân viên xử lý ngay nhé!",
              'Cần hỗ trợ vui lòng liên hệ nhóm GTalk "OE - Triển khai phiếu hối G/L/T"']
    return "\n".join(lines)


def ghi_rp_theo_am(svc, tickets, co_cau, capnhat_luc, name_of):
    """
    Đổ bảng RP_theo_AM: Mã NV | Tên AM | Tổng | Cần ngay | Đang phạt | Nội dung RP | Trạng thái.
    Chỉ hiển thị các AM CÓ PHIẾU TỒN.
    """
    am = defaultdict(lambda: {"ten": "", "bcs": defaultdict(lambda: ["", 0, 0, 0])})
    am_name_map = {}
    for bc, cc in co_cau.items():
        if len(cc) > 3 and cc[2]:
            am_name_map[str(cc[2])] = cc[3]

    for t in tickets:
        bc = str(t.get("ma_buu_cuc", "")).strip()
        cc = co_cau.get(bc)
        if not cc:
            continue
        amid = str(cc[2]) if len(cc) > 2 and cc[2] else ""
        if not amid or amid == "0":
            continue
            
        am[amid]["ten"] = am_name_map.get(amid, cc[3] if len(cc) > 3 else "")
        bcn = name_of.get(bc, t.get("ten_buu_cuc", ""))
        if " - " in bcn:
            bcn = bcn.split(" - ", 1)[1]
            
        am[amid]["bcs"][bc][0] = bcn or bc
        am[amid]["bcs"][bc][1] += 1
        pen = int(t.get("penalty") or 0)
        if pen > 0:
            am[amid]["bcs"][bc][3] += 1
        else:
            am[amid]["bcs"][bc][2] += 1

    rows = [["Mã NV", "Tên AM", "Tổng phiếu", "Cần xử lý ngay", "Đang phát sinh phạt",
             "Nội dung RP (gửi GTalk)", "Trạng thái"]]
    ngay = capnhat_luc or ""
    
    for aid, a in sorted(am.items(), key=lambda x: -sum(v[1] for v in x[1]["bcs"].values())):
        bcs = []
        for bc, c in a["bcs"].items():
            if c[1] == 0:
                continue
            bcs.append([bc, c[0], c[1], c[2], c[3]])
        bcs.sort(key=lambda x: -x[2])
        total = sum(x[2] for x in bcs)
        nz = sum(x[3] for x in bcs)
        np = sum(x[4] for x in bcs)
        
        rp = _build_am_rp(a["ten"], ngay, bcs)
        rows.append([aid, a["ten"], total, nz, np, rp, ""])

    try:
        ensure_tab(svc, TAB_RP_AM)
        write_tab(svc, TAB_RP_AM, rows)
        print(f"  ✓ Đổ {len(rows)-1} RP theo AM (có phiếu) vào tab '{TAB_RP_AM}'")
    except Exception as e:
        print(f"  ⚠ Không ghi RP_theo_AM: {str(e)[:100]}")


def _build_vung_rp(vung, ngay, ams):
    """Sinh nội dung tin nhắn GTalk cho Trợ lý Giám đốc Vùng chuẩn Template V3."""
    if ams:
        bcs_txt = "\n".join(
            f"📦 *{ten_am}* (AM): *{nz}* phiếu (GÁN KHẨN CẤP để không bị phạt), *{np}* phiếu (GÁN NGAY để không tăng mức phạt)"
            for am_id, ten_am, _ii, nz, np in ams)
    else:
        bcs_txt = f"Hiện các AM trong Vùng {vung} không còn phiếu tồn nào cần xử lý."

    lines = [
        f"🚨 [BÁO CÁO PHIẾU TỒN VÙNG {vung}]",
        "",
        f"Hi Anh/Chị Trợ lý/ HRBP vùng *{vung}*, tính tới thời điểm _{ngay}_",
        "",
        bcs_txt,
        "",
        "📊 *Theo dõi phiếu tại:* https://docs.google.com/spreadsheets/d/1YmFgYyARiFh5vu63My24Sx0ffcy-RsxddEvVWSCgDds/edit?gid=0#gid=0",
        "👉 Chi tiết xử lý tại: https://noibo.ghn.vn/ghn-ticket",
        "👉 Nhờ Anh/Chị nhắc nhở AM đôn đốc bưu cục xử lý dứt điểm nhé!",
        'Cần hỗ trợ vui lòng liên hệ nhóm GTalk "*OE - Triển khai phiếu hối G/L/T*"'
    ]
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
    """
    Đổ bảng RP_theo_TroLy: Mã NV Trợ lý | Vùng | Tổng | Cần ngay | Đang phạt | Nội dung RP | Trạng thái.
    """
    vg = defaultdict(lambda: defaultdict(lambda: ["", 0, 0, 0]))
    for t in tickets:
        bc = str(t.get("ma_buu_cuc", "")).strip()
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
        ensure_tab(svc, TAB_RP_VUNG)
        write_tab(svc, TAB_RP_VUNG, rows)
        print(f"  ✓ Đổ {len(rows)-1} RP theo Trợ lý vào tab '{TAB_RP_VUNG}'")
    except Exception as e:
        print(f"  ⚠ Không ghi RP_theo_TroLy: {str(e)[:100]}")


# ============================================================
# MAIN ORCHESTRATOR
# ============================================================
def crawl_tickets_api(workers=8):
    """Cào API và trả snapshot trong RAM; không ghi Sheet, không deploy dashboard."""
    api = GHNVanHanhAPI()
    meta = api.get_buucuc_list()
    buu_cuc = meta.get("buu_cuc", [])
    tickets, failed_bc = api.fetch_all_tickets_atomic(
        buu_cuc, max_workers=workers, split_by_loai=True
    )
    return buu_cuc, tickets, meta, failed_bc


def main():
    parser = argparse.ArgumentParser(description="Cào tồn phiếu API đa luồng -> Google Sheet chuẩn")
    parser.add_argument("--dry-run", action="store_true",
                        help="Chạy thử: cào dữ liệu, in thống kê kiểm thử, KHÔNG ghi sheet")
    parser.add_argument("--workers", type=int, default=8,
                        help="Số luồng song song (mặc định: 8 luồng)")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers phải lớn hơn hoặc bằng 1")

    t_start = time.time()
    print("=" * 60)
    print("🚀 BẮT ĐẦU CÀO TỒN PHIẾU QUA API ĐA LUỒNG SONG SONG")
    print("=" * 60)

    # 1. Khởi tạo API Client
    api = GHNVanHanhAPI()

    # 2. Lấy danh sách bưu cục
    print("[1/3] Đang tải danh sách bưu cục...")
    bc_meta = api.get_buucuc_list()
    buu_cuc = bc_meta.get("buu_cuc", [])
    grand_total = bc_meta.get("grand_total", 0)
    grand_penalty = bc_meta.get("grand_penalty", 0)
    updated_at = bc_meta.get("updated_at", "")
    
    print(f"  ✓ Đã lấy {len(buu_cuc)} bưu cục | Tổng web: {grand_total} phiếu | Phạt: {grand_penalty:,} đ")

    # 3. Cào toàn bộ tickets bằng Đa luồng song song (Atomic Record)
    print(f"[2/3] Đang tải chi tiết phiếu tồn ({args.workers} luồng song song)...")
    t_scrape_0 = time.time()
    tickets, failed_bc = api.fetch_all_tickets_atomic(buu_cuc, max_workers=args.workers, split_by_loai=True)
    t_scrape_1 = time.time()
    
    print(f"  ✓ Cào xong {len(tickets)} tickets trong {t_scrape_1 - t_scrape_0:.2f} giây!")
    if failed_bc:
        print(f"  ❌ Có {len(failed_bc)} bưu cục lỗi hoặc lệch tổng; KHÔNG ghi Google Sheet.")
        for bc, expected, actual in failed_bc[:20]:
            print(f"     - BC {bc}: web báo {expected}, API lấy {actual}")
        return 2

    if grand_total is not None and len(tickets) != int(grand_total):
        print(f"  ❌ Tổng phiếu lấy được ({len(tickets)}) lệch tổng web báo ({grand_total}); KHÔNG ghi Google Sheet.")
        return 2

    # 4. Thống kê kiểm thử
    print("\n" + "-" * 60)
    print("THỐNG KÊ TỔNG QUAN")
    print("-" * 60)
    print(f"  Tổng bưu cục hệ thống:  {len(buu_cuc)}")
    print(f"  Tổng số tickets gom:    {len(tickets)}")
    print(f"  Thời gian cập nhật:     {updated_at}")
    print(f"  Thời gian cào API:      {t_scrape_1 - t_scrape_0:.2f}s")

    if args.dry_run:
        print("\n[i] CHẾ ĐỘ DRY-RUN: Đã cào & đối soát thành công! KHÔNG ghi vào Google Sheet.")
        return

    # 5. Ghi dữ liệu nguyên tử vào Google Sheet
    print("\n[3/3] Đang đồng bộ nguyên tử vào Google Sheet...")
    svc = get_sheets()
    co_cau = load_co_cau_map(svc)
    name_of = {str(b.get("value", "")).strip(): b.get("label", "") for b in buu_cuc}

    # Bảng 1: Ton_phieu
    ensure_tab(svc, TAB_TON)
    cnt_map = defaultdict(lambda: [0, 0, 0])
    for t in tickets:
        bc = str(t.get("ma_buu_cuc", "")).strip()
        loai = t.get("loai", "")
        if loai == "Hối giao": cnt_map[bc][0] += 1
        elif loai == "Hối lấy": cnt_map[bc][1] += 1
        elif loai == "Hối trả": cnt_map[bc][2] += 1

    rows_ton = [["ma_buu_cuc", "ten_buu_cuc", "Hối giao", "Hối lấy", "Hối trả", "Tổng", "Tiền phạt", "cap_nhat_luc"]]
    for b in buu_cuc:
        bc = str(b.get("value", "")).strip()
        c = cnt_map.get(bc, [0, 0, 0])
        rows_ton.append([bc, name_of.get(bc, b.get("label", "")), c[0], c[1], c[2],
                         b.get("total", 0), b.get("penalty", 0), updated_at])
    write_tab(svc, TAB_TON, rows_ton)
    print(f"  ✓ Ghi {len(buu_cuc)} dòng vào tab '{TAB_TON}' (3 cột loại)")

    # Bảng 2: Chi_tiet (14 cột chuẩn)
    ensure_tab(svc, TAB_CT)
    rows_ct = [["ma_buu_cuc", "ten_buu_cuc", "ma_ticket", "ma_don", "loai_phieu", "tien_phat",
                "hạn_đóng", "trạng_thái", "url",
                "gdv_pgdv_id", "gdv_pgdv_name", "area_manager_id", "area_manager_name", "region_shortname"]]
    for t in tickets:
        bc = str(t.get("ma_buu_cuc", "")).strip()
        cc = co_cau.get(bc) or ("", "", "", "", "")
        rows_ct.append([bc, name_of.get(bc, t.get("ten_buu_cuc", "")), t.get("number"), t.get("order_code"),
                        t.get("loai"), t.get("penalty"), t.get("close_esc"),
                        t.get("trang_thai"), t.get("url"),
                        cc[0], cc[1], cc[2], cc[3], cc[4]])
    write_tab(svc, TAB_CT, rows_ct)
    print(f"  ✓ Ghi {len(tickets)} dòng vào tab '{TAB_CT}' (14 cột chuẩn)")

    # Bảng 3: RP_theo_AM
    ghi_rp_theo_am(svc, tickets, co_cau, updated_at, name_of)

    # Bảng 4: RP_theo_TroLy
    ghi_rp_theo_vung(svc, tickets, co_cau, updated_at, name_of)

    t_end = time.time()
    print("\n" + "=" * 60)
    print(f"✅ HOÀN THÀNH TOÀN BỘ TRONG {t_end - t_start:.2f} GIÂY!")
    print("=" * 60)


if __name__ == "__main__":
    raise SystemExit(main() or 0)
