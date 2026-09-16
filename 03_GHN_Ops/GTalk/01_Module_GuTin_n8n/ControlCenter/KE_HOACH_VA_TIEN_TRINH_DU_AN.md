# GHN CONTROL CENTER V3 — ALL-IN-ONE GOOGLE CLOUD RUN

> **Mục tiêu:** Tự động hóa toàn diện hệ thống nhắc phiếu tồn Vận hành GHN (Hối giao, Hối lấy, Hối trả)
> cho 150+ Quản lý Khu vực (AM) và 14 Trợ lý Giám đốc Vùng qua GTalk.
> **Kiến trúc V3:** Hợp nhất 100% về **Google Cloud Platform (Cloud Run + Cloud Scheduler)** — $0đ/tháng, tốc độ bắn tin ~5-10 giây.

---

## 1. THÔNG TIN HỆ THỐNG LIVE (PRODUCTION)

- **Cloud Run URL:** `https://ghn-control-center-748472498606.asia-southeast1.run.app`
- **Health Check:** `https://ghn-control-center-748472498606.asia-southeast1.run.app/health` (`HTTP 200 OK`)
- **Dashboard Quản trị:** `https://ghn-control-center-748472498606.asia-southeast1.run.app/dashboard`
  - **User:** `admin` | **Pass:** `Ghn@2026!`
- **GCP Project:** `ghn-sheets-automation` (Region: `asia-southeast1`)
- **Chi phí vận hành:** **0 VNĐ / tháng** (Dùng < 1% Free tier của GCP).

---

## 2. BẢN ĐỒ KIẾN TRÚC HỆ THỐNG V3 (GCP UNIFIED)

```
┌────────────────────────────────────────────────────────────────────────┐
│                      GOOGLE CLOUD PLATFORM (GCP)                       │
│                                                                        │
│   ┌────────────────────────┐         ┌─────────────────────────────┐   │
│   │ Google Cloud Scheduler │ ──────► │   Google Cloud Run          │   │
│   │ (Cron: 6h, 9h, 12h,    │  POST   │   (All-in-One Python 3.11)  │   │
│   │        15h, 17h)       │         │                             │   │
│   └────────────────────────┘         │  1. Đọc Chi_tiet & Co_Cau   │   │
│                                      │  2. Lọc & Gom theo AM/Vùng  │   │
│                                      │  3. Render Markdown Template│   │
│                                      │  4. Bắn GTalk 172 tin (5s)  │   │
│                                      │  5. Báo cáo Admin (3049378) │   │
│                                      │  6. Ghi Log Google Sheet    │   │
│                                      └──────────────┬──────────────┘   │
│                                                     │                  │
│                                                     ▼                  │
│                                      ┌─────────────────────────────┐   │
│                                      │ Google Sheets Database      │   │
│                                      │ (Chi_tiet, Ton_phieu, Log)  │   │
│                                      └─────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. LỊCH CHẠY TỰ ĐỘNG TRÊN CLOUD SCHEDULER (2 JOBS)

| Job ID | Lịch chạy (Giờ VN) | Endpoint gọi | Trạng thái |
|---|---|---|:---:|
| **`ghn-cron-all`** | `0 6,9,12,17 * * 1-5` (6h, 9h, 12h, 17h T2-T6) | `POST /api/cycle/run?filter=ALL` | 🟢 **ENABLED** |
| **`ghn-cron-hoilay`** | `0 15 * * 1-5` (15h chiều T2-T6) | `POST /api/cycle/run?filter=HOI_LAY` | 🟢 **ENABLED** |

---

## 4. TỔNG KẾT DANH MỤC FILE TOÀN BỘ DỰ ÁN

| File / Thư mục | Chức năng |
|---|---|
| `control_center.py` | Toàn bộ mã nguồn All-in-One Python (HTTP Server + Gom phiếu + Gửi GTalk 5 luồng + Đồng bộ Sheet). |
| `Dockerfile` | Cấu hình đóng gói Container chuẩn Cloud Run Python 3.11-slim. |
| `requirements.txt` | Khai báo thư viện: `requests`, `google-auth`, `google-api-python-client`. |
| `.dockerignore` | Loại trừ file rác và tối ưu dung lượng source upload. |
| `Index.html` | Giao diện Dashboard Control Center quản trị. |
| `dashboard/` | Source code trang biểu đồ phục vụ Cloudflare Pages. |
