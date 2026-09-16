# FAILURE RECOVERY REPORT — SYSTEM TRUTH AUDIT

> **Order Reference:** ORDER-SYS-TRUTH-001  
> **Date:** 15/09/2026  

## 1. Khảo sát Cơ chế Phục hồi Lỗi Google API (Failure Recovery Truth)
- **Retry & Backoff:** Trong module `cao_ton_phieu.py`, thao tác cào web có cơ chế retry tối đa 3 lần. Đối với Google Sheets API, các lệnh gọi hiện được bọc trong `try...except` với log cảnh báo (`_log_sched`).
- **Partial-write recovery:** Đã được xử lý triệt để thông qua việc thay thế `batchClear` bằng ghi đè nguyên tử `values.update` (`RAW`), ngăn chặn triệt để trạng thái trống trung gian (empty state).
- **Hạn chế hiện tại:** Chưa áp dụng một wrapper retry chung với exponential backoff toàn diện cho mọi lệnh gọi Google Sheets API REST riêng lẻ (được phân loại vào P2 / P3 technical debt).
