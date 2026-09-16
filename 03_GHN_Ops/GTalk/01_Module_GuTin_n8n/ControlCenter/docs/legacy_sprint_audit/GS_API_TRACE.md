# GS API TRACE — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-002 (Google Sheets Production Reality Verification)  

## 1. Trace Luồng Gọi API Thực tế (API Trace per Cycle)

Trong một chu kỳ cào và đồng bộ chuẩn (`action_scraper`):
1. **READ:** Đọc tab `Co_Cau` để lấy danh sách ánh xạ AM (`spreadsheets.values.get`).
2. **CLEAR/UPDATE (Tab Ton_phieu):** Gọi `batchClear` dọn tab `Ton_phieu`, sau đó gọi `values.update` ghi đè dữ liệu mới.
3. **CLEAR/UPDATE (Tab Chi_tiet):** Gọi `batchClear` dọn tab `Chi_tiet`, sau đó gọi `values.update` ghi đè dữ liệu chi tiết mới.
4. **WRITE (Tab RP_theo_AM & RP_theo_TroLy):** Gọi `ensure_tab` và `values.update` ghi đè báo cáo tổng hợp AM và Trợ lý Vùng.

## 2. Thống kê Ước tính mỗi Chu kỳ
- **READ:** ~2 requests.
- **WRITE:** ~4 requests.
- **CLEAR:** ~2 requests.
- **METADATA:** ~2 requests (ensure tab).
- **TOTAL API CALLS:** ~10 requests / cycle.
- **Status:** **PROVEN** (dựa trên source code `control_center.py` và `cao_ton_phieu.py`).
