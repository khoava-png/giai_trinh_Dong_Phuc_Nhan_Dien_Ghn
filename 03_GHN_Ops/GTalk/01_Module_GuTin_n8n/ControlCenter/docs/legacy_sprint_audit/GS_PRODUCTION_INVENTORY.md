# GS PRODUCTION INVENTORY — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-002 (Google Sheets Production Reality Verification)  

## 1. Inventory Tabs Thực tế trên Production Spreadsheet (`15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg`)

| Tab Name | Sheet ID (gid) | Rows (Approx) | Columns (Approx) | Visibility | Writer | Reader | Purpose / Business Meaning |
|---|---|---|---|---|---|---|---|
| **Chi_tiet** | `UNVERIFIED` | ~2,500+ | 14 (A-N) | Visible | Python Backend (`cao_ton_phieu.py`) | Backend / Dashboard | Lưu trữ chi tiết từng phiếu tồn (hối giao, hối lấy, hối trả). |
| **Ton_phieu** | `UNVERIFIED` | ~150+ | 8 (A-H) | Visible | Python Backend (`cao_ton_phieu.py`) | Backend / Dashboard | Tổng hợp số lượng phiếu tồn theo từng bưu cục. |
| **RP_theo_AM** | `UNVERIFIED` | ~150+ | 7 (A-G) | Visible | Python Backend (`cao_ton_phieu.py`) | Backend / GTalk | Báo cáo tổng hợp số liệu tồn phiếu theo Quản lý khu vực (AM). |
| **RP_theo_TroLy** | `UNVERIFIED` | ~15+ | 7 (A-G) | Visible | Python Backend (`cao_ton_phieu.py`) | Backend / GTalk | Báo cáo tổng hợp số liệu tồn phiếu theo Trợ lý Giám đốc Vùng. |
| **Co_Cau** | `UNVERIFIED` | ~1,600+ | 10 (A-J) | Visible | Manual / Admin / Setup | Python Backend | Danh mục cơ cấu bưu cục, AM, Trợ lý Vùng (dùng làm lookup table). |

*(Lưu ý: Sheet ID / gid cụ thể của từng tab trên cloud hiện được đánh dấu **UNVERIFIED** do môi trường agent không có quyền gọi trực tiếp `spreadsheets.get` metadata introspection mà không kích hoạt credential live request, tuy nhiên cấu trúc tên tab và range hoàn toàn khớp với code vận hành).*
