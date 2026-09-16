# GENERATION MODEL — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-CORE-001  

## 1. Thiết kế Mô hình Thế hệ Dữ liệu (Data Generation Model)
Để loại bỏ hoàn toàn các lỗi stale rows, empty-state, partial write và mixed-cycle data, hệ thống áp dụng invariant: **MỘT DATA CYCLE CHỈ ĐƯỢC PHÉP Ở TRẠNG THÁI COMMITTED HOẶC ABORTED**.

### A. Các trạng thái thế hệ (`generation_status`):
1. `PREPARING`: Đang cào dữ liệu thô từ web GHN.
2. `WRITING`: Đang đẩy dữ liệu lên các tab Google Sheets (`Ton_phieu`, `Chi_tiet`, `RP_theo_AM`, `RP_theo_TroLy`).
3. `VALIDATING`: Kiểm tra tính toàn vẹn (row count, mapping).
4. `COMMITTED`: Đã hoàn tất toàn bộ, sẵn sàng phục vụ consumer (Dashboard, GTalk).
5. `ABORTED`: Xảy ra lỗi giữa chừng, giữ nguyên generation trước, không overwrite dở dang.

### B. Tài nguyên thuộc Generation:
- `generation_id`: Định danh duy nhất (VD: `gen-1789465558`).
- Dataset trên Google Sheets.
- RAM Cache (`_cached_chi_tiet`).
- GTalk Payload & Dashboard view pointer.
