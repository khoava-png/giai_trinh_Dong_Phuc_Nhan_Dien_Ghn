# PRODUCTION EVIDENCE — INC-P0-001

> **Order Reference:** ORDER-P0-002  
> **Date:** 15/09/2026  

## 1. Bằng chứng Sản xuất (Production Evidence)
- **Source Code Evidence:**
  - `do_GET()` (dòng 988-1023 trong `control_center.py`) hoàn toàn không đăng ký tuyến đường `/api/sched/get`.
  - `do_POST()` (dòng 1024-1053 trong `control_center.py`) đăng ký tuyến đường `/api/sched/get` gọi `action_sched_get()`.
- **Hành vi Runtime:** Mọi request `GET /api/sched/get` từ giao diện dashboard hoặc client đều đi vào `do_GET()` và rơi vào nhánh `404 not found`, chứng minh HTTP 502/404 phát sinh tại tầng **Application Routing / Method Mismatch**, hoàn toàn không phải do Redis, Database hay Unhandled Exception bên trong business logic.
