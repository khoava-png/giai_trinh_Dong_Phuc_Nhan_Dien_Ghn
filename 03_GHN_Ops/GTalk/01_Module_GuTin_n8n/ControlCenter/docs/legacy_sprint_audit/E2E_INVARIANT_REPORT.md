# E2E INVARIANT REPORT — ORDER-CORE-001

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-CORE-001  

## 1. Kết quả Kiểm định Bất biến E2E (End-to-End Invariant Verification)
- **Source ticket count == Chi_tiet committed count == report input count:** Đạt tỷ lệ đồng nhất 100%.
- **Ton_phieu totals == Chi_tiet aggregation:** Khớp tuyệt đối theo từng bưu cục.
- **RP_AM & RP_TroLy totals == Expected aggregation:** Khớp tuyệt đối theo phân nhóm cơ cấu.
- **GTalk & Dashboard payloads:** Đều đọc từ tập dữ liệu đã được commit thành công, không đọc dở dang (uncommitted/partial write).
- **Trạng thái:** **PASS**.
