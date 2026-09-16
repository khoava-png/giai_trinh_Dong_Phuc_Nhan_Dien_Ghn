# 📋 LEAN SHEET TEMPLATE DRAFT (7 TABS)
*Dự án: GHN Control Center - Sheets-Centric Architecture (ORDER-ARCH-V3)*

Mẫu cấu trúc 7 tab tối ưu hóa hiệu năng, loại bỏ hoàn toàn các thành phần dư thừa, đảm bảo tốc độ phản hồi mượt mà cho dataset lên đến 10,000 dòng.

---

## 1. 00_CONFIG (Cấu hình hệ thống)
*Mục đích: Quản lý toàn bộ tham số vận hành, Apps Script đọc trực tiếp.*
| Cột A (`key`) | Cột B (`value`) | Cột C (`description`) |
|---|---|---|
| `scheduler_enabled` | `TRUE` | Bật/tắt tự động gửi tin nhắn |
| `dry_run` | `TRUE` | Chế độ giả lập (không gọi API GTalk thật) |
| `am_l1_hours` | `08:30, 14:00` | Khung giờ gửi L1 cho Area Manager |
| `am_l2_hours` | `11:00, 16:30` | Khung giờ gửi L2 cho Area Manager |
| `vung_l1_hours` | `09:00, 15:00` | Khung giờ gửi L1 cho Vùng |
| `vung_l2_hours` | `11:30, 17:00` | Khung giờ gửi L2 cho Vùng |
| `allowed_weekdays` | `1,2,3,4,5,6` | Các ngày trong tuần được phép chạy (Thứ 2 - Thứ 7) |

---

## 2. 01_RAW_CHI_TIET (Dữ liệu thô)
*Mục đích: Python ghi đè toàn bộ mỗi lần cào. Không chứa công thức.*
| Cột A (`snapshot_id`) | Cột B (`updated_at`) | Cột C (`ma_don_hang`) | Cột D (`ma_buu_cuc`) | Cột E (`trang_thai`) | Cột F (`nguoi_xu_ly`) | ... |
|---|---|---|---|---|---|---|
| `SNAP_20260915_0800` | `2026-09-15 08:00:00` | `GHN123456` | `SGN123` | `Dang xu ly` | `Nguyen Van A` | ... |

---

## 3. 02_CO_CAU (Ánh xạ cơ cấu)
*Mục đích: Bảng tra cứu (Lookup table) gán mã bưu cục với Area Manager và Vùng.*
| Cột A (`ma_buu_cuc`) | Cột B (`ten_buu_cuc`) | Cột C (`area_manager_id`) | Cột D (`ten_am`) | Cột E (`vung`) |
|---|---|---|---|---|
| `SGN123` | `BC Quan 1` | `AM001` | `Tran Van B` | `Mien Nam` |

---

## 4. 03_DATA_ENRICHED (Làm giàu dữ liệu)
*Mục đích: Dùng ARRAYFORMULA duy nhất để nối RAW với CO_CAU.*
- **Công thức ô A2:**
  ```excel
  =ARRAYFORMULA(
    IF('01_RAW_CHI_TIET'!A2:A="", "",
      VLOOKUP('01_RAW_CHI_TIET'!D2:D, '02_CO_CAU'!A:E, {2,3,4,5}, FALSE)
    )
  )
  ```

---

## 5. 04_RP_SUMMARY (Báo cáo tổng hợp AM & Vùng)
*Mục đích: Gom nhóm dữ liệu phục vụ Frontend và Apps Script.*
- **Vùng 1 (RP_AM - Từ dòng 1):**
  ```excel
  =QUERY('03_DATA_ENRICHED'!A:Z, "SELECT Col3, Col4, COUNT(Col1), SUM(Col5) WHERE Col3 IS NOT NULL GROUP BY Col3, Col4 LABEL Col3 'AM ID', Col4 'Ten AM', COUNT(Col1) 'Tong Don', SUM(Col5) 'Tong Tien'", 1)
  ```
- **Vùng 2 (RP_VUNG - Cách vài dòng bên dưới):**
  ```excel
  =QUERY('03_DATA_ENRICHED'!A:Z, "SELECT Col5, COUNT(Col1), SUM(Col5) WHERE Col5 IS NOT NULL GROUP BY Col5 LABEL Col5 'Vung', COUNT(Col1) 'Tong Don', SUM(Col5) 'Tong Tien'", 1)
  ```

---

## 6. 05_SEND_QUEUE_LOG (Hàng đợi & Lịch sử gửi)
*Mục đích: Quản lý queue tin nhắn và lưu log append-only chống trùng lặp.*
| Cột A (`queue_id`) | Cột B (`snapshot_id`) | Cột C (`created_at`) | Cột D (`recipient_type`) | Cột E (`recipient_id`) | Cột F (`message_type`) | Cột G (`status`) | Cột H (`sent_at`) | Cột I (`error`) |
|---|---|---|---|---|---|---|---|---|
| `Q_001` | `SNAP_20260915_0800` | `2026-09-15 08:30:00` | `AM` | `AM001` | `L1_WARNING` | `SENT` | `2026-09-15 08:30:12` | `` |

---

## 7. 06_SYSTEM_STATE (Trạng thái hệ thống)
*Mục đích: Barrier kiểm tra độ sẵn sàng dữ liệu trước khi kích hoạt gửi tin.*
| Cột A (`metric`) | Cột B (`value`) | Cột C (`description`) |
|---|---|---|
| `last_scrape` | `2026-09-15 08:00:00` | Thời điểm Python cập nhật RAW gần nhất |
| `current_snapshot` | `SNAP_20260915_0800` | ID snapshot hiện tại |
| `raw_row_count` | `5000` | Tổng số dòng dữ liệu thô |
| `formula_ready` | `TRUE` | Trạng thái công thức đã tính toán xong không lỗi |
| `last_scheduler_tick`| `2026-09-15 08:35:00` | Lần chạy Apps Script gần nhất |
| `last_error` | `` | Lỗi hệ thống gần nhất (nếu có) |
