# UI MAPPING VERIFY — INC-P0-001

> **Order Reference:** ORDER-P0-004  
> **Date:** 15/09/2026  

## 1. Biên bản Xác thực Mapping Dữ liệu Giao diện (UI Mapping Verification)
Sau khi reload giao diện Production (`index.html`), hàm `loadSched()` gọi thành công endpoint lấy lịch và map chính xác toàn bộ các trường dữ liệu từ backend lên UI:
- **enabled / dry_run / delay_min:** Khớp hoàn toàn.
- **AM L1 & L2 hours (`sch_hours_am_all`, `sch_hours_am_cd`):** Map chuẩn xác.
- **AM loại (`am_cd_loai`):** Map chuẩn xác.
- **Vùng L1 & L2 hours (`sch_hours_vung_all`, `sch_hours_vung_cd`):** Map chuẩn xác.
- **Vùng loại (`vung_cd_loai`):** Map chuẩn xác.
- **allowed_weekdays:** Checkbox hiển thị đúng các ngày trong tuần đã lưu.
- **last_run_am & last_run_vung:** Hiển thị đúng thời điểm chạy gần nhất.
- **Trạng thái Bật/Tắt:** Khi Redis lưu `enabled = true`, UI hiển thị rõ ràng **"ĐANG BẬT"** ngay lập tức sau khi reload browser mà không cần bấm nút "Lưu lịch".
