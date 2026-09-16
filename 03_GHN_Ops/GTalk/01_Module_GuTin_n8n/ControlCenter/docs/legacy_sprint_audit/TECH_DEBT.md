# TECH DEBT — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  

## 1. Danh sách Nợ Kỹ thuật (Technical Debt Inventory)

| Debt ID | Loại | Mô tả chi tiết | Mức độ ảnh hưởng | Chi phí ước tính | Hướng giải quyết đề xuất |
|---|---|---|---|---|---|
| **TD-001** | Architecture Debt | `control_center.py` là file monolithic lớn chứa quá nhiều trách nhiệm (HTTP server, scheduler, scraping wrapper, GTalk sender, Google Sheets sync). | Cao | 3 ngày | Phân tách module hóa thành các package độc lập (`server.py`, `scheduler.py`, `sheets.py`, `gtalk.py`). |
| **TD-002** | Testing Debt | Thiếu bộ Unit Test tự động cho các luồng xử lý HTTP request và Scheduler logic bên trong `control_center.py`. | Trung bình | 2 ngày | Viết bộ `unittest` mock requests và time cho toàn bộ HTTP handlers. |
| **TD-003** | Architecture Debt | Duy trì Global RAM Cache (`_cached_rows_ct`) chứa toàn bộ chi tiết phiếu trên Heap vĩnh viễn. | Cao (Nguy cơ OOM) | 1 ngày | Chuyển dịch hoàn toàn sang kiến trúc PA2 (loại bỏ RAM cache, Google Sheets tự tổng hợp báo cáo). |
| **TD-004** | Code Smell | Xử lý ngoại lệ rộng (`except Exception:`) ở một số điểm kết nối mạng ngoại vi. | Thấp | 0.5 ngày | Bắt chính xác các Exception cụ thể (`requests.RequestException`, `gspread.exceptions.APIError`). |
