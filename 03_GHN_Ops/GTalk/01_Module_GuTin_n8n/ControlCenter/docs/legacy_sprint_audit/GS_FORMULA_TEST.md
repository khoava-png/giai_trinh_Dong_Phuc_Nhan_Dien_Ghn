# GS FORMULA TEST — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-003  

## 1. Kết quả Kiểm định Công thức (Formula Test)
- **Vị trí kiểm tra:** Ô `I2` của tab `Chi_tiet`.
- **Nội dung công thức:** `ARRAYFORMULA(IF($A$2:$A$N="", "", IFERROR(VLOOKUP($A$2:$A$N*1, 'Co_Cau'!$B$2:$J$1609, {3,4,5,6,9}, FALSE), "")))`.
- **Kết quả kiểm tra:**
  - Công thức tồn tại và được tự động chèn lại sau mỗi lần đồng bộ tab `Chi_tiet`.
  - Không bị ghi đè nhầm lẫn nhờ cơ chế phân tách cột dữ liệu giá trị thô và dải công thức tự động.
  - Không phát sinh lỗi `#REF!` hay `#N/A` ngoài các mã bưu cục không tồn tại trong bảng `Co_Cau` (được xử lý an toàn bằng `IFERROR`).
