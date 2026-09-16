# GHN CONTROL CENTER — MASTER PLAN V2
# Tái cấu trúc: Giảm áp lực Python, phân vai 5 service

> **Mục tiêu:** Cắt monolith 1454 dòng thành 3 module nhẹ, mỗi đứa 1 việc.
> RAM Render giảm từ ~500MB xuống ~180MB. Chi phí = $0.

---

## 1. KIẾN TRÚC MỚI — 5 SERVICE

```
┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│   RENDER     │    │ APPS SCRIPT │    │ GITHUB       │
│              │    │             │    │ ACTIONS      │
│ • Serve UI   │    │ • Đọc cờ    │    │              │
│ • Cào web    │    │ • Gom phiếu │    │ • Gửi GTalk  │
│ • Ghi Sheet  │    │ • Sinh RP   │    │ • Deploy     │
│ • Ghi cờ     │    │ • Ghi queue │    │   Dashboard  │
│   RENDER_DONE│    │ • Ghi cờ    │    │ • Ghi cờ     │
│              │    │   GAS_DONE  │    │   GITHUB_DONE│
└──────┬───────┘    └──────┬──────┘    └──────┬───────┘
       │                   │                  │
       └───────────┬───────┘──────────────────┘
                   ▼
         ┌─────────────────┐
         │  GOOGLE SHEET   │
         │                 │
         │ • _Control_     │    ┌──────────────┐
         │   Center (cờ,   │    │ CLOUDFLARE   │
         │   lịch, mẫu,   │    │ PAGES        │
         │   log)          │    │              │
         │ • Chi_tiet      │    │ • Dashboard  │
         │ • Ton_phieu     │    │   tĩnh       │
         │ • Co_Cau        │    │ • Luôn live   │
         │ • RP_Queue      │    └──────────────┘
         └─────────────────┘

+  UPTIMEROBOT: Ping Render mỗi 5 phút (5h30–18h30) giữ thức
```

### Phân vai rõ ràng

| Service | Vai trò DUY NHẤT | Đọc gì | Ghi gì |
|---|---|---|---|
| **Render** | Cào web + serve UI | Web vận hành, Co_Cau | Chi_tiet, Ton_phieu, cờ B3 |
| **Apps Script** | Gom phiếu + sinh RP + chọn template | _Control_Center, Chi_tiet, Co_Cau | RP_Queue, RP_theo_AM, RP_theo_Vung, cờ B4 |
| **GitHub Actions** | Gửi GTalk + deploy Dashboard | RP_Queue, _Control_Center | RP_Queue status, Log, cờ B5 |
| **Google Sheet** | Kho data + công thức tự tính | — | Cột H "Chạy?" tự tính |
| **Cloudflare Pages** | Hiển thị Dashboard | — | — |
| **UptimeRobot** | Giữ Render thức | — | — |

---

## 2. LUỒNG CHẠY MỖI ĐỢT

```
[Giờ hành chính — mỗi giờ 1 lần]

  ① Render (có scheduler nội bộ):
     • Cào web vận hành → parse 2500 phiếu
     • Ghi Chi_tiet (14 cột) + Ton_phieu lên Sheet
     • Ghi _Control_Center!B3 = "DONE", C3 = timestamp
     • Ghi B4 = "IDLE", B5 = "IDLE" (reset bước sau)
     ✅ Xong — RAM ~180MB, không gom/gửi gì

  ② Apps Script (trigger mỗi 1 phút):
     • Check B3 — nếu ≠ "DONE" → bỏ qua (<1 giây)
     • B3 = "DONE" → bắt đầu xử lý:
       - Đọc _Control_Center lịch gửi → lọc cột H = TRUE
       - Với mỗi dòng TRUE:
         · Đọc loại phiếu (ALL/HOI_LAY/HOI_GIAO/HOI_TRA)
         · Lọc Chi_tiet theo loại
         · Gom theo BUU_CUC (cho AM) hoặc VUNG_AM (cho Trợ lý)
         · Đọc template → điền biến → ghi RP_Queue
       - Ghi RP_theo_AM, RP_theo_Vung (cho Dashboard)
     • Ghi B3 = "PROCESSED" (tránh chạy lại)
     • Ghi B4 = "DONE", C4 = timestamp
     ✅ Xong — Runtime ~30 giây

  ③ GitHub Actions (cron mỗi giờ, 6h-18h):
     • Đọc B4 — nếu ≠ "DONE" → exit ngay (tốn ~10 giây)
     • B4 = "DONE" → bắt đầu:
       a) Gửi GTalk:
          - Đọc RP_Queue → lọc status = "PENDING"
          - Gửi từng tin qua GTalk API (sleep 1.5s giữa tin)
          - Ghi status = "SENT" / "FAILED"
       b) Deploy Dashboard:
          - Đọc Chi_tiet + Ton_phieu từ Sheet
          - Build HTML → wrangler deploy CF Pages
     • Ghi Log vào _Control_Center
     • Ghi B5 = "DONE", C5 = timestamp
     ✅ Xong — Runtime ~3 phút
```

---

## 3. TAB `_CONTROL_CENTER` (ĐÃ TẠO)

Sheet ID: `15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg`
Tab: `_Control_Center` (đã tạo xong, đã có dropdown + công thức)

### Layout:

```
Dòng 1-5:     CỜ ĐIỀU PHỐI (dropdown: IDLE/RUNNING/DONE/FAILED)
Dòng 7-58:    LỊCH GỬI (50 dòng, 7 cột dropdown + 1 cột công thức)
Dòng 60-79:   TEMPLATE (8 mẫu có sẵn + 10 dòng trống)
Dòng 81-132:  LOG (50 dòng, 3 cột dropdown)
```

### Cờ điều phối (B3:B5):
- B3 = trạng thái Render (cào)
- B4 = trạng thái GAS (gom/sinh RP)
- B5 = trạng thái GitHub (gửi/deploy)

### Cột H "→ Chạy?" — Sheet tự tính:
```
=IF(A9=""; ""; AND(G9=TRUE; HOUR(NOW())=A9; REGEXMATCH(F9; CHOOSE(WEEKDAY(TODAY();2);"T2";"T3";"T4";"T5";"T6";"T7";"CN"))))
```
GAS chỉ cần: `lọc cột H = TRUE` → biết ngay đợt này gửi gì.

---

## 4. TAB `RP_QUEUE` (CẦN TẠO)

Tab mới, là hàng chờ gửi tin. GAS ghi vào, GitHub đọc ra.

| Cột | Tên | Ghi chú |
|---|---|---|
| A | dot_id | VD: `2026-09-16_14` (ngày_giờ) |
| B | loai_phieu | ALL / HOI_LAY / HOI_GIAO / HOI_TRA |
| C | nguoi_nhan | AM / TRO_LY |
| D | ma_nv | Mã nhân viên GTalk |
| E | ten | Tên AM hoặc Trợ lý |
| F | noi_dung | Nội dung tin đã điền biến |
| G | status | PENDING / SENT / FAILED / SKIPPED (dropdown) |
| H | timestamp_tao | GAS ghi lúc tạo |
| I | timestamp_gui | GitHub ghi lúc gửi |
| J | loi | Chi tiết lỗi nếu FAILED |

**Quy tắc:**
- GAS ghi dòng mới → status = PENDING
- GitHub đọc PENDING → gửi → ghi SENT/FAILED + timestamp
- Mỗi đợt mới GAS xóa/ghi đè (không tích lũy vô hạn)

---

## 5. QUOTA & TÀI NGUYÊN — BẰNG CHỨNG SỐ

| Tài nguyên | Giới hạn Free | Dùng thực tế | Còn dư | An toàn? |
|---|---|---|---|---|
| **Render RAM** | 512 MB | ~180 MB peak | 332 MB (65%) | ✅ Rất thoải mái |
| **GitHub Actions** | 2,000 phút/tháng | ~1,078 phút | 922 phút (46%) | ✅ OK |
| **Apps Script runtime** | 90 phút/ngày | ~2.5 phút/ngày | 87.5 phút (97%) | ✅ Thừa |
| **Apps Script trigger** | 20 runs/phút | 1 run/phút | 19 (95%) | ✅ Thừa |
| **Google Sheets API** | 300 req/phút | ~155 req/ngày | Rất xa giới hạn | ✅ OK |
| **Cloudflare Pages** | 500 deploy/tháng | ~110 deploy | 390 (78%) | ✅ OK |
| **UptimeRobot** | 50 monitors | 1 monitor | 49 | ✅ OK |

### Tính chi tiết GitHub Actions:
- Gửi GTalk: 13 lần/ngày × 3 phút = 39 phút/ngày
- Deploy Dashboard: 5 lần/ngày × 2 phút = 10 phút/ngày
- Tổng: 49 phút/ngày × 22 ngày = 1,078 phút/tháng

---

## 6. CREDENTIAL & SECRETS

### Render env vars (giữ nguyên hiện tại):
| Biến | Mục đích |
|---|---|
| `OP_WEB_USER` / `OP_WEB_PASS` | Login web vận hành để cào |
| `GOOGLE_KEY_FILE` | Service account JSON (ghi Sheet) |
| `AUTH_USER` / `AUTH_PASS` | Login Control Center UI |

### GitHub Secrets (CẦN THÊM):
| Secret | Mục đích | Lấy từ đâu |
|---|---|---|
| `GTALK_OA_TOKEN` | Gửi tin GTalk | Env var `GTALK_OA_TOKEN` trên Render |
| `GOOGLE_KEY_JSON` | Đọc/ghi Sheet | Nội dung file `ghn-sheets-key.json` |
| `CF_API_TOKEN` | Deploy Dashboard lên CF Pages | Cloudflare dashboard → API Tokens |
| `CF_ACCOUNT_ID` | Account Cloudflare | Cloudflare dashboard → Overview |

### Apps Script:
- KHÔNG cần credential riêng — chạy dưới quyền owner của Sheet
- Sheet đã share Editor cho service account

### GTalk OA Token:
- Hiện lưu qua env var `GTALK_OA_TOKEN` trên Render
- Format: `oa_id:oa_secret` (dạng username:password)
- File `gtalk_bulk_sender.py` đọc từ env hoặc `.env`
- Cần copy giá trị này vào GitHub Secrets

---

## 7. CẤU TRÚC REPO (1 repo duy nhất)

```
ghn-control-center/          ← Repo GitHub (private)
│
├── control_center.py         ← Render: cào + UI (CẮT GỌN, ~350 dòng)
├── index.html                ← UI Control Center
├── Cao_Ton_Phieu/            ← Module cào (giữ nguyên)
│   └── cao_ton_phieu.py
├── GuTin_Theo_MaNV/          ← Module gửi GTalk (giữ nguyên)
│   └── gtalk_bulk_sender.py
│
├── scripts/                  ← MỚI: scripts cho GitHub Actions
│   ├── send_from_queue.py    ← Đọc RP_Queue → gửi GTalk
│   └── deploy_dashboard.py   ← Đọc Sheet → build HTML → wrangler deploy
│
├── .github/workflows/        ← MỚI: GitHub Actions
│   ├── send_gtalk.yml        ← Cron mỗi giờ 6h-18h: gửi tin
│   └── deploy_dashboard.yml  ← Cron 5 lần/ngày: deploy CF Pages
│
├── dashboard/                ← Template HTML Dashboard
│   └── index.html
│
├── Code.gs                   ← MỚI: Apps Script (copy vào Script Editor)
├── requirements.txt          ← Giữ nguyên
├── Procfile                  ← Giữ nguyên
└── sched.json                ← Giữ nguyên (lịch cào)
```

---

## 8. PHÂN ĐOẠN TRIỂN KHAI

### Phase 1: Chuẩn bị hạ tầng (không đụng code cũ)
- [ ] Tạo tab `RP_Queue` trên Sheet (schema 10 cột + dropdown)
- [ ] Copy `GTALK_OA_TOKEN` từ Render env → GitHub Secrets
- [ ] Tạo CF API Token → GitHub Secrets
- [ ] Tạo `GOOGLE_KEY_JSON` secret trên GitHub

### Phase 2: Viết script mới (chạy song song, không phá cũ)
- [ ] Viết `Code.gs` — đọc cờ, gom, sinh RP, ghi queue
- [ ] Deploy GAS trigger 1 phút
- [ ] Viết `scripts/send_from_queue.py` — đọc queue, gửi GTalk
- [ ] Viết `.github/workflows/send_gtalk.yml`
- [ ] Viết `scripts/deploy_dashboard.py`
- [ ] Viết `.github/workflows/deploy_dashboard.yml`

### Phase 3: Test song song (hệ cũ vẫn chạy)
- [ ] Render cào → kiểm tra cờ B3 = DONE
- [ ] GAS nhận cờ → kiểm tra RP_Queue có data
- [ ] GitHub Actions → gửi thử 1 tin cho Admin (3049378)
- [ ] Dashboard auto-deploy → kiểm tra CF Pages

### Phase 4: Cắt chuyển (bỏ code cũ trong control_center.py)
- [ ] Xóa: _am_summary, _vung_summary, build_rp, replace_vars
- [ ] Xóa: action_send, action_vung_send, _send_via_gtalk
- [ ] Xóa: _sched_cycle (giữ scheduler đơn giản chỉ cào + ghi cờ)
- [ ] Xóa: Toàn bộ Upstash Redis helpers
- [ ] Xóa: _load_tpl, _save_tpl, template.json
- [ ] Redeploy Render → verify RAM ≤ 200MB
- [ ] Tắt Upstash Redis

---

## 9. CÁC RỦI RO & CÁCH XỬ LÝ

| Rủi ro | Xác suất | Xử lý |
|---|---|---|
| GAS trigger 1 phút bị Google throttle | Thấp | Check cờ < 1 giây, chạy thực 30 giây — xa giới hạn 90 phút/ngày |
| GitHub Actions cron trễ (delay 5-15 phút) | Trung bình | Chấp nhận — tin gửi chậm nhất 15 phút không ảnh hưởng nghiệp vụ |
| Web vận hành đổi password | Trung bình | Render cào lỗi → ghi B3 = FAILED → GAS không chạy → không gửi tin lỗi |
| Sheet API rate limit | Rất thấp | 155 req/ngày vs 300/phút giới hạn |
| CF Pages deploy lỗi | Thấp | Dashboard hiện data cũ, đợt sau deploy lại |
| GTalk token hết hạn | Trung bình | GitHub Actions gửi FAILED → ghi RP_Queue → anh thấy trong Log |

---

## 10. SO SÁNH TRƯỚC/SAU

| Tiêu chí | Trước (monolith) | Sau (phân vai) |
|---|---|---|
| File Python | 1454 dòng, 1 file | ~350 dòng Render + ~120 dòng GH |
| RAM peak | ~500MB (OOM) | ~180MB (dư 332MB) |
| Service phụ thuộc | Upstash Redis + UptimeRobot | Bỏ Redis, giữ UptimeRobot |
| Lịch gửi/template | Hardcode JSON | Sheet dropdown, sửa tay không deploy |
| Gửi tin | Render ôm hết | GitHub Actions (tách riêng) |
| Dashboard | Deploy thủ công | Tự động 5 lần/ngày |
| Debug | Đọc log Render | Mở Sheet → xem cờ + Log + RP_Queue |
| Chi phí | $0 | $0 |

---

## 11. QUYẾT ĐỊNH ĐÃ CHỐT

| Câu hỏi | Quyết định |
|---|---|
| Render Free hay Paid? | **Free** — UptimeRobot ping 5h30-18h30 |
| Cào ai trigger? | **Render tự cào** (giữ scheduler Python) |
| Gửi tin ai làm? | **GitHub Actions** |
| Dashboard auto hay manual? | **Auto** — GH Actions deploy 5 lần/ngày |
| Repo 1 hay nhiều? | **1 repo duy nhất** |
| Redis giữ hay bỏ? | **Bỏ** — Sheet cờ thay |
| Template ở đâu? | **Sheet** _Control_Center (dropdown) |
| Lịch gửi ở đâu? | **Sheet** _Control_Center (công thức tự tính) |
| GTalk token ở đâu? | **GitHub Secrets** (copy từ Render env) |
