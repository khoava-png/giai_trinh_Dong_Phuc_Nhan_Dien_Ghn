# 🧠 ĐÁNH GIÁ HỆ THỐNG — GHN Control Center
> Ngày: 15/09/2026 | Góc nhìn: Tư duy hệ thống, không thuật ngữ kỹ thuật

---

## 1. HỆ THỐNG ĐANG LÀM GÌ?

Mỗi giờ, server tự động thực hiện 4 bước theo thứ tự:

```
Bước 1: Đăng nhập web vận hành → Lấy danh sách phiếu tồn
   ↓
Bước 2: Ghi dữ liệu vào Google Sheet (lưu trữ)
   ↓
Bước 3: Soạn tin nhắn cho từng AM / Trợ lý Vùng
   ↓
Bước 4: Gửi tin GTalk hàng loạt (delay 1.5s/tin)
```

---

## 2. ĐÁNH GIÁ QUY TRÌNH THÔNG BÁO

### 2.1 Quy trình gửi tin AM (Tab 3)

**Luồng đang chạy:**
```
Scheduler tick (mỗi 30s) → đúng giờ → cào web → soạn tin → gửi
                                                              ↓
                                            Gửi 1 tin mẫu về Admin (3049378) TRƯỚC
                                                              ↓
                                            Gửi hết ~150 AM (delay 1.5s/tin ≈ 4 phút)
                                                              ↓
                                            Gửi báo cáo tổng hợp về Admin SAU
```

**Vấn đề phát hiện:**

| # | Vấn đề | Mức độ |
|---|--------|--------|
| A | Sau khi cào xong, hệ thống soạn tin và gửi **trong cùng 1 luồng duy nhất** (không tách riêng). Nếu gửi 1 AM bị lỗi → toàn bộ đợt đó vẫn tiếp tục nhưng không có cơ chế retry. AM bị lỗi đó sẽ **mất tin hẳn** đến giờ sau | 🟡 Trung bình |
| B | Nếu đang gửi giữa chừng (~150 AM × 1.5s = ~4 phút) mà Render restart (OOM hoặc deploy mới) → **hàng chục AM không nhận được tin**, không có log nào báo cụ thể ai bị mất | 🔴 Cao |
| C | Scheduler tick mỗi **30 giây**: nếu cào web thất bại, sau 30s nó thử lại ngay → nếu lỗi kéo dài sẽ tốn tài nguyên liên tục (đây là nguyên nhân sự cố 14/09) | 🔴 Cao |
| D | Hiện **không có cơ chế báo lỗi chủ động**: nếu cào thất bại nhiều giờ liên tiếp, bạn chỉ biết khi vào xem log thủ công, không có tin nhắn tự động cảnh báo | 🟡 Trung bình |

### 2.2 Quy trình gửi tin Vùng (Tab 4)

Tương tự AM, không có vấn đề gì thêm ngoài điểm B và C ở trên.

### 2.3 Luồng 2 (Ưu tiên L2) — Giờ chiều

Hệ thống **không phân biệt được** nếu L1 (sáng) đã gửi xong nhưng L2 (chiều) lại cào về dữ liệu giống hệt → vẫn gửi lại. Không phải bug, nhưng AM có thể nhận 2 tin/ngày với nội dung gần giống nhau nếu số phiếu không đổi.

---

## 3. ĐÁNH GIÁ TÀI NGUYÊN

### Tài nguyên bạn đang có:
| Thứ | Giới hạn | Đang dùng | Nhận xét |
|-----|---------|-----------|---------|
| RAM server (Render Free) | 512MB | ~200-300MB lúc cào | Còn biên độ nhưng **không nhiều** |
| Thời gian gửi 1 đợt AM | ~4 phút | 150 AM × 1.5s | Bình thường |
| Google Sheets API | 100 req/100s | ~10-20 req/lần cào | **An toàn** |
| Upstash Redis (Free) | 10,000 req/ngày | ~50-100 req/ngày | **An toàn** |
| UptimeRobot ping | mỗi 5 phút | — | Giữ server không ngủ ✅ |

### Vấn đề tài nguyên thật sự:

**Mỗi lần cào**, server cần làm nhiều việc cùng lúc trong bộ nhớ:
```
Dữ liệu 2694 phiếu × 14 cột      → ~25MB RAM
Kết nối Google Sheets (nặng)      → ~40MB RAM
Dữ liệu giữ lại trong RAM cache  → ~20MB RAM
Process Python thường trực        → ~60MB RAM
─────────────────────────────────────────────
Tổng ổn định                      → ~145MB
Tổng lúc đỉnh (đang cào)          → ~250-300MB ← còn cách giới hạn 512MB
```

Hiện **đủ dùng**, nhưng nếu dữ liệu tăng lên (nhiều phiếu hơn) hoặc nhiều người truy cập UI cùng lúc với cào → có thể chạm giới hạn lại.

---

## 4. NGHẼN & DƯ THỪA

### Chỗ nghẽn tiềm ẩn:

**Nghẽn 1 — Cào web và gửi tin chạy tuần tự:**
```
Cào xong (2-3 phút) → mới bắt đầu gửi (4 phút) = tổng ~7 phút/đợt
```
Không phải vấn đề lớn với lịch hiện tại (1 đợt/giờ), nhưng nếu tăng tần suất sẽ có thể chồng đợt.

**Nghẽn 2 — Ghi Google Sheets 3 tab liên tiếp:**
Mỗi lần cào ghi: `Ton_phieu` → `Chi_tiet` → `RP_theo_AM` → `RP_theo_TroLy` = 4 lần ghi lớn. Hiện ổn nhưng là điểm chậm nhất trong quy trình.

### Dư thừa:

| # | Dư thừa | Ảnh hưởng |
|---|---------|-----------|
| D1 | Nút **Pipeline (Tab 1)** và nút **Chạy ngay (Tab 5)** làm y hệt nhau | Người dùng bối rối, không ảnh hưởng vận hành |
| D2 | Dashboard `ghn-dashboard.pages.dev` vẫn **hiện data cũ từ 08/09** vì phải deploy thủ công | Mất ý nghĩa realtime hoàn toàn |
| D3 | Google Sheets có đủ dữ liệu nhưng Dashboard không đọc tự động | Công cào web bị lãng phí một nửa |

---

## 5. VẤN ĐỀ LOOP LIÊN TỤC (nguyên nhân sự cố 14/09)

**Sơ đồ vòng lặp chết:**
```
Server khởi động
      ↓
Scheduler tick (30s) → thử cào → THẤT BẠI
      ↓ (sau 30s)
Scheduler tick → thử cào → THẤT BẠI
      ↓ (lặp liên tục)
RAM tích lũy do kết nối hỏng không giải phóng
      ↓
RAM đầy → Server bị kill (OOM)
      ↓
Render khởi động lại server
      ↓
Quay về đầu → Lặp lại vô tận
```

**Hiện tại đã hết vì cào thành công.** Nhưng vòng lặp này sẽ xảy ra lại bất cứ khi nào web vận hành không đăng nhập được (đổi pass, bảo trì, hết hạn...).

**Chốt lại: Hệ thống thiếu 1 cái van an toàn** — "nếu thất bại 3 lần liên tiếp thì nghỉ 1 tiếng rồi thử lại" thay vì cứ thử mãi mỗi 30 giây.

---

## 6. KHUYẾN NGHỊ — THEO THỨ TỰ ƯU TIÊN

### 🔴 Làm ngay (bảo vệ hệ thống đang chạy)

**KN1 — Thêm "van an toàn" cho scheduler**
> Ý nghĩa: Nếu cào thất bại 3 lần liên tiếp → tự nghỉ 60 phút rồi thử lại. Tránh vòng lặp chết ngốn RAM.
> Effort: 15 phút code.

**KN2 — Tự gửi tin cảnh báo về Admin khi lỗi kéo dài**
> Ý nghĩa: Nếu cào thất bại liên tục 2 giờ → tự gửi tin GTalk về `3049378` báo "Hệ thống đang lỗi". Bạn biết sớm thay vì phát hiện muộn.
> Effort: 20 phút code.

### 🟡 Làm trong tuần (cải thiện độ tin cậy)

**KN3 — Dashboard tự cập nhật sau mỗi lần cào**
> Ý nghĩa: Sau khi cào xong, dashboard `ghn-dashboard.pages.dev` hiện data mới luôn, không cần chạy tay.
> Effort: 30 phút.

**KN4 — Log ghi rõ AI nào không nhận được tin**
> Ý nghĩa: Khi gửi xong, hệ thống liệt kê cụ thể AM nào gửi thất bại để bạn biết cần xử lý thủ công.
> Hiện tại đã có nhưng chỉ thấy trong log, không nổi bật.

### 🟢 Làm khi rảnh (hoàn thiện)

**KN5 — Gộp 2 nút Pipeline thành 1**
> Tab 1 và Tab 5 hiện có 2 nút làm y hệt nhau → gây bối rối.

**KN6 — Thêm trang "Tình trạng hệ thống" đơn giản**
> 1 trang hiện: server đang sống/chết, lần cào gần nhất, lần gửi gần nhất, số AM nhận tin hôm nay.
> Để bạn kiểm tra nhanh không cần vào log.

---

## 7. TÓM TẮT 1 TRANG

```
HỆ THỐNG ĐANG TỐT:
✅ Cào web → ghi Sheet → gửi tin: hoạt động đúng
✅ Lịch tự động: lưu bền vững, không mất khi restart
✅ Chống gửi trùng: đã có khóa Redis
✅ Log: lưu bền vững qua Redis + Sheet

CẦN XỬ LÝ:
🔴 Thiếu van an toàn: cào lỗi → retry mãi → crash (đã xảy ra 14/09)
🔴 Dashboard vẫn data cũ từ 08/09 (không tự cập nhật)
🟡 Không có cảnh báo tự động khi hệ thống lỗi
🟡 AM bị lỗi gửi không được retry tự động

KHÔNG CÓ VẤN ĐỀ:
✅ Tài nguyên RAM, API còn dư an toàn
✅ Dữ liệu không mất khi server restart
✅ Quy trình gửi tin đúng nghiệp vụ
```

---

*Cập nhật: 15/09/2026 — Hermes Agent*
