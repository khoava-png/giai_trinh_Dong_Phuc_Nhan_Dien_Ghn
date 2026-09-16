# BLAST RADIUS — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-003 (Change Impact Analysis)  

## 1. Phân tích Bán kính Ảnh hưởng (Blast Radius) cho từng Change Unit

| Change Unit ID | Tên Change Unit | Mức độ ảnh hưởng (Impact Level) | Phạm vi ảnh hưởng chi tiết (Blast Radius Description) |
|---|---|---|---|
| **CU-001** | **Core HTTP Server & Handler** | **Production** | Nếu thay đổi lỗi, toàn bộ HTTP endpoints (`/api/health`, `/api/scrape`, `/api/sched`) ngưng hoạt động, UptimeRobot báo lỗi, Render container mất khả năng phục vụ request. |
| **CU-002** | **Scheduler & Tick Loop** | **System** | Nếu thay đổi lỗi, lịch tự động hối giao/lấy/trả bị ngừng trệ, scheduler không trigger cào dữ liệu, ảnh hưởng trực tiếp đến việc gửi thông báo định kỳ cho AM và Trợ lý Vùng. |
| **CU-003** | **Web Scraper Module** | **System** | Nếu thay đổi lỗi, dữ liệu tồn phiếu không thể cào từ GHN Vận Hành, dẫn đến dữ liệu trên Google Sheets bị cũ (stale data) hoặc trống. |
| **CU-004** | **Google Sheets Sync Engine** | **Module** | Nếu thay đổi lỗi, dữ liệu chi tiết phiếu không đồng bộ lên Google Sheets, Dashboard trên Cloudflare Pages mất dữ liệu hiển thị realtime. |
| **CU-005** | **GTalk Notification Sender** | **Module** | Nếu thay đổi lỗi, AM và Trợ lý Vùng không nhận được tin nhắn nhắc phiếu tồn, gây chậm trễ trong quy trình vận hành bưu cục. |
