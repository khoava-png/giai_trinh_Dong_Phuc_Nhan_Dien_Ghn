# CURRENT SOURCE DIFF — SYSTEM TRUTH AUDIT

> **Order Reference:** ORDER-SYS-TRUTH-001  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  

## 1. Inventory Các File Đã Thay Đổi trong Working Tree
Dựa trên git diff và kiểm tra thực tế working tree tại thời điểm hiện tại:
1. **`control_center.py`**: 
   - Đã thay đổi: Đăng ký tuyến đường `GET /api/sched/get` trong phương thức `do_GET()` của class `H` (hỗ trợ gọi HTTP GET đúng chuẩn REST semantics, khắc phục sự cố P0 routing mismatch).
   - Đã thay đổi: Bổ sung gọi `import gc; gc.collect()` tại mốc `FINISH` trong `action_scrape()` và mốc `done` trong `_sched_cycle()` để tối ưu hóa bộ nhớ theo tinh thần Sprint-02.
2. **`Cao_Ton_Phieu/cao_ton_phieu.py`**:
   - Đã thay đổi: Sửa đổi hàm `write_tab` từ phương thức `batchClear` sang phương thức ghi đè nguyên tử `values.update` (`valueInputOption="RAW"`), khắc phục triệt để lỗi rủi ro Partial Write / Empty State trên Google Sheets.
3. **Thư mục `tests/`**:
   - Thêm mới file `tests/test_sched_get.py` để kiểm thử tự động định tuyến endpoint `/api/sched/get`.
4. **Các file tài liệu Markdown mới**:
   - Toàn bộ các tài liệu phân tích, baseline, impact analysis, incident reports, và Google Sheets audit (`CURRENT_SOURCE_DIFF.md`, `SYSTEM_TRUTH_REPORT.md`, v.v.).
