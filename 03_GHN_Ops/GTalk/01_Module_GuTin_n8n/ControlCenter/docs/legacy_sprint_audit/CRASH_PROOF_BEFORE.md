# CRASH-PROOF BEFORE — ORDER-CORE-002

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-CORE-002 (Crash-Proof Commit Protocol)  

## 1. Trạng thái Khảo sát Trước Thiết kế Crash-Proof
- **Hành vi hiện tại:** Hệ thống ghi trực tiếp vào các tab live (`Chi_tiet`, `Ton_phieu`, `RP_theo_AM`, `RP_theo_TroLy`) thông qua `values.update` mà không có durable generation record trên Upstash Redis làm Control Plane.
- **Rủi ro Crash (F1-F9):** Nếu xảy ra ngắt tiến trình đột ngột (SIGKILL) giữa chừng khi đang ghi các tab, hệ thống có thể dẫn đến trạng thái trộn lẫn dữ liệu giữa chu kỳ cũ và chu kỳ mới (Mixed Generation State) trước khi được khắc phục bằng giao thức durable commit.
- **Mục tiêu:** Triển khai khung Durable Generation Record qua Upstash Redis, Commit Pointer (`CURRENT_COMMITTED_GENERATION`), Retry Policy chuẩn hóa và kiểm tra crash torture test.
