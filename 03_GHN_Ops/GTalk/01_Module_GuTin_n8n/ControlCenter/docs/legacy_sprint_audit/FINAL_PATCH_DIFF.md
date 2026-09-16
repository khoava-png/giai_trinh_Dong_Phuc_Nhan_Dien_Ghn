# FINAL PATCH DIFF — ORDER-ROOT-003

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-ROOT-003  

## 1. Unified Diff của Bản Patch Cuối Cùng (`Cao_Ton_Phieu/cao_ton_phieu.py`)

```diff
--- cao_ton_phieu.py.bak
+++ cao_ton_phieu.py
@@ -191,7 +191,16 @@
 def write_tab(svc, tab, values, only_clear_rows=0):
-    """Ghi dữ liệu vào tab. Sử dụng values.update nguyên tử (không clear trước) để triệt tiêu trạng thái rỗng (empty state)."""
+    """Ghi đè snapshot nguyên tử kèm dọn dẹp phần đuôi thừa (stale tail cleanup) chính xác trên cột A:N."""
+    res = svc.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'!A:A").execute()
+    old_rows = len(res.get("values", []))
+    new_rows = len(values) if values else 0
     if values:
         svc.spreadsheets().values().update(
             spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'!A1",
             valueInputOption="RAW", body={"values": values}).execute()
+    if old_rows > new_rows:
+        clear_range = f"'{tab}'!A{new_rows + 1}:N{old_rows}"
+        svc.spreadsheets().values().clear(
+            spreadsheetId=SPREADSHEET_ID, range=clear_range).execute()
```
