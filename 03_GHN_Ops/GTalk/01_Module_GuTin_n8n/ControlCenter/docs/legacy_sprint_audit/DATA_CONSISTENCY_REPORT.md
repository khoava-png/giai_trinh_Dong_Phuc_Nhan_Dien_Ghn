# DATA CONSISTENCY REPORT — SYSTEM TRUTH AUDIT

> **Order Reference:** ORDER-SYS-TRUTH-001  
> **Date:** 15/09/2026  

## 1. Kết quả Kiểm định Tính Nhất Quán Dữ Liệu (Data Consistency)
- **Kịch bản A (2500 -> 2000 rows):** Đạt tuyệt đối nhờ cơ chế ghi đè nguyên tử `values.update` (loại bỏ hoàn toàn rác dư thừa so với khi dùng clear).
- **Kịch bản B (2000 -> 2500 rows):** Đạt tuyệt đối, dữ liệu mới ghi đè chuẩn xác, không bị giới hạn range cũ.
- **Kịch bản C & D (Dataset <-> Zero rows):** Xử lý an toàn, tab ghi nhận đúng 0 dòng hoặc cập nhật tập dữ liệu mới, không phát sinh stale rows hay formula lệch.
