# EXCEPTION CHAIN — INC-P0-001

> **Order Reference:** ORDER-P0-002  
> **Date:** 15/09/2026  

## 1. Chuỗi Ngoại lệ & Định tuyến (Exception & Routing Chain)
1. **Client Request:** Gửi `GET /api/sched/get`.
2. **Server Dispatcher (`H.do_GET` tại dòng 988):**
   - Kiểm tra đường dẫn `clean_path` (`/api/sched/get`).
   - Khớp khối điều kiện `if`, `elif clean_path.startswith('/assets/')`, `elif clean_path == '/api/health'`.
   - Không khớp bất kỳ điều kiện nào trong `do_GET()`.
3. **Fallback xử lý sai lệch phương thức (Routing Miss):**
   - Rơi vào khối `else:` (dòng 1023): gọi `_reply(self, 404, {"ok": False, "error": "not found"})`.
   - Nếu client/proxy kỳ vọng endpoint API trả về JSON chuẩn nhưng gặp mismatch HTTP method (GET thay vì POST), proxy của Render có thể trả về mã lỗi Gateway 502 Bad Gateway tùy theo cách phân giải response.
4. **Exception đầu tiên:** Routing Mismatch (Client gọi `GET` trong khi route được đăng ký dưới `do_POST`).
