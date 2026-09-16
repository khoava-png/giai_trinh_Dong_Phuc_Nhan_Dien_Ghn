# SOURCE DATA TRUTH — ORDER-ROOT-002

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-ROOT-002 (Data Model & Overwrite Root Cause)  

## 1. Bản chất Dữ liệu Nguồn (Source Data Truth)
- **Trace từ code (`login_and_scrape` / `login_and_scrape_v2`):** Hệ thống gọi API `GET /api/tickets` từ hệ thống nguồn GHN Vận Hành để lấy toàn bộ danh sách các phiếu tồn hiện tại tại thời điểm cào.
- **Xác định loại dữ liệu:** **`FULL_CURRENT_SNAPSHOT`**. 
- **Giải thích:** Dữ liệu trả về từ API là danh sách các phiếu đang tồn đọng thực tế ở thời điểm gọi. Nếu trong Cycle A ticket X tồn đọng, nhưng sang Cycle B ticket X đã được xử lý (không còn tồn đọng), API sẽ không trả về ticket X nữa.
- **Business requirement:** Việc ghi đè toàn bộ (Full Snapshot Replacement) đối với tab `Chi_tiet` và `Ton_phieu` là **ĐÚNG ĐẮN VÀ CẦN THIẾT** theo nghiệp vụ vận hành bưu cục (vì đây là bảng tồn phiếu hiện tại, không phải sổ cái lịch sử - historical ledger).
