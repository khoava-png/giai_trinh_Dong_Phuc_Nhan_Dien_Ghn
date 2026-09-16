# STALE ROW RAW EVIDENCE — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-CORE-001  

## 1. Bằng chứng Thực tế về Stale Rows khi Dữ liệu Giảm (Generation A -> Generation B)
- **Tình huống kiểm chứng (Gate 2):** Khi thế hệ dữ liệu trước (Generation A) có 2500 dòng phiếu, nhưng thế hệ dữ liệu mới (Generation B) chỉ có 2000 dòng phiếu.
- **Hành vi thực tế của `values.update` (RAW):** Lệnh `values.update` ghi đè từ ô `A1` xuống đến dòng 2000. Tuy nhiên, các dòng từ 2001 đến 2500 thuộc dữ liệu cũ vẫn tồn tại trên tab Google Sheets nếu không được dọn dẹp hoặc clear trước.
- **Kết luận (STALE_ROW = CONFIRMED):** Việc chỉ dùng `values.update` đơn thuần mà không clear hoặc đánh dấu giới hạn dải dữ liệu hợp lệ sẽ để lại các **stale rows** (dòng dữ liệu cũ của generation trước). Do đó, cần thiết lập mô hình **Data Generation Commit Architecture** (hoặc cơ chế clear/ghi chuẩn xác) để đảm bảo không bao giờ tồn tại stale rows.
