# BACKLOG — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  

## Product Backlog (Theo WBS & Epic)

### [P0] — Critical & Production Stability
- **BACKLOG-001:** Xóa bỏ Global RAM Cache (`_cached_rows_ct`), chuyển sang file nén tạm trên đĩa (`/tmp`) hoặc truy vấn trực tiếp Google Sheets (Epic 5).
- **BACKLOG-002:** Bổ sung chủ động gọi `gc.collect()` tại mốc `JOB_FINISH` trong scheduler để giải phóng RAM triệt để (Epic 5).
- **BACKLOG-003:** Tối ưu hóa API ghi tab `Chi_tiet` và `Ton_phieu` dạng Batch để giảm thời gian giữ kết nối và tiêu thụ RAM (Epic 2).

### [P1] — Architecture & Reporting Migration
- **BACKLOG-004:** Cấu hình công thức `QUERY`/`FILTER` tự động cho tab `RP_AM` và tab `RP_Vùng` trên Google Sheets để hoàn tất phương án PA2 (Epic 3).
- **BACKLOG-005:** Viết Unit Test tự động cho backend lõi (`control_center.py`) đạt độ bao phủ tối thiểu 80%.

### [P2] — Monitoring & Dashboard Enhancement
- **BACKLOG-006:** Tích hợp kiểm tra hiển thị Dashboard Cloudflare Pages với cấu trúc dữ liệu mới sau khi tách bảng báo cáo (Epic 4).
- **BACKLOG-007:** Chuẩn hóa toàn bộ log hoạt động lưu vào Upstash Redis kèm cơ chế xoay vòng (rotation) chống phình to bộ nhớ (Epic 6).

### [P3] — Refactoring & Code Quality
- **BACKLOG-008:** Refactor `control_center.py` thành các module nhỏ (Technical Debt TD-001).
