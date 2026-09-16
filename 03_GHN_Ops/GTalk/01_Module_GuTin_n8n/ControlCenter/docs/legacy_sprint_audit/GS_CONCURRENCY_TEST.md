# GS CONCURRENCY TEST — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-003  

## 1. Kiểm định Đồng thời (Concurrency Test)
- **Kịch bản kiểm tra:** Kích hoạt đồng thời các entry points (`POST /api/scrape`, `POST /api/sched/now`, và Scheduler worker tick).
- **Kết quả:**
  - Biến trạng thái `_cycle_state["running"]` phối hợp cùng `_sched_lock` (RLock) ngăn chặn hoàn toàn việc chạy 2 chu kỳ cào song song trên cùng một instance backend.
  - Không phát sinh xung đột ghi dữ liệu đồng thời lên Google Sheets trong phạm vi đơn tiến trình (single instance).
- **Trạng thái:** **PASS**.
