# MASTER PROMPT: PHÁT KIẾN ALL-IN-ONE GOOGLE CLOUD RUN (CONTROL CENTER V3)

> **Dành cho AI nhận nhiệm vụ:** Bạn là Kỹ sư Vận hành & Backend Senior. Nhiệm vụ của bạn là xây dựng hệ thống **GHN Control Center V3** theo kiến trúc **All-in-One trên Google Cloud Run & Cloud Scheduler**.
> Hệ thống này thay thế toàn bộ giải pháp phân mảnh cũ (Render + Apps Script + GitHub Actions), hợp nhất 100% về Python chạy trên Google Cloud Platform với chi phí $0/tháng.

---

## 1. TỔNG QUAN KIẾN TRÚC & LUỒNG HOẠT ĐỘNG

```
┌────────────────────────────────────────────────────────────────────────┐
│                      GOOGLE CLOUD PLATFORM (GCP)                       │
│                                                                        │
│   ┌────────────────────────┐         ┌─────────────────────────────┐   │
│   │ Google Cloud Scheduler │ ──────► │   Google Cloud Run          │   │
│   │ (Cron: 6h, 9h, 12h,    │  POST   │   (All-in-One Python 3.11)  │   │
│   │        15h, 17h, 18h)  │         │                             │   │
│   └────────────────────────┘         │  1. Đọc Chi_tiet & Co_Cau   │   │
│                                      │  2. Lọc & Gom theo AM/Vùng  │   │
│                                      │  3. Render Template Chuẩn   │   │
│                                      │  4. Bắn GTalk 166 tin (20s) │   │
│                                      │  5. Gửi mẫu duyệt & báo cáo │   │
│                                      │     cho Admin (3049378)     │   │
│                                      │  6. Ghi Log vào Google Sheet│   │
│                                      └──────────────┬──────────────┘   │
│                                                     │                  │
│                                                     ▼                  │
│                                      ┌─────────────────────────────┐   │
│                                      │ Google Sheets Database      │   │
│                                      │ (ID: 15Ph9h9pOf5MfvtSaqs...)│   │
│                                      └─────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. THÔNG SỐ CẤU HÌNH & TÀI NGUYÊN (CREDENTIALS)

- **GCP Project ID:** `ghn-sheets-automation`
- **Google Sheet ID:** `15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg`
- **Service Account Email:** `ghn-sheet-bot@ghn-sheets-automation.iam.gserviceaccount.com`
- **GTalk Open API Token:** `2079459965803360256:4d830b80540d5885f8f8be0f9b69152b`
- **Mã NV Admin (Nhận duyệt & Báo cáo tổng):** `3049378` (Khoa)
- **Timezone chuẩn:** `Asia/Ho_Chi_Minh` (UTC+7)
- **Basic Auth:** `admin` / `Ghn@2026!`

---

## 3. YÊU CẦU KỸ THUẬT CHI TIẾT CẦN CODE

### A. Đọc & Gom nhóm dữ liệu từ Google Sheets
1. Đọc tab `Chi_tiet` (Cột A:N, ~2500 dòng phiếu):
   - Cột quan trọng: `ma_buu_cuc`, `ten_buu_cuc`, `loai_phieu`, `tien_phat`, `trang_thai`, `area_manager_id`, `area_manager_name`, `region_shortname`.
2. Đọc tab `Co_Cau!S3:W25` để lấy danh sách Trợ lý Vùng (Hỗ trợ vùng có nhiều hơn 1 trợ lý như Hà Nội, Tây Nam Bộ).
3. Hỗ trợ 4 bộ lọc phiếu theo tham số query `?filter=`:
   - `ALL`: Lấy toàn bộ phiếu (Hối giao, Hối lấy, Hối trả).
   - `HOI_LAY`: Chỉ lọc phiếu `loai_phieu` chứa chữ "lấy".
   - `HOI_GIAO`: Chỉ lọc phiếu `loai_phieu` chứa chữ "giao".
   - `HOI_TRA`: Chỉ lọc phiếu `loai_phieu` chứa chữ "trả".
4. Phân nhóm dữ liệu:
   - **Nhóm AM (`BUU_CUC`):** Nhóm theo `area_manager_id`. Nếu `area_manager_id` rỗng hoặc `"0"` thì bỏ qua (không tạo tin gửi cho ID 0). Sắp xếp bưu cục nhiều phiếu nhất lên đầu.
   - **Nhóm Trợ lý Vùng (`VUNG_AM`):** Nhóm theo `region_shortname`. Liệt kê danh sách các AM trong vùng kèm số phiếu, sắp xếp AM nhiều phiếu nhất lên đầu.

---

### B. Bắn tin GTalk tốc độ cao (Speed-Optimized Pool)
1. **Quy tắc bảo vệ Admin (BẮT BUỘC):**
   - Trước khi bắn diện rộng, tìm tin nhắn có **tổng số phiếu nhiều nhất (Top 1)** gửi trực tiếp cho Admin `3049378` kèm tiêu đề `*[MẪU DUYỆT TỰ ĐỘNG - TOP 1]*`.
2. **Cơ chế gửi đa luồng (20 giây xong 166 tin):**
   - Dùng `ThreadPoolExecutor(max_workers=5)` với khoảng nghỉ an toàn `150ms/tin` giữa các request để tránh nghẽn Gateway GTalk.
   - Endpoint gửi tin: `POST https://openapi.ghn.vn/gtalk/v1/message/send` (Header: `Authorization: Bearer <GTALK_OA_TOKEN>`).
   - Tự động thử lại (Retry) tối đa 2 lần nếu gặp lỗi mạng chập chờn hoặc `HTTP 429`.
3. **Báo cáo hoàn tất:**
   - Khi gửi xong toàn bộ, gửi 1 tin nhắn tổng kết tới Admin `3049378` (Báo rõ: Tổng số tin, số thành công, số thất bại, thời gian hoàn tất).
   - Ghi 1 dòng nhật ký vào tab `_Control_Center!A83` trên Google Sheet.

---

### C. HTTP REST Server cho Cloud Run (Port 8080)
1. `GET /health` hoặc `GET /api/health`: Trả về `{"status": "HEALTHY", "service": "GHN Control Center Cloud Run V3"}` (Dùng cho Google Cloud Run Health Check).
2. `POST /api/cycle/run`: Nhận query params `?filter=ALL` hoặc `?filter=HOI_LAY`, thực thi toàn bộ quy trình cào $\rightarrow$ gom $\rightarrow$ bắn GTalk $\rightarrow$ báo cáo.
3. `GET /dashboard`: Serve giao diện quản trị `index.html` (Bảo vệ bằng Basic Auth).

---

## 4. HỒ SƠ FILE GIAO HÀNG (DELIVERABLES)

1. `control_center.py`: Toàn bộ logic All-in-One gói gọn trong 1 file Python duy nhất.
2. `Dockerfile`: Base `python:3.11-slim`, cài đặt dependencies, mở port 8080.
3. `requirements.txt`: `requests`, `google-auth`, `google-api-python-client`.
4. `.dockerignore`: Bỏ qua các file rác không cần thiết.

---

## 5. LỆNH DEPLOY & CẤU HÌNH CLOUD SCHEDULER

```bash
# 1. Deploy lên Cloud Run (Singapore)
gcloud config set project ghn-sheets-automation

gcloud run deploy ghn-control-center \
  --source . \
  --region asia-southeast1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 300 \
  --set-env-vars SHEET_ID=15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg,ADMIN_MA_NV=3049378,GTALK_OA_TOKEN=2079459965803360256:4d830b80540d5885f8f8be0f9b69152b

# 2. Tạo Lịch Cron trên Cloud Scheduler
# Lịch ALL lúc 6h, 9h, 12h, 17h (T2 - T6)
gcloud scheduler jobs create http ghn-cron-all \
  --schedule="0 6,9,12,17 * * 1-5" \
  --time-zone="Asia/Ho_Chi_Minh" \
  --uri="https://<URL_CLOUD_RUN>/api/cycle/run?filter=ALL" \
  --http-method=POST

# Lịch Hối Lấy lúc 15h (T2 - T6)
gcloud scheduler jobs create http ghn-cron-hoilay \
  --schedule="0 15 * * 1-5" \
  --time-zone="Asia/Ho_Chi_Minh" \
  --uri="https://<URL_CLOUD_RUN>/api/cycle/run?filter=HOI_LAY" \
  --http-method=POST
```

---

## 6. TIÊU CHUẨN HẬU KIỂM (QA ACCEPTANCE CRITERIA)
- [ ] Không có bất kỳ phụ thuộc nào vào Redis, Apps Script hay GitHub Actions Cron.
- [ ] Thử nghiệm bắn 166 tin hoàn tất trong $\le 30$ giây.
- [ ] Bắt buộc gửi tin mẫu nhiều phiếu nhất cho Admin `3049378` trước khi gửi đại trà.
- [ ] Không gửi tin rác cho các AM có 0 phiếu tồn.
- [ ] Hỗ trợ đầy đủ các vùng có 2 trợ lý (Hà Nội, Tây Nam Bộ).
