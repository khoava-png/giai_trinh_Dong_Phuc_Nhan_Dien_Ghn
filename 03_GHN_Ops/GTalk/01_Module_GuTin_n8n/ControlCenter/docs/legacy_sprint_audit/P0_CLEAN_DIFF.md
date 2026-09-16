# P0 CLEAN DIFF — INC-P0-001

> **Order Reference:** ORDER-P0-004  
> **Date:** 15/09/2026  
> **Status:** CLEANED & VERIFIED  

## 1. Xác thực Working Tree & Phạm vi Bản vá P0
- Toàn bộ các thay đổi không liên quan đến lỗi routing (như `gc.collect()`, memory optimization, PA2) đã được loại bỏ hoàn toàn khỏi working tree.
- Bản vá P0 cuối cùng chỉ chứa đúng một thay đổi duy nhất để route `GET /api/sched/get` tới `action_sched_get()`, đồng thời giữ nguyên `POST /api/sched/get` để đảm bảo backward compatibility tuyệt đối với hàm `post()` trong `index.html`.

## 2. Unified Diff Cuối Cùng (`control_center.py`)
```diff
--- control_center.py
+++ control_center.py
@@ -1020,6 +1020,8 @@
                 _reply(self, 404, {"ok": False, "error": "asset not found"})
         elif clean_path == "/api/health":
             _reply(self, 200, {"ok": True, "time": _now().strftime("%d/%m/%Y %H:%M:%S")})
+        elif clean_path == "/api/sched/get":
+            _reply(self, 200, action_sched_get())
         else:
             _reply(self, 404, {"ok": False, "error": "not found"})
     def do_POST(self):
```
