# GOOGLE API AUDIT — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-001 (Google Sheets & Apps Script Full Audit)  

## 1. Kiểm định Google Sheets API Usage
- **Client Library:** `googleapiclient.discovery.build` (Google API Python Client v4).
- **Authentication:** Service Account JSON (`GOOGLE_KEY_FILE`).
- **Các phương thức API sử dụng:**
  - `spreadsheets.values.get`: Đọc dữ liệu từ các tab (`Chi_tiet`, `Co_Cau`).
  - `spreadsheets.values.update` / `write_tab`: Ghi dữ liệu thô và báo cáo lên các tab.
  - `ensure_tab`: Kiểm tra và tạo tab nếu chưa tồn tại.
- **Tần suất & Quota:** Mỗi chu kỳ cào thực hiện khoảng 5 đến 12 request API (đọc cấu trúc cơ cấu, ghi tab Ton_phieu, ghi tab Chi_tiet, ghi RP_AM, ghi RP_Vùng). Hạn mức này nằm hoàn toàn trong giới hạn cho phép của Google Sheets API (300 requests per minute per project).
- **Error Handling:** Được bọc trong các khối `try...except` với cơ chế log cảnh báo, ngăn chặn làm sập tiến trình backend chính.
