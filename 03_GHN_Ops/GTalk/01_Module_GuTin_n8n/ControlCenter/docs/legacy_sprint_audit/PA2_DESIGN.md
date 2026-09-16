# PA2 DESIGN — GHN CONTROL CENTER SPRINT-2

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-006 (Sprint-02 Hardening)  

## 1. Kiến trúc Tối ưu hóa Bộ nhớ (PA2 Architecture Design)
- **Nguyên tắc Cốt lõi:**
  1. **Không giữ dataset lớn dư thừa:** Xóa bỏ các biến cục bộ trỏ tới raw tickets ngay sau khi đã ghi hoàn tất lên Google Sheets và nạp bộ đệm cần thiết.
  2. **Giải phóng Reference kịp thời:** Gán giá trị `None` cho các object dữ liệu cào thô kích thước lớn ngay khi kết thúc vòng đời xử lý trong `action_scrape()`.
  3. **Streaming & Chunk Processing:** Giữ nguyên các thao tác batching hiện có của Google Sheets API để tránh tràn bộ nhớ đệm HTTP client.
  4. **Garbage Collection có chọn lọc:** Chỉ sử dụng `gc.collect()` đúng một điểm duy nhất tại mốc kết thúc chu kỳ (`FINISH`) để gom rác các object tạm thời sinh ra trong quá trình parse HTML/JSON.
