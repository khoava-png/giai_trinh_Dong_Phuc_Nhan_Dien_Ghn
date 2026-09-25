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
import sso_oidc
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- CẤU HÌNH HỆ THỐNG ---
VN_TZ = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")

AUTH_USER = os.environ.get("AUTH_USER", "admin")
AUTH_PASS = os.environ.get("AUTH_PASS", "Ghn@2026!")

SHEET_ID = os.environ.get("SHEET_ID", "15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg")
ADMIN_MA_NV = os.environ.get("ADMIN_MA_NV", "3049378")
ADMIN_IDS = ["3049378", "3026736"]  # Danh sách 2 Admin bất biến nhận báo cáo giám sát Master Pipeline

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

# Khóa luồng cào & pipeline dùng chung cho toàn server (Single-flight lock)
_scrape_lock = threading.Lock()

# Staged Snapshots cho quy trình Preview / Dispatch 2 giai đoạn an toàn
_STAGED_SNAPSHOTS = {}
_STAGED_LOCK = threading.Lock()
_SNAPSHOT_TTL = 1800  # 30 phút TTL

# Trạng thái Health Report cho Admin GTalk State Transition Alerting (RAM-only; container restart sẽ reset state)
_LAST_HEALTH_STATE = {"status": "HEALTHY", "last_checked": 0}
_HEALTH_LOCK = threading.Lock()

def check_and_notify_api_state_transition(new_status, probe_info):
    """
    Hàm riêng biệt xử lý State Transition Alerting cho Admin.
    CHỈ được gọi từ trigger chủ động (Background Watchdog hoặc Trigger Action rõ ràng).
    TUYỆT ĐỐI không gọi ngầm từ GET /api/health/report.
    Lưu ý: State lưu trong RAM, container restart sẽ reset state về ban đầu.
    """
    with _HEALTH_LOCK:
        prev_status = _LAST_HEALTH_STATE.get("status", "HEALTHY")
        if new_status == prev_status:
            return False, prev_status

        _LAST_HEALTH_STATE["status"] = new_status
        _LAST_HEALTH_STATE["last_checked"] = time.time()

    # Gửi alert GTalk khi có chuyển trạng thái (HEALTHY -> WARNING/FAILED hoặc ngược lại)
    try:
        now_str = _now().strftime("%d/%m/%Y %H:%M:%S")
        status_icon = "🟢" if new_status == "HEALTHY" else ("🟡" if new_status == "WARNING" else "🔴")
        transition_str = f"{prev_status} ➔ {new_status}"
        alert_msg = (
            f"{status_icon} *[BÁO CÁO TÌNH TRẠNG API NGUỒN]*\n"
            f"• Trạng thái: *{transition_str}*\n"
            f"• Thời gian: *{now_str}*\n"
            f"• Độ trễ API: *{probe_info.get('latency_ms', 'N/A')}ms*\n"
            f"• Tổng bưu cục: *{probe_info.get('total_buu_cuc', 'N/A')}* | Tổng phiếu web: *{probe_info.get('total_tickets_web', 'N/A')}*\n"
            f"• Run ID: *{probe_info.get('run_id', 'N/A')}*"
        )
        send_gtalk_message(ADMIN_MA_NV, alert_msg)
        return True, prev_status
    except Exception as ex:
        print(f"[WARN] Không thể gửi alert GTalk cho Admin: {ex}", flush=True)
        return False, prev_status

# Template mặc định chuẩn Markdown GTalk (Version 3.3.0 - Link xử lý nội bộ)
TEMPLATE_VERSION = "v3.3.0"

DEFAULT_TEMPLATES = {
    "mau_am_all": (
        "BÁO CÁO PHIẾU TỒN AM {ten_am}\n\n"
        "Hi Anh/Chị {ten_am}, tính tới thời điểm\n"
        "{ngay_gio}\n\n"
        "{bcs}\n\n"
        "📊 *Theo dõi phiếu tại:* https://docs.google.com/spreadsheets/d/1YmFgYyARiFh5vu63My24Sx0ffcy-RsxddEvVWSCgDds/edit?gid=0#gid=0\n"
        "👉 Chi tiết xử lý tại: https://noibo.ghn.vn/ghn-ticket\n"
        "Nhờ Anh/Chị đôn đốc bưu cục xử lý phiếu tồn nhé!\n"
        "Cần hỗ trợ vui lòng liên hệ nhóm GTalk\n"
        "\"OE - Triển khai phiếu hối G/L/T\""
    ),
    "mau_vung_all": (
        "🚨 [BÁO CÁO PHIẾU TỒN VÙNG {vung}]\n\n"
        "Hi Anh/Chị Trợ lý/ HRBP vùng *{vung}*, tính tới thời điểm _{ngay_gio}_\n\n"
        "{bcs}\n\n"
        "📊 *Theo dõi phiếu tại:* https://docs.google.com/spreadsheets/d/1YmFgYyARiFh5vu63My24Sx0ffcy-RsxddEvVWSCgDds/edit?gid=0#gid=0\n"
        "👉 Chi tiết xử lý tại: https://noibo.ghn.vn/ghn-ticket\n"
        "👉 Nhờ Anh/Chị nhắc nhở AM đôn đốc bưu cục xử lý dứt điểm nhé!\n"
        "Cần hỗ trợ vui lòng liên hệ nhóm GTalk \"*OE - Triển khai phiếu hối G/L/T*\""
    ),
    "mau_am_hoilay": (
        "BÁO CÁO PHIẾU HỐI LẤY AM {ten_am}\n\n"
        "Hi Anh/Chị {ten_am}, tính tới thời điểm\n"
        "{ngay_gio}\n\n"
        "{bcs}\n\n"
        "📊 *Theo dõi phiếu tại:* https://docs.google.com/spreadsheets/d/1YmFgYyARiFh5vu63My24Sx0ffcy-RsxddEvVWSCgDds/edit?gid=0#gid=0\n"
        "👉 Chi tiết xử lý tại: https://noibo.ghn.vn/ghn-ticket\n"
        "Nhờ Anh/Chị đôn đốc shipper đi lấy hàng trước khi đóng ca!\n"
        "Cần hỗ trợ vui lòng liên hệ nhóm GTalk\n"
        "\"OE - Triển khai phiếu hối G/L/T\""
    ),
    "mau_vung_hoilay": (
        "📥 [BÁO CÁO HỐI LẤY VÙNG {vung}]\n\n"
        "Hi Anh/Chị Trợ lý/ HRBP vùng *{vung}*, tính tới thời điểm _{ngay_gio}_\n\n"
        "{bcs}\n\n"
        "📊 *Theo dõi phiếu tại:* https://docs.google.com/spreadsheets/d/1YmFgYyARiFh5vu63My24Sx0ffcy-RsxddEvVWSCgDds/edit?gid=0#gid=0\n"
        "👉 Chi tiết xử lý tại: https://noibo.ghn.vn/ghn-ticket\n"
        "👉 Nhờ Anh/Chị nhắc nhở các AM đôn đốc lấy hàng dứt điểm ca chiều!\n"
        "Cần hỗ trợ vui lòng liên hệ nhóm GTalk \"*OE - Triển khai phiếu hối G/L/T*\""
    ),
    "mau_am_hoigiao": (
        "BÁO CÁO PHIẾU HỐI GIAO AM {ten_am}\n\n"
        "Hi Anh/Chị {ten_am}, tính tới thời điểm\n"
        "{ngay_gio}\n\n"
        "{bcs}\n\n"
        "📊 *Theo dõi phiếu tại:* https://docs.google.com/spreadsheets/d/1YmFgYyARiFh5vu63My24Sx0ffcy-RsxddEvVWSCgDds/edit?gid=0#gid=0\n"
        "👉 Chi tiết xử lý tại: https://noibo.ghn.vn/ghn-ticket\n"
        "Nhờ Anh/Chị đôn đốc bưu cục giao hàng dứt điểm!\n"
        "Cần hỗ trợ vui lòng liên hệ nhóm GTalk\n"
        "\"OE - Triển khai phiếu hối G/L/T\""
    ),
    "mau_vung_hoigiao": (
        "🚚 [BÁO CÁO HỐI GIAO VÙNG {vung}]\n\n"
        "Hi Anh/Chị Trợ lý/ HRBP vùng *{vung}*, tính tới thời điểm _{ngay_gio}_\n\n"
        "{bcs}\n\n"
        "📊 *Theo dõi phiếu tại:* https://docs.google.com/spreadsheets/d/1YmFgYyARiFh5vu63My24Sx0ffcy-RsxddEvVWSCgDds/edit?gid=0#gid=0\n"
        "👉 Chi tiết xử lý tại: https://noibo.ghn.vn/ghn-ticket\n"
        "👉 Nhờ Anh/Chị nhắc nhở các AM đôn đốc bưu cục giao dứt điểm các đơn hối!\n"
        "Cần hỗ trợ vui lòng liên hệ nhóm GTalk \"*OE - Triển khai phiếu hối G/L/T*\""
    ),
    "mau_am_hoitra": (
        "BÁO CÁO PHIẾU HỐI TRẢ AM {ten_am}\n\n"
        "Hi Anh/Chị {ten_am}, tính tới thời điểm\n"
        "{ngay_gio}\n\n"
        "{bcs}\n\n"
        "📊 *Theo dõi phiếu tại:* https://docs.google.com/spreadsheets/d/1YmFgYyARiFh5vu63My24Sx0ffcy-RsxddEvVWSCgDds/edit?gid=0#gid=0\n"
        "👉 Chi tiết xử lý tại: https://noibo.ghn.vn/ghn-ticket\n"
        "Nhờ Anh/Chị đôn đốc hoàn tất trả hàng cho Shop!\n"
        "Cần hỗ trợ vui lòng liên hệ nhóm GTalk\n"
        "\"OE - Triển khai phiếu hối G/L/T\""
    ),
    "mau_vung_hoitra": (
        "🔄 [BÁO CÁO HỐI TRẢ VÙNG {vung}]\n\n"
        "Hi Anh/Chị Trợ lý/ HRBP vùng *{vung}*, tính tới thời điểm _{ngay_gio}_\n\n"
        "{bcs}\n\n"
        "📊 *Theo dõi phiếu tại:* https://docs.google.com/spreadsheets/d/1YmFgYyARiFh5vu63My24Sx0ffcy-RsxddEvVWSCgDds/edit?gid=0#gid=0\n"
        "👉 Chi tiết xử lý tại: https://noibo.ghn.vn/ghn-ticket\n"
        "👉 Nhờ Anh/Chị nhắc nhở các AM đôn đốc xử lý đơn hối trả!\n"
        "Cần hỗ trợ vui lòng liên hệ nhóm GTalk \"*OE - Triển khai phiếu hối G/L/T*\""
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

    for bc in sorted_bcs:
        bname = bc.get("name") or bc.get("bl") or "—"
        bcs_lines.append(f"📦 Bưu cục {bname}: {bc.get('nz', 0)} phiếu (GÁN KHẨN CẤP để không bị phạt), {bc.get('np', 0)} phiếu (GÁN NGAY để không tăng mức phạt)")

    bcs_txt = "\n".join(bcs_lines) if bcs_lines else "Hiện không có phiếu tồn nào cần xử lý."
    content = template_text.replace("{ten_am}", am_info.get("name", ""))\
                           .replace("{vung}", am_info.get("region", ""))\
                           .replace("{ngay_gio}", now_str)\
                           .replace("{bcs}", bcs_txt)\
                           .replace("{link}", "https://noibo.ghn.vn/ghn-ticket")
    return content

def render_vung_message(reg_name, vung_info, filter_type, template_text, now_str):
    """Render tin nhắn hoàn chỉnh gửi Trợ lý Vùng (sắp xếp AM nhiều phiếu nhất lên đầu)."""
    sorted_ams = sorted(vung_info["ams"].items(), key=lambda x: x[1]["total"], reverse=True)
    am_lines = []

    for aname, stats in sorted_ams:
        am_lines.append(f"📦 *{aname}* (AM): *{stats['nz']}* phiếu (GÁN KHẨN CẤP để không bị phạt), *{stats['np']}* phiếu (GÁN NGAY để không tăng mức phạt)")

    bcs_txt = "\n".join(am_lines) if am_lines else "Hiện các AM trong Vùng không còn phiếu tồn nào cần xử lý."
    content = template_text.replace("{vung}", reg_name)\
                           .replace("{ngay_gio}", now_str)\
                           .replace("{bcs}", bcs_txt)
    return content

# --- BÁO CÁO GIÁM SÁT 2 ADMIN BẤT BIẾN (3049378, 3026736) ---
def render_admin_health_report(info):
    """Tin 1/3: Báo cáo tình trạng sống Health API, Hạ tầng & Dashboard Deploy."""
    tot = info.get('total_tickets', 0)
    tre = info.get('tre_sla', 0)
    chua = info.get('chua_tre_sla', 0)
    pct_tre = f"{tre/tot*100:.1f}%" if tot else "0%"
    pct_chua = f"{chua/tot*100:.1f}%" if tot else "0%"
    phat_val = info.get('total_phat', 0)
    return (
        f"📊 [BÁO CÁO GIÁM SÁT 1/3] — HEALTH API, HẠ TẦNG & DASHBOARD\n\n"
        f"• Trạng thái API: {info.get('api_status', 'HEALTHY')}\n"
        f"• Xác thực API: {info.get('auth_status', 'PASS')}\n"
        f"• Độ trễ API (Latency): {info.get('latency_ms', 0)}ms\n"
        f"• Bưu cục lỗi (failed_bc): {info.get('failed_bc_count', 0)}\n"
        f"• Tổng bưu cục: {info.get('total_buu_cuc', 0)}\n"
        f"• Tổng phiếu: {tot} phiếu\n"
        f"• Tổng tiền phạt: {phat_val:,} đ\n"
        f"• Trễ SLA: {tre} ({pct_tre}) | Chưa Trễ SLA: {chua} ({pct_chua})\n"
        f"• Snapshot ID: {info.get('snapshot_id', 'N/A')}\n"
        f"• Nguồn cập nhật: {info.get('source_updated_at', info.get('timestamp', 'N/A'))}\n"
        f"• Thời gian build: {info.get('built_at', 'N/A')}\n"
        f"• Thời gian deploy: {info.get('deployed_at', 'N/A')}\n"
        f"• Artifact Hash: {info.get('artifact_hash', 'N/A')}\n"
        f"• Filter: {info.get('filter', 'ALL')}\n"
        f"• Run ID: {info.get('run_id', 'N/A')}\n"
        f"• Revision: {info.get('revision', os.environ.get('K_REVISION', 'local'))}\n\n"
        f"📊 Dashboard Vùng: https://ghn-dashboard.pages.dev/"
    )

def send_admin_monitoring_reports(ams_data, vungs_data, tro_ly_map, meta_info, dry_run=False):
    """
    Gửi đúng 3 tin giám sát cho 2 Admin bất biến (3049378, 3026736), tổng cộng 6 tin:
    1. Health API (render_admin_health_report)
    2. Tin AM Top 1 (Bản sao NGUYÊN VĂN 100% tin AM gốc từ render_am_message)
    3. Tin Trợ lý Top 1 (Bản sao NGUYÊN VĂN 100% tin Trợ lý Vùng gốc từ render_vung_message)
    """
    admin_logs = []
    if not ams_data or not vungs_data:
        return admin_logs

    filter_type = meta_info.get("filter", "ALL").upper()
    now_str = meta_info.get("timestamp", _now().strftime("%d/%m/%Y %H:%M"))

    # Lọc AM Top 1
    sorted_ams = sorted(ams_data.values(), key=lambda x: x["total"], reverse=True)
    top_am = sorted_ams[0] if sorted_ams else None

    # Lọc Trợ lý / Vùng Top 1
    sorted_vungs = sorted(vungs_data.items(), key=lambda x: x[1]["total"], reverse=True)
    top_reg, top_vung = sorted_vungs[0] if sorted_vungs else ("", {})

    # Tin 1: Health API
    msg_health = render_admin_health_report(meta_info)

    # Tin 2: Bản sao nguyên văn 100% tin AM Top 1 (theo đúng template khóa)
    tpl_key_am = "mau_am_hoilay" if filter_type == "HOI_LAY" else ("mau_am_hoigiao" if filter_type == "HOI_GIAO" else ("mau_am_hoitra" if filter_type == "HOI_TRA" else "mau_am_all"))
    tpl_am = DEFAULT_TEMPLATES.get(tpl_key_am, DEFAULT_TEMPLATES["mau_am_all"])
    msg_top_am = render_am_message(top_am, filter_type, tpl_am, now_str) if top_am else ""

    # Tin 3: Bản sao nguyên văn 100% tin Trợ lý Vùng Top 1 (theo đúng template khóa)
    tpl_key_vung = "mau_vung_hoilay" if filter_type == "HOI_LAY" else ("mau_vung_hoigiao" if filter_type == "HOI_GIAO" else ("mau_vung_hoitra" if filter_type == "HOI_TRA" else "mau_vung_all"))
    tpl_vung = DEFAULT_TEMPLATES.get(tpl_key_vung, DEFAULT_TEMPLATES["mau_vung_all"])
    msg_top_vung = render_vung_message(top_reg, top_vung, filter_type, tpl_vung, now_str) if top_vung else ""

    reports = [
        ("HEALTH_API", "Health API", msg_health),
        ("TOP_AM", f"AM Top 1 ({top_am['name']})" if top_am else "AM Top 1", msg_top_am),
        ("TOP_TRO_LY", f"Trợ lý Top 1 (Vùng {top_reg})" if top_reg else "Trợ lý Top 1", msg_top_vung)
    ]

    for admin_id in ADMIN_IDS:
        for rtype, rsource, content in reports:
            if not content:
                continue
            if dry_run:
                admin_logs.append({
                    "admin_id": admin_id,
                    "report_type": rtype,
                    "source_name": rsource,
                    "success": True,
                    "error": None,
                    "retry_count": 0
                })
            else:
                try:
                    res = send_gtalk_message(admin_id, content)
                    admin_logs.append({
                        "admin_id": admin_id,
                        "report_type": rtype,
                        "source_name": rsource,
                        "success": res.get("success", False),
                        "error": res.get("error"),
                        "retry_count": res.get("retries", 0)
                    })
                except Exception as e:
                    admin_logs.append({
                        "admin_id": admin_id,
                        "report_type": rtype,
                        "source_name": rsource,
                        "success": False,
                        "error": str(e),
                        "retry_count": 0
                    })

    return admin_logs

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

    if not _scrape_lock.acquire(blocking=False):
        print(f"[{now_str}] ⚠️ [CYCLE_RUN] LOCK -> FAILED (Locked)", flush=True)
        return {"success": False, "error": "Đang có tiến trình khác thực thi trên instance này", "cycle_id": cycle_id}

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
        try:
            _scrape_lock.release()
        except Exception:
            pass
        return {"success": False, "error": f"Sheet read failed: {str(e)}", "cycle_id": cycle_id}
    t_read_dur = round(time.time() - t_read_start, 3)

    val_ranges = resp.get("valueRanges", [])
    ct_vals = val_ranges[0].get("values", [])
    tl_vals = val_ranges[2].get("values", []) if len(val_ranges) > 2 else []

    if len(ct_vals) <= 1:
        _log_activity("CYCLE_RUN", "FAILED", f"[{cycle_id}] Không có dữ liệu trong Chi_tiet")
        try:
            _scrape_lock.release()
        except Exception:
            pass
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

    try:
        _scrape_lock.release()
    except Exception:
        pass

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
    def _reply(self, code, data, content_type="application/json", headers_extra=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        if headers_extra:
            for k, v in headers_extra.items():
                self.send_header(k, v)
        self.end_headers()
        if isinstance(data, (dict, list)):
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        elif isinstance(data, str):
            self.wfile.write(data.encode("utf-8"))
        elif isinstance(data, bytes):
            self.wfile.write(data)

    def _get_cookies(self):
        cookie_hdr = self.headers.get("Cookie", "")
        cookies = {}
        for item in cookie_hdr.split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                cookies[k.strip()] = v.strip()
        return cookies

    def _get_current_user(self):
        cookies = self._get_cookies()
        session_token = cookies.get("ghn_session")
        if not session_token:
            return None
        return sso_oidc.verify_session_token(session_token)

    def _check_auth(self):
        if not sso_oidc.is_sso_configured():
            return True
        return bool(self._get_current_user())

    def do_OPTIONS(self):
        self._reply(200, "")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # ─── SSO OIDC Authentication Endpoints ───
        if path in ("/auth/login", "/login"):
            if not sso_oidc.is_sso_configured():
                return self._reply(500, {"error": "SSO chưa được cấu hình (thiếu GHN_SSO_CLIENT_ID hoặc GHN_SSO_CLIENT_SECRET)"})
            state, nonce = sso_oidc.generate_state_and_nonce()
            state_token = sso_oidc.sign_state_payload(state, nonce)
            auth_url = sso_oidc.build_authorization_url(state, nonce)
            
            # Lưu state_token vào cookie HttpOnly tạm thời 5 phút
            cookie_val = f"ghn_oidc_state={state_token}; Path=/; Max-Age=300; HttpOnly; SameSite=Lax"
            self.send_response(302)
            self.send_header("Location", auth_url)
            self.send_header("Set-Cookie", cookie_val)
            self.end_headers()
            return

        if path == "/auth/callback":
            qs = parse_qs(parsed.query)
            if "error" in qs:
                err_desc = qs.get("error_description", [qs.get("error", ["Unknown error"])[0]])[0]
                return self._reply(400, {"ok": False, "error": f"SSO Authorization Error: {err_desc}"})
            
            code = qs.get("code", [None])[0]
            state = qs.get("state", [None])[0]
            if not code or not state:
                return self._reply(400, {"ok": False, "error": "Thiếu mã xác thực (code) hoặc tham số state"})
            
            cookies = self._get_cookies()
            state_token = cookies.get("ghn_oidc_state", "")
            is_valid_state, nonce = sso_oidc.verify_state_payload(state_token, state)
            if not is_valid_state:
                return self._reply(400, {"ok": False, "error": "Xác thực state thất bại (CSRF check failed hoặc state đã hết hạn)"})

            try:
                tokens = sso_oidc.exchange_code_for_tokens(code)
                uinfo = sso_oidc.fetch_userinfo(tokens["access_token"])
                session_token = sso_oidc.create_session_token(uinfo, id_token=tokens.get("id_token", ""))
                
                # Tạo cookie session 8 giờ
                session_cookie = f"ghn_session={session_token}; Path=/; Max-Age={sso_oidc.SESSION_TTL_SECONDS}; HttpOnly; SameSite=Lax"
                clear_state_cookie = "ghn_oidc_state=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
                
                self.send_response(302)
                self.send_header("Location", "/dashboard")
                self.send_header("Set-Cookie", session_cookie)
                self.send_header("Set-Cookie", clear_state_cookie)
                self.end_headers()
                return
            except Exception as e_sso:
                return self._reply(500, {"ok": False, "error": f"Đăng nhập SSO thất bại: {str(e_sso)}"})

        if path == "/auth/me":
            user = self._get_current_user()
            if user:
                return self._reply(200, {
                    "authenticated": True,
                    "user": {
                        "employee_id": user.get("employee_id"),
                        "name": user.get("name"),
                        "phone_number": user.get("phone_number"),
                        "jobtitle_name": user.get("jobtitle_name"),
                        "team_name": user.get("team_name"),
                    }
                })
            return self._reply(200, {"authenticated": False})

        if path in ("/auth/logout", "/logout"):
            user = self._get_current_user()
            id_token = user.get("id_token", "") if user else ""
            logout_url = sso_oidc.build_logout_url(id_token_hint=id_token) if sso_oidc.is_sso_configured() else "/dashboard"
            
            clear_session_cookie = "ghn_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
            self.send_response(302)
            self.send_header("Location", logout_url)
            self.send_header("Set-Cookie", clear_session_cookie)
            self.end_headers()
            return

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
            if sso_oidc.is_sso_configured() and not self._get_current_user():
                self.send_response(302)
                self.send_header("Location", "/auth/login")
                self.end_headers()
                return

            cur_dir = os.path.dirname(__file__)
            html_candidates = [
                os.path.join(cur_dir, "index.html"),
                os.path.join(cur_dir, "Index.html"),
                os.path.join(cur_dir, "dashboard", "index.html"),
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

        # GET /api/health/report — Probe tình trạng sống API Nguồn (Read-only, max timeout 10s, KHÔNG crawl full, KHÔNG lock, KHÔNG gửi GTalk)
        if path == "/api/health/report":
            import hmac
            expected_secret = os.environ.get("SCHEDULER_SECRET")
            if not expected_secret:
                return self._reply(403, {"ok": False, "error": "SCHEDULER_SECRET is not set"})

            x_scheduler_secret = self.headers.get("X-Scheduler-Secret", "")
            if not (x_scheduler_secret and hmac.compare_digest(x_scheduler_secret.encode("utf-8"), expected_secret.encode("utf-8"))):
                return self._reply(401, {"ok": False, "error": "Unauthorized: Invalid or missing X-Scheduler-Secret header"})

            now_vn = datetime.datetime.now(VN_TZ)
            run_id = f"HLT-{uuid.uuid4().hex[:8]}"

            # 1. Probe kết nối API Nguồn & danh mục bưu cục (Read-only, timeout 10s)
            ctp_dir = os.path.join(os.path.dirname(__file__), "Cao_Ton_Phieu")
            if ctp_dir not in sys.path:
                sys.path.insert(0, ctp_dir)
            import ghn_vanhanh_api as gva

            t0 = time.time()
            api_reachable = False
            api_auth = "FAIL"
            total_buu_cuc = 0
            total_tickets_web = 0
            err_detail = None

            try:
                api = gva.GHNVanHanhAPI()
                # Timeout tối đa 10s cho probe nhẹ
                api.session.timeout = 10
                meta = api.get_buucuc_list()
                t1 = time.time()
                latency_ms = round((t1 - t0) * 1000, 2)
                api_reachable = True
                api_auth = "PASS"
                bcs = meta.get("buu_cuc", [])
                total_buu_cuc = len(bcs)
                total_tickets_web = int(meta.get("grand_total", 0))
            except Exception as e_probe:
                latency_ms = round((time.time() - t0) * 1000, 2)
                err_detail = str(e_probe)

            # 2. Đánh giá api_status tách biệt hoàn toàn với snapshot
            if not api_reachable or api_auth != "PASS":
                api_status = "FAILED"
            elif latency_ms > 5000 or total_buu_cuc == 0:
                api_status = "WARNING"
            else:
                api_status = "HEALTHY"

            # 3. Đánh giá snapshot_status độc lập
            last_snapshot_id = None
            snapshot_age_s = None
            snapshot_status = "NOT_AVAILABLE"
            with _STAGED_LOCK:
                if _STAGED_SNAPSHOTS:
                    latest_k = sorted(_STAGED_SNAPSHOTS.keys())[-1]
                    last_snapshot_id = latest_k
                    snap_data = _STAGED_SNAPSHOTS[latest_k]
                    snapshot_age_s = round(time.time() - snap_data.get("created_at", time.time()), 1)
                    snapshot_status = "FRESH" if snapshot_age_s <= 1800 else "STALE"

            auto_sched = os.environ.get("AUTO_SCHEDULER", "false").strip().lower() not in ("false", "0", "no")

            # Không chạy full ticket crawl tại GET endpoint: các trường deep audit để null rõ ràng
            return self._reply(200, {
                "timestamp": now_vn.isoformat(),
                "service": "GHN Control Center Cloud Run V3",
                "revision": os.environ.get("K_REVISION", "local"),
                "app_health": "HEALTHY",
                "api_source_reachable": api_reachable,
                "api_auth_status": api_auth,
                "api_latency_ms": latency_ms,
                "total_buu_cuc": total_buu_cuc,
                "total_tickets_web": total_tickets_web,
                "total_tickets_api": None,
                "failed_bc": None,
                "web_api_match": None,
                "last_snapshot_id": last_snapshot_id,
                "snapshot_age_seconds": snapshot_age_s,
                "auto_scheduler_enabled": auto_sched,
                "api_status": api_status,
                "snapshot_status": snapshot_status,
                "data_check": "NOT_RUN",
                "admin_notified": False,
                "error": err_detail
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

        # POST /api/data-integrity/report — Deep Audit toàn diện tính toàn vẹn dữ liệu Web vs API (Dùng thủ công, Lock an toàn, KHÔNG ghi Sheet, KHÔNG gửi GTalk)
        if path == "/api/data-integrity/report":
            import hmac
            expected_secret = os.environ.get("SCHEDULER_SECRET")
            if not expected_secret:
                return self._reply(403, {"ok": False, "error": "SCHEDULER_SECRET is not set"})

            x_scheduler_secret = self.headers.get("X-Scheduler-Secret", "")
            if not (x_scheduler_secret and hmac.compare_digest(x_scheduler_secret.encode("utf-8"), expected_secret.encode("utf-8"))):
                return self._reply(401, {"ok": False, "error": "Unauthorized: Invalid or missing X-Scheduler-Secret header"})

            if not _scrape_lock.acquire(blocking=False):
                return self._reply(429, {"ok": False, "error": "Đang có tiến trình cào/dispatch khác thực thi trên instance này"})

            run_id = f"AUDIT-{uuid.uuid4().hex[:8]}"
            t_start = time.time()
            now_vn = datetime.datetime.now(VN_TZ)

            try:
                ctp_dir = os.path.join(os.path.dirname(__file__), "Cao_Ton_Phieu")
                if ctp_dir not in sys.path:
                    sys.path.insert(0, ctp_dir)
                import cao_ton_phieu_api as ctp

                buu_cuc, tickets, meta, failed_bc = ctp.crawl_tickets_api(workers=8)
                t_end = time.time()
                dur = round(t_end - t_start, 2)

                grand_total_web = int(meta.get("grand_total", 0)) if isinstance(meta, dict) else 0
                total_tickets_api = len(tickets)
                total_buu_cuc = len(buu_cuc)

                # Đối soát theo từng bưu cục
                bc_expected = {str(b.get("value", "")).strip(): int(b.get("total") or 0) for b in buu_cuc}
                bc_actual = defaultdict(int)
                for t in tickets:
                    bc_actual[str(t.get("ma_buu_cuc", "")).strip()] += 1

                mismatched_bc = []
                for bc, exp in bc_expected.items():
                    act = bc_actual.get(bc, 0)
                    if exp != act:
                        mismatched_bc.append({"ma_buu_cuc": bc, "expected": exp, "actual": act})

                data_check = "PASS" if (len(failed_bc) == 0 and len(mismatched_bc) == 0 and total_tickets_api == grand_total_web) else "FAIL"

                return self._reply(200, {
                    "ok": True,
                    "run_id": run_id,
                    "timestamp": now_vn.isoformat(),
                    "total_buu_cuc": total_buu_cuc,
                    "total_tickets_web": grand_total_web,
                    "total_tickets_api": total_tickets_api,
                    "web_api_match": (total_tickets_api == grand_total_web),
                    "failed_bc_count": len(failed_bc),
                    "failed_bc": [list(x) for x in failed_bc[:20]],
                    "mismatched_bc_count": len(mismatched_bc),
                    "mismatched_bc": mismatched_bc[:20],
                    "data_check": data_check,
                    "duration_seconds": dur
                })

            except Exception as ex:
                dur = round(time.time() - t_start, 2)
                return self._reply(500, {
                    "ok": False,
                    "run_id": run_id,
                    "error": str(ex),
                    "data_check": "FAIL",
                    "duration_seconds": dur
                })
            finally:
                try:
                    _scrape_lock.release()
                except Exception:
                    pass

        # POST /api/pipeline/run | /api/pipeline/preview | /api/pipeline/dispatch
        # MASTER PIPELINE 2 GIAI ĐOẠN AN TOÀN:
        # - Chế độ Preview (Mặc định): Crawl API -> Verify Snapshot -> Map nội dung RAM -> Gửi duy nhất 1 tin Top 1 cho Admin duyệt -> Trả về metadata & snapshot_id. KHÔNG gửi diện rộng, KHÔNG ghi Sheet.
        # - Chế độ Full Dispatch: Yêu cầu cung cấp snapshot_id đã preview và confirm=true -> Ghi Sheet (fail-closed) -> Gửi toàn bộ GTalk theo snapshot RAM -> Gửi Admin summary.
        if path in ("/api/pipeline/run", "/api/pipeline/preview", "/api/pipeline/dispatch"):
            # 1. SECURITY FAIL-CLOSED
            import hmac
            expected_secret = os.environ.get("SCHEDULER_SECRET")
            if not expected_secret:
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ [SECURITY] SCHEDULER_SECRET environment variable is missing. Fail-closed rejection.", flush=True)
                return self._reply(403, {"ok": False, "error_stage": "LOCK", "error": "Server security misconfigured: SCHEDULER_SECRET is not set"})

            x_scheduler_secret = self.headers.get("X-Scheduler-Secret", "")
            if not (x_scheduler_secret and hmac.compare_digest(x_scheduler_secret.encode("utf-8"), expected_secret.encode("utf-8"))):
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] 🚫 [SECURITY] Unauthorized pipeline attempt. Rejecting with 401.", flush=True)
                return self._reply(401, {"ok": False, "error_stage": "LOCK", "error": "Unauthorized: Invalid or missing X-Scheduler-Secret header"})

            qs = parse_qs(parsed.query)
            dry_run = qs.get("dry_run", ["false"])[0].lower() in ("true", "1", "yes")

            # Phân biệt rõ ràng mode: "run" (MẶC ĐỊNH PRODUCTION) vs "preview" (Kiểm thử) vs "dispatch" (Thủ công)
            mode_param = qs.get("action", qs.get("mode", [None]))[0]
            if path == "/api/pipeline/dispatch":
                pipeline_mode = "dispatch"
            elif path == "/api/pipeline/preview":
                pipeline_mode = "preview"
            elif mode_param:
                mode_lower = mode_param.strip().lower()
                if mode_lower in ("dispatch",):
                    pipeline_mode = "dispatch"
                elif mode_lower in ("preview", "sample"):
                    pipeline_mode = "preview"
                elif mode_lower in ("run", "production", "full"):
                    pipeline_mode = "run"
                else:
                    return self._reply(400, {"ok": False, "error": f"Mode '{mode_param}' không hợp lệ. Chỉ chấp nhận 'run', 'preview' hoặc 'dispatch'."})
            else:
                # MẶC ĐỊNH PRODUCTION PIPELINE DUY NHẤT KHI SCHEDULER GỌI
                pipeline_mode = "run"

            # ----------------------------------------------------
            # CHẾ ĐỘ 1: PRODUCTION MASTER PIPELINE DUY NHẤT (MẶC ĐỊNH CHO CLOUD SCHEDULER)
            # Luồng: Lock -> Chọn filter theo giờ VN -> Crawl API -> Verify (failed_bc/tổng/rỗng) -> Mapping Co_Cau -> Ghi Google Sheet -> Dispatch GTalk từ cùng snapshot RAM -> Gửi summary Admin -> Kết thúc.
            # ----------------------------------------------------
            if pipeline_mode == "run":
                filter_param = qs.get("filter", [None])[0]
                now_vn = datetime.datetime.now(VN_TZ)
                current_hour = now_vn.hour
                is_manual = False

                if filter_param:
                    filter_upper = filter_param.strip().upper()
                    if filter_upper not in ("ALL", "HOI_LAY"):
                        return self._reply(400, {
                            "ok": False,
                            "error_stage": "FILTER",
                            "error": f"Filter '{filter_param}' không hợp lệ. Chỉ chấp nhận 'ALL' hoặc 'HOI_LAY'."
                        })
                    filter_type = filter_upper
                    is_manual = True
                else:
                    if 6 <= current_hour < 14:
                        filter_type = "ALL"
                    elif 14 <= current_hour < 17:
                        filter_type = "HOI_LAY"
                    else:
                        return self._reply(400, {
                            "ok": False,
                            "error_stage": "FILTER",
                            "error": f"Ngoài khung giờ vận hành (06:00-16:59 VN). Giờ hiện tại: {now_vn.strftime('%H:%M:%S')}. Pipeline bị từ chối."
                        })

                if not _scrape_lock.acquire(blocking=False):
                    print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ [PIPELINE_RUN] LOCK -> FAILED (Locked)", flush=True)
                    return self._reply(429, {"ok": False, "error_stage": "LOCK", "error": "Đang có tiến trình cào/dispatch khác thực thi trên instance này"})

                pipeline_id = f"PIPE-{uuid.uuid4().hex[:8]}"
                t_pipe_start = time.time()
                now_str = now_vn.strftime("%d/%m/%Y %H:%M")
                run_mode_str = f"MANUAL ({filter_type})" if is_manual else f"AUTO ({filter_type})"
                _log_activity("PIPELINE", "START", f"[{pipeline_id}] Bắt đầu Master Pipeline [{run_mode_str}] (dry_run={dry_run})")

                err_stage = "INIT"
                try:
                    # BƯỚC 1: CRAWL API & VERIFY TỔNG / BƯU CỤC
                    err_stage = "CRAWLER"
                    ctp_dir = os.path.join(os.path.dirname(__file__), "Cao_Ton_Phieu")
                    if ctp_dir not in sys.path:
                        sys.path.insert(0, ctp_dir)
                    import cao_ton_phieu_api as ctp

                    t_crawl_start = time.time()
                    buu_cuc, tickets, meta, failed_bc = ctp.crawl_tickets_api(workers=8)
                    t_crawl_dur = round(time.time() - t_crawl_start, 2)
                    grand_total = meta.get("grand_total") if isinstance(meta, dict) else None
                    if failed_bc:
                        details = ", ".join(f"{bc}:{actual}/{expected}" for bc, expected, actual in failed_bc[:20])
                        raise RuntimeError(f"Crawler có {len(failed_bc)} bưu cục lỗi/lệch tổng; dừng pipeline ({details})")
                    if grand_total is not None and len(tickets) != int(grand_total):
                        raise RuntimeError(f"Tổng phiếu API ({len(tickets)}) lệch tổng web báo ({grand_total}); dừng pipeline")
                    if not tickets or len(tickets) == 0:
                        raise RuntimeError("Crawler trả về 0 ticket (Dữ liệu rỗng hoặc lỗi API nguồn)")

                    # Trigger State Transition Alerting
                    try:
                        check_and_notify_api_state_transition("HEALTHY", {
                            "latency_ms": round((time.time() - t_pipe_start) * 1000, 2),
                            "total_buu_cuc": len(buu_cuc),
                            "total_tickets_web": grand_total or len(tickets),
                            "run_id": pipeline_id
                        })
                    except Exception:
                        pass

                    # BƯỚC 2: MAPPING CO_CAU
                    err_stage = "MAPPING"
                    svc = get_sheets_service()
                    def _fetch_co_cau(s):
                        return s.spreadsheets().values().batchGet(
                            spreadsheetId=SHEET_ID,
                            ranges=["Co_Cau!A:J", "Co_Cau!S3:W30"]
                        ).execute()
                    co_cau_resp = execute_with_sheets_retry(_fetch_co_cau)
                    vranges = co_cau_resp.get("valueRanges", [])
                    cc_vals = vranges[0].get("values", []) if len(vranges) > 0 else []
                    tl_vals = vranges[1].get("values", []) if len(vranges) > 1 else []

                    co_cau = {}
                    if cc_vals:
                        hdr_cc = cc_vals[0]
                        def ci_cc(n): return hdr_cc.index(n) if n in hdr_cc else -1
                        i_wid = ci_cc("warehouse_id"); i_gid = ci_cc("gdv_pgdv_id")
                        i_gn = ci_cc("gdv_pgdv_name"); i_amid = ci_cc("area_manager_id")
                        i_amn = ci_cc("area_manager_name"); i_reg = ci_cc("region_shortname")
                        for r in cc_vals[1:]:
                            if i_wid >= 0 and i_wid < len(r) and str(r[i_wid]).strip():
                                def gv_cc(j): return (str(r[j]).strip() if 0 <= j < len(r) else "")
                                co_cau[str(r[i_wid]).strip()] = (gv_cc(i_gid), gv_cc(i_gn), gv_cc(i_amid), gv_cc(i_amn), gv_cc(i_reg))

                    name_of = {str(b.get("value", "")).strip(): b.get("label", "") for b in buu_cuc}
                    bc_label = {str(b.get("value", "")).strip(): b.get("label", "") for b in buu_cuc}

                    cnt_map = {}
                    for t in tickets:
                        bc = str(t.get("ma_buu_cuc", "")).strip()
                        loai = t.get("loai", "")
                        if bc not in cnt_map:
                            cnt_map[bc] = [0, 0, 0]
                        if loai == "Hối giao": cnt_map[bc][0] += 1
                        elif loai == "Hối lấy": cnt_map[bc][1] += 1
                        elif loai == "Hối trả": cnt_map[bc][2] += 1

                    au = meta.get("updated_at", now_vn.strftime("%Y-%m-%d %H:%M:%S"))
                    snapshot_id = f"SNAP-{now_vn.strftime('%Y%m%d-%H%M')}"

                    rows_ton = [["ma_buu_cuc", "ten_buu_cuc", "Hối giao", "Hối lấy", "Hối trả", "Tổng", "Tiền phạt", "cap_nhat_luc"]]
                    for b in buu_cuc:
                        bc = str(b.get("value", "")).strip()
                        c = cnt_map.get(bc, [0, 0, 0])
                        rows_ton.append([
                            bc, name_of.get(bc, b.get("label")), c[0], c[1], c[2],
                            b.get("total"), b.get("penalty"), au
                        ])

                    rows_ct = [[
                        "ma_buu_cuc", "ten_buu_cuc", "ma_ticket", "ma_don", "loai_phieu", "tien_phat",
                        "hạn_đóng", "trạng_thái", "url", "gdv_pgdv_id", "gdv_pgdv_name",
                        "area_manager_id", "area_manager_name", "region_shortname"
                    ]]
                    for t in tickets:
                        bc = str(t.get("ma_buu_cuc", ""))
                        cc_info = co_cau.get(bc, ("", "", "", "", ""))
                        rows_ct.append([
                            t.get("ma_buu_cuc"),
                            bc_label.get(bc, ""),
                            t.get("number", ""),
                            t.get("order_code", ""),
                            t.get("loai", ""),
                            t.get("penalty", 0),
                            t.get("close_esc", ""),
                            t.get("trang_thai", ""),
                            t.get("url", ""),
                            cc_info[0], cc_info[1], cc_info[2], cc_info[3], cc_info[4]
                        ])

                    # BƯỚC 3: GHI GOOGLE SHEET (Fail-closed: lỗi ghi Sheet sẽ dừng, KHÔNG gửi GTalk)
                    err_stage = "SHEET_WRITE"
                    if not dry_run:
                        ctp.ensure_tab(svc, ctp.TAB_TON)
                        ctp.write_tab(svc, ctp.TAB_TON, rows_ton)

                        ctp.ensure_tab(svc, ctp.TAB_CT)
                        ctp.write_tab(svc, ctp.TAB_CT, rows_ct)

                        try:
                            ctp.ghi_rp_theo_am(svc, tickets, co_cau, au, name_of)
                        except Exception as e_am:
                            print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] Lỗi ghi RP_theo_AM: {e_am}", flush=True)

                        try:
                            if hasattr(ctp, "ghi_rp_theo_vung"):
                                ctp.ghi_rp_theo_vung(svc, tickets, co_cau, au, name_of)
                        except Exception as e_vg:
                            print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] Lỗi ghi RP_theo_TroLy: {e_vg}", flush=True)

                    # BƯỚC 3.5: TỰ ĐỘNG BUILD & DEPLOY DASHBOARD LÊN CLOUDFLARE PAGES
                    err_stage = "DASHBOARD_BUILD_DEPLOY"
                    cf_deploy_id = None
                    built_artifact_hash = None
                    try:
                        import dashboard_sync as dsync
                        cached_dash = {
                            "hdr": rows_ct[0],
                            "rows": rows_ct[1:],
                            "ton_hdr": rows_ton[0],
                            "ton_rows": rows_ton[1:],
                            "co_cau_hdr": cc_vals[0] if cc_vals else [],
                            "co_cau_rows": cc_vals[1:] if len(cc_vals) > 1 else [],
                            "source_updated_at": au,
                            "snapshot_id": snapshot_id,
                        }
                        built_html = dsync._build_raw(cached_dash)
                        built_artifact_hash = hashlib.sha256(built_html.encode("utf-8")).hexdigest()
                        if not dry_run and os.environ.get("CF_ACCOUNT_ID") and os.environ.get("CF_API_TOKEN"):
                            cf_deploy_id = dsync._deploy_to_cloudflare(built_html)
                            print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] ✓ [DASHBOARD_DEPLOY] Tự động deploy Cloudflare Pages thành công. ID: {cf_deploy_id}", flush=True)
                    except Exception as e_dash:
                        print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠ [DASHBOARD_DEPLOY] Lỗi auto-deploy dashboard: {e_dash}", flush=True)

                    # BƯỚC 4: DISPATCH GTALK TỪ CÙNG DỮ LIỆU SNAPSHOT TRONG RAM (Không đọc lại Sheet)
                    err_stage = "DISPATCH"
                    headers_ct = rows_ct[0]
                    raw_tickets_ct = rows_ct[1:]

                    tro_ly_map = defaultdict(list)
                    curr_vung = ""
                    for r in tl_vals:
                        if len(r) >= 5:
                            vung = r[0].strip().upper()
                            if vung: curr_vung = vung
                            ma_nv = r[3].strip()
                            ten_nv = r[4].strip()
                            if curr_vung and ma_nv and ma_nv.isdigit():
                                tro_ly_map[curr_vung].append({"id": ma_nv, "name": ten_nv})

                    ams_data, vungs_data = aggregate_tickets(raw_tickets_ct, headers_ct, filter_type)

                    tasks = []
                    tpl_key_am = f"mau_am_{filter_type.lower()}"
                    tpl_am = DEFAULT_TEMPLATES.get(tpl_key_am, DEFAULT_TEMPLATES["mau_am_all"])
                    for aid, am in ams_data.items():
                        if am["total"] > 0:
                            msg = render_am_message(am, filter_type, tpl_am, now_str)
                            tasks.append({
                                "type": "AM",
                                "id": aid,
                                "name": am["name"],
                                "total": am["total"],
                                "content": msg
                            })

                    tpl_key_vung = f"mau_vung_{filter_type.lower()}"
                    tpl_vung = DEFAULT_TEMPLATES.get(tpl_key_vung, DEFAULT_TEMPLATES["mau_vung_all"])
                    for reg, vinfo in vungs_data.items():
                        if vinfo["total"] > 0:
                            msg = render_vung_message(reg, vinfo, filter_type, tpl_vung, now_str)
                            for tl in tro_ly_map.get(reg, []):
                                tasks.append({
                                    "type": "TRO_LY",
                                    "id": tl["id"],
                                    "name": f"{tl['name']} (Vùng {reg})",
                                    "total": vinfo["total"],
                                    "content": msg
                                })

                    success_count = 0
                    fail_count = 0
                    sent_details = []
                    admin_report_logs = []

                    if tasks:
                        tasks.sort(key=lambda x: x["total"], reverse=True)

                        def _p_worker(t):
                            time.sleep(0.15)
                            if dry_run:
                                return t, {"success": True, "msg_id": "dry_run"}
                            res = send_gtalk_message(t["id"], t["content"])
                            return t, res

                        with ThreadPoolExecutor(max_workers=5) as executor:
                            futures = [executor.submit(_p_worker, t) for t in tasks]
                            for f in as_completed(futures):
                                t, r = f.result()
                                if r.get("success"):
                                    success_count += 1
                                else:
                                    fail_count += 1
                                    sent_details.append(f"{t['id']} ({t['name']}): {r.get('error')}")

                    # Tính toán số liệu SLA cho admin_meta
                    total_phat_val = sum(int(t.get("penalty", 0) or 0) for t in tickets)
                    tre_sla_val = sum(1 for t in tickets if int(t.get("penalty", 0) or 0) > 0)
                    chua_sla_val = len(tickets) - tre_sla_val

                    # Gửi đúng 3 loại báo cáo giám sát cho 2 Admin bất biến (3049378 & 3026736), tổng cộng 6 tin
                    admin_meta = {
                        "api_status": "HEALTHY",
                        "auth_status": "PASS",
                        "latency_ms": round(t_crawl_dur * 1000, 1),
                        "total_buu_cuc": len(buu_cuc),
                        "total_tickets": len(tickets),
                        "total_phat": total_phat_val,
                        "tre_sla": tre_sla_val,
                        "chua_tre_sla": chua_sla_val,
                        "failed_bc_count": len(failed_bc),
                        "run_id": pipeline_id,
                        "snapshot_id": snapshot_id,
                        "source_updated_at": au,
                        "built_at": now_str,
                        "deployed_at": now_str if cf_deploy_id else "",
                        "artifact_hash": built_artifact_hash or "N/A",
                        "filter": filter_type,
                        "timestamp": now_str,
                        "revision": os.environ.get("K_REVISION", "local")
                    }
                    admin_report_logs = send_admin_monitoring_reports(
                        ams_data, vungs_data, tro_ly_map, admin_meta, dry_run=dry_run
                    )

                    total_pipe_dur = round(time.time() - t_pipe_start, 2)
                    _log_activity("PIPELINE", "SUCCESS", f"[{pipeline_id}] Hoàn tất ({run_mode_str}): {len(tickets)} tickets, {success_count}/{len(tasks)} GTalk, {total_pipe_dur}s")

                    return self._reply(200, {
                        "ok": True,
                        "pipeline_id": pipeline_id,
                        "snapshot_id": snapshot_id,
                        "filter": filter_type,
                        "mode": "PRODUCTION" if not is_manual else f"MANUAL_{filter_type}",
                        "tickets_count": len(tickets),
                        "warehouses_count": len(buu_cuc),
                        "gtalk_total": len(tasks),
                        "gtalk_sent": success_count,
                        "gtalk_failed": fail_count,
                        "admin_reports_sent": len(admin_report_logs),
                        "admin_report_logs": admin_report_logs,
                        "dashboard_deployed": False,
                        "duration_seconds": total_pipe_dur
                    })

                except Exception as ex:
                    try:
                        check_and_notify_api_state_transition("FAILED", {
                            "latency_ms": round((time.time() - t_pipe_start) * 1000, 2),
                            "total_buu_cuc": 0,
                            "total_tickets_web": 0,
                            "run_id": pipeline_id
                        })
                    except Exception:
                        pass
                    total_pipe_dur = round(time.time() - t_pipe_start, 2)
                    _log_activity("PIPELINE", "FAILED", f"[{pipeline_id}] Lỗi pipeline ({err_stage}): {ex}")
                    return self._reply(500, {
                        "ok": False,
                        "error_stage": err_stage,
                        "error": str(ex),
                        "duration_seconds": total_pipe_dur
                    })
                finally:
                    try:
                        _scrape_lock.release()
                    except Exception:
                        pass

            # ----------------------------------------------------
            # CHẾ ĐỘ A: PREVIEW / ADMIN-ONLY (MẶC ĐỊNH AN TOÀN)
            # ----------------------------------------------------
            if pipeline_mode == "preview":
                filter_param = qs.get("filter", [None])[0]
                now_vn = datetime.datetime.now(VN_TZ)
                current_hour = now_vn.hour
                is_manual = False

                if filter_param:
                    filter_upper = filter_param.strip().upper()
                    if filter_upper not in ("ALL", "HOI_LAY"):
                        return self._reply(400, {
                            "ok": False,
                            "error_stage": "FILTER",
                            "error": f"Filter '{filter_param}' không hợp lệ. Chỉ chấp nhận 'ALL' hoặc 'HOI_LAY'."
                        })
                    filter_type = filter_upper
                    is_manual = True
                else:
                    if 6 <= current_hour < 14:
                        filter_type = "ALL"
                    elif 14 <= current_hour < 17:
                        filter_type = "HOI_LAY"
                    else:
                        return self._reply(400, {
                            "ok": False,
                            "error_stage": "FILTER",
                            "error": f"Ngoài khung giờ vận hành (06:00-16:59 VN). Giờ hiện tại: {now_vn.strftime('%H:%M:%S')}. Pipeline bị từ chối."
                        })

                if not _scrape_lock.acquire(blocking=False):
                    print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ [PIPELINE_PREVIEW] LOCK -> FAILED (Locked)", flush=True)
                    return self._reply(429, {"ok": False, "error_stage": "LOCK", "error": "Đang có tiến trình ingestion/pipeline khác thực thi trên instance này"})

                pipeline_id = f"PIPE-{uuid.uuid4().hex[:8]}"
                t_pipe_start = time.time()
                now_str = now_vn.strftime("%d/%m/%Y %H:%M")
                _log_activity("PIPELINE_PREVIEW", "START", f"[{pipeline_id}] Bắt đầu Pipeline Preview ({filter_type}, dry_run={dry_run})")

                err_stage = "INIT"
                try:
                    err_stage = "CRAWLER"
                    ctp_dir = os.path.join(os.path.dirname(__file__), "Cao_Ton_Phieu")
                    if ctp_dir not in sys.path:
                        sys.path.insert(0, ctp_dir)
                    import cao_ton_phieu_api as ctp

                    buu_cuc, tickets, meta, failed_bc = ctp.crawl_tickets_api(workers=8)
                    grand_total = meta.get("grand_total") if isinstance(meta, dict) else None
                    if failed_bc:
                        details = ", ".join(f"{bc}:{actual}/{expected}" for bc, expected, actual in failed_bc[:20])
                        raise RuntimeError(f"Crawler có {len(failed_bc)} bưu cục lỗi/lệch tổng; dừng preview ({details})")
                    if grand_total is not None and len(tickets) != int(grand_total):
                        raise RuntimeError(f"Tổng phiếu API ({len(tickets)}) lệch tổng web báo ({grand_total}); dừng preview")
                    if not tickets or len(tickets) == 0:
                        raise RuntimeError("Crawler trả về 0 ticket (Dữ liệu rỗng hoặc lỗi API nguồn)")

                    # Trigger duy nhất cho State Transition Alerting (Production trigger từ Master Pipeline)
                    try:
                        check_and_notify_api_state_transition("HEALTHY", {
                            "latency_ms": round((time.time() - t_pipe_start) * 1000, 2),
                            "total_buu_cuc": len(buu_cuc),
                            "total_tickets_web": grand_total or len(tickets),
                            "run_id": pipeline_id
                        })
                    except Exception:
                        pass

                    err_stage = "MAPPING"
                    svc = get_sheets_service()
                    def _fetch_co_cau(s):
                        return s.spreadsheets().values().batchGet(
                            spreadsheetId=SHEET_ID,
                            ranges=["Co_Cau!A:J", "Co_Cau!S3:W30"]
                        ).execute()
                    co_cau_resp = execute_with_sheets_retry(_fetch_co_cau)
                    vranges = co_cau_resp.get("valueRanges", [])
                    cc_vals = vranges[0].get("values", []) if len(vranges) > 0 else []
                    tl_vals = vranges[1].get("values", []) if len(vranges) > 1 else []

                    co_cau = {}
                    if cc_vals:
                        hdr_cc = cc_vals[0]
                        def ci_cc(n): return hdr_cc.index(n) if n in hdr_cc else -1
                        i_wid = ci_cc("warehouse_id"); i_gid = ci_cc("gdv_pgdv_id")
                        i_gn = ci_cc("gdv_pgdv_name"); i_amid = ci_cc("area_manager_id")
                        i_amn = ci_cc("area_manager_name"); i_reg = ci_cc("region_shortname")
                        for r in cc_vals[1:]:
                            if i_wid >= 0 and i_wid < len(r) and str(r[i_wid]).strip():
                                def gv_cc(j): return (str(r[j]).strip() if 0 <= j < len(r) else "")
                                co_cau[str(r[i_wid]).strip()] = (gv_cc(i_gid), gv_cc(i_gn), gv_cc(i_amid), gv_cc(i_amn), gv_cc(i_reg))

                    name_of = {str(b.get("value", "")).strip(): b.get("label", "") for b in buu_cuc}
                    bc_label = {str(b.get("value", "")).strip(): b.get("label", "") for b in buu_cuc}

                    cnt_map = {}
                    for t in tickets:
                        bc = str(t.get("ma_buu_cuc", "")).strip()
                        loai = t.get("loai", "")
                        if bc not in cnt_map:
                            cnt_map[bc] = [0, 0, 0]
                        if loai == "Hối giao": cnt_map[bc][0] += 1
                        elif loai == "Hối lấy": cnt_map[bc][1] += 1
                        elif loai == "Hối trả": cnt_map[bc][2] += 1

                    au = meta.get("updated_at", now_vn.strftime("%Y-%m-%d %H:%M:%S"))
                    snapshot_id = f"SNAP-{now_vn.strftime('%Y%m%d-%H%M%S')}"

                    rows_ton = [["ma_buu_cuc", "ten_buu_cuc", "Hối giao", "Hối lấy", "Hối trả", "Tổng", "Tiền phạt", "cap_nhat_luc"]]
                    for b in buu_cuc:
                        bc = str(b.get("value", "")).strip()
                        c = cnt_map.get(bc, [0, 0, 0])
                        rows_ton.append([
                            bc, name_of.get(bc, b.get("label")), c[0], c[1], c[2],
                            b.get("total"), b.get("penalty"), au
                        ])

                    rows_ct = [[
                        "ma_buu_cuc", "ten_buu_cuc", "ma_ticket", "ma_don", "loai_phieu", "tien_phat",
                        "hạn_đóng", "trạng_thái", "url", "gdv_pgdv_id", "gdv_pgdv_name",
                        "area_manager_id", "area_manager_name", "region_shortname"
                    ]]
                    for t in tickets:
                        bc = str(t.get("ma_buu_cuc", ""))
                        cc_info = co_cau.get(bc, ("", "", "", "", ""))
                        rows_ct.append([
                            t.get("ma_buu_cuc"),
                            bc_label.get(bc, ""),
                            t.get("number", ""),
                            t.get("order_code", ""),
                            t.get("loai", ""),
                            t.get("penalty", 0),
                            t.get("close_esc", ""),
                            t.get("trang_thai", ""),
                            t.get("url", ""),
                            cc_info[0], cc_info[1], cc_info[2], cc_info[3], cc_info[4]
                        ])

                    headers_ct = rows_ct[0]
                    raw_tickets_ct = rows_ct[1:]

                    tro_ly_map = defaultdict(list)
                    curr_vung = ""
                    for r in tl_vals:
                        if len(r) >= 5:
                            vung = r[0].strip().upper()
                            if vung: curr_vung = vung
                            ma_nv = r[3].strip()
                            ten_nv = r[4].strip()
                            if curr_vung and ma_nv and ma_nv.isdigit():
                                tro_ly_map[curr_vung].append({"id": ma_nv, "name": ten_nv})

                    ams_data, vungs_data = aggregate_tickets(raw_tickets_ct, headers_ct, filter_type)

                    tasks = []
                    tpl_key_am = f"mau_am_{filter_type.lower()}"
                    tpl_am = DEFAULT_TEMPLATES.get(tpl_key_am, DEFAULT_TEMPLATES["mau_am_all"])
                    for aid, am in ams_data.items():
                        if am["total"] > 0:
                            msg = render_am_message(am, filter_type, tpl_am, now_str)
                            tasks.append({
                                "type": "AM",
                                "id": aid,
                                "name": am["name"],
                                "total": am["total"],
                                "content": msg
                            })

                    tpl_key_vung = f"mau_vung_{filter_type.lower()}"
                    tpl_vung = DEFAULT_TEMPLATES.get(tpl_key_vung, DEFAULT_TEMPLATES["mau_vung_all"])
                    for reg, vinfo in vungs_data.items():
                        if vinfo["total"] > 0:
                            msg = render_vung_message(reg, vinfo, filter_type, tpl_vung, now_str)
                            for tl in tro_ly_map.get(reg, []):
                                tasks.append({
                                    "type": "TRO_LY",
                                    "id": tl["id"],
                                    "name": f"{tl['name']} (Vùng {reg})",
                                    "total": vinfo["total"],
                                    "content": msg
                                })

                    if tasks:
                        tasks.sort(key=lambda x: x["total"], reverse=True)
                        top_task = tasks[0]
                    else:
                        top_task = None

                    # Lưu snapshot vào bộ nhớ Staged Snapshots kèm TTL (30 phút)
                    with _STAGED_LOCK:
                        now_ts = time.time()
                        exp_keys = [k for k, v in _STAGED_SNAPSHOTS.items() if now_ts - v.get("created_at", 0) > _SNAPSHOT_TTL]
                        for k in exp_keys:
                            _STAGED_SNAPSHOTS.pop(k, None)

                        _STAGED_SNAPSHOTS[snapshot_id] = {
                            "created_at": now_ts,
                            "snapshot_id": snapshot_id,
                            "pipeline_id": pipeline_id,
                            "filter_type": filter_type,
                            "now_str": now_str,
                            "au": au,
                            "buu_cuc": buu_cuc,
                            "tickets": tickets,
                            "meta": meta,
                            "rows_ton": rows_ton,
                            "rows_ct": rows_ct,
                            "co_cau": co_cau,
                            "name_of": name_of,
                            "bc_label": bc_label,
                            "tasks": tasks,
                            "top_task": top_task
                        }

                    # GỬI DUY NHẤT 1 TIN MẪU CHO ADMIN (Không gửi recipients khác, không gửi summary)
                    sample_sent = False
                    if top_task:
                        top_approval_msg = f"*[MẪU DUYỆT TỰ ĐỘNG - TOP 1]*\n\n" + top_task["content"]
                        if not dry_run:
                            _log_activity("ADMIN_APPROVAL", "PREVIEW_SENT", f"[{pipeline_id}] Gửi tin mẫu Top 1 cho Admin {ADMIN_MA_NV} ({top_task['name']} - {top_task['total']} phiếu)")
                            send_gtalk_message(ADMIN_MA_NV, top_approval_msg)
                            sample_sent = True
                        else:
                            _log_activity("ADMIN_APPROVAL", "PREVIEW_DRY_RUN", f"[{pipeline_id}] Dry-run mẫu Top 1 cho Admin {ADMIN_MA_NV}")

                    total_dur = round(time.time() - t_pipe_start, 2)
                    _log_activity("PIPELINE_PREVIEW", "SUCCESS", f"[{pipeline_id}] Preview hoàn tất ({snapshot_id}): {len(tickets)} tickets, {len(tasks)} tasks dự kiến")

                    return self._reply(200, {
                        "ok": True,
                        "mode": "preview",
                        "pipeline_id": pipeline_id,
                        "snapshot_id": snapshot_id,
                        "filter": filter_type,
                        "tickets_count": len(tickets),
                        "warehouses_count": len(buu_cuc),
                        "sample_recipient": ADMIN_MA_NV if top_task else None,
                        "sample_target_name": top_task["name"] if top_task else None,
                        "sample_target_total": top_task["total"] if top_task else 0,
                        "tasks_count": len(tasks),
                        "sample_sent": sample_sent,
                        "dashboard_deployed": False,
                        "duration_seconds": total_dur
                    })

                except Exception as ex:
                    try:
                        check_and_notify_api_state_transition("FAILED", {
                            "latency_ms": round((time.time() - t_pipe_start) * 1000, 2),
                            "total_buu_cuc": 0,
                            "total_tickets_web": 0,
                            "run_id": pipeline_id
                        })
                    except Exception:
                        pass
                    total_dur = round(time.time() - t_pipe_start, 2)
                    _log_activity("PIPELINE_PREVIEW", "FAILED", f"[{pipeline_id}] Lỗi preview ({err_stage}): {ex}")
                    return self._reply(500, {
                        "ok": False,
                        "mode": "preview",
                        "error_stage": err_stage,
                        "error": str(ex),
                        "duration_seconds": total_dur
                    })
                finally:
                    try:
                        _scrape_lock.release()
                    except Exception:
                        pass

            # ----------------------------------------------------
            # CHẾ ĐỘ B: FULL DISPATCH (YÊU CẦU XÁC NHẬN RÕ RÀNG)
            # ----------------------------------------------------
            elif pipeline_mode == "dispatch":
                snapshot_id = qs.get("snapshot_id", [None])[0]
                confirm = qs.get("confirm", ["false"])[0].lower() in ("true", "1", "yes")

                if not snapshot_id or not confirm:
                    return self._reply(400, {
                        "ok": False,
                        "mode": "dispatch",
                        "error": "Full dispatch yêu cầu cung cấp đúng snapshot_id đã preview và tham số confirm=true"
                    })

                # Lấy snapshot từ RAM staged snapshots
                staged = None
                with _STAGED_LOCK:
                    staged = _STAGED_SNAPSHOTS.get(snapshot_id)
                    if staged and (time.time() - staged.get("created_at", 0) > _SNAPSHOT_TTL):
                        _STAGED_SNAPSHOTS.pop(snapshot_id, None)
                        staged = None

                if not staged:
                    return self._reply(400, {
                        "ok": False,
                        "mode": "dispatch",
                        "error": f"Snapshot '{snapshot_id}' không tồn tại hoặc đã hết hạn (> {_SNAPSHOT_TTL//60} phút). Vui lòng chạy preview để tạo snapshot mới."
                    })

                if not _scrape_lock.acquire(blocking=False):
                    return self._reply(429, {"ok": False, "mode": "dispatch", "error": "Đang có tiến trình khác thực thi trên instance này"})

                t_disp_start = time.time()
                dispatch_id = f"DISP-{uuid.uuid4().hex[:8]}"
                _log_activity("PIPELINE_DISPATCH", "START", f"[{dispatch_id}] Bắt đầu Full Dispatch cho {snapshot_id} (dry_run={dry_run})")

                err_stage = "INIT"
                try:
                    # BƯỚC 1: GHI GOOGLE SHEET TỪ SNAPSHOT TRONG RAM
                    err_stage = "SHEET_WRITE"
                    ctp_dir = os.path.join(os.path.dirname(__file__), "Cao_Ton_Phieu")
                    if ctp_dir not in sys.path:
                        sys.path.insert(0, ctp_dir)
                    import cao_ton_phieu_api as ctp

                    svc = get_sheets_service()
                    if not dry_run:
                        ctp.ensure_tab(svc, ctp.TAB_TON)
                        ctp.write_tab(svc, ctp.TAB_TON, staged["rows_ton"])

                        ctp.ensure_tab(svc, ctp.TAB_CT)
                        ctp.write_tab(svc, ctp.TAB_CT, staged["rows_ct"])

                        try:
                            ctp.ghi_rp_theo_am(svc, staged["tickets"], staged["co_cau"], staged["au"], staged["name_of"])
                        except Exception as e_am:
                            print(f"[WARN] Lỗi ghi RP_theo_AM: {e_am}", flush=True)

                        try:
                            if hasattr(ctp, "ghi_rp_theo_vung"):
                                ctp.ghi_rp_theo_vung(svc, staged["tickets"], staged["co_cau"], staged["au"], staged["name_of"])
                        except Exception as e_vg:
                            print(f"[WARN] Lỗi ghi RP_theo_TroLy: {e_vg}", flush=True)

                    # BƯỚC 2: DISPATCH GTALK TỪ SNAPSHOT TRONG RAM (Chỉ khi Sheet write thành công)
                    err_stage = "DISPATCH"
                    tasks = staged["tasks"]
                    success_count = 0
                    fail_count = 0
                    sent_details = []

                    def _d_worker(t):
                        time.sleep(0.15)
                        if dry_run:
                            return t, {"success": True, "msg_id": "dry_run"}
                        res = send_gtalk_message(t["id"], t["content"])
                        return t, res

                    with ThreadPoolExecutor(max_workers=5) as executor:
                        futures = [executor.submit(_d_worker, t) for t in tasks]
                        for f in as_completed(futures):
                            t, r = f.result()
                            if r.get("success"):
                                success_count += 1
                            else:
                                fail_count += 1
                                sent_details.append(f"{t['id']} ({t['name']}): {r.get('error')}")

                    # Gửi đúng 3 loại báo cáo giám sát cho 2 Admin bất biến (3049378 & 3026736), tổng cộng 6 tin
                    admin_meta = {
                        "api_status": "HEALTHY",
                        "auth_status": "PASS",
                        "latency_ms": 0,
                        "total_buu_cuc": staged.get("warehouses_count", 0),
                        "total_tickets": staged.get("tickets_count", 0),
                        "failed_bc_count": 0,
                        "run_id": dispatch_id,
                        "snapshot_id": snapshot_id,
                        "filter": staged.get("filter", "ALL"),
                        "timestamp": staged.get("now_str", _now().strftime("%d/%m/%Y %H:%M")),
                        "revision": os.environ.get("K_REVISION", "local")
                    }
                    admin_report_logs = send_admin_monitoring_reports(
                        staged.get("ams_data", {}), staged.get("vungs_data", {}), staged.get("tro_ly_map", {}), admin_meta, dry_run=dry_run
                    )

                    # Xóa snapshot sau khi đã dispatch thành công để chống replay
                    with _STAGED_LOCK:
                        _STAGED_SNAPSHOTS.pop(snapshot_id, None)

                    total_disp_dur = round(time.time() - t_disp_start, 2)
                    _log_activity("PIPELINE_DISPATCH", "SUCCESS", f"[{dispatch_id}] Hoàn tất ({snapshot_id}): {success_count}/{len(tasks)} sent, {total_disp_dur}s")

                    return self._reply(200, {
                        "ok": True,
                        "mode": "dispatch",
                        "snapshot_id": snapshot_id,
                        "gtalk_total": len(tasks),
                        "gtalk_sent": success_count,
                        "gtalk_failed": fail_count,
                        "admin_reports_sent": len(admin_report_logs),
                        "admin_report_logs": admin_report_logs,
                        "dashboard_deployed": False,
                        "duration_seconds": total_disp_dur
                    })

                except Exception as ex:
                    total_disp_dur = round(time.time() - t_disp_start, 2)
                    _log_activity("PIPELINE_DISPATCH", "FAILED", f"[{dispatch_id}] Lỗi dispatch ({err_stage}): {ex}")
                    return self._reply(500, {
                        "ok": False,
                        "mode": "dispatch",
                        "error_stage": err_stage,
                        "error": str(ex),
                        "duration_seconds": total_disp_dur
                    })
                finally:
                    try:
                        _scrape_lock.release()
                    except Exception:
                        pass
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] 🔓 [{pipeline_id}] PIPELINE_LOCK_RELEASED", flush=True)

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
                # Dùng crawler API mới làm đường chạy online duy nhất.
                # File cao_ton_phieu.py cũ chỉ giữ lại để đối chiếu, không dùng production.
                import cao_ton_phieu_api as ctp

                buu_cuc, tickets, meta, failed_bc = ctp.crawl_tickets_api(workers=8)
                grand_total = meta.get("grand_total") if isinstance(meta, dict) else None
                if failed_bc:
                    details = ", ".join(
                        f"{bc}:{actual}/{expected}" for bc, expected, actual in failed_bc[:20]
                    )
                    raise RuntimeError(
                        f"Crawler có {len(failed_bc)} bưu cục lỗi/lệch tổng; không ghi snapshot ({details})"
                    )
                if grand_total is not None and len(tickets) != int(grand_total):
                    raise RuntimeError(
                        f"Tổng phiếu API ({len(tickets)}) lệch tổng web báo ({grand_total}); không ghi snapshot"
                    )
                if not tickets or len(tickets) == 0:
                    raise RuntimeError("Crawler trả về 0 ticket (Dữ liệu rỗng hoặc lỗi API nguồn)")
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ [{run_id}] CRAWLER_SUCCESS ({len(tickets)} tickets, {len(buu_cuc)} bưu cục)", flush=True)

                # 4. Sheet Write Start & Execute (Fail-closed: crawler fail -> không chạy phần này)
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] 📊 [{run_id}] SHEET_WRITE_START", flush=True)
                svc = get_sheets_service()
                co_cau = ctp.load_co_cau_map(svc)
                name_of = {str(b.get("value", "")): b.get("label") for b in buu_cuc}
                bc_label = {str(b.get("value", "")): b.get("label", "") for b in buu_cuc}  # map BC -> ten chinh xac

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
                        t.get("ma_buu_cuc"),                                    # ma_buu_cuc
                        bc_label.get(bc, ""),                                   # ten_buu_cuc
                        t.get("number", ""),                                    # ma_ticket  (API field: number)
                        t.get("order_code", ""),                                # ma_don     (API field: order_code)
                        t.get("loai", ""),                                      # loai_phieu
                        t.get("penalty", 0),                                    # tien_phat  (API field: penalty)
                        t.get("close_esc", ""),                                 # hạn_đóng   (API field: close_esc)
                        t.get("trang_thai", ""),                                # trạng_thái
                        t.get("url", ""),                                       # url
                        cc_info[0], cc_info[1], cc_info[2], cc_info[3], cc_info[4]  # gdv_id, gdv_name, am_id, am_name, region
                    ])
                ctp.write_tab(svc, ctp.TAB_CT, rows_ct)

                # Ghi RP_theo_AM
                try:
                    ctp.ghi_rp_theo_am(svc, tickets, co_cau, au, name_of)
                except Exception as e_am:
                    print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] [WARN] Lỗi ghi RP_theo_AM: {e_am}", flush=True)

                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ [{run_id}] SHEET_WRITE_SUCCESS (snapshot_id={snapshot_id}, cap_nhat_luc={au})", flush=True)

                # 5. Dashboard đang FREEZE: ingestion không tự deploy Cloudflare.
                print(f"[{_now().strftime('%Y-%m-%d %H:%M:%S')}] ⏸️ [{run_id}] DASHBOARD_DEPLOY_SKIPPED_FREEZE", flush=True)
                dashboard_deployed = False
                cf_deployment_id = "—"

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
                # Đọc Chi_tiet và Ton_phieu từ Google Sheet (không crawl)
                _svc = get_sheets_service()
                _res_ct = _svc.spreadsheets().values().get(
                    spreadsheetId=SHEET_ID, range="'Chi_tiet'!A:ZZ"
                ).execute()
                _vals_ct = _res_ct.get("values", [])
                _hdr  = _vals_ct[0] if _vals_ct else []
                _rows = _vals_ct[1:] if len(_vals_ct) > 1 else []

                _ton_hdr, _ton_rows = [], []
                try:
                    _res_ton = _svc.spreadsheets().values().get(
                        spreadsheetId=SHEET_ID, range="'Ton_phieu'!A:ZZ"
                    ).execute()
                    _vals_ton = _res_ton.get("values", [])
                    _ton_hdr  = _vals_ton[0] if _vals_ton else []
                    _ton_rows = _vals_ton[1:] if len(_vals_ton) > 1 else []
                except Exception as _e_ton:
                    print(f"[WARN] Không đọc được tab Ton_phieu: {_e_ton}", flush=True)

                cached = {
                    "hdr": _hdr,
                    "rows": _rows,
                    "ton_hdr": _ton_hdr,
                    "ton_rows": _ton_rows,
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
                        import cao_ton_phieu_api as ctp

                        buu_cuc, tickets, meta, failed_bc = ctp.crawl_tickets_api(workers=8)
                        grand_total = meta.get("grand_total") if isinstance(meta, dict) else None
                        if failed_bc:
                            details = ", ".join(
                                f"{bc}:{actual}/{expected}" for bc, expected, actual in failed_bc[:20]
                            )
                            raise RuntimeError(
                                f"Crawler có {len(failed_bc)} bưu cục lỗi/lệch tổng; không ghi snapshot ({details})"
                            )
                        if grand_total is not None and len(tickets) != int(grand_total):
                            raise RuntimeError(
                                f"Tổng phiếu API ({len(tickets)}) lệch tổng web báo ({grand_total}); không ghi snapshot"
                            )
                        if not tickets or len(tickets) == 0:
                            raise RuntimeError("Crawler trả về 0 ticket (Dữ liệu rỗng hoặc lỗi API nguồn)")
                        svc = get_sheets_service()
                        co_cau = ctp.load_co_cau_map(svc)
                        name_of = {str(b.get("value", "")): b.get("label") for b in buu_cuc}
                        bc_label = {str(b.get("value", "")): b.get("label", "") for b in buu_cuc}

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
                                t.get("ma_buu_cuc"),
                                bc_label.get(bc, ""),
                                t.get("number", ""),
                                t.get("order_code", ""),
                                t.get("loai", ""),
                                t.get("penalty", 0),
                                t.get("close_esc", ""),
                                t.get("trang_thai", ""),
                                t.get("url", ""),
                                cc_info[0], cc_info[1], cc_info[2], cc_info[3], cc_info[4]
                            ])
                        ctp.write_tab(svc, ctp.TAB_CT, rows_ct)
                            
                        # Ghi RP_theo_AM
                        try:
                            ctp.ghi_rp_theo_am(svc, tickets, co_cau, au, name_of)
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
