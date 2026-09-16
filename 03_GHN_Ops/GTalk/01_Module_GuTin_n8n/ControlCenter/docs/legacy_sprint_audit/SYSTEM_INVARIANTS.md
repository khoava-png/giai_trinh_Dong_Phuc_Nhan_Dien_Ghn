# SYSTEM INVARIANTS — GHN CONTROL CENTER PRODUCTION

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-002 (Baseline Freeze)  

## 1. Định nghĩa Invariants Hệ thống (System Invariants)
System Invariants là các bất biến kỹ thuật bắt buộc phải được duy trì trong mọi hoàn cảnh, không được phép vi phạm dưới bất kỳ hình thức refactor hay thay đổi nào.

| Invariant ID | Tên Bất Biến (Invariant Name) | Quy tắc kỹ thuật bắt buộc | Bằng chứng / Source Reference |
|---|---|---|---|
| **SYS-INV-001** | **Single-Process Binding** | Render Free chỉ cho phép vận hành duy nhất một tiến trình Python đơn, sử dụng mô hình Threading cho HTTP request. | `control_center.py` (ThreadingHTTPServer) |
| **SYS-INV-002** | **Environment Variables Mandatory** | Hệ thống không được khởi động nếu thiếu các biến môi trường cốt lõi (`OP_WEB_USER`, `OP_WEB_PASS`, `GOOGLE_KEY_FILE`, `GTALK_OA_TOKEN`). | `KE_HOACH_VA_TIEN_TRINH_DU_AN.md` |
| **SYS-INV-003** | **Memory Meter Compliance** | Mọi điểm ghi loglifecycle bắt buộc phải tuân thủ chuẩn JSON 17 trường do `memory_meter.py` định nghĩa. | `memory_meter.py`, `control_center.py` |
| **SYS-INV-004** | **Safety Backoff Guard (KN1)** | Khi cào dữ liệu thất bại liên tiếp 3 lần, hệ thống bắt buộc phải tự động kích hoạt chế độ nghỉ (backoff) trong 60 phút. | `KE_HOACH_VA_TIEN_TRINH_DU_AN.md` |
| **SYS-INV-005** | **Admin Alert Guard (KN2)** | Khi cào thất bại liên tiếp đủ 3 lần, bắt buộc phải gửi 1 thông báo cảnh báo khẩn cấp về GTalk Admin (`3049378`). | `KE_HOACH_VA_TIEN_TRINH_DU_AN.md` |
| **SYS-INV-006** | **Timezone Consistency** | Toàn bộ mốc thời gian lịch trình và lịch chạy bắt buộc tuân thủ múi giờ chuẩn `Asia/Ho_Chi_Minh`. | `PROJECT_MASTER.md` |
