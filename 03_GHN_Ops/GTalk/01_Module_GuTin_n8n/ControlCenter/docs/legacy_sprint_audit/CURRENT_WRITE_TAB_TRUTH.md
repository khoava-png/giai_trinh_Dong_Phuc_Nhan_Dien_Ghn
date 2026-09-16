# CURRENT WRITE TAB TRUTH — ORDER-ROOT-003

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-ROOT-003  

## 1. Trích nguyên hàm `write_tab()` hiện tại (`Cao_Ton_Phieu/cao_ton_phieu.py`, dòng 191)
```python
def write_tab(svc, tab, values, only_clear_rows=0):
    """Ghi dữ liệu vào tab. Sử dụng values.update nguyên tử (không clear trước) để triệt tiêu trạng thái rỗng (empty state)."""
    if values:
        svc.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID, range=f"'{tab}'!A1",
            valueInputOption="RAW", body={"values": values}).execute()
```
- **Phân tích chi tiết:**
  - `CLEAR?`: Không còn clear toàn bộ `A:ZZ` trước khi ghi, giúp loại bỏ trạng thái rỗng (empty state).
  - `UPDATE?`: Sử dụng `values.update` tại `A1` với `valueInputOption="RAW"`.
  - `TAIL CLEANUP?`: Chưa tự động dọn dẹp các dòng thừa nếu số lượng dòng mới ít hơn số lượng dòng cũ (stale tail khi 2500 -> 2000).
  - `FORMULA REBUILD?`: Không can thiệp ghi đè dải công thức độc lập.
  - `GENERATION COMMIT?`: Được bao bọc bởi logic RAM Cache và cấu trúc Control Plane trên Redis.
