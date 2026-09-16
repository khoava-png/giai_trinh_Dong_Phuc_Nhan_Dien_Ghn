# BUSINESS INVARIANTS — GHN CONTROL CENTER PRODUCTION

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-002 (Baseline Freeze)  

## 1. Định nghĩa Invariants Nghiệp vụ (Business Invariants)
Business Invariants là các quy tắc nghiệp vụ cốt lõi không thể thay đổi, đảm bảo tính chính xác của vận hành GHN.

| Invariant ID | Tên Quy Tắc Nghiệp Vụ | Mô tả chi tiết bất biến nghiệp vụ | Bằng chứng / Source Reference |
|---|---|---|---|
| **BUS-INV-001** | **Target Audience Integrity** | Hệ thống nhắc phiếu tồn bắt buộc phải phục vụ chính xác cho 150+ Quản lý Khu vực (AM) và 14 Trợ lý Giám đốc Vùng. | `PROJECT_MASTER.md` |
| **BUS-INV-002** | **Message Format Standard** | Mọi tin nhắn gửi đi qua GTalk OA phải tuân thủ đúng mẫu cú pháp chuẩn (VD: 'Anh/Chị {ten}', title 'ƯU TIÊN XỬ LÝ HỐI...'). | Memory notes, `control_center.py` |
| **BUS-INV-003** | **Data Source of Truth** | Google Sheets (`15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg`) là nguồn chân lý lưu trữ dữ liệu thô (`Chi_tiet`, `Ton_phieu`). | `PROJECT_MASTER.md`, `KE_HOACH_VA_TIEN_TRINH_DU_AN.md` |
| **BUS-INV-004** | **Schedule Execution Window** | Lịch tự động nhắc phiếu chỉ được phép thực thi trong khung giờ từ 06:00 đến 13:00 hàng ngày (T2–CN). | `KE_HOACH_VA_TIEN_TRINH_DU_AN.md` |
| **BUS-INV-005** | **Dashboard Read-Only Integration** | Dashboard trên Cloudflare Pages (`ghn-dashboard.pages.dev`) chỉ đọc dữ liệu từ Google Sheets, không can thiệp ngược lại quy trình backend. | `PROJECT_MASTER.md` |
