# SNAPSHOT WRITER FINAL — ORDER-ROOT-003

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-ROOT-003  

## 1. Thiết kế Snapshot Writer Cuối Cùng (Part D)
Nâng cấp hàm `write_tab` trong `Cao_Ton_Phieu/cao_ton_phieu.py` để thực hiện deterministic snapshot replacement kèm dọn dẹp phần đuôi thừa (stale tail cleanup) một cách chính xác:
```python
def write_tab(svc, tab, values, owned_cols="A:N"):
    """Ghi đè snapshot nguyên tử, đồng thời tự động dọn dẹp các dòng thừa (stale tail) nếu số dòng mới ít hơn số dòng cũ."""
    # 1. Đọc số dòng hiện tại trên tab
    res = svc.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'!A:A").execute()
    old_rows = len(res.get("values", []))
    
    new_rows = len(values) if values else 0
    
    # 2. Ghi đè dữ liệu mới tại A1
    if values:
        svc.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'!A1",
            valueInputOption="RAW", body={"values": values}).execute()
            
    # 3. Dọn dẹp stale tail nếu old_rows > new_rows
    if old_rows > new_rows:
        clear_range = f"'{tab}'!{owned_cols}{new_rows + 1}:{old_rows}"
        svc.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID, range=clear_range).execute()
```
- **Quy tắc tuân thủ:**
  1. Không clear trước khi ghi đè (triệt tiêu empty/partial state).
  2. Chỉ clear đúng dải dòng thừa (`new_rows + 1` đến `old_rows`) và đúng cột Python sở hữu (`A:N`).
  3. Giữ nguyên vẹn các dải không thuộc sở hữu.
