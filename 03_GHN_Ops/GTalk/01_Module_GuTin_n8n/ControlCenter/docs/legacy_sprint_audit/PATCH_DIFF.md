# PATCH DIFF — /api/sched/get ROUTING FIX

> **Order Reference:** ORDER-P0-003  
> **Date:** 15/09/2026  

## 1. Unified Diff của Bản Patch (`control_center.py`)

```diff
--- control_center.py.bak
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
