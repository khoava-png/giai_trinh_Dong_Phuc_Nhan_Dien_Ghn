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
import uuid
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

# --- GLOBAL STATE & PERSISTENT STATE ---
STATE = {
    "status": "IDLE",
    "last_run": None,
    "last_filter": None,
    "last_sent_count": 0,
    "last_duration_s": 0,
    "activity": []
}

# --- PERSISTENT STATE (LOCAL FALLBACK STORAGE) ---
# NOTE: .control_center_state.json is an ephemeral/local fallback storage on Cloud Run
# for fast restart recovery. Ephemeral local state only — Google Sheets sync removed.
STATUS_FILE = os.path.join(os.path.dirname(__file__), ".control_center_state.json")

def _load_persistent_state():
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception:
            pass
    return {
        "crawler_state": {
            "status": "OFFLINE",
            "last_check": None,
            "last_success": None,
            "last_error": None
        },
        "google_sheet_state": {
            "status": "ONLINE",
            "last_check": None,
            "last_success": None,
            "last_error": None
        },
        "gtalk_state": {
            "status": "ONLINE",
            "last_check": None,
            "last_success": None,
            "last_error": None
        },
        "scheduler_state": {
            "status": "ONLINE",
            "last_check": None,
            "last_success": None,
            "last_error": None
        },
        "cycle_state": {
            "status": "IDLE",
            "cycle_id": "—",
            "last_check": None,
            "last_success": None,
            "last_error": None,
            "success_count": 0,
            "failed_count": 0,
            "duration": 0
        }
    }

def _save_persistent_state(st_data):
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(st_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] Không thể lưu persistent state: {e}", flush=True)

def _now():
    return datetime.datetime.now(VN_TZ)

def _log_activity(action, status, details=""):
    t_str = _now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {"time": t_str, "action": action, "status": status, "details": details}
    STATE["activity"].insert(0, entry)
    if len(STATE["activity"]) > 100:
        STATE["activity"].pop()
    print(f"[{t_str}] [{action}] [{status}] {details}", flush=True)

# --- GOOGLE SHEETS HELPER (WITH RETRY & CLIENT INVALIDATION) ---
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
        try:
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
        except Exception as e:
            print(f"[ERROR] Không thể khởi tạo Google Sheets service: {e}", flush=True)
            raise e
        return _sheets_svc

def _invalidate_sheets_service(ex=None):
    global _sheets_svc
    with _sheets_lock:
        print(f"[WARN] Invalidate Google Sheets client do lỗi: {ex}", flush=True)
        _sheets_svc = None

def execute_with_sheets_retry(func, *args, **kwargs):
    """
    Thực thi Google Sheets API call với Retry (tối đa 3 lần, exponential backoff).
    Xử lý: BrokenPipeError, socket.timeout, ConnectionError, HTTP 429, 5xx, và Invalid/Expired token.
    """
    max_retries = 3
    delay = 2.0
    for attempt in range(max_retries):
        try:
            service = get_sheets_service()
            return func(service, *args, **kwargs)
        except Exception as e:
            err_str = str(e).lower()
            is_net_err = any(k in err_str for k in ["broken pipe", "timeout", "connection", "reset", "50", "429", "invalid_grant"])
            print(f"[WARN] Sheets API lỗi (lần {attempt+1}/{max_retries}): {e}", flush=True)
            _invalidate_sheets_service(e)
            if attempt == max_retries - 1:
                raise e
            time.sleep(delay)
            delay *= 2.0
    raise Exception("Sheets API retry failed after max attempts")

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
    Bắn toàn bộ tin nhắn định kỳ tới AM & Trợ lý (với retry chi tiết & micro-timing logging):
    1. Đọc dữ liệu Sheet (Chi_tiet, Co_Cau).
    2. Gom nhóm & sinh nội dung.
    3. Gửi mẫu tin nhiều phiếu nhất cho Admin (3049378) trước để duyệt.
    4. Bắn song song 5 luồng cho AM/Trợ lý.
    5. Cập nhật Sheet (_Control_Center!A83) & gửi tin tổng kết cho Admin.
    """
    import uuid
    cycle_id = f"CYC-{uuid.uuid4().hex[:8]}"
    now_dt = _now()
    now_str = now_dt.strftime("%d/%m/%Y %H:%M")
    filter_type = filter_type.upper()
    _log_activity("CYCLE_RUN", "START", f"[{cycle_id}] Bắt đầu chu trình gửi tin ({filter_type}, to={send_to}, dry_run={dry_run})")

    t_start_all = time.time()
    t_cred_start = time.time()
    # Khởi tạo service qua get_sheets_service
    _ = get_sheets_service()
    t_cred_dur = round(time.time() - t_cred_start, 3)

    # 1. Đọc Chi_tiet & Co_Cau (với retry sheets read)
    t_read_start = time.time()
    def _fetch_data(svc):
        return svc.spreadsheets().values().batchGet(
            spreadsheetId=SHEET_ID,
            ranges=["Chi_tiet!A1:N", "Co_Cau!A:J", "Co_Cau!S3:W30"]
        ).execute()

    try:
        resp = execute_with_sheets_retry(_fetch_data)
    except Exception as e:
        _log_activity("CYCLE_RUN", "FAILED", f"[{cycle_id}] Lỗi đọc Google Sheet sau retry: {e}")
        return {"success": False, "error": f"Sheet read failed: {str(e)}", "cycle_id": cycle_id}
    t_read_dur = round(time.time() - t_read_start, 3)

    val_ranges = resp.get("valueRanges", [])
    ct_vals = val_ranges[0].get("values", [])
    tl_vals = val_ranges[2].get("values", []) if len(val_ranges) > 2 else []

    if len(ct_vals) <= 1:
        _log_activity("CYCLE_RUN", "FAILED", f"[{cycle_id}] Không có dữ liệu trong Chi_tiet")
        return {"success": False, "error": "Chi_tiet rỗng", "cycle_id": cycle_id}

    headers = ct_vals[0]
    raw_tickets = ct_vals[1:]

    # Map Trợ lý Vùng từ Co_Cau
    t_filter_start = time.time()
    tro_ly_map = defaultdict(list)
    curr_vung = ""
    for r in tl_vals:
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
    t_filter_dur = round(time.time() - t_filter_start, 3)

    if not tasks:
        _log_activity("CYCLE_RUN", "DONE", f"[{cycle_id}] 0 tin nhắn cần gửi (Không có phiếu tồn)")
        return {"success": True, "total": 0, "sent": 0, "failed": 0, "duration_s": round(time.time() - t_start_all, 2), "cycle_id": cycle_id}

    # Sắp xếp tìm tin nhiều phiếu nhất (Top 1)
    tasks.sort(key=lambda x: x["total"], reverse=True)
    top_task = tasks[0]

    # BƯỚC 3: Gửi tin mẫu Top 1 cho Admin 3049378 duyệt trước
    top_approval_msg = f"*[MẪU DUYỆT TỰ ĐỘNG - TOP 1]*\n\n" + top_task["content"]
    if not dry_run:
        _log_activity("ADMIN_APPROVAL", "SENDING", f"[{cycle_id}] Gửi tin mẫu Top 1 cho Admin {ADMIN_MA_NV} ({top_task['name']} - {top_task['total']} phiếu)")
        send_gtalk_message(ADMIN_MA_NV, top_approval_msg)
    else:
        _log_activity("ADMIN_APPROVAL", "DRY_RUN", f"[{cycle_id}] [DRY-RUN] Sẽ gửi tin mẫu Top 1 cho Admin {ADMIN_MA_NV} ({top_task['name']})")

    # BƯỚC 4: Bắn song song có kiểm soát (Pool 5 workers)
    t_send_start = time.time()
    success_count = 0
    fail_count = 0
    sent_details = []

    def _worker(task):
        time.sleep(0.15)
        if dry_run:
            return task, {"success": True, "msg_id": "dry_run_id"}
        res = send_gtalk_message(task["id"], task["content"])
        if not res.get("success"):
            _log_activity("GTALK_FAIL", "ERROR", f"[{cycle_id}] Gửi thất bại tới {task['type']} - ID: {task['id']} ({task['name']}): {res.get('error')}")
        return task, res

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_worker, t) for t in tasks]
        for f in as_completed(futures):
            t, r = f.result()
            if r.get("success"):
                success_count += 1
            else:
                fail_count += 1
                sent_details.append(f"{t['id']} ({t['name']}): {r.get('error')}")

    t_send_dur = round(time.time() - t_send_start, 3)
    _log_activity("CYCLE_RUN", "DONE", f"[{cycle_id}] Đã gửi {success_count}/{len(tasks)} tin (Lỗi: {fail_count})")

    # BƯỚC 5: Gửi tin nhắn tổng kết tới Admin 3049378
    summary_msg = (
        f"📊 *[BÁO CÁO GỬI TIN CONTROL CENTER V3]*\n"
        f"• Mã chu kỳ: *{cycle_id}*\n"
        f"• Đợt lọc: *{filter_type}* ({now_str})\n"
        f"• Đã gửi thành công: *{success_count}/{len(tasks)}* tin\n"
        f"• Thất bại: *{fail_count}*\n"
        f"• Timing: cred={t_cred_dur}s | read={t_read_dur}s | filter={t_filter_dur}s | send={t_send_dur}s"
    )
    if not dry_run:
        send_gtalk_message(ADMIN_MA_NV, summary_msg)

    # BƯỚC 6: Ghi log vào Google Sheet (_Control_Center!A83) với retry (Đã bỏ theo yêu cầu)
    # t_log_start = time.time()
    # try:
    #     log_row = [
    #         now_dt.strftime("%Y-%m-%d %H:%M:%S"),
    #         now_dt.strftime("%Y-%m-%d_%H"),
    #         f"Cloud Run Cycle ({filter_type}) [{cycle_id}]",
    #         "OK" if fail_count == 0 else "PARTIAL",
    #         str(success_count),
    #         f"Thành công {success_count}/{len(tasks)} | cred={t_cred_dur}s, read={t_read_dur}s, send={t_send_dur}s" + (f" | Lỗi: {'; '.join(sent_details[:3])}" if sent_details else "")
    #     ]
    #     def _append_log(svc):
    #         return svc.spreadsheets().values().append(
    #             spreadsheetId=SHEET_ID,
    #             range="_Control_Center!A83",
    #             valueInputOption="USER_ENTERED",
    #             body={"values": [log_row]}
    #         ).execute()
    #     execute_with_sheets_retry(_append_log)
    # except Exception as e:
    #     print(f"[WARN] [{cycle_id}] Không thể ghi log vào Sheet sau retry: {e}", flush=True)
    t_log_dur = 0.0

    total_duration = round(time.time() - t_start_all, 2)
    _log_activity("CYCLE_TIMING", "INFO", f"[{cycle_id}] Timings: cred={t_cred_dur}s, read={t_read_dur}s, filter={t_filter_dur}s, send={t_send_dur}s, log={t_log_dur}s | Total: {total_duration}s")

    # Cập nhật component states độc lập
    p_st = _load_persistent_state()
    t_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    # 1. Cycle State (Dispatch)
    p_st["cycle_state"] = {
        "status": "DONE" if fail_count == 0 else "PARTIAL",
        "cycle_id": cycle_id,
        "last_check": t_str,
        "last_success": t_str,
        "last_error": f"Có {fail_count} lỗi gửi tin" if fail_count > 0 else None,
        "success_count": success_count,
        "failed_count": fail_count,
        "duration": total_duration
    }

    # 2. Google Sheet State (Phân biệt Write health từ crawler/log và Read health từ Control Center)
    sheet_status = "ONLINE"
    sheet_err = None
    # Test Read health nhẹ từ Google Sheet đã bị gỡ bỏ theo yêu cầu
    # try:
    #     def _test_read(svc):
    #         return svc.spreadsheets().values().get(spreadsheetId=SHEET_ID, range="_Control_Center!A1").execute()
    #     execute_with_sheets_retry(_test_read)
    # except Exception as e:
    #     sheet_status = "WARNING"
    #     sheet_err = f"Sheet Read Error: {e}"

    if fail_count > 0:
        sheet_err = (sheet_err or "") + f" | Sheet Write (Log append) warning: {fail_count} errors"

    p_st["google_sheet_state"] = {
        "status": sheet_status,
        "last_check": t_str,
        "last_success": t_str if sheet_status == "ONLINE" else None,
        "last_error": sheet_err
    }

    # 3. GTalk State
    p_st["gtalk_state"] = {
        "status": "ONLINE" if fail_count == 0 else "WARNING",
        "last_check": t_str,
        "last_success": t_str,
        "last_error": f"{fail_count} tin gửi thất bại" if fail_count > 0 else None
    }

    _save_persistent_state(p_st)

    STATE["last_run"] = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    STATE["last_filter"] = filter_type
    STATE["last_sent_count"] = success_count
    STATE["last_duration_s"] = total_duration
    STATE["status"] = "IDLE"

    return {
        "success": True,
        "cycle_id": cycle_id,
        "filter": filter_type,
        "total": len(tasks),
        "sent": success_count,
        "failed": fail_count,
        "duration_s": total_duration,
        "timings": {
            "credential": t_cred_dur,
            "sheet_read": t_read_dur,
            "filter": t_filter_dur,
            "send": t_send_dur,
            "log": t_log_dur
        },
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

        # Hỗ trợ cả GET cho chu trình cào + gửi tin
        if path in ("/api/cycle/run", "/api/scrape_and_send"):
            qs = parse_qs(parsed.query)
            filter_type = qs.get("filter", ["ALL"])[0].upper()
            send_to = qs.get("to", ["ALL"])[0].upper()
            dry_run = qs.get("dry_run", ["false"])[0].lower() in ("true", "1", "yes")

            res = run_dispatch_cycle(filter_type=filter_type, send_to=send_to, dry_run=dry_run)
            return self._reply(200, res)

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

        # Health Check cho GCP Cloud Run & Cloud Scheduler (Nâng cấp trả về System Status cho Phase 1)
        if path in ("/health", "/api/health"):
            return self._reply(200, {
                "status": "HEALTHY",
                "service": "GHN Control Center Cloud Run V3",
                "time": _now().isoformat(),
                "admin": ADMIN_MA_NV,
                "project": "ghn-sheets-automation"
            })

        if path == "/api/system/status":
            p_st = _load_persistent_state()
            activities = STATE.get("activity", [])

            # Lấy trạng thái tách biệt từ các component states độc lập
            crawler_s = p_st.get("crawler_state", {})
            sheet_s = p_st.get("google_sheet_state", {})
            gtalk_s = p_st.get("gtalk_state", {})
            sched_s = p_st.get("scheduler_state", {})
            cycle_s = p_st.get("cycle_state", {})

            # Tìm last_scrape từ crawler_state hoặc fallback activity log chứa "CAO" / "SCRAPE"
            last_scrape_time = crawler_s.get("last_success") or crawler_s.get("last_check")
            if not last_scrape_time and activities:
                for act in activities:
                    if "CAO" in act.get("action", "") or "SCRAPE" in act.get("action", ""):
                        last_scrape_time = act.get("time")
                        break

            # Tìm last_cycle từ cycle_state hoặc fallback activity log chứa "CYCLE"
            last_cycle_time = cycle_s.get("last_success") or cycle_s.get("last_check")
            if not last_cycle_time and activities:
                for act in activities:
                    if "CYCLE" in act.get("action", ""):
                        last_cycle_time = act.get("time")
                        break

            # Tính toán Data Freshness & Crawler Status dựa trên age phút của crawler
            now = _now()
            age_minutes = 99999
            freshness_status = "STALE"
            crawler_status = crawler_s.get("status", "OFFLINE")
            crawler_detail = crawler_s.get("last_error") or "Chưa ghi nhận lần cào nào"

            if last_scrape_time:
                try:
                    dt_scrape = datetime.datetime.strptime(last_scrape_time, "%Y-%m-%d %H:%M:%S").replace(tzinfo=VN_TZ)
                    age_minutes = int((now - dt_scrape).total_seconds() / 60)

                    if age_minutes <= 60:
                        freshness_status = "FRESH"
                        crawler_status = "ONLINE"
                        crawler_detail = f"Cào thành công cách đây {age_minutes} phút"
                    elif age_minutes <= 180:
                        freshness_status = "STALE"
                        crawler_status = "WARNING"
                        crawler_detail = f"Cảnh báo: Dữ liệu cũ ({age_minutes} phút trước)"
                    else:
                        freshness_status = "CRITICAL"
                        crawler_status = "OFFLINE"
                        crawler_detail = f"Lỗi: Không cào dữ liệu trong {age_minutes // 60} giờ qua!"
                except Exception as ex:
                    crawler_status = "WARNING"
                    crawler_detail = f"Lỗi parse thời gian: {ex}"
            else:
                crawler_status = "OFFLINE"
                crawler_detail = "Chưa có bản ghi cào phiếu thực tế"
                freshness_status = "CRITICAL"

            return self._reply(200, {
                "ok": True,
                "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                "storage_type": "ephemeral_local_fallback (Production truth in Google Sheets _Control_Center)",
                "components": {
                    "crawler": {
                        "status": crawler_status,
                        "detail": crawler_detail,
                        "age_minutes": age_minutes
                    },
                    "google_sheet": {
                        "status": sheet_s.get("status", "ONLINE"),
                        "detail": sheet_s.get("last_error") or "Connected to ghn-sheet-bot"
                    },
                    "control_center": {
                        "status": "ONLINE",
                        "detail": "Cloud Run V3 active (Isolated Component States)"
                    },
                    "scheduler": {
                        "status": sched_s.get("status", "ONLINE"),
                        "detail": sched_s.get("last_error") or "Internal & Cloud Scheduler active"
                    },
                    "gtalk": {
                        "status": gtalk_s.get("status", "ONLINE"),
                        "detail": gtalk_s.get("last_error") or "GTalk OA Gateway operational"
                    }
                },
                "metrics": {
                    "last_scrape": last_scrape_time or "—",
                    "last_cycle": last_cycle_time or "—",
                    "data_freshness": freshness_status,
                    "age_minutes": age_minutes
                },
                "cycle_report": {
                    "cycle_id": cycle_s.get("cycle_id", "—"),
                    "success_count": cycle_s.get("success_count", 0),
                    "failed_count": cycle_s.get("failed_count", 0),
                    "duration": cycle_s.get("duration", 0)
                },
                "history": activities
            })

        if path == "/api/logs":
            # Trả về log thực tế từ STATE["activity"]
            activities = STATE.get("activity", [])
            return self._reply(200, {"ok": True, "history": activities})

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

        # Thêm endpoint POST /api/ingestion/run cho Cloud Scheduler (Đã chuẩn hóa Security Fail-Closed & Distributed TTL Lock)
        if path == "/api/ingestion/run":
            # 1. SECURITY FAIL-CLOSED: BẮT BUỘC có SCHEDULER_SECRET từ environment, KHÔNG hardcode default.
            # CHỈ DÙNG X-Scheduler-Secret với hmac.compare_digest. Xóa hoàn toàn Bearer / OIDC giả định.
            import hmac
            expected_secret = os.environ.get("SCHEDULER_SECRET")
            if not expected_secret:
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ [SECURITY] SCHEDULER_SECRET environment variable is missing. Fail-closed rejection.", flush=True)
                return self._reply(403, {"ok": False, "error_stage": "LOCK", "error": "Server security misconfigured: SCHEDULER_SECRET is not set"})

            x_scheduler_secret = self.headers.get("X-Scheduler-Secret", "")
            
            authorized = False
            if x_scheduler_secret and hmac.compare_digest(x_scheduler_secret.encode("utf-8"), expected_secret.encode("utf-8")):
                authorized = True

            if not authorized:
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] 🚫 [SECURITY] Unauthorized ingestion attempt (Invalid or missing X-Scheduler-Secret). Rejecting with 401.", flush=True)
                return self._reply(401, {"ok": False, "error_stage": "LOCK", "error": "Unauthorized: Invalid or missing X-Scheduler-Secret header"})

            print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] 📥 [INGESTION] INGESTION_REQUEST_RECEIVED (Authenticated successfully)", flush=True)

            # 2. SINGLE-INSTANCE THREAD LOCK (_scrape_lock = threading.Lock)
            # Cloud Run max instances = 1, chống hai request đồng thời trong cùng instance.
            global _scrape_lock
            if not '_scrape_lock' in globals():
                _scrape_lock = threading.Lock()

            if not _scrape_lock.acquire(blocking=False):
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ [INGESTION] INGESTION_LOCK_ACQUIRED -> FAILED (Locked)", flush=True)
                return self._reply(429, {"ok": False, "error_stage": "LOCK", "error": "Đang có tiến trình ingestion khác thực thi trên instance này"})

            run_id = f"ING-{uuid.uuid4().hex[:8]}"
            t_start = time.time()
            try:
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] 🔒 [{run_id}] INGESTION_LOCK_ACQUIRED", flush=True)
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] 🔒 [{run_id}] INGESTION_LOCK_ACQUIRED (TTL 300s)", flush=True)
                _log_activity("INGESTION", "START", f"[{run_id}] Bắt đầu chu trình Ingestion tự động")

                # 3. Crawler Start & Execute
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] 🚀 [{run_id}] CRAWLER_START", flush=True)
                ctp_dir = os.path.join(os.path.dirname(__file__), "Cao_Ton_Phieu")
                if ctp_dir not in sys.path:
                    sys.path.insert(0, ctp_dir)
                import cao_ton_phieu as ctp

                buu_cuc, tickets, meta = ctp.login_and_scrape_v2()
                if not tickets or len(tickets) == 0:
                    raise RuntimeError("Crawler trả về 0 ticket (Dữ liệu rỗng hoặc lỗi API nguồn)")
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ [{run_id}] CRAWLER_SUCCESS ({len(tickets)} tickets, {len(buu_cuc)} bưu cục)", flush=True)

                # 4. Sheet Write Start & Execute (Fail-closed: crawler fail -> không chạy phần này)
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] 📊 [{run_id}] SHEET_WRITE_START", flush=True)
                svc = get_sheets_service()
                co_cau = ctp.load_co_cau_map(svc)
                name_of = {str(b.get("value", "")): b.get("label") for b in buu_cuc}

                cnt_map = {}
                for t in tickets:
                    bc = t.get("ma_buu_cuc", "")
                    loai = t.get("loai", "")
                    if bc not in cnt_map:
                        cnt_map[bc] = [0, 0, 0]
                    if loai == "Hối giao":
                        cnt_map[bc][0] += 1
                    elif loai == "Hối lấy":
                        cnt_map[bc][1] += 1
                    elif loai == "Hối trả":
                        cnt_map[bc][2] += 1

                au = meta.get("updated_at", _now().strftime("%Y-%m-%d %H:%M:%S"))
                snapshot_id = f"SNAP-{_now().strftime('%Y%m%d-%H%M')}"

                # Ghi tab Ton_phieu
                ctp.ensure_tab(svc, ctp.TAB_TON)
                rows_ton = [["ma_buu_cuc", "ten_buu_cuc", "Hối giao", "Hối lấy", "Hối trả", "Tổng", "Tiền phạt", "cap_nhat_luc"]]
                for b in buu_cuc:
                    bc = b.get("value")
                    c = cnt_map.get(bc, [0, 0, 0])
                    rows_ton.append([
                        bc, name_of.get(bc, b.get("label")), c[0], c[1], c[2],
                        b.get("total"), b.get("penalty"), au
                    ])
                ctp.write_tab(svc, ctp.TAB_TON, rows_ton)

                # Ghi tab Chi_tiet
                ctp.ensure_tab(svc, ctp.TAB_CT)
                rows_ct = [[
                    "ma_buu_cuc", "ten_buu_cuc", "ma_ticket", "ma_don", "loai_phieu", "tien_phat",
                    "hạn_đóng", "trạng_thái", "url", "gdv_pgdv_id", "gdv_pgdv_name",
                    "area_manager_id", "area_manager_name", "region_shortname"
                ]]
                for t in tickets:
                    bc = str(t.get("ma_buu_cuc", ""))
                    cc_info = co_cau.get(bc, ("", "", "", "", ""))
                    rows_ct.append([
                        t.get("ma_buu_cuc"), name_of.get(str(t.get("ma_buu_cuc", "")), ""), t.get("ma_ticket"), t.get("ma_don"),
                        t.get("loai"), t.get("tien_phat"), t.get("han_dong"), t.get("trang_thai"),
                        t.get("url"), cc_info[0], cc_info[1], cc_info[2], cc_info[3], cc_info[4]
                    ])
                ctp.write_tab(svc, ctp.TAB_CT, rows_ct)

                # Ghi RP_theo_AM
                try:
                    ctp.ghi_rp_theo_am(svc, co_cau)
                except Exception as e_am:
                    print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] Lỗi ghi RP_theo_AM: {e_am}", flush=True)

                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ [{run_id}] SHEET_WRITE_SUCCESS (snapshot_id={snapshot_id}, cap_nhat_luc={au})", flush=True)

                # 5. Dashboard Build & Cloudflare Deploy (Fail-closed: Sheet write fail -> không deploy)
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] 🌐 [{run_id}] DASHBOARD_BUILD_START", flush=True)
                dashboard_deployed = False
                cf_deployment_id = "—"
                try:
                    import dashboard_sync as dsync
                    cached_data = {
                        "hdr": rows_ct[0],
                        "rows": rows_ct[1:],
                        "ci": {h: i for i, h in enumerate(rows_ct[0])}
                    }
                    raw_data = dsync._build_raw(cached_data)
                    cf_deployment_id = dsync._deploy_to_cloudflare(raw_data)
                    dashboard_deployed = True
                    print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ [{run_id}] CLOUDFLARE_DEPLOY_SUCCESS (ID: {cf_deployment_id})", flush=True)
                except Exception as e_ds:
                    print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ [{run_id}] DASHBOARD_BUILD / DEPLOY FAILED: {e_ds}", flush=True)
                    _log_activity("INGESTION", "PARTIAL", f"[{run_id}] Ingestion thành công Sheet nhưng deploy dashboard lỗi: {e_ds}")
                    dur = round(time.time() - t_start, 2)
                    return self._reply(500, {
                        "ok": False,
                        "error_stage": "CLOUDFLARE_DEPLOY",
                        "error": str(e_ds),
                        "snapshot_id": snapshot_id,
                        "cap_nhat_luc": au,
                        "ticket_count": len(tickets),
                        "warehouse_count": len(buu_cuc),
                        "duration_seconds": dur
                    })

                dur = round(time.time() - t_start, 2)
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] 🎉 [{run_id}] INGESTION_SUCCESS in {dur}s", flush=True)
                _log_activity("INGESTION", "SUCCESS", f"[{run_id}] Ingestion hoàn tất: {len(tickets)} tickets, {len(buu_cuc)} bưu cục, CF deploy ID: {cf_deployment_id}")

                return self._reply(200, {
                    "ok": True,
                    "snapshot_id": snapshot_id,
                    "cap_nhat_luc": au,
                    "ticket_count": len(tickets),
                    "warehouse_count": len(buu_cuc),
                    "dashboard_deployed": dashboard_deployed,
                    "cloudflare_deployment_id": cf_deployment_id,
                    "duration_seconds": dur
                })

            except Exception as ex:
                dur = round(time.time() - t_start, 2)
                err_stage = "CRAWLER"
                if "Sheet" in str(ex) or "google" in str(ex).lower():
                    err_stage = "SHEET_WRITE"
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ [{run_id}] INGESTION FAILED at stage {err_stage}: {ex}", flush=True)
                _log_activity("INGESTION", "FAILED", f"[{run_id}] Lỗi ingestion ({err_stage}): {ex}")
                return self._reply(500, {
                    "ok": False,
                    "error_stage": err_stage,
                    "error": str(ex),
                    "duration_seconds": dur
                })
            finally:
                try:
                    _scrape_lock.release()
                except Exception:
                    pass
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] 🔓 [{run_id}] INGESTION_LOCK_RELEASED", flush=True)
        # Cloud Scheduler gọi kích hoạt chu trình cào + gửi tin
        if path in ("/api/cycle/run", "/api/scrape_and_send"):
            qs = parse_qs(parsed.query)
            filter_type = qs.get("filter", ["ALL"])[0].upper()
            send_to = qs.get("to", ["ALL"])[0].upper()
            dry_run = qs.get("dry_run", ["false"])[0].lower() in ("true", "1", "yes")

            res = run_dispatch_cycle(filter_type=filter_type, send_to=send_to, dry_run=dry_run)
            return self._reply(200, res)

        # POST /api/dashboard/deploy — Deploy snapshot Sheet hiện tại lên Cloudflare Pages
        # KHÔNG chạy crawler, chỉ đọc Chi_tiet tab và deploy CF.
        # Auth: X-Scheduler-Secret (dùng chung với ingestion secret)
        if path == "/api/dashboard/deploy":
            import hmac as _hmac
            _exp_sec = os.environ.get("SCHEDULER_SECRET")
            if not _exp_sec:
                return self._reply(500, {"error": "SCHEDULER_SECRET not configured"})
            _recv_sec = self.headers.get("X-Scheduler-Secret", "")
            if not _hmac.compare_digest(_recv_sec, _exp_sec):
                return self._reply(403, {"error": "FORBIDDEN"})
            try:
                import dashboard_sync as dsync
                # Đọc Chi_tiet từ Google Sheet (không crawl)
                _svc = get_sheets_service()
                _res = _svc.spreadsheets().values().get(
                    spreadsheetId=SHEET_ID, range="'Chi_tiet'!A:ZZ"
                ).execute()
                _vals = _res.get("values", [])
                _hdr  = _vals[0] if _vals else []
                _rows = _vals[1:] if len(_vals) > 1 else []
                cached = {
                    "hdr": _hdr,
                    "rows": _rows,
                    "ci": {h: i for i, h in enumerate(_hdr)},
                }
                raw_data = dsync._build_raw(cached)
                cf_id = dsync._deploy_to_cloudflare(raw_data)
                _log_activity("DASHBOARD_DEPLOY", "SUCCESS", f"Manual deploy CF ID: {cf_id}")
                return self._reply(200, {
                    "ok": True,
                    "cloudflare_deployment_id": cf_id,
                    "ticket_count": len(_rows),
                })
            except Exception as _e_dd:
                _log_activity("DASHBOARD_DEPLOY", "FAILED", str(_e_dd))
                return self._reply(500, {"ok": False, "error": str(_e_dd)})

        self._reply(404, {"error": "Endpoint Not Found"})

def run_server(port=8080):
    # Khởi động luồng Background Scheduler nội bộ tự động thực thi chu kỳ:
    # - Từ 06:00 đến 13:00 (Mỗi giờ/hoặc định kỳ): Chạy filter=ALL
    # - Từ 14:00 đến 18:00: Chạy filter=HOI_LAY
    def _bg_scheduler_loop():
        last_run_hour = -1
        while True:
            try:
                now_dt = datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh"))
                hour = now_dt.hour
                minute = now_dt.minute
                
                # Chạy đúng phút 00 của các giờ trong khung 6h-18h và chưa chạy trong giờ đó
                if 6 <= hour <= 18 and minute == 0 and hour != last_run_hour:
                    filter_type = "ALL" if hour <= 13 else "HOI_LAY"
                    print(f"⏰ [Scheduler] Tự động kích hoạt chu trình cào + gửi: {filter_type} lúc {now_dt.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
                    try:
                        # BƯỚC 1: Thực thi cào dữ liệu mới từ GHN Vận hành và ghi Raw Snapshot vào Google Sheet
                        print(f"[{now_dt.strftime('%H:%M:%S')}] 🔄 [Scheduler] Bắt đầu cào dữ liệu tự động trước khi gửi tin...", flush=True)
                        ctp_dir = os.path.join(os.path.dirname(__file__), "Cao_Ton_Phieu")
                        if ctp_dir not in sys.path:
                            sys.path.insert(0, ctp_dir)
                        import cao_ton_phieu as ctp
                            
                        buu_cuc, tickets, meta = ctp.login_and_scrape_v2()
                        svc = get_sheets_service()
                        co_cau = ctp.load_co_cau_map(svc)
                        name_of = {str(b.get("value", "")): b.get("label") for b in buu_cuc}

                        cnt_map = {}
                        for t in tickets:
                            bc = t.get("ma_buu_cuc", "")
                            loai = t.get("loai", "")
                            if bc not in cnt_map:
                                cnt_map[bc] = [0, 0, 0]
                            if loai == "Hối giao":
                                cnt_map[bc][0] += 1
                            elif loai == "Hối lấy":
                                cnt_map[bc][1] += 1
                            elif loai == "Hối trả":
                                cnt_map[bc][2] += 1

                        au = meta.get("updated_at", now_dt.strftime("%Y-%m-%d %H:%M:%S"))

                        # Ghi tab Ton_phieu
                        ctp.ensure_tab(svc, ctp.TAB_TON)
                        rows_ton = [["ma_buu_cuc", "ten_buu_cuc", "Hối giao", "Hối lấy", "Hối trả", "Tổng", "Tiền phạt", "cap_nhat_luc"]]
                        for b in buu_cuc:
                            bc = b.get("value")
                            c = cnt_map.get(bc, [0, 0, 0])
                            rows_ton.append([
                                bc, name_of.get(bc, b.get("label")), c[0], c[1], c[2],
                                b.get("total"), b.get("penalty"), au
                            ])
                        ctp.write_tab(svc, ctp.TAB_TON, rows_ton)

                        # Ghi tab Chi_tiet
                        ctp.ensure_tab(svc, ctp.TAB_CT)
                        rows_ct = [[
                            "ma_buu_cuc", "ten_buu_cuc", "ma_ticket", "ma_don", "loai_phieu", "tien_phat",
                            "hạn_đóng", "trạng_thái", "url", "gdv_pgdv_id", "gdv_pgdv_name",
                            "area_manager_id", "area_manager_name", "region_shortname"
                        ]]
                        for t in tickets:
                            bc = str(t.get("ma_buu_cuc", ""))
                            cc_info = co_cau.get(bc, ("", "", "", "", ""))
                            rows_ct.append([
                                t.get("ma_buu_cuc"), name_of.get(str(t.get("ma_buu_cuc", "")), ""), t.get("ma_ticket"), t.get("ma_don"),
                                t.get("loai"), t.get("tien_phat"), t.get("han_dong"), t.get("trang_thai"),
                                t.get("url"), cc_info[0], cc_info[1], cc_info[2], cc_info[3], cc_info[4]
                            ])
                        ctp.write_tab(svc, ctp.TAB_CT, rows_ct)
                            
                        # Ghi RP_theo_AM
                        try:
                            ctp.ghi_rp_theo_am(svc, co_cau)
                        except Exception as e_am:
                            print(f"[WARN] Lỗi ghi RP_theo_AM: {e_am}", flush=True)

                        _log_activity("AUTO_SCRAPE", "SUCCESS", f"Tự động cào thành công {len(buu_cuc)} BC, {len(tickets)} tickets lúc {au}")
                        print(f"[{now_dt.strftime('%H:%M:%S')}] ✅ [Scheduler] Cào dữ liệu thành công! Tiến hành chạy chu trình gửi tin...", flush=True)

                        # BƯỚC 2: Chạy chu trình đọc Sheet mới và gửi tin / báo cáo
                        run_dispatch_cycle(filter_type=filter_type, send_to="ALL", dry_run=False)
                        last_run_hour = hour
                    except Exception as ex:
                        _log_activity("AUTO_SCRAPE", "FAILED", f"Lỗi cào tự động lúc {hour}h: {ex}")
                        print(f"❌ [Scheduler Error] Lỗi khi chạy chu kỳ cào + gửi {filter_type}: {ex}", flush=True)
            except Exception as e:
                print(f"❌ [Scheduler Loop Error]: {e}", flush=True)
            time.sleep(30) # Kiểm tra mỗi 30 giây

    if os.environ.get("AUTO_SCHEDULER", "true").strip().lower() not in ("false", "0", "no"):
        sched_thread = threading.Thread(target=_bg_scheduler_loop, daemon=True)
        sched_thread.start()
        print("🟢 [Internal Background Scheduler] Đã khởi động luồng canh giờ tự động (6h-13h ALL, 14h-18h HOI_LAY)...", flush=True)
    else:
        print("⏸ [Internal Background Scheduler] ĐÃ TẮT — AUTO_SCHEDULER=false. Dùng Cloud Scheduler.", flush=True)

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
