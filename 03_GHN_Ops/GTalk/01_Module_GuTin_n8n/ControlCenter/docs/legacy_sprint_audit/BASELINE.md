# BASELINE — GHN CONTROL CENTER PRODUCTION

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-002 (Baseline Freeze)  

## 1. Tổng quan Trạng thái Production (Production State Inventory)
Tài liệu này ghi nhận trạng thái đóng băng (Baseline) toàn bộ hệ thống GHN Control Center trước khi bước vào các giai đoạn can thiệp kỹ thuật tiếp theo.

## 2. Inventory Thành phần Production (BSL-INV-001 to BSL-INV-010)

| ID | Thành phần | Mô tả chi tiết trạng thái Baseline | Bằng chứng / Source Reference |
|---|---|---|---|
| **BSL-INV-001** | **Kiến trúc (Architecture)** | Monolithic Python Server sử dụng `ThreadingHTTPServer` (tiến trình đơn, xử lý đa luồng HTTP). | `control_center.py` (dòng 16, 1438) |
| **BSL-INV-002** | **Cấu hình (Config)** | Quản lý qua file cấu hình tĩnh và biến môi trường; không hardcode secret. | `control_center.py`, `KE_HOACH_VA_TIEN_TRINH_DU_AN.md` |
| **BSL-INV-003** | **Environment Variables** | Yêu cầu bắt buộc: `OP_WEB_USER`, `OP_WEB_PASS`, `GOOGLE_KEY_FILE`, `GTALK_OA_TOKEN`. | `KE_HOACH_VA_TIEN_TRINH_DU_AN.md` |
| **BSL-INV-004** | **Scheduler** | Tích hợp trong Python, tick kiểm tra mỗi 30 giây, kết hợp cơ chế sleep khởi động 90s và backoff 60 phút (KN1). | `control_center.py` |
| **BSL-INV-005** | **Redis** | Upstash Redis REST API dùng lưu trữ persistent trạng thái lịch trình (`control_center:sched`) và log hoạt động. | `control_center.py` |
| **BSL-INV-006** | **Google Sheets** | Sử dụng Google Sheets API v4 (`15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg`) qua Service Account. | `control_center.py` (dòng 231-232) |
| **BSL-INV-007** | **GTalk** | Tích hợp GTalk OA API gửi tin nhắn thông báo hối giao/lấy/trả cho AM và Trợ lý Vùng, kèm chế độ mẫu cho Admin (`3049378`). | `control_center.py` (dòng 515, 781) |
| **BSL-INV-008** | **Render Platform** | Render Free Container (512 MB RAM, giới hạn tiến trình đơn, không tự scale). | `PROJECT_MASTER.md`, `KE_HOACH_VA_TIEN_TRINH_DU_AN.md` |
| **BSL-INV-009** | **Memory & Logging** | Tích hợp module `memory_meter.py` xuất log JSON chuẩn 17 trường theo từng pha lifecycle. | `memory_meter.py`, `control_center.py` |
| **BSL-INV-010** | **Monitoring** | UptimeRobot ping mỗi 5 phút tới endpoint `/api/health` chống sleep container; cảnh báo tự động GTalk khi lỗi 3 lần (KN2). | `KE_HOACH_VA_TIEN_TRINH_DU_AN.md` |
