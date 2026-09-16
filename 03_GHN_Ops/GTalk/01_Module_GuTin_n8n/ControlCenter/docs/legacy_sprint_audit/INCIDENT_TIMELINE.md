# INCIDENT TIMELINE — SYSTEM TRUTH AUDIT

> **Order Reference:** ORDER-SYS-TRUTH-001  
> **Date:** 15/09/2026  

## 1. Dòng thời gian Sự cố & Khắc phục (Incident Timeline)

### Incident 1: `INC-P0-001` (/api/sched/get HTTP 502/404)
- **Symptom:** Client/Dashboard gọi lấy lịch tự động nhận HTTP 502 / 404.
- **Root Cause ban đầu (Suy luận):** Nghi ngờ Upstash Redis timeout hoặc OOM.
- **Root Cause cuối (Chứng minh):** Route `/api/sched/get` chỉ được đăng ký trong khối `do_POST()`, nhưng client gọi nhầm phương thức GET, dẫn đến Routing Mismatch trong `do_GET()`.
- **Patch:** Đăng ký bổ sung route `GET /api/sched/get` trong `do_GET()` kết hợp giữ nguyên `POST` cho backward compatibility.
- **Regression:** Không có.
- **Production Verification:** Đạt 30/30 HTTP 200 OK trên Production.
- **Trạng thái:** **CLOSED**.

### Incident 2: Google Sheets Partial Write / Empty State
- **Symptom:** Rủi ro Dashboard đọc phải tab trống khi backend đang ghi dữ liệu.
- **Root Cause cuối (Chứng minh):** Hàm `write_tab` gọi `batchClear` (xóa A:ZZ) trước khi `values.update`.
- **Patch:** Loại bỏ `batchClear`, chuyển sang ghi đè nguyên tử bằng `values.update` (`RAW`).
- **Regression:** Không có.
- **Trạng thái:** **CLOSED**.
