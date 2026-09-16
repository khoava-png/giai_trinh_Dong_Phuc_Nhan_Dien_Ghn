# 📖 HƯỚNG DẪN GỬI TIN GTalk OA TỰ ĐỘNG THEO MÃ NV

Hệ thống đọc danh sách từ **Google Sheet**, tự gửi tin nhắn GTalk tới từng nhân viên theo **Mã NV**.
Chạy bằng **CMD/PowerShell** (ngoài Hermes) để đọc token chính xác.

---

## ✅ Đã xác minh hoạt động
- Gửi tin thật cho test **Mã NV 3049378 → thành công** (globalMsgId `2090292978373222400`)
- API prod `https://mbff.ghn.vn` ổn định
- OA token hợp lệ

---

## 📋 1. CẤU TRÚC GOOGLE SHEET (tab `Sheet1`)

| Cột A | Cột B | Cột C | Cột D | Cột E | F | G | H |
|---|---|---|---|---|---|---|---|
| **Mã NV** | Họ tên | **Nội dung** | Loại tin | Trạng thái | Chi tiết | Gửi lúc | Mã gửi |
| `3049378` | (tùy chọn) | Xin kiểm tra tồn phiếu... | TEXT | *(để trống)* | | | |

- **Chỉ cần điền cột A (Mã NV) + cột C (Nội dung).**
- Các cột còn lại hệ thống tự ghi sau khi gửi.
- **Cột E "Trạng thái"**: để TRỐNG để hệ thống gửi. Nếu đã có `ĐÃ GỬI`/`SENT` → bỏ qua (chống gửi trùng).

---

## 🚀 2. CÁCH CHẠY

> ⚠️ **Quan trọng:** phải chạy MỞ NGOÀI (bằng CMD/PowerShell), KHÔNG chạy trong Hermes —
> trong Hermes hệ thống tự che mật khẩu nên sẽ báo lỗi.

### Cách 1 — Bấm file (dễ nhất, không cần gõ lệnh)
Trong thư mục `E:\GHN\AntiGravity\Khua_Ho_Tro\03_GHN_Ops\GTalk\01_Module_GuTin`:
- **`Run_GTalk.bat`** → bấm đúp để **GỬI THẬT** tất cả dòng chưa gửi trong sheet
- **`Run_DryRun.bat`** → bấm đúp để **KIỂM TRA THỬ** (đọc sheet, không gửi)

### Cách 2 — Gõ lệnh (CMD / PowerShell)
Mở **Command Prompt (CMD)** rồi gõ:

```bat
cd /d E:\GHN\AntiGravity\Khua_Ho_Tro\03_GHN_Ops\GTalk\01_Module_GuTin
python gtalk_bulk_sender.py
```

**Các lệnh hữu ích:**

```bat
:: Chạy THỬ (đọc sheet, không gửi thật, không ghi gì)
python gtalk_bulk_sender.py --dry-run

:: Chỉ gửi 1 mã NV cụ thể (test 1 người)
python gtalk_bulk_sender.py --ma-nv 3049378

:: Muốn gửi dạng card có nút bấm (template) thay vì text
python gtalk_bulk_sender.py --template
```

---

## ⚙️ 3. NƠI LƯU OA TOKEN (quan trọng)

File chứa OA token: 
`E:\GHN\AntiGravity\Khua_Ho_Tro\03_GHN_Ops\GTalk\Automate_Sheets_Gtalk\.env`

```
GTALK_OA_TOKEN=2079459965803360256:<mật_khẩu>
```

- Định dạng: `username:password` (phần trước dấu `:` là oaId)
- ⚠️ **Không chia sẻ file `.env` này ra ngoài** (lộ token là mất quyền gửi)

---

## 🔧 4. CẤU HÌNH KHÁC (nếu cần sửa trong mã nguồn)

| Tham số | Vị trí | Giá trị mặc định |
|---|---|---|
| Spreadsheet ID | `SPREADSHEET_ID` | `15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg` |
| Tab sheet | `SHEET_TAB` | `Sheet1` |
| Key Service Account | `KEY_FILE` | `05_TaiLieu_Note\Keys\ghn-sheets-automation-90e4499c91ec.json` |
| Môi trường | biến `GTALK_ENV` | `prod` (hoặc `test`) |

> Sheet phải **chia sẻ quyền Editor** cho `ghn-sheet-bot@ghn-sheets-automation.iam.gserviceaccount.com` thì hệ thống mới đọc/ghi được.

---

## 🛡️ 5. CHỐNG GỬI TRÙNG (tự động có sẵn)
- Hệ thống **chỉ gửi dòng nào "Trạng thái" để TRỐNG**.
- Gửi xong → tự ghi `ĐÃ GỬI` + thời gian + mã gửi.
- Gửi lỗi → ghi `LỖI` + lý do, dòng đó giữ nguyên để xử lý lại.
- Chạy bao nhiêu lần cũng **không gửi đúp**.

---

## ❓ 6. LỖI THƯỜNG GẶP

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `Không tìm thấy GTALK_OA_TOKEN` | `.env` thiếu token | Kiểm tra mục 3 |
| `Tạo kênh thất bại: failed` | Token thiếu dấu `:`, hoặc SHEET chưa share bot | Kiểm tra token + chia sẻ sheet |
| Đọc sheet lỗi 403 | Chưa share quyền Editor | Share cho `ghn-sheet-bot@...` |
| Gửi được nhưng người không thấy | Sai Mã NV | Đối chiếu lại mã NV trong sheet |

---

📁 **Vị trí file:** `E:\GHN\AntiGravity\Khua_Ho_Tro\03_GHN_Ops\GTalk\01_Module_GuTin\`
- `Run_GTalk.bat` — bấm để **gửi thật**
- `Run_DryRun.bat` — bấm để **xem thử**
- `gtalk_bulk_sender.py` — chương trình gửi tin
- `HUONG_DAN_GUI_GTALK.md` — tài liệu này

> 📄 OA token nằm ở: `E:\GHN\AntiGravity\Khua_Ho_Tro\03_GHN_Ops\GTalk\Automate_Sheets_Gtalk\.env`