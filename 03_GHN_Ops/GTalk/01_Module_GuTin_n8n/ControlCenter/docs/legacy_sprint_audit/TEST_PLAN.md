# TEST PLAN — GHN CONTROL CENTER

> **Last Updated:** 15/09/2026
> **Current Version:** v2.0.0-PA2
> **Current Phase:** Phase 2
> **Progress:** 78%
> **Next Action:** Chạy Unit Test kiểm thử code khi implement.
> **Decision Log:** Chuẩn hóa chiến lược kiểm thử từ Unit Test đến Load Test.

- **Unit Test:** unittest cho module `memory_meter.py` và module cào (đạt 100% coverage).
- **Integration Test:** Kiểm thử kết nối Google Sheets (Dry-run).
- **Load Test:** Mô phỏng 5-10 chu kỳ cào liên tiếp trên local với dữ liệu giả lập.
- **Production Verification:** Theo dõi log JSON Memory Meter trên Render.
- **Rollback Test:** Kiểm tra quy trình khôi phục bản backup.
