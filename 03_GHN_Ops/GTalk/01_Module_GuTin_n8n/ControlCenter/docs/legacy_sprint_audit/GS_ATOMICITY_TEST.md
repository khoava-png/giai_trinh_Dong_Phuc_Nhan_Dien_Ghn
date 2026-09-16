# GS ATOMICITY TEST — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-003  

## 1. Kiểm định Tính Nguyên vẹn Ghi & Khắc phục Rủi ro Partial Write (Atomicity Test)
- **Vấn đề đã xác nhận (`GS-ERR-PARTIAL`):** Trước đây hàm `write_tab` sử dụng lệnh `batchClear` (xóa sạch dải `A:ZZ`) trước, sau đó mới gọi `values.update` để ghi dữ liệu mới. Điều này tạo ra khoảng thời gian trễ trong đó Google Sheet rơi vào trạng thái trống (Empty State), làm Dashboard có thể đọc phải dữ liệu rỗng.
- **Giải pháp khắc phục (Đã chứng minh & Áp dụng):**
  - Chuyển đổi phương thức ghi đè sang sử dụng trực tiếp `values.update` với `valueInputOption="RAW"` mà không cần gọi lệnh `batchClear` trước đó. Thao tác `values.update` của Google Sheets API tự động ghi đè lên các ô hiện hữu và cập nhật dải mới một cách nguyên tử, triệt tiêu hoàn toàn trạng thái trống trung gian.
- **Kết quả kiểm tra:**
  - `GS-ERR-PARTIAL` đã được giải quyết triệt để (CONFIRMED FIXED).
