# ROOT CAUSE ANALYSIS — /api/sched/get

> **Incident ID:** INC-P0-001  
> **Date:** 15/09/2026  

## 1. Nguyên nhân gốc rễ (Root Cause)
1. **Route & Handler Check:** Route `/api/sched/get` tồn tại trong `control_center.py` (dòng 1052) và gọi đúng handler `action_sched_get()`.
2. **Handler Logic:** `action_sched_get()` gọi `_load_sched()`.
3. **`_load_sched()` Flow:**
   - Đọc từ Upstash Redis qua `_redis_get("control_center:sched")`.
   - Nếu Redis trả về dữ liệu hỏng / JSON malformed hoặc network timeout (3s) gây ngoại lệ bên trong `_redis_get` (mặc dù có `try...except` trả về `None`), hệ thống fallback về đọc file local `sched.json`.
   - Nếu file `sched.json` bị thiếu, hỏng định dạng hoặc không đọc được, `_load_sched()` trả về `base` (default sched).
   - Tuy nhiên, nếu Upstash Redis REST API trả về HTTP status khác 200 (ví dụ 401 Unauthorized, 429 Rate Limit, hoặc 500 Upstash Error) mà không được bọc strict JSON decoding, hoặc khi `json.loads(val)` gặp chuỗi không hợp lệ, `_redis_get` bắt ngoại lệ và trả về `None`.
   - Điểm phát sinh HTTP 502 thực tế trên Render thường xảy ra khi **Upstash Redis timeout/rate limit** kết hợp với **lỗi timeout của Gunicorn/Reverse Proxy** khi chờ phản hồi HTTP từ Python `ThreadingHTTPServer` (đặc biệt khi request bị treo quá lâu ở blocking I/O call tới Redis REST API hoặc Google Sheets API trong các luồng đồng thời).
