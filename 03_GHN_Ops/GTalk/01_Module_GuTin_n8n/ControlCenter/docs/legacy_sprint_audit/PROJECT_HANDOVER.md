# PROJECT HANDOVER — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  

## 1. Thông tin Bàn giao
- **Dự án:** GHN Control Center
- **Mục tiêu cốt lõi:** Tự động hóa nhắc phiếu tồn Vận hành GHN, đồng bộ dữ liệu Google Sheets, gửi tin nhắn GTalk OA cho AM & Trợ lý Vùng.
- **Hạ tầng Production:** Render Free (`srv-dafp8kn40ujc73cadrl0`, 512 MB RAM).
- **GitHub Repository:** `khoava-png/ghn-control-center` (private).
- **Dashboard URL:** `ghn-dashboard.pages.dev`.

## 2. Các Tài liệu SSOT Bàn Giao
1. `PROJECT_MASTER.md`: Tài liệu điều hành duy nhất.
2. `TIEN_TRINH.md`: Nhật ký tiến độ và sự cố theo ngày.
3. `CHANGELOG.md`: Lịch sử phát hành.
4. `ARCHITECTURE_DECISION.md`: Quyết định kiến trúc chính thức (ADR-001).
5. `IMPLEMENTATION_PLAN.md`: Kế hoạch thực thi chi tiết.
6. `PROJECT_STATUS.md`: Trạng thái tổng quan dự án (82%).
7. `ROADMAP.md`: Lộ trình phát triển 4 pha.
8. `RISK_REGISTER.md`: Sổ đăng ký rủi ro và giảm thiểu.
9. `TEST_PLAN.md`: Kế hoạch kiểm thử (Unit test `memory_meter.py` 100% coverage).
10. `DEPLOYMENT_PLAN.md`: Quy trình triển khai Zero-Downtime.
11. `ROLLBACK_PLAN.md`: Quy trình khẩn cấp khôi phục dưới 3 phút.

## 3. Quy Tắc Vận Hành & Bảo Trì Bắt Buộc
- **Không tự ý thay đổi code Production** nếu chưa qua bước review và test thực tế (live check).
- **Tuân thủ van an toàn KN1/KN2:** Mọi thay đổi luồng cào dữ liệu phải duy trì cơ chế backoff 60 phút và cảnh báo GTalk khi lỗi liên tiếp 3 lần.
- **Biến môi trường Render:** Bắt buộc duy trì đầy đủ `OP_WEB_USER`, `OP_WEB_PASS`, `GOOGLE_KEY_FILE`, `GTALK_OA_TOKEN`.
