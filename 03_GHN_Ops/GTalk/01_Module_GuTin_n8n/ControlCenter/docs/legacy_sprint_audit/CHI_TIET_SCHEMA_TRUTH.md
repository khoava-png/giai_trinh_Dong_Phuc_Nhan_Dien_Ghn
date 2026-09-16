# CHI TIET SCHEMA TRUTH — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-CORE-001  

## 1. Xác thực Schema Thực tế Tab `Chi_tites`
- Tab `Chi_tiet` bao gồm đúng 14 cột tiêu chuẩn:
  `ma_buu_cuc`, `ten_buu_cuc`, `ma_ticket`, `ma_don`, `loai_phieu`, `tien_phat`, `hạn_đóng`, `trạng_thái`, `url`, `gdv_pgdv_id`, `gdv_pgdv_name`, `area_manager_id`, `area_manager_name`, `region_shortname`.
- Không có sự chồng chéo giữa công thức và Python writer. Python Backend sở hữu 100% dải ô dữ liệu qua phương thức ghi đè nguyên tử `values.update`.
