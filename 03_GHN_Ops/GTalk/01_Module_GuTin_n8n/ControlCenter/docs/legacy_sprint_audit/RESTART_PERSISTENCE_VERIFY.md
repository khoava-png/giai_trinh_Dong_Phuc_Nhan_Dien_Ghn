# RESTART PERSISTENCE VERIFY — INC-P0-001

> **Order Reference:** ORDER-P0-004  
> **Date:** 15/09/2026  

## 1. Biên bản Kiểm tra Tính bền vững Sau khi Restart (Restart Persistence Verification)
- **Trình tự kiểm tra:**
  1. Lưu cấu hình lịch trên UI (`enabled = true`).
  2. Xác nhận dữ liệu đã được lưu persistent trên Upstash Redis (`control_center:sched`) và file local `sched.json`.
  3. Thực hiện restart service (mô phỏng Render instance restart).
  4. Gọi request `GET /api/sched/get`.
  5. Reload giao diện UI và so sánh dữ liệu trước/sau restart.
- **Kết quả:**
  - Dữ liệu lịch được map lại hoàn toàn nguyên vẹn từ backend.
  - Trạng thái `enabled = true` vẫn duy trì vững chắc, UI hiển thị **"ĐANG BẬT"**.
  - Không phát sinh hiện tượng mất lịch cũ hay tạo lịch mới ngoài ý muốn.
  - Idempotency Lock không bị ảnh hưởng, không có hiện tượng chạy lặp chu kỳ hay gửi trùng lặp tin nhắn GTalk.
  - Scheduler hoạt động ổn định, không có regression.
