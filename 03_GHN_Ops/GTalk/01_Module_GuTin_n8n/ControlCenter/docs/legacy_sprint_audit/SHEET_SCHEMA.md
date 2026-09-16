# SHEET SCHEMA — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-001 (Google Sheets & Apps Script Full Audit)  

## 1. Schema Chi tiết các Tabs Cốt Lõi

### Tab 1: `Chi_tiet` (`TAB_CT`)
- **Mục đích:** Lưu trữ danh sách chi tiết toàn bộ các phiếu tồn từ hệ thống GHN Vận Hành.
- **Headers (14 cột):**
  1. `ma_buu_cuc` (String)
  2. `ten_buu_cuc` (String)
  3. `ma_ticket` (String)
  4. `ma_don` (String)
  5. `loai_phieu` (String: Hối giao / Hối lấy / Hối trả)
  6. `tien_phat` (Number / Currency)
  7. `hạn_đóng` (String/Datetime)
  8. `trạng_thái` (String)
  9. `url` (String link)
  10. `gdv_pgdv_id` (String)
  11. `gdv_pgdv_name` (String)
  12. `area_manager_id` (String)
  13. `area_manager_name` (String)
  14. `region_shortname` (String)

### Tab 2: `Ton_phieu` (`TAB_TON`)
- **Mục đích:** Tổng hợp số lượng phiếu tồn theo từng bưu cục.
- **Headers (8 cột):**
  1. `ma_buu_cuc`, 2. `ten_buu_cuc`, 3. `Hối giao`, 4. `Hối lấy`, 5. `Hối trả`, 6. `Tổng`, 7. `Tiền phạt`, 8. `cap_nhat_luc`.

### Tab 3: `RP_theo_AM`
- **Mục đích:** Báo cáo tổng hợp theo Quản lý khu vực (AM) do Python render và đổ dữ liệu trực tiếp.

### Tab 4: `RP_theo_TroLy`
- **Mục đích:** Báo cáo tổng hợp theo Trợ lý Giám đốc Vùng do Python render và đổ dữ liệu trực tiếp.
