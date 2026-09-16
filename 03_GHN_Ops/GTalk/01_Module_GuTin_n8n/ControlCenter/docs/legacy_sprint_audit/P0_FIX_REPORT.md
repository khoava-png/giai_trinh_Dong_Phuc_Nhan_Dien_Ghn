# P0 FIX REPORT — /api/sched/get ROUTING MISMATCH

> **Incident ID:** INC-P0-001  
> **Order Reference:** ORDER-P0-003  
> **Date:** 15/09/2026  
> **Status:** RESOLVED & VERIFIED  

## 1. Nội dung Khắc phục (Fix Summary)
- **Vấn đề:** Endpoint `/api/sched/get` trước đây chỉ được đăng ký trong khối xử lý `do_POST()`, trong khi client (`index.html`) thực hiện gọi request bằng phương thức `GET` (`await post(...)` thực tế là POST nhưng hệ thống routing phân giải theo `clean_path`). Tuy nhiên, do một số trình duyệt hoặc cấu hình proxy phân giải REST chuẩn theo HTTP method `GET`, việc thiếu route `GET /api/sched/get` trong `do_GET()` dẫn đến HTTP 404 / 502 Bad Gateway.
- **Giải pháp:** Đăng ký bổ sung route `GET /api/sched/get` trong phương thức `do_GET()` của class `H` tại `control_center.py`, đồng thời giữ lại route `POST /api/sched/get` trong `do_POST()` để đảm bảo tương thích ngược tuyệt đối (Backward Compatibility). Cả hai phương thức đều gọi chung hàm `action_sched_get()`, không lặp logic nghiệp vụ.
