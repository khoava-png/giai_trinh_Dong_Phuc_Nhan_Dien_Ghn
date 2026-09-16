# CHANGE ZONES & SEQUENCE — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-003 (Change Impact Analysis)  

## 1. Phân vùng Thay đổi (Change Zones)

### A. Safe Change Zone (Vùng thay đổi an toàn)
- Các file tài liệu Markdown (`PROJECT_MASTER.md`, `TIEN_TRINH.md`, v.v.).
- Thư mục kiểm thử đơn vị (`tests/test_memory_meter.py`) và module đo lường độc lập (`memory_meter.py`).
- Giao diện tĩnh Cloudflare Pages (`index.html`).

### B. Restricted Change Zone (Vùng thay đổi hạn chế)
- Module đồng bộ Google Sheets API và cấu trúc Batching.
- Logic cấu hình Scheduler tick và Upstash Redis integration.
- Logic định dạng và gửi tin nhắn GTalk OA.

### C. Forbidden Change Zone (Vùng cấm thay đổi tuyệt đối)
- Các van an toàn bảo vệ Production hiện hữu: **KN1** (Backoff 60 phút sau 3 lần lỗi liên tiếp) và **KN2** (Cảnh báo tự động GTalk cho Admin `3049378`).
- Các biến môi trường cốt lõi trên Render (`OP_WEB_USER`, `OP_WEB_PASS`, `GOOGLE_KEY_FILE`, `GTALK_OA_TOKEN`).
- Cấu trúc endpoint `/api/health` dùng cho UptimeRobot giám sát chống sleep.

---

## 2. Thứ tự Triển khai An toàn (Change Sequence cho Backlog)

Để đảm bảo an toàn tuyệt đối cho Production, lộ trình thực hiện các Task trong Backlog phải tuân thủ nghiêm ngặt trình tự sau:

1. **Bước 1 (Testing & Validation - Safe Zone):** Hoàn thiện và mở rộng Unit Test trong `tests/` mà không chạm vào lõi server.
2. **Bước 2 (Memory Optimization - Restricted Zone):** Triển khai gỡ bỏ Global RAM Cache (`_cached_rows_ct`) và bổ sung `gc.collect()` tại mốc `JOB_FINISH` (Epic 5), có chạy thử nghiệm load trên local trước khi deploy.
3. **Bước 3 (Batching & Sheets Engine - Restricted Zone):** Tối ưu hóa API ghi tab `Chi_tiet` và `Ton_phieu` dạng Batch (Epic 2).
4. **Bước 4 (Apps Script & Formulas - External Zone):** Cấu hình công thức `QUERY`/`FILTER` tự động trên Google Sheets cho tab `RP_AM` và `RP_Vùng` (Epic 3).
5. **Bước 5 (Dashboard & Monitoring - Safe/Restricted Zone):** Kiểm tra hiển thị Dashboard Cloudflare Pages và chuẩn hóa log Redis (Epic 4 & 6).
