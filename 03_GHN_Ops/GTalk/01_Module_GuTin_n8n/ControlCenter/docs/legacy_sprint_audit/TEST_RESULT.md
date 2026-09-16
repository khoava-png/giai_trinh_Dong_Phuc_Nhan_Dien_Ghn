# TEST RESULT — /api/sched/get ROUTING FIX

> **Order Reference:** ORDER-P0-003  
> **Date:** 15/09/2026  

## 1. Kết quả Kiểm thử (Test Results)
- **Số lần gọi liên tiếp:** 30 lần.
- **HTTP Status Code:** 30/30 lần trả về HTTP 200 OK.
- **JSON Parsing:** 30/30 lần parse thành công, trả về đúng schema lịch hiện hành.
- **HTTP 404 / 502 / 500:** 0 lần xuất hiện.
- **Fallback Mechanism:** Hoạt động chính xác khi Redis không khả dụng (đọc từ `sched.json`).
- **Backward Compatibility:** Cả GET và POST đều hoạt động hoàn hảo, map đúng trạng thái `enabled`, AM schedule, Vùng schedule và `allowed_weekdays` lên UI mà không làm mất lịch cũ.
