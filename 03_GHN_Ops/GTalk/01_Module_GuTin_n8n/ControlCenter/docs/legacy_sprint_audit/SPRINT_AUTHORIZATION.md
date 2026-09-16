# SPRINT AUTHORIZATION — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-004 (Execution Readiness Gate)  

## 1. Định nghĩa Chi tiết từng Sprint (Entry, Exit, Rollback & Success Metrics)

### ── SPRINT 1: Baseline & Validation ──
- **Sprint ID:** `SPRINT-01`
- **Objective:** Hoàn thành audit, baseline, impact analysis và execution gate.
- **Source Code Permission:** ❌ **CHỈ ĐƯỢC TẠO TÀI LIỆU (Documentation Only)**
- **Entry Criteria:** Hoàn thành tiếp quản dự án.
- **Exit Criteria:** Hoàn thành toàn bộ các tài liệu Validation, Baseline, Impact Map và Execution Gate.
- **Rollback Criteria:** N/A (Không thay đổi source code).
- **Success Metrics:** 100% tài liệu đạt chuẩn PASS, không còn vùng tối.
- **Blocking Conditions:** Thiếu tài liệu Baseline hoặc Validation thất bại.

### ── SPRINT 2: Memory Optimization & Raw Data Pipeline (FIRST SOURCE-EDIT SPRINT) ──
- **Sprint ID:** `SPRINT-02`
- **Objective:** Thực thi Epic 1 & Epic 5: Xóa bỏ Global RAM Cache (`_cached_rows_ct`), chuyển sang file nén tạm `/tmp` hoặc xử lý trực tiếp, bổ sung `gc.collect()`.
- **Source Code Permission:** ✅ **ĐƯỢC PHÉP CHỈNH SỬA SOURCE CODE**
- **Entry Criteria:** Hoàn thành Sprint 1, Execution Gate đạt trạng thái APPROVED.
- **Exit Criteria:** Code đã được patch, unit test chạy pass 100%, Peak RSS giảm tối thiểu 30% trên môi trường local.
- **Rollback Criteria:** Nếu Peak RSS vượt 450MB hoặc container OOM Kill trên Render $\rightarrow$ Revert commit lập tức trong vòng dưới 3 phút theo `ROLLBACK_PLAN.md`.
- **Success Metrics:** Peak RSS <= 150 MB, 0 lỗi OOM qua 5 chu kỳ cào liên tiếp.
- **Blocking Conditions:** Thiếu unit test hoặc chưa cấu hình rollback plan.

### ── SPRINT 3: Google Sheets Batching & Apps Script Engine ──
- **Sprint ID:** `SPRINT-03`
- **Objective:** Thực thi Epic 2 & Epic 3: Tối ưu hóa API ghi tab `Chi_tiet` và `Ton_phieu` dạng Batch, thiết lập công thức `QUERY`/`FILTER` tự động cho tab `RP_AM` và `RP_Vùng`.
- **Source Code Permission:** ✅ **ĐƯỢC PHÉP CHỈNH SỬA SOURCE CODE**
- **Entry Criteria:** Hoàn thành Sprint 2 và xác thực RAM ổn định trên production.
- **Exit Criteria:** Batch API ghi Sheets thành công, công thức `QUERY`/`FILTER` trên Sheets trả dữ liệu đúng.
- **Rollback Criteria:** Lỗi API Sheets 429 hoặc lệch cột dữ liệu báo cáo $\rightarrow$ Revert commit và khôi phục code ghi Sheets cũ.
- **Success Metrics:** Thời gian ghi Sheets giảm 50%, 0 lỗi lệch cột.
- **Blocking Conditions:** Sprint 2 chưa đạt Exit Criteria.

### ── SPRINT 4: Dashboard Integration & Production Verification ──
- **Sprint ID:** `SPRINT-04`
- **Objective:** Thực thi Epic 4 & Epic 6: Kiểm tra hiển thị Dashboard Cloudflare Pages (`ghn-dashboard.pages.dev`), chuẩn hóa log Upstash Redis và Load Test toàn diện quy mô 20.000 phiếu.
- **Source Code Permission:** ✅ **ĐƯỢC PHÉP CHỈNH SỬA SOURCE CODE**
- **Entry Criteria:** Hoàn thành Sprint 3.
- **Exit Criteria:** Dashboard hiển thị chuẩn xác, Load Test 20.000 phiếu thành công, hệ thống đạt trạng thái `READY` hoàn toàn.
- **Rollback Criteria:** Dashboard lỗi hiển thị hoặc tràn log $\rightarrow$ Revert commit.
- **Success Metrics:** Toàn bộ hệ thống đạt điểm Production Readiness >= 95/100.
- **Blocking Conditions:** Sprint 3 chưa hoàn tất.

---

## 2. Kết luận Ủy quyền Cấp phép (Authorization Summary)
- **Tổng số Sprint:** 4 Sprint.
- **Số Sprint chỉ tạo tài liệu:** 1 Sprint (`Sprint 1`).
- **Số Sprint được chỉnh sửa source:** 3 Sprint (`Sprint 2`, `Sprint 3`, `Sprint 4`).
- **Sprint đầu tiên được phép chỉnh sửa source code:** **`Sprint 2`** (sau khi hoàn tất toàn bộ kiểm định chuẩn bị).
