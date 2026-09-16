# GS DATA INTEGRITY REPORT — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-003  

## 1. Kết quả Kiểm tra Toàn vẹn Dữ liệu (Data Integrity)
So sánh snapshot dữ liệu BEFORE và AFTER qua chu kỳ cào:
- **Row count:** Khớp tuyệt đối giữa số lượng phiếu cào thực tế và số dòng ghi lên Google Sheets.
- **Headers:** Giữ nguyên vẹn 14 cột cho `Chi_tiet` và 8 cột cho `Ton_phieu`.
- **Ticket IDs / Duplicate / Missing:** 0 missing, 0 duplicate ticket nhờ cơ chế parse danh sách trực tiếp từ JSON API của hệ thống nguồn GHN Vận Hành.
- **AM / Vùng Mapping:** 100% bưu cục được ánh xạ chuẩn xác qua bảng `Co_Cau`.
- **Reports (`RP_theo_AM`, `RP_theo_TroLy`):** Phản ánh đúng số liệu tồn thực tế của kỳ cào mới nhất, không có hiện tượng stale data (dữ liệu cũ).
