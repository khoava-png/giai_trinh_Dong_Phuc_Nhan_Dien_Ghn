# -*- coding: utf-8 -*-
"""
ghn_vanhanh_api.py — Module chuyên trách bảo trì kết nối & tương tác API Web Vận Hành (ghn-vanhanh.dedyn.io).

Mục đích:
  - Đóng gói toàn bộ cấu hình API (Base URL, Credentials, Endpoints, Headers, Session).
  - Cung cấp các phương thức gọi API tối ưu (Đa luồng song song, Đóng gói nguyên tử Atomic Record).
  - Khi Web Vận Hành có sự thay đổi (đổi route, đổi tham số, đổi header, đổi logic cookie),
    chỉ cần cập nhật duy nhất file này mà không phải sửa logic xử lý Sheet hay GTalk.
"""

import time
import zoneinfo
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# Timezone chuẩn Việt Nam
VN_TZ = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")

# ============================================================
# CẤU HÌNH KẾT NỐI API WEB VẬN HÀNH
# ============================================================
WEB_BASE = "https://ghn-vanhanh.dedyn.io"
WEB_USER = "vanhanh"
WEB_PASS = "GHN@2026"

# Endpoint danh mục
ENDPOINT_LOGIN = f"{WEB_BASE}/login"
ENDPOINT_BUUCUC = f"{WEB_BASE}/api/buucuc"
ENDPOINT_SUMMARY = f"{WEB_BASE}/api/summary"
ENDPOINT_TICKETS = f"{WEB_BASE}/api/tickets"

# Danh sách phân loại lý do
LOAI_LIST = ["Hối giao", "Hối lấy", "Hối trả"]

# Ngưỡng phạt kịch khung (VNĐ)
CAP_PHAT = 200000

# Header chuẩn giả lập trình duyệt để tránh bị chặn WAF / CORS
DEFAULT_HEADERS = {
    "accept": "*/*",
    "accept-language": "vi,en;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "referer": f"{WEB_BASE}/",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def tinh_trang_thai(close_esc, penalty, cap_phat=CAP_PHAT):
    """
    Xác định trạng thái của phiếu chuẩn hóa theo mức tiền phạt:
      - tien_phat == 0:        'Chưa trễ hạn'
      - 0 < tien_phat < 200k:  'Trễ hạn còn cứu được'
      - tien_phat >= 200k:     'Phạt kịch khung'
    """
    try:
        pen = int(penalty or 0)
    except Exception:
        pen = 0

    if pen >= cap_phat:
        return "Phạt kịch khung"
    if pen > 0:
        return "Trễ hạn còn cứu được"
    return "Chưa trễ hạn"


class GHNVanHanhAPI:
    """
    Client giao tiếp chuẩn hóa với Web Vận Hành GHN.
    Hỗ trợ auto login, auto reconnect, gọi đơn lẻ và đa luồng song song.
    """
    def __init__(self, username=WEB_USER, password=WEB_PASS, base_url=WEB_BASE):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.is_logged_in = False

    def login(self, max_retries=3):
        """Đăng nhập lấy session cookie."""
        for attempt in range(max_retries):
            try:
                r = self.session.post(
                    f"{self.base_url}/login",
                    data={"username": self.username, "password": self.password},
                    timeout=30
                )
                if r.status_code in (200, 302) and "/login" not in r.url:
                    self.is_logged_in = True
                    return True
            except Exception:
                time.sleep(1)
        raise RuntimeError("Đăng nhập Web Vận Hành thất bại sau nhiều lần thử.")

    def ensure_login(self):
        """Đảm bảo session luôn hợp lệ."""
        if not self.is_logged_in:
            self.login()

    def get_buucuc_list(self, top=""):
        """
        Lấy danh sách tất cả các bưu cục có phiếu tồn và số liệu tổng hợp.
        Trả về dict: {buu_cuc, cols, grand_total, grand_penalty, updated_at}
        """
        self.ensure_login()
        url = f"{self.base_url}/api/buucuc"
        params = {"top": top} if top else {}
        r = self.session.get(url, params=params, timeout=45)
        if r.status_code != 200:
            self.login()
            r = self.session.get(url, params=params, timeout=45)
            
        data = r.json()
        try:
            gt = int(data.get("grand_total") or 0)
        except Exception:
            gt = 0
        try:
            gp = int(data.get("grand_penalty") or 0)
        except Exception:
            gp = 0
        return {
            "buu_cuc": data.get("buu_cuc", []),
            "cols": data.get("cols", LOAI_LIST),
            "grand_total": gt,
            "grand_penalty": gp,
            "updated_at": data.get("updated_at", "")
        }

    def get_tickets_by_bc(self, ma_bc, ly_do="__all__", max_retries=3):
        """
        Lấy phiếu tồn của 1 bưu cục theo lý do (Hối giao / Hối lấy / Hối trả / __all__).
        """
        self.ensure_login()
        url = f"{self.base_url}/api/tickets"
        params = {"bc": ma_bc, "ly_do": ly_do}
        
        for attempt in range(max_retries):
            try:
                r = self.session.get(url, params=params, timeout=30)
                if r.status_code == 200:
                    data = r.json()
                    if not isinstance(data, dict):
                        raise ValueError("API tickets trả về JSON không phải object")
                    data["_ok"] = True
                    return data
                elif r.status_code in (401, 403):
                    self.login()
            except Exception:
                time.sleep(0.8)
        # Không biến lỗi API thành một bưu cục '0 phiếu'. Caller phải chặn
        # snapshot nếu _ok=False để tránh ghi đè dữ liệu đúng bằng dữ liệu rỗng.
        return {"tickets": [], "total_penalty": 0, "_ok": False}

    def fetch_all_tickets_atomic(self, buu_cuc_list, max_workers=8, split_by_loai=True):
        """
        Cào toàn bộ vé tồn phiếu bằng Đa luồng song song (ThreadPoolExecutor).
        
        Quy tắc đóng gói nguyên tử (Atomic Tuple Binding):
          - Xử lý từng bưu cục độc lập trong 1 luồng riêng biệt.
          - Gán trực tiếp `ma_buu_cuc`, `ten_buu_cuc`, `loai`, `trang_thai` vào từng ticket item.
          - Triệt tiêu hoàn toàn rủi ro trôi dòng hoặc lệch cơ cấu giữa các bưu cục.
        
        Trả về:
          tickets: danh sách ticket hoàn chỉnh.
          failed_bc: danh sách bưu cục có phiếu nhưng không lấy được (nếu có).
        """
        self.ensure_login()
        active_bcs = [b for b in buu_cuc_list if (b.get("total") or 0) > 0]
        
        all_tickets = []
        failed_bc = []

        def _worker(b):
            bc = str(b.get("value", "")).strip()
            label = b.get("label", "")
            exp_total = b.get("total") or 0
            
            bc_tickets = []
            request_failed = False
            if split_by_loai:
                for loai in LOAI_LIST:
                    res = self.get_tickets_by_bc(bc, ly_do=loai)
                    if not res.get("_ok", False):
                        request_failed = True
                    for t in res.get("tickets", []):
                        bc_tickets.append({
                            "ma_buu_cuc": bc,
                            "ten_buu_cuc": label,
                            "number": str(t.get("number", "")).strip(),
                            "order_code": str(t.get("order_code", "")).strip(),
                            "title": t.get("title", ""),
                            "url": t.get("url", ""),
                            "penalty": int(t.get("penalty") or 0),
                            "close_esc": t.get("close_esc", ""),
                            "loai": loai,
                            "trang_thai": tinh_trang_thai(t.get("close_esc"), t.get("penalty") or 0)
                        })
            else:
                res = self.get_tickets_by_bc(bc, ly_do="__all__")
                request_failed = not res.get("_ok", False)
                for t in res.get("tickets", []):
                    t_loai = t.get("loai") or t.get("ly_do") or t.get("type") or "Hối giao"
                    bc_tickets.append({
                        "ma_buu_cuc": bc,
                        "ten_buu_cuc": label,
                        "number": str(t.get("number", "")).strip(),
                        "order_code": str(t.get("order_code", "")).strip(),
                        "title": t.get("title", ""),
                        "url": t.get("url", ""),
                        "penalty": int(t.get("penalty") or 0),
                        "close_esc": t.get("close_esc", ""),
                        "loai": t_loai,
                        "trang_thai": tinh_trang_thai(t.get("close_esc"), t.get("penalty") or 0)
                    })
                    
            return bc, exp_total, bc_tickets, request_failed

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_worker, b): b for b in active_bcs}
            for future in as_completed(futures):
                try:
                    bc, exp_total, t_list, request_failed = future.result()
                    all_tickets.extend(t_list)
                    # Chặn cả lỗi request và lệch tổng; không ghi snapshot thiếu.
                    if request_failed or len(t_list) != exp_total:
                        failed_bc.append((bc, exp_total, len(t_list)))
                except Exception as ex:
                    b_info = futures[future]
                    failed_bc.append((b_info.get("value"), b_info.get("total"), 0))

        return all_tickets, failed_bc
