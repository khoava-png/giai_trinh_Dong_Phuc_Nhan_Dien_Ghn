# FORMULA AUDIT — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-001 (Google Sheets & Apps Script Full Audit)  

## 1. Kiểm định Công thức (Formulas)
- **Khảo sát:** Hệ thống Google Sheets hiện tại **không phụ thuộc vào các công thức phức tạp như QUERY, FILTER, ARRAYFORMULA** lưu sẵn trong các tab tính toán cốt lõi.
- **Lý do:** Toàn bộ quá trình tổng hợp số lượng phiếu tồn, phân nhóm theo AM và theo Trợ lý Vùng đều được xử lý trực tiếp bằng mã nguồn Python (`cao_ton_phieu.py`) trước khi ghi kết quả dạng phẳng (flat values) lên các tab `Ton_phieu`, `Chi_tiet`, `RP_theo_AM`, `RP_theo_TroLy`.
- **Rủi ro công thức (#REF!, #N/A):** Bằng không (0), do dữ liệu được ghi dạng giá trị thuần túy (pure values), tránh được hiện tượng lệch công thức hay lỗi mở rộng mảng (array expansion conflict).
