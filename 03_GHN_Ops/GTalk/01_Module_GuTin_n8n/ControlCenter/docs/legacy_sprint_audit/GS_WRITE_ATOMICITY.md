# GS WRITE ATOMICITY — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-002 (Google Sheets Production Reality Verification)  

## 1. Đánh giá Tính Nguyên vẹn Ghi (Write Atomicity & Partial Read Risk)
- **Hành vi ghi tab (`write_tab`):** Hàm thực hiện thao tác **`batchClear`** (xóa sạch dải ô `A:ZZ`) trước, sau đó mới gọi **`values.update`** để ghi dữ liệu mới lên `A1`.
- **Đánh giá Rủi ro (Partial State / Empty State):**
  - **CÓ (YES):** Tồn tại khoảng thời gian trễ ngắn (vài trăm mili-giây đến vài giây) giữa thời điểm `batchClear` hoàn tất và `values.update` ghi dữ liệu mới lên tab.
  - **Nguy cơ:** Nếu Cloudflare Pages Dashboard hoặc tiến trình đọc dữ liệu gọi API vào đúng khoảng trống này, Dashboard có thể đọc phải trạng thái dữ liệu trống (empty state) hoặc dữ liệu một phần (partial write).
- **Biện pháp giảm thiểu hiện tại:** Backend sử dụng In-Memory RAM Cache (`_cached_chi_tiet`) cho các luồng gửi tin nhắn GTalk, giảm thiểu việc đọc trực tiếp Google Sheets liên tục trong thời điểm nhạy cảm.
