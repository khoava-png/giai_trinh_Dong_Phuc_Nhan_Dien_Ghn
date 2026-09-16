# HTTP ROUTE TEST — INC-P0-001

> **Order Reference:** ORDER-P0-004  
> **Date:** 15/09/2026  

## 1. Kết quả Automated Test qua HTTP Layer Thật
- **Mô phỏng Test Server HTTP (ThreadingHTTPServer):** Khởi động test server thực tế chạy lớp network layer, thực hiện gọi đồng thời `GET /api/sched/get` và `POST /api/sched/get`.
- **Kết quả xác nhận:**
  - Cả hai phương thức `GET` và `POST` đều điều hướng chính xác vào `action_sched_get()`.
  - HTTP Status Code: `200 OK`.
  - Content-Type: `application/json; charset=utf-8`.
  - Body trả về hợp lệ: `body.ok == true` và `body.sched` chứa đầy đủ cấu hình lịch (`enabled`, `dry_run`, `delay_min`, `hours_am_all`, `hours_vung_all`, `allowed_weekdays`, v.v.).
- **Không ghi nhận HTTP 404, 500 hay 502.**
