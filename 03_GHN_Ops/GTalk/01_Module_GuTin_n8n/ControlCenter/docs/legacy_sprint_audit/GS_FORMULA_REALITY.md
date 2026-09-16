# GS FORMULA REALITY — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-002 (Google Sheets Production Reality Verification)  

## 1. Khảo sát Thực tế Công thức (Formulas)
- **ARRAYFORMULA / VLOOKUP:** Module `cao_ton_phieu.py` (hàm `rebuild_formulas`) có cơ chế ghi một công thức `ARRAYFORMULA` kết hợp `VLOOKUP` vào ô `I2` của tab `Chi_tiet` để ánh xạ tự động cơ cấu (AM, Vùng) dựa vào `Co_Cau`.
- **QUERY / FILTER / IMPORTRANGE:** Không được sử dụng trong các tab báo cáo chính. Báo cáo `RP_theo_AM` và `RP_theo_TroLy` được tính toán hoàn toàn bằng mã Python và ghi đè giá trị thuần túy (`RAW`).
- **Trạng thái xác thực:** **PROVEN** (dựa trên source code quản lý bảng tính `cao_ton_phieu.py`).
