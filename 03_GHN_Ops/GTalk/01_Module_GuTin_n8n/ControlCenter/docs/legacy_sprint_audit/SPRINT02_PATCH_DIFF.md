# SPRINT02 PATCH DIFF — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-006 (Sprint-02 Hardening)  

## 1. Unified Diff Hoàn Chỉnh của Sprint-02 (`control_center.py`)

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
@@ -218,6 +218,8 @@
         print(json.dumps(measure_memory_usage(job_id=job_id, phase="FINISH"), ensure_ascii=False), flush=True)
         _log_sched(f"Cào dữ liệu: {len(buu_cuc)} BC · {len(tickets)} phiếu · phạt {meta.get('grand_penalty')}")
+        import gc
+        gc.collect()
         return {"ok": True, "buu_cuc": len(buu_cuc), "phieu": len(tickets), "meta": meta}
     except Exception as e:
         _log_sched(f"LỖI cào dữ liệu: {str(e)[:150]}")
@@ -1319,6 +1321,8 @@
     _cycle_state.update(running=False, finished=True, phase="done",
                         detail="Chu kỳ hoàn tất.", result=str(results)[:200])
     _log_sched(f"Chu kỳ hoàn tất ({flow_mode_am}/{flow_mode_vung}): kết quả gửi: {results}")
+    import gc
+    gc.collect()
     # Thông báo admin
     try:
         summary = f"🔄 *Chu kỳ tự động hoàn tất*\nAM: *{flow_mode_am}* | Vùng: *{flow_mode_vung}*\n📊 {results}"
```
