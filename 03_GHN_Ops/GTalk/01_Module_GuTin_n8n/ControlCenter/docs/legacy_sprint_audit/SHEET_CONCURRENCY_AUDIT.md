# SHEET CONCURRENCY AUDIT — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-001 (Google Sheets & Apps Script Full Audit)  

## 1. Kiểm định Đồng thời (Concurrency Audit)
- **Apps Script Locks:** Không áp dụng (do không sử dụng Apps Script).
- **Backend Thread Locks:** Python backend sử dụng `_sched_lock` (RLock) để đồng bộ hóa các thao tác lịch trình và trạng thái chu kỳ.
- **Race Condition Analysis:** Do hệ thống chỉ chạy một instance duy nhất trên Render Free và các chu kỳ cào được khóa tuần tự qua `_cycle_state["running"]`, nguy cơ ghi đè dữ liệu đồng thời (concurrent write race condition) từ phía backend là cực kỳ thấp. Tuy nhiên, việc đọc dữ liệu từ Google Sheets bởi Dashboard tĩnh trên Cloudflare có thể xảy ra trong lúc backend đang ghi, được giảm thiểu nhờ sử dụng In-Memory RAM Cache (`_cached_chi_tiet`).
