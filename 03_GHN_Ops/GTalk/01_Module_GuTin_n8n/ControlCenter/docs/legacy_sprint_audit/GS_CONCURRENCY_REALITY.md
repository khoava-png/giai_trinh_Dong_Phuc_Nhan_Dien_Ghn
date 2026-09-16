# GS CONCURRENCY REALITY — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-002 (Google Sheets Production Reality Verification)  

## 1. Khảo sát Toàn bộ Điểm Ghi Google Sheets (Write Entry Points)
Danh sách các luồng có khả năng kích hoạt ghi dữ liệu lên Google Sheets trong hệ thống:
1. **Scheduler Worker (`_sched_worker`):** Tự động chạy định kỳ theo lịch trình.
2. **Manual Scrape API (`POST /api/scrape`):** Người dùng kích hoạt thủ công qua Dashboard.
3. **Scheduler Now API (`POST /api/sched/now`):** Người dùng bấm chạy lịch ngay lập tức.
4. **Startup Sync (nếu có):** Đồng bộ khởi động service.

## 2. Kiểm tra Khóa đồng bộ (Locking Mechanism)
- **Cơ chế hiện tại:** Toàn bộ các thao tác cào và đồng bộ được bảo vệ bởi trạng thái `_cycle_state["running"]` kết hợp với kiểm tra vòng lặp, đảm bảo không có 2 tiến trình cào đồng thời chạy song song trên cùng một instance backend.
- **Kết luận:** **PROVEN** đối với phạm vi đơn tiến trình (single instance) trên Render Free. Tuy nhiên, nếu triển khai scale-out nhiều replica (nhiều instance chạy đồng thời), cơ chế khóa hiện tại qua biến RAM sẽ không đủ và cần đồng bộ qua Redis Distributed Lock.
