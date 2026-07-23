# 🚀 EForm Auto-Fill — Tự động điền phiếu đánh giá Camera

> **Dành cho đồng nghiệp GHN** — Chỉ cần 3 bước, không cần biết code.

---

## 📋 Mục lục

- [Yêu cầu hệ thống](#-yêu-cầu-hệ-thống)
- [Cài đặt (1 lần duy nhất)](#-cài-đặt-1-lần-duy-nhất)
- [Chạy script](#-chạy-script)
- [Luồng hoạt động](#-luồng-hoạt-động)
- [Các field được điền](#-các-field-được-điền)
- [Xử lý lỗi](#-xử-lý-lỗi)
- [FAQ](#-faq)

---

## 💻 Yêu cầu hệ thống

| Thành phần | Yêu cầu |
|---|---|
| **Hệ điều hành** | Windows 10/11 |
| **Python** | 3.10+ (script sẽ hướng dẫn cài nếu chưa có) |
| **Chrome** | Đã cài + đã đăng nhập `noibo.ghn.vn` |
| **Internet** | Kết nối mạng GHN nội bộ |

---

## 🔧 Cài đặt (1 lần duy nhất)

### Bước 1: Nhận file từ anh Khoa

Giải nén file `.zip` vào thư mục bất kỳ (VD: `D:\EForm_AutoFill\`)

### Bước 2: Chạy setup

Double-click vào file **`setup.bat`**

```
✅ Python OK
✅ Thu vien OK  
✅ Playwright Chromium OK
✅ CAI DAT HOAN TAT!
```

> [!TIP]
> Nếu chưa có Python, script sẽ báo và hướng dẫn cài từ python.org. Nhớ **tick "Add Python to PATH"** khi cài!

### Bước 3: Đăng nhập Chrome

Mở Chrome → vào `noibo.ghn.vn` → đăng nhập bằng tài khoản GHN của bạn.

> [!IMPORTANT]
> **Phải đăng nhập noibo.ghn.vn trước khi chạy script.** Script dùng chính Chrome + tài khoản của bạn để điền form.

---

## ▶️ Chạy script

### Hàng ngày, chỉ cần:

1. **Mở Chrome** (đã đăng nhập `noibo.ghn.vn`)
2. **Double-click `run.bat`**
3. **Đợi script chạy xong** (~6-7 giây/tab)
4. **Kiểm tra kết quả** → bấm **Submit** tay

```
═══ EFORM AUTO-FILL ═══
[Chrome] ✅ CDP đã sẵn sàng trên port 9222.
[Sheet] Đã kết nối: TM Camera - T07/2026 / Camera (qua GAS Web App)

🔍 Tìm thấy 3 dòng AD=ON:
  → Dòng 12: BC 3057 | Vùng ABC
  → Dòng 15: BC 3060 | Vùng XYZ
  → Dòng 18: BC 3080 | Vùng DEF

📝 Dòng 12: Đang điền 3 nhóm...
  ✅ Tab 3057-1: Đã điền (6.2s)
  ✅ Tab 3057-2: Đã điền (6.1s)
  ✅ Tab 3057-3: Đã điền (6.0s)
  [Sheet] Dòng 12: AD ← Done

══════════════════════════════
✅ HOAN TAT!
👉 Cac tab EForm dang mo san trong Chrome.
👉 KIEM TRA LAI ROI BAM SUBMIT TAY.
```

> [!WARNING]
> **Script KHÔNG tự submit!** Bạn phải tự kiểm tra nội dung từng tab rồi bấm Submit tay. Đây là cơ chế an toàn.

---

## 🔄 Luồng hoạt động

```
run.bat
  │
  ├─► Kiểm tra Chrome CDP → auto mở nếu cần
  │
  ├─► Đọc Google Sheet (dòng AD=ON)
  │     └─► Gọi qua GAS Web App (HTTP)
  │
  └─► Với mỗi dòng ON:
        │
        ├─► Mở tab EForm mới
        ├─► Đợi React render (~3s)
        ├─► Điền các field bằng DOM Injection (cực nhanh)
        │     ├─ VÙNG
        │     ├─ Mã Bưu Cục
        │     ├─ Tên Bưu Cục
        │     ├─ Mẫu chấm điểm
        │     ├─ Radio Tiêu chí
        │     ├─ TÊN NGƯỜI CHẤM *
        │     └─ Mô tả lỗi → để trống
        │
        ├─► Ghi AD=Done vào Sheet
        └─► Sang dòng tiếp theo
```

> \* TÊN NGƯỜI CHẤM dùng click UI vì field này gọi API server, không bypass được. Vẫn nhanh và ổn định.

---

## 📊 Các field được điền

| # | Field | Phương pháp | Nguồn dữ liệu |
|---|---|---|---|
| 1 | Nhóm quy trình | ⏭️ Skip (EForm tự fill từ URL) | URL flowId |
| 2 | Quy trình | ⏭️ Skip (EForm tự fill từ URL) | URL flowId |
| 3 | **TÊN NGƯỜI CHẤM** | 🖱️ Click UI | Cột ID + search API |
| 4 | **VÙNG** | ⚡ DOM Inject | Cột B (VUNG) |
| 5 | **Mã Bưu Cục** | ⚡ DOM Inject | Cột D (MA_BC) |
| 6 | **Tên Bưu Cục** | ⚡ DOM Inject | Cột C (BUU_CUC) |
| 7 | **Mẫu chấm điểm** | ⚡ DOM Inject | Cột N (BAI_CHAM) |
| 8 | **Radio Tiêu chí** | ⚡ DOM Inject | Cột O (TIEU_CHI) |
| 9 | Mô tả chi tiết lỗi | 📝 Để trống | — |

---

## 🐛 Xử lý lỗi

| Lỗi | Nguyên nhân | Cách fix |
|---|---|---|
| `Chrome CDP chưa chạy` | Chrome đang mở nhưng không có CDP | Script tự kill + mở lại. Nếu vẫn lỗi → **tắt hết Chrome → chạy run.bat** |
| `Không kết nối được GAS` | Mất mạng hoặc GAS Web App down | Kiểm tra mạng GHN. Báo anh Khoa. |
| `form_item_not_found` | Label field không khớp | Báo anh Khoa kèm screenshot |
| Tab trắng không render | React load chậm | Script tự retry 3 lần |
| `AD` không chuyển Done | GAS Web App lỗi | Kiểm tra Sheet thủ công |

---

## ❓ FAQ

**Q: Có cần tắt Chrome trước khi chạy không?**
A: Không cần. Script tự xử lý (kill + mở lại nếu thiếu CDP).

**Q: Mất bao lâu cho 1 dòng?**
A: ~6-7 giây/tab × số nhóm ảnh. VD: 3 nhóm → ~20 giây/dòng.

**Q: Có tự submit không?**
A: **KHÔNG.** Bạn phải tự kiểm tra + submit tay. Đây là cơ chế an toàn.

**Q: Máy không có Python thì sao?**
A: `setup.bat` sẽ hướng dẫn cài Python. Chỉ cần vào python.org → Download → Next → Next → Done.

**Q: Dùng được cho form khác không?**
A: Hiện tại chỉ hỗ trợ form `flowId=69d371b7af6a207f9ca7ce12` (Camera). Liên hệ anh Khoa nếu cần form khác.

**Q: Bị lỗi thì sao?**
A: Xem log trên màn hình console. Lỗi cũng được ghi vào cột AI trong Sheet. Chụp màn hình gửi anh Khoa.

---

## 📞 Hỗ trợ

- **Anh Khoa** — `khoava@ghn.vn`
- **File script**: `eform_auto/` (folder giải nén)
- **Sheet dữ liệu**: TM Camera - T07/2026 → tab `Camera`

---

> [!NOTE]
> **Version**: v2.0 — GAS Web App | **Ngày cập nhật**: 22/07/2026
