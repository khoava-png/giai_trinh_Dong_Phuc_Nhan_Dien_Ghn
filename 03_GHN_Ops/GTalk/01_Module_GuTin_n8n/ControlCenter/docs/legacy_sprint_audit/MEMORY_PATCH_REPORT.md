# MEMORY PATCH REPORT — GHN CONTROL CENTER SPRINT-2

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-005 (Sprint-2 Authorization)  

## 1. Nội dung Patch Tối ưu hóa Bộ nhớ
- **Bổ sung Garbage Collection chủ động:** Gọi `import gc; gc.collect()` tại các mốc `FINISH` trong `action_scrape()` và mốc `done` trong `_sched_cycle()`.
- **Mục đích:** Ép Python thu hồi ngay lập tức các cấu trúc dữ liệu thô tạm thời (`tickets`, `rows_ct`, `rows_ton`, `co_cau`) sau khi hoàn tất chu kỳ nhắc phiếu, ngăn chặn hiện tượng tích lũy bộ nhớ (Memory Creep) trên môi trường Render Free (512 MB RAM).
- **Tuân thủ nguyên tắc:** Không làm thay đổi bất kỳ business logic, API contract, Google Sheets output hay GTalk message payload nào.
