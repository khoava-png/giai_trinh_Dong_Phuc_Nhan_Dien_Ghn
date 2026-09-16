# IMPACT MATRIX — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-003 (Change Impact Analysis)  

## 1. Bảng Ma trận Tác động (Impact Matrix)

| Component / Change Unit | Affected Files | Runtime Impact | Business Impact | Recovery Difficulty | Rollback Difficulty | Risk Level |
|---|---|---|---|---|---|---|
| **CU-001: Core HTTP Server** | `control_center.py` | Ngưng toàn bộ HTTP API | Mất khả năng giám sát & trigger thủ công | Trung bình | Thấp (Revert commit) | **HIGH** |
| **CU-002: Scheduler & Tick Loop** | `control_center.py`, `sched.json` | Dừng lịch tự động định kỳ | Bỏ lỡ khung giờ nhắc phiếu tồn cho AM/Vùng | Trung bình | Thấp (Revert commit) | **HIGH** |
| **CU-003: Web Scraper Module** | `cao_ton_phieu.py`, `control_center.py` | Lỗi cào dữ liệu thô | Dữ liệu tồn phiếu không cập nhật | Cao | Thấp (Revert commit) | **CRITICAL** |
| **CU-004: Google Sheets Sync** | `control_center.py` | Lỗi đồng bộ Google Sheets | Dashboard Cloudflare không có dữ liệu mới | Trung bình | Thấp (Revert commit) | **MEDIUM** |
| **CU-005: GTalk Notification** | `control_center.py`, `gtalk_bulk_sender.py` | Không gửi được tin nhắn OA | Shipper/AM không nhận được cảnh báo hối | Trung bình | Thấp (Revert commit) | **HIGH** |
