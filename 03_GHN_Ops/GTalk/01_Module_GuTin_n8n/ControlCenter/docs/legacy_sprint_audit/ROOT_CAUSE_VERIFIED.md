# ROOT CAUSE VERIFIED — /api/sched/get

> **Incident ID:** INC-P0-001  
> **Order Reference:** ORDER-P0-002  
> **Date:** 15/09/2026  
> **Status:** VERIFIED & PROVEN  

## 1. Kết luận Root Cause Xác thực
Sau khi kiểm tra trực tiếp mã nguồn, cơ chế định tuyến (Routing), phương thức HTTP (`GET` vs `POST`), và cấu trúc exception handler:
- **Nguyên nhân chính xác:** Endpoint `/api/sched/get` trong `control_center.py` được định nghĩa bên trong phương thức **`do_POST()`** (dòng 1052). Do đó, khi trình duyệt hoặc client thực hiện request bằng phương thức **`GET /api/sched/get`**, phương thức **`do_GET()`** xử lý và **không tìm thấy route `/api/sched/get`** trong khối điều kiện của `do_GET()` (chỉ có `/`, `/index.html`, `/assets/*`, `/api/health`).
- **Hệ quả:** `do_GET()` trả về phản hồi **`404 Not found`** (hoặc nếu client gọi nhầm phương thức gây lỗi phân giải proxy phía Render, dẫn đến HTTP 502 Bad Gateway tùy thuộc vào cấu hình client proxy).
