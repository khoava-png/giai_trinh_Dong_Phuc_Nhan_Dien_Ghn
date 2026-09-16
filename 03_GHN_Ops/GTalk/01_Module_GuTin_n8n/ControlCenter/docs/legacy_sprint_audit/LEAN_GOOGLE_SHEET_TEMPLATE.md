# GOOGLE SHEET TEMPLATE STRUCTURE & SETUP GUIDE
*Dự án: GHN Control Center - Sheets-Centric Architecture (ORDER-ARCH-V3)*

## Hướng dẫn tạo Google Sheet Template thực tế (7 Tabs chuẩn)

Bạn hãy tạo một Google Sheet mới trên Google Drive với tên gọi: **`GHN_ControlCenter_Lean_POC`** và thiết lập chính xác **7 tab** theo thứ tự và cấu trúc dưới đây để sẵn sàng kết nối Python collector và Apps Script scheduler:

---

### TAB 1: `00_CONFIG`
*Mục đích: Quản lý toàn bộ tham số scheduler, giờ gửi, chế độ dry_run.*

| A (`key`) | B (`value`) | C (`description`) |
| :--- | :--- | :--- |
| `scheduler_enabled` | `TRUE` | Bật/tắt tự động gửi tin nhắn |
| `dry_run` | `TRUE` | Chế độ giả lập (không gọi API GTalk thật) |
| `am_l1_hours` | `08:30, 14:00` | Khung giờ gửi L1 cho Area Manager |
| `am_l2_hours` | `11:00, 16:30` | Khung giờ gửi L2 cho Area Manager |
| `vung_l1_hours` | `09:00, 15:00` | Khung giờ gửi L1 cho Vùng |
| `vung_l2_hours` | `11:30, 17:00` | Khung giờ gửi L2 cho Vùng |
| `allowed_weekdays` | `1,2,3,4,5,6` | Các ngày trong tuần được phép chạy (Thứ 2 - Thứ 6/7) |

---

### TAB 2: `01_RAW_CHI_TIET`
*Mục đích: Python ghi đè toàn bộ dữ liệu thô tại đây (Full snapshot replacement).*

| A (`snapshot_id`) | B (`updated_at`) | C (`ma_don_hang`) | D (`ma_buu_cuc`) | E (`trang_thai`) | F (`nguoi_xu_ly`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| *(Dữ liệu do Python đẩy lên tự động mỗi chu kỳ cào)* | | | | | |

---

### TAB 3: `02_CO_CAU`
*Mục đích: Bảng tra cứu (Lookup table) ánh xạ Mã bưu cục với Area Manager và Vùng.*

| A (`ma_buu_cuc`) | B (`ten_buu_cuc`) | C (`area_manager_id`) | D (`ten_am`) | E (`vung`) |
| :--- | :--- | :--- | :--- | :--- |
| `SGN123` | `BC Quan 1` | `AM001` | `Tran Van B` | `Mien Nam` |
| `HAN456` | `BC Cau Giay` | `AM002` | `Le Van C` | `Mien Bac` |

---

### TAB 4: `03_DATA_ENRICHED`
*Mục đích: Làm giàu dữ liệu tự động bằng ARRAYFORMULA kết hợp RAW và CO_CAU.*

- **Công thức tại ô `A2`**:
  ```excel
  =ARRAYFORMULA(
    IF('01_RAW_CHI_TIET'!A2:A="", "",
      VLOOKUP('01_RAW_CHI_TIET'!D2:D, '02_CO_CAU'!A:E, {2,3,4,5}, FALSE)
    )
  )
  ```

---

### TAB 5: `04_RP_SUMMARY`
*Mục đích: Báo cáo tổng hợp AM & Vùng dùng hàm QUERY.*

- **Khối 1 (RP_AM - Bắt đầu từ ô `A1`):**
  ```excel
  =QUERY('03_DATA_ENRICHED'!A:Z, "SELECT Col3, Col4, COUNT(Col1), SUM(Col5) WHERE Col3 IS NOT NULL GROUP BY Col3, Col4 LABEL Col3 'AM ID', Col4 'Ten AM', COUNT(Col1) 'Tong Don', SUM(Col5) 'Tong Tien'", 1)
  ```

- **Khối 2 (RP_VUNG - Đặt cách xuống 5 dòng, ví dụ tại ô `F1` hoặc dòng bên dưới):**
  ```excel
  =QUERY('03_DATA_ENRICHED'!A:Z, "SELECT Col5, COUNT(Col1), SUM(Col5) WHERE Col5 IS NOT NULL GROUP BY Col5 LABEL Col5 'Vung', COUNT(Col1) 'Tong Don', SUM(Col5) 'Tong Tien'", 1)
  ```

---

### TAB 6: `05_SEND_QUEUE_LOG`
*Mục đích: Hàng đợi tin nhắn và lịch sử gửi (Append-only).*

| A (`queue_id`) | B (`snapshot_id`) | C (`created_at`) | D (`recipient_type`) | E (`recipient_id`) | F (`message_type`) | G (`status`) | H (`sent_at`) | I (`error`) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Q_001` | `SNAP_2026` | `2026-09-15` | `AM` | `AM001` | `L1_WARNING` | `PENDING` | | |

---

### TAB 7: `06_SYSTEM_STATE`
*Mục đích: Trạng thái hệ thống & Data Ready Barrier.*

| A (`metric`) | B (`value`) | C (`description`) |
| :--- | :--- | :--- |
| `last_scrape` | `2026-09-15 08:00:00` | Thời điểm Python cập nhật RAW gần nhất |
| `current_snapshot` | `SNAP_20260915_0800` | ID snapshot hiện tại |
| `raw_row_count` | `5000` | Tổng số dòng dữ liệu thô |
| `formula_ready` | `TRUE` | Trạng thái công thức đã tính toán xong không lỗi |
| `last_scheduler_tick` | `2026-09-15 08:35:00` | Lần chạy Apps Script gần nhất |
| `last_error` | *(Trống)* | Lỗi hệ thống gần nhất (nếu có) |
