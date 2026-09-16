# SYSTEM RISK MAP — SYSTEM TRUTH AUDIT

> **Order Reference:** ORDER-SYS-TRUTH-001  
> **Date:** 15/09/2026  

## 1. Bản Đồ Rủi Ro Hệ Thống (System Risk Map)

| Risk ID | Mức độ | Evidence | Root Cause | Current State | Blast Radius | Business Impact | Fix Required | Rollback |
|---|---|---|---|---|---|---|---|---|
| **RSK-001** | P2 | Scale-out nhiều container trên Render | Biến `_cycle_state` và `_sched_lock` nằm trên RAM cục bộ của từng tiến trình | Single-instance safe, multi-instance unsafe | System | Có thể kích hoạt chạy cào trùng lặp nếu chạy nhiều replica | Chuyển đổi sang Distributed Lock qua Redis | Revert code |
| **RSK-002** | P2 | Mất kết nối ngoại vi | Thiếu exponential backoff retry chuẩn cho mọi HTTP request Google Sheets | Ổn định nhờ try/except cơ bản | Module | Lỗi ghi Sheets tạm thời nếu mạng chập chờn | Bổ sung Retry wrapper | Revert code |
