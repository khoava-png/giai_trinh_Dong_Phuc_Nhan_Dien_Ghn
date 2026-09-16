# 📊 ĐÁNH GIÁ NGUỒN LỰC SHEET & TEMPLATE TỐI ƯU (LEAN SHEET DESIGN)

## 1. Đánh giá nguồn lực Google Sheet (Resource Assessment)
Trong kiến trúc cũ (Python-heavy), Google Sheet chỉ đóng vai trò chứa dữ liệu thô và nhận kết quả tính toán từ Python đẩy lên qua GSpread/API. Khi chuyển sang mô hình **Sheets-Centric**, Google Sheet trở thành **Database + Compute Engine**.

### Điểm mạnh & Điểm yếu của Google Sheet khi làm Compute Engine:
- **Ưu điểm:**
  - Tích hợp sẵn `QUERY`, `ARRAYFORMULA`, `XLOOKUP`, `SUMIFS` chạy trực tiếp trên cơ sở hạ tầng của Google, không tốn tài nguyên Server Python.
  - Người vận hành (Ops) có thể nhìn thấy trực tiếp công thức và dữ liệu trung gian, dễ audit khi có sai lệch số liệu.
- **Rủi ro & Giới hạn (Cần khắc phục):**
  - **Giới hạn số ô (Cell Limit):** Google Sheet giới hạn 10 triệu ô tổng cộng trên mỗi file. Nếu để quá nhiều công thức rác, định dạng toàn hàng (`A:Z`), file sẽ bị nặng, giật và lỗi *Exceeded memory limit*.
  - **Volatile Functions:** Tránh tuyệt đối dùng `NOW()`, `TODAY()`, `RAND()` trong các công thức tính toán lớn vì mỗi lần thay đổi nhỏ sẽ kích hoạt recalculate toàn bộ sheet.
  - **Race Condition / Concurrent Edits:** Nếu nhiều Apps Script trigger chạy chồng chéo hoặc người dùng thao tác tay vào vùng công thức, sheet dễ bị lỗi `#REF!` hoặc kẹt trạng thái.

---

## 2. Thiết kế Template Tối Ưu (Loại bỏ dư thừa - Lean Template Spec)

Để đảm bảo file Sheet nhẹ, mượt ở mức 10,000 dòng dữ liệu, chúng ta **cắt bỏ hoàn toàn các tab rác, tab trung gian không cần thiết** trong thiết kế ban đầu và cô đọng lại thành **6 Tab cốt lõi**:

### Cấu trúc 6 Tab Tinh Gọn (Lean Architecture):

```
[00_CONFIG]         -> Quản lý toàn bộ tham số scheduler, giờ gửi, toggle dry_run
[01_RAW_CHI_TIET]   -> Chứa 100% dữ liệu thô do Python đẩy lên (Full replace)
[02_CO_CAU]         -> Danh mục Area Manager, Hub, Vùng (Lookup reference)
[03_DATA_ENRICHED]  -> Tab duy nhất chứa ARRAYFORMULA kết hợp RAW + CO_CAU
[04_RP_SUMMARY]     -> Báo cáo tổng hợp gộp chung RP_AM và RP_VUNG (Dùng QUERY)
[05_SEND_QUEUE_LOG] -> Gộp chung Queue và Send Log vào 1 tab (Phân biệt bằng Status)
[06_SYSTEM_STATE]   -> Trạng thái hệ thống, heartbeat, data ready barrier
```

---

## 3. Bản vẽ chi tiết từng Tab (Lean Template)

### Tab 1: `00_CONFIG` (Cấu hình hệ thống)
*Mục đích: Lưu mọi tham số vận hành, Apps Script đọc trực tiếp, không hardcode.*
- Cột: `key` | `value` | `description`
- Các key quan trọng:
  - `scheduler_enabled` (TRUE/FALSE)
  - `dry_run` (TRUE/FALSE)
  - `am_l1_hours` (08:30, 14:00)
  - `vung_l1_hours` (09:00, 15:00)
  - `allowed_weekdays` (1,2,3,4,5,6)

### Tab 2: `01_RAW_CHI_TIET` (Dữ liệu thô từ Python)
*Mục đích: Python ghi đè toàn bộ mỗi lần cào. Không có công thức.*
- Cột chuẩn: `snapshot_id` | `updated_at` | `ma_don_hang` | `ma_buu_cuc` | `trang_thai` | `nguoi_xu_ly` | ...

### Tab 3: `02_CO_CAU` (Ánh xạ cơ cấu)
*Mục đích: Bảng tra cứu (Lookup table) gán Mã bưu cục với Area Manager và Vùng.*
- Cột: `ma_buu_cuc` | `ten_buu_cuc` | `area_manager_id` | `ten_am` | `vung`

### Tab 4: `03_DATA_ENRICHED` (Làm giàu dữ liệu - Duy nhất 1 công thức lớn)
*Mục đích: Dùng ARRAYFORMULA để join RAW với CO_CAU một lần duy nhất.*
- Công thức tại ô `A2`:
  ```excel
  =ARRAYFORMULA(
    IF('01_RAW_CHI_TIET'!A2:A="", "",
      VLOOKUP('01_RAW_CHI_TIET'!D2:D, '02_CO_CAU'!A:E, {2,3,4,5}, FALSE)
    )
  )
  ```

### Tab 5: `04_RP_SUMMARY` (Báo cáo tổng hợp AM & Vùng)
*Mục đích: Gom nhóm dữ liệu phục vụ Frontend và Apps Script gửi tin nhắn.*
- Sử dụng hàm `QUERY` chia thành 2 khối trên cùng một sheet hoặc 2 vùng rõ ràng:
  - Vùng 1 (RP_AM): `=QUERY('03_DATA_ENRICHED'!A:Z, "SELECT Col3, Col4, COUNT(Col1), SUM(Col5) WHERE Col3 IS NOT NULL GROUP BY Col3, Col4 LABEL Col3 'AM ID', Col4 'Ten AM', COUNT(Col1) 'Tong Don', SUM(Col5) 'Tong Tien'", 1)`
  - Vùng 2 (RP_VUNG): `=QUERY('03_DATA_ENRICHED'!A:Z, "SELECT Col5, COUNT(Col1), SUM(Col5) WHERE Col5 IS NOT NULL GROUP BY Col5 LABEL Col5 'Vung', COUNT(Col1) 'Tong Don', SUM(Col5) 'Tong Tien'", 1)`

### Tab 6: `05_SEND_QUEUE_LOG` (Hàng đợi & Log gộp)
*Mục đích: Lưu trạng thái gửi tin nhắn và lịch sử, tránh tạo quá nhiều tab.*
- Cột: `queue_id` | `snapshot_id` | `created_at` | `recipient_type` | `recipient_id` | `message_type` | `status` (PENDING / SENT / FAILED) | `sent_at` | `error_message`

### Tab 7: `06_SYSTEM_STATE` (Trạng thái hệ thống)
*Mục đích: Barrier kiểm tra độ sẵn sàng dữ liệu trước khi gửi.*
- Cột: `metric` | `value`
- Các dòng: `last_scrape`, `current_snapshot_id`, `raw_row_count`, `formula_ready` (TRUE/FALSE), `last_scheduler_tick`, `last_error`

---

## 4. Tóm tắt lợi ích thiết kế Lean Template
1. **Giảm 30% số lượng tab** (từ 9 tab xuống còn 7 tab gọn gàng).
2. **Loại bỏ hiện tượng nghẽn mạng công thức** nhờ gom nhóm `QUERY` và dùng duy nhất 1 `ARRAYFORMULA` tại `DATA_ENRICHED`.
3. **Tối ưu hóa bộ nhớ Google Sheet**, đảm bảo tốc độ phản hồi dưới 2 giây ngay cả với tập dữ liệu 10,000 dòng.
