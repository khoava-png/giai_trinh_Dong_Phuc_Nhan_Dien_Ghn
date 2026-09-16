# PRODUCTION CONSTRAINTS — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-002 (Baseline Freeze)  

## 1. Định nghĩa Ràng buộc Production (Production Constraints)
Production Constraints là các giới hạn phần cứng, hạ tầng và vận hành bắt buộc phải tuân thủ nghiêm ngặt trong mọi tình huống thiết kế và triển khai.

| Constraint ID | Tên Ràng Buộc (Constraint Name) | Mô tả giới hạn hạ tầng / vận hành | Ảnh hưởng & Biện pháp |
|---|---|---|---|
| **CONST-001** | **RAM Limit (512 MB Max)** | Render Free Container bị giới hạn cứng tối đa 512 MB RAM. Vượt ngưỡng này container sẽ bị OOM Kill ngay lập tức. | Yêu cầu phải kiểm soát Peak RSS, áp dụng chiến lược giải phóng RAM và kiến trúc PA2. |
| **CONST-002** | **Single Instance Concurrency** | Không thể chạy nhiều replica song song trên Render Free (gây xung đột Scheduler tick và ghi trùng lặp Google Sheets). | Duy trì mô hình tiến trình đơn độc lập trên 1 container duy nhất. |
| **CONST-003** | **Render Sleep Limitation** | Render Free sẽ tự động đưa container vào trạng thái "sleep" sau khoảng thời gian không có request HTTP. | Bắt buộc duy trì UptimeRobot ping mỗi 5 phút tới endpoint `/api/health`. |
| **CONST-004** | **Google Sheets API Rate Limits** | Google Sheets API áp dụng hạn mức số lần gọi (quota) mỗi phút, dễ gây lỗi HTTP 429 nếu spam request. | Bắt buộc áp dụng batching và retry backoff khi tương tác với Sheets. |
| **CONST-005** | **Zero-Downtime Deployment Window** | Các thay đổi deploy lên production cần được thực hiện ngoài giờ cao điểm vận hành (sau 22:00 hoặc trước 06:00 sáng). | Tuân thủ `DEPLOYMENT_PLAN.md` và sẵn sàng quy trình rollback dưới 3 phút. |
| **CONST-006** | **Immutable Production Components** | Các thành phần van an toàn KN1, KN2, module `memory_meter.py`, và endpoints cốt lõi không được phép tự ý gỡ bỏ. | Bảo vệ tuyệt đối tính toàn vẹn của các cơ chế phòng thủ hiện hữu. |
