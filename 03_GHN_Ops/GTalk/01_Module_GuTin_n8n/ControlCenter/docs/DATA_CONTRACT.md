# GHN CONTROL CENTER — DATA CONTRACT & DATA DICTIONARY V3

## 1. TỔNG QUAN
Tài liệu Data Contract quy định chặt chẽ cấu trúc, kiểu dữ liệu, alias nguồn và ràng buộc xác thực dữ liệu giữa Web Vận Hành GHN (API Source), Google Sheets (Storage Layer), RAM Cache và GTalk Dispatch Layer.

---

## 2. BẢNG ÁNH XẠ ALIAS NGUỒN (SOURCE API ALIAS MATRIX)

| Tên Cột Chuẩn | Tên Nguồn API | Kiểu Dữ Liệu | Bắt Buộc | Giá Trị Hợp Lệ | Mục Đích Sử Dụng |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ma_buu_cuc` | `value` / `bc` | `string` | **BẮT BUỘC** | Không rỗng (VD: `"9101"`, `"HN01"`) | Khóa chính bưu cục, định danh kho |
| `ten_buu_cuc` | `label` / `name` | `string` | **BẮT BUỘC** | Tên bưu cục có dấu (VD: `"Kho Tân Bình"`) | Hiển thị bảng tính, thông báo GTalk |
| `ma_ticket` | `number` | `string` | **BẮT BUỘC** | Số định danh ticket (VD: `"T123456"`) | Khóa chính ticket xử lý |
| `ma_don` | `order_code` | `string` | **BẮT BUỘC** | Mã đơn hàng GHN (VD: `"GHOE123"`) | Mã tra cứu đơn trên hệ thống |
| `loai_phieu` | `loai` / `ly_do` | `string` | **BẮT BUỘC** | `"Hối giao"`, `"Hối lấy"`, `"Hối trả"` | Phân loại luồng xử lý và lọc khung giờ |
| `tien_phat` | `penalty` | `integer` | Tùy chọn | $\ge 0$ (mặc định `0`, kịch khung `200000`) | Tính tổng tiền phạt và mức độ ưu tiên |
| `han_dong` | `close_esc` | `string` | Tùy chọn | ISO DateTime string hoặc rỗng | Tính trạng thái trễ hạn cứu được |
| `trang_thai` | *(derived)* | `string` | **BẮT BUỘC** | `"Phạt kịch khung"`, `"Trễ hạn còn cứu được"`, `"Chưa trễ hạn"` | Xác định tính khẩn cấp trong tin GTalk |
| `url` | `url` | `string` | Tùy chọn | URL hợp lệ tới ticket eForm | Link xử lý phiếu trực tiếp |

---

## 3. CƠ CẤU & MAPPING NHÂN SỰ (CO_CAU DATA CONTRACT)

| Tên Cột | Cột Sheet Co_Cau | Kiểu Dữ Liệu | Bắt Buộc | Mô Tả |
| :--- | :--- | :--- | :--- | :--- |
| `warehouse_id` | `A` | `string` | **BẮT BUỘC** | Mã bưu cục (khớp với `ma_buu_cuc`) |
| `gdv_pgdv_id` | `F` | `string` | Tùy chọn | Mã Giám đốc vùng |
| `gdv_pgdv_name` | `G` | `string` | Tùy chọn | Tên Giám đốc vùng |
| `area_manager_id` | `I` | `string` | **BẮT BUỘC** | Mã Quản lý Khu vực (AM) nhận tin GTalk |
| `area_manager_name`| `J` | `string` | **BẮT BUỘC** | Tên Quản lý Khu vực (AM) |
| `region_shortname`| `D` | `string` | **BẮT BUỘC** | Mã Vùng (VD: `"HCM"`, `"HNO"`, `"XBG"`) |

---

## 4. SCHEMA CÁC TAB GOOGLE SHEETS

### 4.1 Tab `Ton_phieu` (8 Cột)
1. `ma_buu_cuc` (string)
2. `ten_buu_cuc` (string)
3. `Hối giao` (integer)
4. `Hối lấy` (integer)
5. `Hối trả` (integer)
6. `Tổng` (integer)
7. `Tiền phạt` (integer)
8. `cap_nhat_luc` (string datetime)

### 4.2 Tab `Chi_tiet` (14 Cột Chuẩn)
1. `ma_buu_cuc`
2. `ten_buu_cuc`
3. `ma_ticket`
4. `ma_don`
5. `loai_phieu`
6. `tien_phat`
7. `hạn_đóng`
8. `trạng_thái`
9. `url`
10. `gdv_pgdv_id`
11. `gdv_pgdv_name`
12. `area_manager_id`
13. `area_manager_name`
14. `region_shortname`

### 4.3 Tab `RP_theo_AM` (7 Cột)
1. `Mã NV AM`
2. `Tên AM`
3. `Tổng phiếu`
4. `Cần xử lý ngay`
5. `Đang phát sinh phạt`
6. `Nội dung RP (gửi GTalk)`
7. `Trạng thái`

### 4.4 Tab `RP_theo_TroLy` (7 Cột)
1. `Mã NV Trợ lý`
2. `Vùng`
3. `Tổng phiếu`
4. `Cần xử lý ngay`
5. `Đang phát sinh phạt`
6. `Nội dung RP (gửi GTalk)`
7. `Trạng thái`

---

## 5. NGUYÊN TẮC BẢO VỆ DỮ LIỆU (FAIL-CLOSED DATA INTEGRITY RULES)
1. **String Type Enforcement:** Mã bưu cục, mã ticket, mã nhân sự bắt buộc là kiểu string (loại bỏ lỗi mất số 0 đầu).
2. **Missing Field Halting:** Thiếu hoặc đổi tên bất kỳ trường bắt buộc nào (`number`, `value`, `loai`) sẽ kích hoạt Fail-Closed dừng toàn bộ downstream.
3. **Mismatched Count Halting:** Tổng số tickets API lấy được lệch so với `grand_total` web báo hoặc có bất kỳ bưu cục nào `failed_bc > 0` sẽ dừng pipeline ngay lập tức.
4. **Zero Guessing Policy:** Khi chưa chạy full ticket crawl, các chỉ số audit (`total_tickets_api`, `failed_bc`, `web_api_match`) bắt buộc trả `null`, không suy đoán hoặc trả `0` giả.
