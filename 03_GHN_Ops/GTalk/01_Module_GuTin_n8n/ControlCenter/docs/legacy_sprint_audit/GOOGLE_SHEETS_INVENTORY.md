# GOOGLE SHEETS INVENTORY — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-001 (Google Sheets & Apps Script Full Audit)  

## 1. Inventory Tổng quan (Spreadsheet & Tabs)
- **Spreadsheet ID:** `15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg`
- **Authentication:** Google Service Account (`ghn-sheet-bot@ghn-sheets-automation.iam.gserviceaccount.com`), tải qua biến môi trường `GOOGLE_KEY_FILE`.
- **Danh sách Tabs / Worksheets thực tế trong hệ thống:**
  1. `Chi_tiet` (`TAB_CT`): Lưu danh sách chi tiết toàn bộ phiếu tồn (14 cột).
  2. `Ton_phieu` (`TAB_TON`): Lưu tổng hợp tồn phiếu theo bưu cục (8 cột).
  3. `RP_theo_AM` (`TAB_RP` cho AM): Lưu bảng báo cáo tổng hợp theo Quản lý khu vực (AM).
  4. `RP_theo_TroLy` (`TAB_RP` cho Trợ lý Vùng): Lưu bảng báo cáo tổng hợp theo Trợ lý Giám đốc Vùng.
  5. `Co_Cau`: Lưu dữ liệu ánh xạ cơ cấu tổ chức (bưu cục, AM, vùng).
  6. Các tab bổ trợ khác (nếu có trên Cloud).
- **Apps Script & Triggers:** Hệ thống hiện tại **không sử dụng Google Apps Script `.gs` trực tiếp**, mà toàn bộ logic tính toán, kết xuất báo cáo (`ghi_rp_theo_am`, `ghi_rp_theo_vung`) và ghi nhận dữ liệu đều được thực thi trực tiếp bằng Python backend (`control_center.py` kết hợp với module `cao_ton_phieu.py`).
