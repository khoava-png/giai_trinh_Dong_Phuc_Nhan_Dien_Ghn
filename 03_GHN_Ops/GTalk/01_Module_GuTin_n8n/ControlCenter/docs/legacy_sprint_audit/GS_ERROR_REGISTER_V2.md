# GS ERROR REGISTER V2 — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-002 (Google Sheets Production Reality Verification)  

## 1. Sổ đăng ký Lỗi Phân tách (Error Register V2)

| Error ID | Severity | Function | Root Cause | Evidence | Recovery Strategy |
|---|---|---|---|---|---|
| **GS-ERR-429** | P1 | Google Sheets API Calls | Quota / Rate Limit exceeded do gửi quá nhiều request trong thời gian ngắn (vượt 300 req/min). | Google API HTTP 429 Too Many Requests response. | Cần áp dụng Exponential Backoff Retry. |
| **GS-ERR-NET** | P1 | `_sheets()` / `write_tab` | Network Timeout hoặc mất kết nối internet từ Render tới Google API endpoints. | `requests.exceptions.Timeout` / `socket.timeout`. | Bổ sung Retry với backoff thời gian. |
| **GS-ERR-PARTIAL** | P2 | `write_tab` (Clear + Update) | Khoảng trống dữ liệu (Empty State) giữa bước `batchClear` và `values.update`. | Trạng thái tab tạm thời trống trên Google Sheets. | Chuyển sang ghi đè trực tiếp hoặc dùng atomic batch update. |
