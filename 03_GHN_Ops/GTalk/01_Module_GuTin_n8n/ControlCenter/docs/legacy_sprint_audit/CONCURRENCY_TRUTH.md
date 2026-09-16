# CONCURRENCY TRUTH — SYSTEM TRUTH AUDIT

> **Order Reference:** ORDER-SYS-TRUTH-001  
> **Date:** 15/09/2026  

## 1. Khảo sát Cơ chế Đồng thời (Concurrency Truth)
- **Entry Points:** Scheduler worker (`_sched_worker`), Manual Scrape (`POST /api/scrape`), Scheduler Now (`POST /api/sched/now`).
- **Khóa bảo vệ:** Trạng thái `_cycle_state["running"]` phối hợp cùng `_sched_lock` (RLock).
- **Phân biệt Single-Process vs Distributed Safety:**
  - Hệ thống vận hành an toàn tuyệt đối trong mô hình **single-process** (đúng với hạ tầng Render Free 1 container).
  - Tuy nhiên, hệ thống **không đạt distributed safety** nếu scale-out nhiều replica trên Cloud (do khóa nằm trên RAM cục bộ của từng container). Hiện tại trên Render Free, điều này không xảy ra.
