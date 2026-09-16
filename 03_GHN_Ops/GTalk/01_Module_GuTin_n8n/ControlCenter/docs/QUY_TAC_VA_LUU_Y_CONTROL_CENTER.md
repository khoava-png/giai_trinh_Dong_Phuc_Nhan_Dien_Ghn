# 📌 QUY TẮC VÀ LƯU Ý VẬN HÀNH CONTROL CENTER (GTALK)

> **Dự án:** Control Center - GTalk Báo cáo Tồn phiếu Vận hành GHN  
> **Thư mục:** `01_Module_GuTin_n8n/ControlCenter`  
> **Cập nhật:** Tháng 09/2026 (Phiên bản 2 Luồng chuẩn hóa)

---

## 1. 🚨 QUY TẮC BẮT BUỘC: Gửi bản sao & Kiểm duyệt về Admin (Khoa - `3049378`)

**Bất kỳ khi nào có đợt gửi tin** (dù chạy tự động theo lịch ngầm hay bấm nút gửi thủ công), hệ thống **BẮT BUỘC** phải gửi 2 loại tin về GTalk của anh Khoa (`ADMIN_ID = 3049378`):

1. **Gửi Mẫu Tin Thực Tế (Trước khi gửi hàng loạt):**
   * **Đợt gửi AM:** Lấy 1 tin thực tế đầu tiên (AM có phiếu) gửi thẳng tới `3049378` để kiểm duyệt format/biến/nội dung.
   * **Đợt gửi Trợ lý Vùng:** Lấy 1 tin thực tế đầu tiên của Vùng gửi thẳng tới `3049378` để kiểm duyệt.
   * *Log hệ thống:* `✓ Đã gửi mẫu tin AM/Trợ lý Vùng thực tế tới 3049378 để kiểm duyệt.`

2. **Gửi Báo Cáo Tổng Hợp (Sau khi gửi xong):**
   * Sau khi hoàn tất toàn bộ tiến trình, gửi tin tóm tắt kết quả (số lượng thành công, thất bại, luồng phiếu).
   * *Log hệ thống:* `[admin] Đã gửi thông báo tổng hợp cho admin (flow=...)`

---

## 2. ⚡ CẤU TRÚC 2 LUỒNG GỬI TIN

Hệ thống vận hành song song 2 luồng độc lập với khung giờ và cấu hình riêng:

| Thuộc tính | Luồng 1 (Toàn bộ phiếu) | Luồng 2 (Ưu tiên theo nhu cầu) |
|---|---|---|
| **Mục đích** | Báo cáo tổng thể toàn bộ tồn phiếu Giao + Lấy + Trả | Đôn đốc chuyên sâu 1 loại phiếu cần xử lý gấp |
| **Khung giờ AM** | `hours_am_all` (VD: 9, 10, 11, 12, 13) | `hours_am_cd` (VD: 14, 15, 16) |
| **Khung giờ Vùng**| `hours_vung_all` (VD: 9, 10, 11, 12, 13) | `hours_vung_cd` (VD: 14, 15, 16) |
| **Loại phiếu** | Cố định `ALL` (Tổng hợp) | Tự chọn qua Radio (`HOI_LAY`, `HOI_GIAO`, `HOI_TRA`) |
| **Format dòng AM** | `📦 Bưu cục X: N phiếu — A cần ngay, B phạt` *(gọn, không chia lẻ)* | `📥 Bưu cục X: N phiếu Hối Lấy (A cần ngay, B phạt)` |
| **Format dòng Vùng**| `👤 Tên AM (AM): N phiếu — A cần ngay, B phạt` | `📥 Tên AM (AM): N phiếu Hối Lấy (A cần ngay, B phạt)` |

---

## 3. 📝 CHUẨN HÓA MẪU TIN & VĂN PHONG (TEMPLATE)

* **Thông báo popup (`shortMessage`):**
  * AM: `🚨 [{loai_luong}] Cần xử lý gấp — Anh/ Chị {ten_am}` *(Hiển thị đích danh người nhận)*.
  * Vùng: `🚨 [{loai_luong}] Báo cáo Vùng {vung}`.
* **Tiêu đề Card (`{loai_tieude}`):**
  * Hối Lấy: `ƯU TIÊN XỬ LÝ HỐI LẤY` *(hoặc `... — VÙNG {vung}`)*.
  * Hối Giao: `ƯU TIÊN XỬ LÝ HỐI GIAO`.
  * Hối Trả: `ƯU TIÊN XỬ LÝ HỐI TRẢ`.
  * Tất cả (ALL): `CẢNH BÁO TỔNG HỢP HỐI G/L/T`.
* **Hành động (`{hanh_dong_nhac_nho}`):**
  * Hối Lấy AM: `đôn đốc shipper đi lấy hàng trước khi đóng ca`.
  * Hối Lấy Vùng: `nhắc nhở các AM đôn đốc lấy hàng dứt điểm ca chiều`.
  * ALL AM: `xử lý dứt điểm các phiếu tồn ngay`.
  * ALL Vùng: `nhắc nhở AM đôn đốc xử lý ngay`.

---

## 4. ⚙️ QUY TẮC KỸ THUẬT & TRÁNH XUNG ĐỘT (BACKEND/FRONTEND)

1. **Lưu cấu hình Atomic (`sched.json`):**
   * Mọi thao tác ghi `sched.json` **bắt buộc** đi qua `_update_sched(mutator)` với khóa `_sched_lock` (`threading.RLock`) để chống race condition và lost-update khi có nhiều request đồng thời.
2. **Frontend Debounce & Focus Guard:**
   * Auto-save trên giao diện có debounce `400ms`.
   * Vòng lặp poll 15s (`loadSched`) phải kiểm tra `document.activeElement` để không ghi đè giá trị ô mà người dùng đang gõ/chỉnh sửa.
3. **Quy trình Restart Server sạch:**
   * (1) Tìm và kill PID chiếm port 8090: `netstat -ano | grep :8090` -> `taskkill /F /PID <pid>`
   * (2) Xóa cache: `rm -rf __pycache__`
   * (3) Chạy lại server: `python control_center.py`
