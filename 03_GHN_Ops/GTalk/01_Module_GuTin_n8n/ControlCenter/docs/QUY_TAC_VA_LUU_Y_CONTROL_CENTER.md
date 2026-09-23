# 📝 NHẬT KÝ KỸ THUẬT & GHI CHÚ VẬN HÀNH GHN CONTROL CENTER
*Vị trí lưu file: e:\GHN\AntiGravity\Khua_Ho_Tro\03_GHN_Ops\GTalk\01_Module_GuTin_n8n\ControlCenter\docs\QUY_TAC_VA_LUU_Y_CONTROL_CENTER.md*

## 1. TỔNG QUAN HẠ TẦNG VÀ DEPLOYMENT
- **Google Cloud Project:** `ghn-sheets-automation`
- **Cloud Run Service:** `ghn-control-center` (Region: `asia-southeast1`)
- **GitHub Repository:** `khoava-png/ghn-control-center` (Branch: `main`)
- **Cloudflare Pages Dashboard:** `ghn-dashboard.pages.dev`
- **Service Account:** `ghn-sheet-bot@ghn-sheets-automation.iam.gserviceaccount.com`

---

## 2. CÁC VẤN ĐỀ KỸ THUẬT ĐÃ KHẮC PHỤC (CRITICAL FIXES LOG)
1. **Lỗi NameError (uuid missing):**
   - *Nguyên nhân:* Hàm tạo `run_id` gọi `uuid.uuid4()` nhưng thiếu `import uuid` tại đầu file `control_center.py`.
   - *Khắc phục:* Đã thêm `import uuid` vào khối import chuẩn của `control_center.py`.
2. **Lỗi ModuleNotFoundError (dashboard_sync missing):**
   - *Nguyên nhân:* Quá trình cào ghi sheet gọi module `dashboard_sync` nhưng file này chưa được đưa vào thư mục nguồn của Cloud Run.
   - *Khắc phục:* Đã bổ sung file `dashboard_sync.py` chuẩn vào thư mục gốc của Control Center, đảm bảo Docker build tự động pack thành công vào container image.
3. **Cơ chế tiền phạt (`penalty` & `trang_thai`)**:
   - *Lưu ý quan trọng cho AI agent sau:* Khi cào dữ liệu từ API `/api/tickets` và `/api/buucuc`, phải đảm bảo bám sát giá trị `penalty` thực tế trả về từ nguồn hệ thống vận hành để tính toán số tiền phạt và phân loại trạng thái (`Chưa trễ hạn`, `Trễ hạn còn cứu được`, `Phạt kịch khung`) khớp 100% với giao diện quản lý thực tế (`ghn-vanhanh.dedyn.io`).

---

## 3. QUY TẮC BẮT BUỘC CHO AI AGENT KHI THAO TÁC TRÊN WORKSPACE NÀY
- **Không tự ý chạy cào thật (`/api/ingestion/run`)** khi kiểm tra an toàn không có Secret.
- **Giữ giới hạn Cloud Run `max-instances=1`** để tránh xung đột process-level threading lock của bộ lập lịch ingestion (`_scrape_lock`).
- **Tuân thủ tuyệt đối Quy tắc số 0**: Tự động dùng `clarify` tool khi yêu cầu chưa rõ ràng, tuyệt đối không đoán ý định.
