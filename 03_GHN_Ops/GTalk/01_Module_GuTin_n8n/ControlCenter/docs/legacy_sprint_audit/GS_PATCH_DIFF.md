# GS PATCH DIFF — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-003  

## 1. Unified Diff của Bản Patch Khắc phục Partial Write (`Cao_Ton_Phieu/cao_ton_phieu.py`)

```diff
--- cao_ton_phieu.py.bak
+++ cao_ton_phieu.py
@@ -191,10 +191,7 @@
 def write_tab(svc, tab, values, only_clear_rows=0):
-    """Ghi dữ liệu vào tab. Mặc định clear A:ZZ rồi ghi.
-    only_clear_rows>0: chỉ clear đúng số dòng (từ A1), giữ nguyên các cột khác (vd cột I-M công thức)."""
-    if only_clear_rows:
-        svc.spreadsheets().values().batchClear(
-            spreadsheetId=SPREADSHEET_ID,
-            body={"ranges": [f"'{tab}'!A1:H{only_clear_rows}"]}).execute()
-    else:
-        clear = {"clear": {"range": f"'{tab}'!A:ZZ"}}
-        svc.spreadsheets().values().batchClear(
-            spreadsheetId=SPREADSHEET_ID, body={"ranges": [f"'{tab}'!A:ZZ"]}).execute()
+    """Ghi dữ liệu vào tab. Sử dụng values.update nguyên tử (không clear trước) để triệt tiêu trạng thái rỗng (empty state)."""
     if values:
         svc.spreadsheets().values().update(
             spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'!A1",
             valueInputOption="RAW", body={"values": values}).execute()
```
