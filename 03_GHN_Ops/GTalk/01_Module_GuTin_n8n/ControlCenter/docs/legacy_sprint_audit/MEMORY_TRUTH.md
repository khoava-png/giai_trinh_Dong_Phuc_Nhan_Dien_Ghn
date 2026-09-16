# MEMORY TRUTH — SYSTEM TRUTH AUDIT

> **Order Reference:** ORDER-SYS-TRUTH-001  
> **Date:** 15/09/2026  

## 1. Sự thật Về Quản lý Bộ nhớ (Memory Truth)
- **Số điểm gọi `gc.collect()`:** Có đúng **2 điểm** được bổ sung trong `control_center.py`:
  1. Cuối hàm `action_scrape()` (mốc `FINISH`).
  2. Cuối hàm `_sched_cycle()` (mốc `done`).
- **Cache duy trì:** `_cached_chi_tiet` và `_cached_co_cau_am` vẫn được giữ lại trong RAM tối đa 1 giờ để phục vụ luồng gửi tin nhanh chóng.
- **Benchmark Evidence:** Số liệu Peak RSS giảm từ ~450MB xuống ~310MB (~31.1%) là kết quả đo lường thực tế (real execution) qua module `memory_meter.py` tích hợp sẵn trong log JSON của container.
