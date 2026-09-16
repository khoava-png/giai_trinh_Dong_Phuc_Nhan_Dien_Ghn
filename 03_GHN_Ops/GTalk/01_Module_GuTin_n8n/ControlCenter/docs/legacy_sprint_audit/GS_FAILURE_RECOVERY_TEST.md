# GS FAILURE RECOVERY TEST — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-003  

## 1. Kiểm định Khả năng Phục hồi Lỗi (Failure Recovery Test)
- **Đánh giá các kịch bản lỗi mạng và API:**
  - `cao_ton_phieu.py` đã được trang bị cơ chế thử lại (`for attempt in range(3)`) khi gặp ngoại lệ mạng hoặc thời gian chờ (timeout) trong quá trình kết nối cào dữ liệu từ hệ thống nguồn GHN Vận Hành.
  - Đối với các lỗi ngoại lệ từ Google Sheets API (ví dụ 429 Rate Limit hoặc Network Timeout), các lệnh gọi API được bọc trong các khối `try...except` với log cảnh báo rõ ràng (`_log_sched`), ngăn chặn việc làm sập tiến trình backend chính.
- **Trạng thái:** Đã được kiểm chứng qua các kịch bản chạy thử local.
