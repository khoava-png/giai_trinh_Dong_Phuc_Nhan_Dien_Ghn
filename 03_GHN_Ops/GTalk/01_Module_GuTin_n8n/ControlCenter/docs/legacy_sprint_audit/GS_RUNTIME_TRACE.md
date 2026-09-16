# GS RUNTIME TRACE — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-003  

## 1. Trace Runtime một Chu kỳ Cào Chuẩn
1. **Scrape:** Đăng nhập GHN Vận Hành, cào danh sách bưu cục và danh sách phiếu tồn (`tickets`, `buu_cuc`, `meta`). (~5-15s).
2. **Transform:** Map mã bưu cục, tính tiền phạt, phân loại trạng thái phiếu tồn, xây dựng `rows_ton`, `rows_ct`. (<1s).
3. **Google Sheets Sync (`Ton_phieu`):** Cập nhật dữ liệu tổng hợp bưu cục lên tab `Ton_phieu`. (~0.5s).
4. **Google Sheets Sync (`Chi_tiet`):** Cập nhật danh sách chi tiết phiếu tồn lên tab `Chi_tiet`. (~1.0s).
5. **Formula Rebuild:** Đưa công thức ARRAYFORMULA vào ô `I2` của tab `Chi_tiet`. (~0.3s).
6. **Reports Generation (`RP_theo_AM`, `RP_theo_TroLy`):** Tổng hợp và ghi báo cáo AM và Trợ lý Vùng. (~1.0s).
7. **RAM Cache Update:** Nạp bộ đệm `_set_cached_data()` phục vụ luồng gửi GTalk nhanh chóng. (<0.1s).
8. **Finish & GC:** Giải phóng reference và gọi `gc.collect()`.
