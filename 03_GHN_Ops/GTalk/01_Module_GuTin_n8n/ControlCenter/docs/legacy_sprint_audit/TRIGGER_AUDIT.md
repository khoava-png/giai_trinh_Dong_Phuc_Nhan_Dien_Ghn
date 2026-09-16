# TRIGGER AUDIT — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-001 (Google Sheets & Apps Script Full Audit)  

## 1. Kiểm định Triggers
- **Google Apps Script Triggers:** Không tồn tại (0 trigger).
- **Backend Scheduler Triggers:** Hệ thống sử dụng Python `_sched_worker()` chạy nền (tick mỗi 30 giây) kiểm tra thời gian hiện tại khớp với lịch trình (`sched.json` / Upstash Redis) để kích hoạt chu kỳ cào và gửi tin nhắn.
- **Concurrent Risk:** Đã có cơ chế khóa `_sched_lock` và trạng thái `_cycle_state["running"]` ngăn chặn việc kích hoạt trùng lặp đồng thời nhiều chu kỳ cào.
