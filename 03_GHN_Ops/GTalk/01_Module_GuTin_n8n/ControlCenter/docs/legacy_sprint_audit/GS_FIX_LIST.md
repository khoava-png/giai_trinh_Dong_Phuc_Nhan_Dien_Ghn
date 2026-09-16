# GS FIX LIST — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-003  

## 1. Danh sách Các Lỗi Đã Được Chứng Minh và Khắc Phục (Fixed Issues)

| Fix ID | Mức độ | Vấn đề (Issue) | Root Cause | Giải pháp Đã Áp dụng (Fix) | Trạng thái |
|---|---|---|---|---|---|
| **FIX-001** | P1 | Rủi ro Partial Write / Empty State trên Google Sheets khi Dashboard đọc đúng lúc tab đang bị xóa (`batchClear`). | Lệnh `batchClear` xóa sạch dải ô trước khi `values.update` ghi dữ liệu mới. | Loại bỏ lệnh `batchClear`, chuyển sang sử dụng trực tiếp `values.update` với `valueInputOption="RAW"` để ghi đè nguyên tử. | **FIXED & PROVEN** |
