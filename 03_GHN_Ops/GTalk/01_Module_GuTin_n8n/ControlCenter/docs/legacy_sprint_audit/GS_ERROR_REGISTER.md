# GS ERROR REGISTER — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-001 (Google Sheets & Apps Script Full Audit)  

## 1. Sổ đăng ký Lỗi Tiềm năng (Error Register)

| Error ID | Severity | Function | Sheet / Tab | Root Cause | Evidence | Business Impact |
|---|---|---|---|---|---|---|
| **GS-ERROR-001** | P1 | `_sheets()` / `write_tab` | All Tabs | Google Sheets API Quota Exhaustion (HTTP 429) hoặc Network Timeout khi ghi dữ liệu lớn. | Python requests exception / gspread error logs. | Dữ liệu tồn phiếu trên Sheets không được cập nhật kịp thời. |
| **GS-ERROR-002** | P2 | `_read_chi_tiet()` | `Chi_tiet` | Mất kết nối Service Account hoặc file JSON credentials không hợp lệ trên biến môi trường Render. | `FileNotFoundError` hoặc Google Auth Exception khi khởi tạo client. | Không đọc được dữ liệu chi tiết để preview hoặc gửi GTalk. |
