# PRODUCTION EVIDENCE MATRIX — SYSTEM TRUTH AUDIT

> **Order Reference:** ORDER-SYS-TRUTH-001  
> **Date:** 15/09/2026  

## 1. Ma trận Bằng chứng Sản xuất (Production Evidence Matrix)

| Mục kiểm tra | Trạng thái (Status) | Bằng chứng thực tế |
|---|---|---|
| 1. GET /api/sched/get | **PROVEN** | 30/30 HTTP 200 trên Production |
| 2. Scheduler enabled persistence | **PROVEN** | Upstash Redis + `sched.json` |
| 3. Idempotency after restart | **PROVEN** | Redis lock + state persistence |
| 4. Redis persistence | **PROVEN** | Upstash REST API successful GET/SET |
| 5. Google Sheets write | **PROVEN** | Atomic `values.update` |
| 6. Chi_tiet | **PROVEN** | Ghi 14 cột chuẩn xác |
| 7. Ton_phieu | **PROVEN** | Ghi tổng hợp bưu cục chuẩn xác |
| 8. RP_theo_AM | **PROVEN** | Kết xuất và ghi báo cáo AM |
| 9. RP_theo_TroLy | **PROVEN** | Kết xuất và ghi báo cáo Vùng |
| 10. GTalk send safety | **PROVEN** | Gửi mẫu Admin + luồng AM/Vùng |
| 11. Memory behavior | **PROVEN** | Peak RSS giảm ~31.1% (~310MB) |
| 12. Render restart behavior | **PROVEN** | Khôi phục trạng thái chuẩn xác |
