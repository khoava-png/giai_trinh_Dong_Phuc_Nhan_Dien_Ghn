# MEMORY ANALYSIS — GHN CONTROL CENTER SPRINT-2

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-005 (Sprint-2 Authorization)  

## 1. Phân tích Hiện trạng Quản lý Bộ nhớ (Memory Lifecycle Analysis)
- **Cơ chế lưu trữ hiện tại:** Server Python duy trì biến toàn cục `_cached_chi_tiet` và `_cached_co_cau_am` trong module `control_center.py` để tránh nghẽn I/O đọc lại Google Sheets.
- **Vấn đề Peak RSS:** Khi hàm `action_scrape()` cào dữ liệu thô (hơn 2500+ dòng phiếu), việc parse HTML/JSON và nạp toàn bộ vào RAM kết hợp ghi đồng thời lên Google Sheets và render báo cáo phụ trợ gây ra hiện tượng đỉnh bộ nhớ (Peak RSS) tăng vọt từ ~180MB lên đến ~380-460MB.
- **Global Objects tồn tại sau chu kỳ:** Các dictionary dữ liệu chi tiết (`rows`, `hdr`) được giữ lại trong `_cached_chi_tiet` suốt 1 giờ (`time.time() - ts < 3600`), ngăn cản Python Garbage Collector thu hồi các object lớn ngay lập tức sau khi chu kỳ nhắc phiếu kết thúc (`JOB_FINISH`).

## 2. Mục tiêu Tối ưu hóa (PA2 Alignment)
- Bổ sung chủ động gọi `gc.collect()` ngay tại mốc kết thúc chu kỳ (`FINISH`) và sau các thao tác cào dữ liệu nặng.
- Đảm bảo giải phóng triệt để các object tạm thời không còn sử dụng mà không làm thay đổi business logic, API contract hay GTalk output.
