# HYPOTHESIS MATRIX — INC-P0-001

> **Order Reference:** ORDER-P0-002  
> **Date:** 15/09/2026  

## 1. Bảng Ma trận Kiểm tra Giả thuyết (Hypothesis Matrix)

| Giả thuyết ID | Tên giả thuyết | Bằng chứng thực tế (Evidence) | Verdict |
|---|---|---|---|
| **A** | Redis Timeout | `_redis_get` có timeout 3s và try-except fallback an toàn. | **REJECTED** |
| **B** | Redis Authentication | `_redis_get` gửi Bearer token đầy đủ; nếu sai trả None chứ không sập HTTP server. | **REJECTED** |
| **C** | Redis Rate Limit | Không có log 429 từ Upstash. | **REJECTED** |
| **D** | Malformed JSON | `_redis_get` kiểm tra `json.loads` và catch exception an toàn. | **REJECTED** |
| **E** | Missing Environment Variable | `UPSTASH_URL`/`TOKEN` thiếu thì trả None, có fallback file `sched.json`. | **REJECTED** |
| **F** | Deadlock | `_sched_lock` dùng `threading.RLock()` chuẩn. | **REJECTED** |
| **G** | Blocking I/O | Timeout Redis là 3s, không gây treo vĩnh viễn. | **REJECTED** |
| **H** | Thread Starvation | `ThreadingHTTPServer` cấp thread mới cho mỗi request. | **REJECTED** |
| **I** | Render Instance Restart | Render logs ổn định, UptimeRobot ping đều đặn. | **REJECTED** |
| **J** | Unhandled Exception / Routing Mismatch | Route `/api/sched/get` nằm trong `do_POST()` nhưng client gọi `GET /api/sched/get`, dẫn đến `do_GET()` trả 404/502. | **CONFIRMED** |
