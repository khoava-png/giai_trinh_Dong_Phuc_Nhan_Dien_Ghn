# PROMPT CHO AI CODE — DỰ ÁN GHN CONTROL CENTER V2

> **Ngữ cảnh:** Anh đưa file `MASTER_PLAN_V2.md` kèm prompt tương ứng cho AI khác code.
> Mỗi prompt là 1 nhiệm vụ độc lập, AI nhận prompt + file tham khảo là đủ.

---

## PROMPT 1: CẮT GỌN `control_center.py` (Render)

### Giao cho AI:

```
Tôi cần bạn cắt gọn file control_center.py (1454 dòng) theo kế hoạch trong MASTER_PLAN_V2.md.

YÊU CẦU:
1. GIỮ LẠI:
   - Web server (HTTP handler class H, do_GET, do_POST)
   - action_scrape() — cào web + ghi Chi_tiet + Ton_phieu
   - Serve index.html + assets
   - /api/health, /api/scrape, /api/cycle/state, /api/activity
   - Auth (Basic Auth)
   - Scheduler đơn giản: chỉ tick → cào → ghi cờ RENDER_DONE

2. THÊM MỚI:
   - Sau khi cào xong, ghi '_Control_Center'!B3 = "DONE", C3 = timestamp
   - Trước khi cào, ghi B3 = "RUNNING", B4 = "IDLE", B5 = "IDLE"
   - Nếu cào lỗi, ghi B3 = "FAILED", D3 = mô tả lỗi

3. XÓA TOÀN BỘ:
   - _am_summary(), _vung_summary(), build_rp(), replace_vars()
   - action_send(), action_send_preview(), action_vung_send(), action_vung_preview()
   - action_vung_list(), action_vung_save()
   - _send_via_gtalk(), _notify_admin()
   - _sched_cycle() (thay bằng scheduler đơn giản)
   - Upstash Redis: _redis_get, _redis_set, _redis_log_append, _redis_log_load
   - Template: _load_tpl, _save_tpl, _default_tpl, action_tpl_get/save/reset
   - sync_vung_ids_from_google_sheet(), _load_vung_ids(), _save_vung_ids()

FILE THAM KHẢO:
- control_center.py (file gốc 1454 dòng)
- MASTER_PLAN_V2.md (kế hoạch chung)

OUTPUT: File control_center.py mới, ~350 dòng. Giữ nguyên style UTF-8, zoneinfo, BaseHTTPRequestHandler.
Sheet ID: 15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg
Tab cờ: _Control_Center (B3 = bước 1, B4 = bước 2, B5 = bước 3)
```

---

## PROMPT 2: VIẾT `Code.gs` (Apps Script)

### Giao cho AI:

```
Tôi cần bạn viết Code.gs (Google Apps Script) cho dự án GHN Control Center.

NHIỆM VỤ:
Script này chạy dưới trigger Time-driven (mỗi 1 phút) trong Google Sheet.

LUỒNG XỬ LÝ:
1. Đọc ô _Control_Center!B3
   - Nếu B3 ≠ "DONE" → return ngay (< 1 giây)
   - Nếu B3 = "DONE" → tiếp tục

2. Ghi B4 = "RUNNING"

3. Đọc vùng LỊCH GỬI (_Control_Center!A9:H58)
   - Lọc các dòng có cột H = TRUE (Sheet đã tính sẵn bằng công thức)
   - Mỗi dòng TRUE có: giờ, loại_phiếu, gửi_cho, gom_theo, tên_mẫu

4. Với mỗi dòng lịch gửi đang TRUE:
   a) Đọc tab Chi_tiet (A:N, ~2500 dòng)
      - Header: ma_buu_cuc, ten_buu_cuc, ma_ticket, ma_don, loai_phieu, tien_phat,
                han_dong, trang_thai, url, gdv_pgdv_id, gdv_pgdv_name,
                area_manager_id, area_manager_name, region_shortname
   b) Lọc theo loại phiếu:
      - ALL → lấy tất cả
      - HOI_LAY → chỉ loai_phieu = "Hối lấy"
      - HOI_GIAO → chỉ loai_phieu = "Hối giao"
      - HOI_TRA → chỉ loai_phieu = "Hối trả"
   c) Gom theo cách gom:
      - BUU_CUC → gom phiếu theo bưu cục, nhóm theo area_manager_id
        Mỗi AM có: tên, danh sách bưu cục (tên, số phiếu, số cần ngay, số phạt)
      - VUNG_AM → gom phiếu theo region_shortname, nhóm theo AM
        Mỗi Vùng có: tên vùng, danh sách AM (tên, số phiếu)
   d) Đọc template:
      - Tên mẫu ở cột E lịch gửi → match với _Control_Center!A62:B79
      - Lấy nội dung (cột B) → điền biến:
        {ten_am}, {vung}, {ngay_gio}, {bcs}, {loai_tieude}, {hanh_dong}, {link}
   e) Ghi RP vào tab RP_Queue:
      - Cột: dot_id, loai_phieu, nguoi_nhan, ma_nv, ten, noi_dung, status="PENDING", timestamp_tao
      - Xóa dữ liệu cũ trong RP_Queue trước khi ghi mới (hoặc ghi đè)

5. Ghi RP_theo_AM và RP_theo_Vung (cho Dashboard) — giữ format hiện tại

6. Ghi _Control_Center!B3 = "PROCESSED" (tránh GAS chạy lại)
7. Ghi _Control_Center!B4 = "DONE", C4 = timestamp

BIẾN TEMPLATE:
- {ten_am} → tên AM (cho AM) hoặc tên Trợ lý (cho Trợ lý)
- {vung} → tên vùng (region_shortname)
- {ngay_gio} → Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "dd/MM/yyyy HH:mm")
- {bcs} → danh sách bưu cục/AM đã format (mỗi dòng 1 bưu cục)
- {loai_tieude} → "TỔNG HỢP HỐI G/L/T" hoặc "ƯU TIÊN HỐI LẤY" tùy loại
- {hanh_dong} → câu nhắc hành động tùy loại phiếu
- {link} → "https://g.ghn.studio/PhieuKhachHang"

DANH SÁCH NGƯỜI NHẬN TRỢ LÝ:
- Đọc từ tab Co_Cau cột S3:W19 (vùng → mã trợ lý)
- Mỗi vùng có 1 hoặc nhiều mã trợ lý

CHỐNG LỖI:
- Nếu không có phiếu nào khớp → bỏ qua dòng đó, không tạo RP
- Nếu AM không có area_manager_id hợp lệ (= 0 hoặc rỗng) → bỏ qua
- Runtime tối đa 6 phút → 2500 dòng Chi_tiet chỉ tốn ~30 giây, OK
- Log kết quả vào _Control_Center vùng Log (dòng 83+)

SHEET ID: 15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg
```

---

## PROMPT 3: VIẾT `send_from_queue.py` + `send_gtalk.yml` (GitHub Actions)

### Giao cho AI:

```
Tôi cần bạn viết 2 file cho GitHub Actions gửi tin GTalk.

### FILE 1: scripts/send_from_queue.py

LUỒNG:
1. Đọc _Control_Center!B4 từ Google Sheet
   - Nếu ≠ "DONE" → exit 0 ngay
2. Ghi B5 = "RUNNING"
3. Đọc tab RP_Queue → lọc cột G (status) = "PENDING"
4. Gửi mẫu tin đầu tiên cho Admin (mã NV 3049378) để kiểm duyệt
5. Với mỗi tin PENDING:
   - Đọc cột D (ma_nv) + cột F (noi_dung)
   - Gọi GTalk API gửi tin (dùng module gtalk_bulk_sender.py)
   - Sleep 1.5 giây giữa tin
   - Ghi cột G = "SENT" nếu thành công, "FAILED" nếu lỗi
   - Ghi cột I = timestamp gửi
   - Ghi cột J = chi tiết lỗi (nếu có)
6. Ghi log vào _Control_Center vùng Log (dòng 83+):
   - Dòng mới: timestamp, giờ đợt, "Gửi", OK/FAILED, số tin, chi tiết
7. Ghi B5 = "DONE", C5 = timestamp
8. Gửi tin tổng kết cho Admin (3049378)

GTalk API:
- File gtalk_bulk_sender.py ở cùng repo (GuTin_Theo_MaNV/)
- Import: from GuTin_Theo_MaNV.gtalk_bulk_sender import _load_oa_token, create_direct_channel, send_message
- Token từ env var GTALK_OA_TOKEN (format: oa_id:oa_secret)

Google Sheets:
- Auth bằng service account JSON (từ env var GOOGLE_KEY_JSON — nội dung JSON, không phải file path)
- Sheet ID: 15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg

### FILE 2: .github/workflows/send_gtalk.yml

```yaml
name: Send GTalk Messages
on:
  schedule:
    - cron: '20 23,0,1,2,3,4,5,6,7,8,9,10,11 * * 1-5'
    # = mỗi giờ từ 6h20-18h20 VN (UTC+7), T2-T6
    # Chạy phút 20 để chờ Render cào (đầu giờ) + GAS xử lý (~phút 5)
  workflow_dispatch:  # cho phép chạy tay

jobs:
  send:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install google-auth google-api-python-client requests
      - run: python scripts/send_from_queue.py
        env:
          GTALK_OA_TOKEN: ${{ secrets.GTALK_OA_TOKEN }}
          GOOGLE_KEY_JSON: ${{ secrets.GOOGLE_KEY_JSON }}
```

CHỐNG LỖI:
- Nếu RP_Queue rỗng hoặc không có PENDING → log "Không có tin cần gửi" + exit 0
- Nếu GTalk API lỗi 1 tin → ghi FAILED, tiếp tục tin khác (không dừng)
- Nếu Sheet API lỗi → retry 1 lần, sau đó exit 1
- KHÔNG bao giờ hardcode token — chỉ đọc từ env
```

---

## PROMPT 4: DEPLOY DASHBOARD (scripts/deploy_dashboard.py + workflow)

### Giao cho AI:

```
Tôi cần bạn viết script + workflow để tự động deploy Dashboard lên Cloudflare Pages.

### FILE 1: scripts/deploy_dashboard.py

LUỒNG:
1. Đọc Google Sheet tab Chi_tiet + Ton_phieu
2. Build dashboard HTML (template ở dashboard/index.html)
3. Deploy lên Cloudflare Pages dùng wrangler CLI

OUTPUT: thư mục _site/ chứa file HTML tĩnh

### FILE 2: .github/workflows/deploy_dashboard.yml

```yaml
name: Deploy Dashboard
on:
  schedule:
    - cron: '30 23,2,5,8,11 * * 1-5'
    # = 5 lần/ngày: 6h30, 9h30, 12h30, 15h30, 18h30 VN
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install google-auth google-api-python-client
      - run: python scripts/deploy_dashboard.py
        env:
          GOOGLE_KEY_JSON: ${{ secrets.GOOGLE_KEY_JSON }}
      - uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CF_API_TOKEN }}
          accountId: ${{ secrets.CF_ACCOUNT_ID }}
          command: pages deploy _site --project-name=ghn-dashboard
```

PROJECT NAME: ghn-dashboard (đã tồn tại trên CF Pages: ghn-dashboard.pages.dev)
SHEET ID: 15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg
Template dashboard: tham khảo file Dashboard_TonPhieu/sync_and_deploy.py trong repo
```

---

## THỨ TỰ GIAO PROMPT

| Thứ tự | Prompt | Lý do |
|---|---|---|
| 1 | Prompt 2 (Code.gs) | Tạo bộ não trước, test độc lập trên Sheet |
| 2 | Prompt 3 (send_from_queue.py) | Gửi tin, test với RP_Queue có sẵn |
| 3 | Prompt 4 (deploy_dashboard.py) | Dashboard, test độc lập |
| 4 | Prompt 1 (cắt control_center.py) | Cắt cuối cùng khi mọi thứ đã chạy |

> ⚠️ **Quan trọng:** Prompt 1 (cắt Python) làm SAU CÙNG. Hệ cũ vẫn chạy bình thường
> trong khi test 3 module mới. Chỉ khi nào 3 module mới OK → mới cắt.
