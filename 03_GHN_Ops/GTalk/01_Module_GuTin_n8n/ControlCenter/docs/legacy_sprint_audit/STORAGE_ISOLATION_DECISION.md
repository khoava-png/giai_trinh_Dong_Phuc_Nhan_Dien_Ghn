# STORAGE ISOLATION DECISION — ORDER-CORE-002

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-CORE-002  

## 1. Quyết định Về Cô lập Lưu trữ (Storage Isolation Decision)
- **Lựa chọn:** **Option A kết hợp deterministic tail cleanup và kiểm tra tính hợp lệ trước khi dịch chuyển Commit Pointer**.
- **Lý do:** Do hạ tầng Google Sheets không có tính năng atomic table swapping ngay lập tức giữa các tab production mà không làm gián đoạn URL/liên kết tab của Dashboard, giải pháp tối ưu là thực hiện ghi toàn bộ dữ liệu của generation mới, chạy bước `VALIDATING` tính toán checksum/ticket count, và chỉ khi PASS tuyệt đối mới cập nhật `CURRENT_COMMITTED_GENERATION` pointer trên Upstash Redis. Mọi consumer (GTalk, Dashboard) bắt buộc phải đọc qua pointer này.
