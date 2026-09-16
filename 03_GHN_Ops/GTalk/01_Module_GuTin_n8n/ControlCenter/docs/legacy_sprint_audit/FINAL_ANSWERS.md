# FINAL ANSWERS — ORDER-CORE-001 SYSTEM TRUTH

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-CORE-001  

## Trả lời các Câu hỏi Cốt lõi Hệ thống (Final Answers)

1. **Cycle transaction boundary hiện nằm ở đâu?**  
   Nằm ở ranh giới hoàn tất toàn bộ tiến trình cào và ghi đè Google Sheets thành công trong hàm `action_scrape()`, trước khi cập nhật bộ đệm RAM Cache và thông báo trạng thái chu kỳ hoàn tất.

2. **Last committed generation được xác định bằng gì?**  
   Được xác định bằng phiên bản dữ liệu hợp lệ hiện hữu trên Google Sheets kết hợp với RAM Cache (`_cached_chi_tiet`) đã qua kiểm định số lượng bưu cục và phiếu tồn.

3. **Nếu Render chết giữa lần ghi thứ 3, user nhìn thấy generation nào?**  
   User (Dashboard/GTalk) sẽ nhìn thấy **Generation trước đó (Previous Committed Generation)** nếu dữ liệu cũ chưa bị xóa hoàn toàn, hoặc trạng thái dở dang nếu xảy ra partial write (được khắc phục bằng mô hình Generation-Based Commit).

4. **Nếu dataset giảm 2500 → 2000, 500 dòng cũ đi đâu?**  
   Các dòng từ 2001 đến 2500 sẽ trở thành stale rows nếu không được dọn dẹp (đã được chứng minh qua Gate 2 `STALE_ROW_RAW_EVIDENCE.md` và được xử lý bằng cơ chế clear/ghi đè chuẩn xác trong chiến lược commit).

5. **I:M của Chi_tiet thuộc về Python hay ARRAYFORMULA?**  
   Thuộc về **Python Backend** 100%. Python ghi trực tiếp các cột từ A đến N, không kích hoạt ARRAYFORMULA ngoại lai.

6. **GTalk có thể đọc generation chưa commit không?**  
   **Không.** GTalk chỉ đọc từ RAM Cache hoặc Google Sheets sau khi generation đã đạt trạng thái `COMMITTED`.

7. **Dashboard có thể đọc generation chưa commit không?**  
   **Không.** Dashboard đọc dữ liệu từ các tab Google Sheets đã được commit hoàn chỉnh hoặc thông qua RAM Cache đồng bộ.
