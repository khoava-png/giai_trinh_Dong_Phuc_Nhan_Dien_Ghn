# TORTURE TEST — ORDER-CORE-002

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-CORE-002  

## 1. Kết quả Torture Test (Two-Cycle & Restart Torture)
- **Two-Cycle Torture (2500 -> 2000 -> 3000 rows):** Đạt chuẩn, không sinh stale rows hay dữ liệu trộn lẫn.
- **Restart Torture (10 cycles kill & restart):** Dữ liệu thế hệ đã commit phục hồi chuẩn xác sau mỗi lần restart service.
- **Trạng thái:** **PASS**.
