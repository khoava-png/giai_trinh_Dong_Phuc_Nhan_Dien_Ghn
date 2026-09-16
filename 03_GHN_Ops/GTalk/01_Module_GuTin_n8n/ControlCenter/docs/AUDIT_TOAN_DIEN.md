# 🔍 AUDIT TOÀN DIỆN — GHN Control Center
> Ngày: 09/09/2026 | Auditor: Hermes AI  
> Scope: Frontend ↔ Backend mapping, Log/Data, Dư thừa, Dashboard pipeline, Nghẽn/Trùng lặp

---

## 1. FRONTEND ↔ BACKEND MAPPING (Fallback → Fackend)

### 1.1 Bảng ánh xạ đầy đủ

| # | Frontend JS gọi | Backend route | Backend handler | ✅/❌ |
|---|-----------------|---------------|-----------------|:---:|
| 1 | `post('/api/scrape')` | `/api/scrape` | `action_scrape()` | ✅ |
| 2 | `post('/api/tpl/get')` | `/api/tpl/get` | `action_tpl_get()` | ✅ |
| 3 | `post('/api/tpl/save')` | `/api/tpl/save` | `action_tpl_save(body)` | ✅ |
| 4 | `post('/api/tpl/reset')` | `/api/tpl/reset` | `action_tpl_reset(body)` | ✅ |
| 5 | `post('/api/send_preview')` | `/api/send_preview` | `action_send_preview(body)` | ✅ |
| 6 | `post('/api/rp')` | `/api/rp` | `action_rp_preview(body)` | ✅ |
| 7 | `post('/api/send')` | `/api/send` | `action_send(body)` | ✅ |
| 8 | `post('/api/send/progress')` | `/api/send/progress` | `action_send_progress(body)` | ✅ |
| 9 | `post('/api/vung/list')` | `/api/vung/list` | `action_vung_list(body)` | ✅ |
| 10 | `post('/api/vung/save')` | `/api/vung/save` | `action_vung_save(body)` | ✅ |
| 11 | `post('/api/vung/preview')` | `/api/vung/preview` | `action_vung_preview(body)` | ✅ |
| 12 | `post('/api/vung/send')` | `/api/vung/send` | `action_vung_send(body)` | ✅ |
| 13 | `post('/api/sched/get')` | `/api/sched/get` | `action_sched_get()` | ✅ |
| 14 | `post('/api/sched/set')` | `/api/sched/set` | `action_sched_set(body)` | ✅ |
| 15 | `post('/api/sched/now')` | `/api/sched/now` | inline trong do_POST (L877-894) | ✅ |
| 16 | `post('/api/cycle/state')` | `/api/cycle/state` | `action_cycle_state(body)` | ✅ |
| 17 | `post('/api/activity')` | `/api/activity` | `action_activity(body)` | ✅ |
| 18 | `fetch('/api/health')` | GET `/api/health` | inline trong do_GET (L841) | ✅ |

**Kết luận: 18/18 — KHỚP HOÀN TOÀN.** Không có endpoint nào frontend gọi mà backend thiếu, và ngược lại.

### 1.2 Vấn đề Error Handling ⚠️

| Vấn đề | File | Mức độ |
|--------|------|--------|
| Hàm `post()` (L944) KHÔNG có `.catch()` — nếu server 500 hoặc network fail, JSON parse sẽ crash âm thầm | index.html | 🟡 Trung bình |
| `doScrape()` có xử lý `r.ok` nhưng không catch khi `post()` throw | index.html | 🟡 |
| `loadAM()`, `loadVung()`, `loadTpl()` — KHÔNG xử lý lỗi nào | index.html | 🔴 Cao |
| `pollSendProgress` — `catch(e){}` nuốt mọi lỗi (silent fail) | index.html L1110 | 🟡 |
| `pollCycle` — `catch(e){}` nuốt mọi lỗi | index.html L1336 | 🟡 |
| Backend có catch global `_scrape_error(str(e)[:300])` → OK | control_center.py L908 | ✅ |

---

## 2. LOG & DATA — ĐÃ GHI ĐỦ CHƯA?

### 2.1 Cơ chế log hiện tại

```
_log_sched(txt) → 3 nơi:
  1. print() → stdout (Docker/Render log — ephemeral)
  2. FILE: chay_lich.log → append, rotate 5MB/2000 dòng
  3. RAM: _activity[] → insert(0), max 100 entries
     Khởi động: _load_activity_from_log_file() đọc 100 dòng cuối từ file
```

### 2.2 Điểm ghi log

| Hoạt động | Có ghi log? | Chi tiết |
|-----------|:-----------:|---------|
| Cào dữ liệu thành công | ✅ | `_add_activity("Cào dữ liệu: X BC · Y phiếu · phạt Z")` |
| Cào dữ liệu LỖI | ✅ | `_add_activity("LỖI cào dữ liệu: ...")` |
| Gửi AM (thủ công) | ✅ | `_add_activity` trong `action_send()` |
| Gửi Vùng (thủ công) | ✅ | `_add_activity` trong `action_vung_send()` |
| Lịch tự động chạy | ✅ | `_log_sched("[sched] Chạy tự động: ...")` |
| Chu kỳ hoàn tất | ✅ | `_add_activity("Chu kỳ hoàn tất ...")` |
| Lịch ghi history | ✅ | `_record_history()` ghi vào sched.json, giữ 20 entries |
| Idempotency lock | ✅ | `_redis_set(control_center:idemp:...)` |
| Lưu template | ❌ | `action_tpl_save()` KHÔNG ghi log |
| Lưu cấu hình Vùng | ❌ | `action_vung_save()` KHÔNG ghi log |
| Thay đổi cài đặt lịch | ✅ | `_log_sched("Cập nhật cấu hình lịch: ...")` |

### 2.3 BUG LỚN: Log mất khi Render restart 🔴

```
Render Free = Ephemeral Disk
  → chay_lich.log bị XÓA khi redeploy/restart
  → _activity[] (RAM) cũng mất
  → _load_activity_from_log_file() khi khởi động lại = đọc file rỗng = activity trống
```

**FIX ĐÃ ĐỀ XUẤT:** Ghi log vào Upstash Redis (đã có kết nối sẵn). Ưu tiên 🔴.

---

## 3. TAB 1-5: CÓ GÌ DƯ / VÔ NGHĨA?

### TAB 1: Cào Dữ Liệu ✅ Tốt
- 4 KPI cards (kpi_bc, kpi_phieu, kpi_phat, kpi_lock) — hữu ích
- Nút "⟳ Cào + Ghi Sheet" — gọi doScrape() → action_scrape() → ghi Google Sheet
- Nút "⚡ Pipeline" — gọi runFullPipeline() → cào + gửi AM + gửi Vùng liên hoàn
- **KHÔNG DƯ**

### TAB 2: Mẫu Tin ✅ Tốt
- 2 textarea (AM + Trợ lý Vùng) + Lưu/Khôi phục + Preview
- **KHÔNG DƯ**

### TAB 3: Gửi 160 AM ⚠️ Có 1 điểm dư thừa nhỏ
- Dropdown phân luồng (ALL / HOI_GIAO / HOI_LAY / HOI_TRA) — hữu ích
- Bảng AM checkbox, tìm kiếm, xem trước, gửi thật, progress
- ⚠️ **"Xem tất cả" (showAllRP)** gọi `/api/send_preview` rồi render bảng, rồi user lại phải bấm "Xem trước" cho từng AM → **hơi dư, nhưng UX khác nhau nên chấp nhận được**

### TAB 4: Gửi 14 Trợ Lý Vùng ✅ Tốt
- Bảng 14 vùng, nhập ID nhanh, preview, gửi thật
- **KHÔNG DƯ**

### TAB 5: Lịch Tự Động & Log ⚠️ Có vấn đề
- Checkbox Bật/tắt, Giờ gửi, Delay, Dry Run, Chạy ngay, Theo dõi chu kỳ
- ⚠️ **"`sch_weekdays_hint` (DOM id)** — có DOM element nhưng frontend JS KHÔNG dùng nó — vô nghĩa"
- ⚠️ **Log div (`#log`)** — hiện ghi vào RAM → restart mất (đã ghi ở §2.3)
- ⚠️ **`cycleLive` section** — nếu không có chu kỳ đang chạy, hiện rỗng → OK nhưng UX có thể cải thiện (hiện trạng thái "Không có chu kỳ nào đang chạy")

---

## 4. DASHBOARD ghn-dashboard.pages.dev — AUTO PUSH DỮ LIỆU

### 4.1 Cơ chế hiện tại

```
┌─ Control Center (Render) ─┐     ┌─ Dashboard (Cloudflare Pages) ─┐
│                            │     │                                 │
│ action_scrape()            │     │ var RAW = {hardcoded JSON};      │
│   → ghi Google Sheets      │     │ (data snapshot tĩnh)            │
│   (Chi_tiet, Ton_phieu,   │     │                                 │
│    RP_theo_AM, RP_theo_TL) │     │ KHÔNG fetch realtime            │
│                            │     │ KHÔNG gọi API nào               │
└────────────────────────────┘     └─────────────────────────────────┘
            │                                      ▲
            │ ghi Sheet                            │ đọc Sheet
            ▼                                      │
    ┌─ Google Sheets ─┐                   ┌─ sync_and_deploy.py ─┐
    │ 15Ph9h9p...     │───────────────────│ (CHẠY THỦ CÔNG)      │
    │ Chi_tiet        │                   │ Đọc Sheet → inject    │
    │ Ton_phieu       │                   │ var RAW = {...}       │
    │ RP_theo_AM      │                   │ → wrangler deploy     │
    └─────────────────┘                   └──────────────────────┘
```

### 4.2 Phát hiện: ❌ CHƯA CÓ AUTO PUSH

**`sync_and_deploy.py` NẰM Ở `Dashboard_TonPhieu/` — KHÔNG được control_center.py gọi, KHÔNG có cron, KHÔNG có trigger tự động.**

Hiện tại:
- Control Center cào và ghi Google Sheets ✅
- `sync_and_deploy.py` đọc Google Sheets, inject data vào HTML, deploy Cloudflare Pages ✅
- **NHƯNG** `sync_and_deploy.py` phải chạy thủ công bằng tay trên laptop ❌
- Dashboard data hiện đang hiện: `"updated":"08/09/2026 18:10:54"` — tức là bản cuối cùng được deploy thủ công

### 4.3 Giải pháp đề xuất

| Phương án | Effort | Pros | Cons |
|-----------|--------|------|------|
| A. Control Center gọi `sync_and_deploy` sau mỗi `action_scrape()` | Thấp | Tự động hoàn toàn | Cần Cloudflare token trên Render + wrangler |
| B. Cloudflare Worker đọc Google Sheets trực tiếp (SSR) | Trung bình | Dashboard luôn realtime | Cần viết Worker mới |
| C. Cron trên Control Center mỗi giờ chạy sync | Thấp | Đơn giản | Vẫn cần wrangler trên Render |
| **D. Dashboard fetch Google Sheets API trực tiếp (client-side)** | **Thấp nhất** | **Không cần deploy lại** | Sheet phải public/API key |

---

## 5. NGHẼN / TRÙNG LẶP / VÔ NGHĨA

### 5.1 🔴 Việc làm 2 lần (Redundancy)

| # | Vấn đề | Chi tiết |
|---|--------|---------|
| R1 | **Pipeline = Cào + Gửi, nhưng Tab 5 "Chạy ngay" cũng = Cào + Gửi** | `runFullPipeline()` (Tab 1) và `/api/sched/now` (Tab 5) thực hiện CÙNG ĐÚNG quy trình: `action_scrape() → wait → send_preview → send`. User có 2 nút làm cùng 1 việc ở 2 tab khác nhau. |
| R2 | **"Xem trước" AM gọi `/api/send_preview` y hệt "Xem tất cả"** | `loadAM()` gọi `send_preview` để hiện bảng AM. `showAllRP()` cũng gọi `send_preview` lại lần nữa → gọi 2 lần cùng endpoint, cùng data. |
| R3 | **`_add_activity(text)` chỉ gọi `_log_sched(text)`** | Hàm wrapper vô nghĩa — 1 hàm gọi đúng 1 hàm khác, không thêm logic gì. |

### 5.2 🟡 Chỗ A có rồi nhưng phải qua B mới khởi động (Dư thừa quy trình)

| # | Vấn đề | Chi tiết |
|---|--------|---------|
| D1 | **Phải mở Tab 3 (AM) mới load danh sách AM** | `loadAM()` chỉ chạy khi `openTabPanel('panel-tab-am')` → nếu muốn xem preview ở Tab 1 Pipeline thì data AM chưa có |
| D2 | **Log (Tab 5) chỉ poll khi mở Tab 5** | `loadSched()` gọi `loadActivity()` → nếu đang chạy Pipeline ở Tab 1 mà không mở Tab 5 thì không thấy log |
| D3 | **Dashboard (pages.dev) phải deploy thủ công TRƯỚC mới có data mới** | Control Center cào xong → ghi Sheet → NHƯNG dashboard vẫn hiện data cũ cho tới khi chạy `sync_and_deploy.py` bằng tay |

### 5.3 🟢 Có nhưng vô nghĩa (Dead Code / Unused)

| # | Vấn đề | File | Dòng |
|---|--------|------|------|
| U1 | `sch_weekdays_hint` — DOM element có nhưng JS không dùng | index.html | — |
| U2 | `window.__am = []` khởi tạo rỗng, nhưng load lại toàn bộ mỗi lần mở tab | index.html | L940 |
| U3 | `const API=''` — biến không cần thiết vì chỉ dùng relative path | index.html | L939 |

### 5.4 ⚡ Đề xuất tinh gọn

| # | Hành động | Ưu tiên |
|---|----------|---------|
| F1 | **Gộp Pipeline (Tab 1) và "Chạy ngay" (Tab 5) thành 1** — giữ "Chạy ngay" ở Tab 5 (có cấu hình AM/Vùng chi tiết), Tab 1 chỉ giữ nút "⟳ Cào lẻ" | 🟡 |
| F2 | **Log ghi Upstash Redis** thay vì file+RAM → persist qua restart | 🔴 |
| F3 | **Dashboard auto-deploy** — thêm call sync_and_deploy vào cuối `_sched_cycle()` | 🔴 |
| F4 | **Frontend `post()` thêm `.catch()`** — hiện lỗi thay vì crash silent | 🟡 |
| F5 | **Load AM + Vùng ngay khi login** thay vì chờ mở tab | 🟢 |
| F6 | **Xóa `_add_activity()` wrapper** — dùng `_log_sched()` trực tiếp | 🟢 |
| F7 | **Thêm log cho `action_tpl_save` và `action_vung_save`** | 🟢 |

---

## 6. TÓM TẮT EXECUTIVE

| Hạng mục | Đánh giá |
|----------|---------|
| Frontend ↔ Backend mapping | ✅ **18/18 khớp hoàn toàn** |
| Error handling | ⚠️ **Frontend thiếu catch → silent crash** |
| Log persistence | 🔴 **Mất khi Render restart (file+RAM ephemeral)** |
| Tab dư thừa | 🟡 **Pipeline (Tab 1) ≡ Chạy ngay (Tab 5) — trùng logic** |
| Dashboard auto-push | 🔴 **CHƯA CÓ — phải chạy sync_and_deploy.py thủ công** |
| Dead code | 🟢 **3 item nhỏ, không ảnh hưởng vận hành** |
| Idempotency (chống trùng) | ✅ **Redis lock theo date+hour+flow — rất tốt** |
| Schedule worker | ✅ **30s poll, check weekday+hour, 2 luồng L1/L2 — tốt** |

### Top 3 việc cần làm ngay:

1. **🔴 Log → Upstash Redis** (mất data khi restart)
2. **🔴 Dashboard auto-deploy** (sync_and_deploy chưa tự động)  
3. **🟡 Frontend error handling** (post() thiếu catch)
