# PROJECT REVIEW — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Status:** REVIEWED & COMPLETED  

## 1. Tổng quan dự hệ thống
GHN Control Center là hệ thống vận hành tự động hóa nhắc phiếu tồn (Hối giao, Hối lấy, Hối trả) cho 150+ Quản lý Khu vực (AM) và 14 Trợ lý Giám đốc Vùng qua GTalk OA, kết hợp cung cấp Dashboard trực quan trên Cloudflare Pages (`ghn-dashboard.pages.dev`).

## 2. Kiến trúc & Vận hành thực tế
- **Backend:** Python Standard Library (`http.server`, `ThreadingHTTPServer`), vận hành trên tiến trình đơn, tuân thủ mô hình Blocking I/O kết hợp Threading cho các request HTTP.
- **Scheduler & State:** Tích hợp trực tiếp trong backend Python, tick kiểm tra mỗi 30 giây, đồng bộ trạng thái qua Upstash Redis và file local `sched.json`.
- **Google Sheets:** Lưu trữ dữ liệu thô (`Chi_tiet`, `Ton_phieu`) qua Google Sheets API sử dụng Service Account (`ghn-sheet-bot@ghn-sheets-automation.iam.gserviceaccount.com`).
- **Dashboard:** Giao diện tĩnh deploy trên Cloudflare Pages (`ghn-dashboard.pages.dev`), đọc trực tiếp dữ liệu từ Google Sheets.
- **Monitoring & Safety Guards:** Đã tích hợp module `memory_meter.py` (chuẩn log JSON 17 trường), van an toàn KN1 (backoff 60 phút sau 3 lần lỗi liên tiếp) và KN2 (cảnh báo tự động GTalk cho Admin `3049378`).

## 3. Đánh giá hiện trạng
- Hệ thống đang chạy ổn định trên Render Free (512 MB RAM) nhờ các van an toàn KN1/KN2.
- Kiến trúc mục tiêu PA2 (Tách biệt tính toán báo cáo sang Google Sheets/Apps Script) đã được phê duyệt qua ADR-001 nhằm giải quyết triệt để rủi ro OOM Peak Memory.
