# SPRINT SEQUENCE — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-004 (Execution Readiness Gate)  

## 1. Khóa Trình tự Thực hiện Toàn bộ Sprint (Sprint Master Sequence)

| Sprint ID | Tên Sprint | Mục tiêu chính (Objective) | Trạng thái ủy quyền code |
|---|---|---|---|
| **Sprint 1** | Baseline & Validation | Hoàn thiện take over, audit, baseline, impact analysis & execution gate. | ❌ **Chỉ tạo tài liệu** |
| **Sprint 2** | Memory Optimization & Raw Data | Thực thi Epic 1 & Epic 5: Xóa bỏ Global RAM Cache, tích hợp `gc.collect()`, tối ưu hóa RAM. | ✅ **ĐƯỢC PHÉP CHỈNH SỬA SOURCE** |
| **Sprint 3** | Sheets Batching & Formulas | Thực thi Epic 2 & Epic 3: Tối ưu Batching Google Sheets và cấu hình `QUERY`/`FILTER`. | 🕒 Chờ sau Sprint 2 |
| **Sprint 4** | Dashboard & Verification | Thực thi Epic 4 & Epic 6: Kiểm tra Dashboard Cloudflare và Load Test toàn diện. | 🕒 Chờ sau Sprint 3 |
