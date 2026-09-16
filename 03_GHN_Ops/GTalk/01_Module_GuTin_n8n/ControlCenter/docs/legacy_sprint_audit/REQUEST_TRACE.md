# REQUEST TRACE — /api/sched/get

> **Incident ID:** INC-P0-001  
> **Date:** 15/09/2026  

## 1. Theo vết toàn bộ Request (Request Trace Workflow)

1. **Browser / Client:** Gửi HTTP GET request tới `https://ghn-control-center.onrender.com/api/sched/get`.
2. **Render Reverse Proxy (Load Balancer):** Nhận request, chuyển tiếp tới Python ThreadingHTTPServer bên trong container.
3. **Route Matching (`do_GET` tại dòng 1052):** Khớp điều kiện `elif p == "/api/sched/get":`.
4. **Handler Invocation (`action_sched_get()` tại dòng 1189):**
   - Gọi `_load_sched()`.
5. **Business Service / Redis (`_load_sched` -> `_redis_get`):**
   - Gói HTTP GET request tới Upstash Redis (`{UPSTASH_URL}/get/control_center:sched`).
   - *Điểm phát sinh nghẽn/timeout:* Nếu Upstash Redis phản hồi chậm hơn timeout 3s hoặc gặp lỗi mạng, `_redis_get` bắt lỗi và trả về `None`.
6. **Fallback Mechanism:**
   - Đọc tệp local `sched.json` (`SCHED_FILE`).
   - Trả về dictionary cấu hình lịch.
7. **Response Serialization & Delivery:**
   - Đóng gói JSON `{"ok": true, "sched": s}` qua hàm `_reply(self, 200, ...)`.
   - Trả về HTTP 200 OK cho Client.
   - *Nguyên nhân gây HTTP 502:* Nếu toàn bộ các luồng trong ThreadingHTTPServer bị kẹt (blocking do I/O bên ngoài), Render Gateway chờ quá thời gian timeout (gateway timeout) và trả về HTTP 502 Bad Gateway.
