# DEPLOYMENT PLAN — GHN CONTROL CENTER

> **Last Updated:** 15/09/2026
> **Current Version:** v2.0.0-PA2
> **Current Phase:** Phase 2
> **Progress:** 78%
> **Next Action:** Chuẩn bị deploy staging/production cho Sprint 2.
> **Decision Log:** Quy trình triển khai zero-downtime lên Render.

- Triển khai ngoài giờ cao điểm vận hành (sau 22:00 hoặc trước 06:00 sáng).
- Sử dụng cơ chế auto-deploy trên Render thông qua nhánh release.
- Kiểm tra ngay lập tức endpoint `/api/health` và log JSON Memory Meter.
