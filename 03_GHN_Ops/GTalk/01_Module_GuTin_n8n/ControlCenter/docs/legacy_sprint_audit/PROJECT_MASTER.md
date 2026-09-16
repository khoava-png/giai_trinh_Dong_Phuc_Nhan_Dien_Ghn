# PROJECT MASTER — GHN CONTROL CENTER

> **Single Source of Truth (SSOT)**
> **Last Updated:** 15/09/2026
> **Current Version:** v2.0.0-PA2
> **Current Phase:** Phase 2 (Architecture Design & Planning Completed, Ready for Execution)
> **Overall Progress:** 78%

---

## 1. Tổng quan dự án
GHN Control Center là hệ thống tự động hóa nhắc phiếu tồn Vận hành GHN (Hối giao, Hối lấy, Hối trả) cho 150+ Quản lý Khu vực (AM) và 14 Trợ lý Giám đốc Vùng qua GTalk OA, kết hợp cung cấp Dashboard trực quan trên Cloudflare Pages.

## 2. Mục tiêu dự án
- Giải quyết triệt để sự cố OOM Kill (Out Of Memory) trên hạ tầng Render Free (512 MB RAM).
- Đảm bảo hệ thống vận hành bền vững, tự động hóa 100% không cần can thiệp thủ công từ máy local.
- Mở rộng quy mô xử lý ổn định lên đến 20.000 phiếu.
- Chuẩn hóa quy trình giám sát, cảnh báo tự động và khẩn cấp (Rollback trong vòng 3 phút).

## 3. Hiện trạng hệ thống
- **Server chính:** Render Free (`srv-dafp8kn40ujc73cadrl0`, 512 MB RAM).
- **Hạ tầng lưu trữ & đồng bộ:** Google Sheets (`15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg`), Upstash Redis.
- **Giao diện:** Cloudflare Pages (`ghn-dashboard.pages.dev`).
- **Nghiệp vụ:** Hối giao/lấy/trả; gửi AM & Trợ lý Vùng; múi giờ `Asia/Ho_Chi_Minh`.

## 4. Kiến trúc hiện tại (Monolithic Synchronous - Đang loại bỏ)
- Server Python đảm nhiệm toàn bộ: Cào web nội bộ, parse dữ liệu, lưu trữ Global RAM Cache vĩnh viễn (`_cached_rows_ct`), tự render bảng báo cáo nặng trên RAM, ghi trực tiếp từng dòng lên Google Sheets và gọi API GTalk.
- *Nhược điểm chí mạng:* Tích lũy bộ nhớ (Memory Creep) qua các chu kỳ, dẫn đến tràn 512 MB RAM và sập container.

## 5. Kiến trúc mục tiêu đã được lựa chọn (PA2: Server-to-Sheets Separation)
- **Cốt lõi:** Tách biệt hoàn toàn tính toán bảng biểu ra khỏi Server Python.
- Server Python chỉ thực hiện: Đăng nhập, cào dữ liệu thô, parse danh sách `tickets` / `rows_ct` và đẩy lên Google Sheets bằng Batch API, sau đó giải phóng bộ nhớ ngay lập tức (`gc.collect()`).
- Mọi bảng báo cáo phụ trợ (`RP_theo_AM`, `RP_theo_Vùng`) do Google Sheets tự động tổng hợp bằng công thức (`QUERY`/`FILTER`) hoặc Apps Script Trigger.
- Loại bỏ hoàn toàn Global RAM Cache trên Python.

## 6. Các quyết định kiến trúc (ADR)
- **ADR-001:** Lựa chọn Phương án Kiến trúc PA2 (Tách biệt tính toán báo cáo sang Google Sheets/Apps Script) nhằm giảm 70% lượng RAM tiêu thụ trên Render Free và loại bỏ hoàn toàn nguy cơ OOM.

## 7. Các nguyên tắc thiết kế
- **Ephemerality & Stream Processing:** Xử lý dòng chảy dữ liệu ngắn hạn, giải phóng RAM ngay lập tức sau khi hoàn thành nhiệm vụ.
- **Separation of Concerns:** Server chuyên xử lý I/O và cào web; Google Sheets/Apps Script chuyên xử lý tính toán bảng biểu.
- **Fail-Safe & Graceful Degradation:** Xử lý lỗi cục bộ mà không làm sập toàn bộ hệ thống (kết hợp KN1/KN2 backoff và cảnh báo GTalk cho Admin).

## 8. Các nguyên tắc triển khai
- Mọi thay đổi phải tuân thủ Test-Driven Development (TDD) hoặc kiểm chứng qua unit test (100% coverage cho module mới).
- Tuyệt đối không hardcode secret; sử dụng biến môi trường Render.
- Đảm bảo khả năng Zero-Downtime Migration và Rollback an toàn dưới 3 phút.

## 9. Quy tắc làm việc với AI
- AI không tự ý push code lên production hoặc thay đổi cấu hình bảo mật khi chưa có phê duyệt rõ ràng từ Admin (Khoa).
- Mọi giải pháp đưa ra phải dựa trên chứng cứ đo lường thực tế (Evidence-based), không phỏng đoán hay suy diễn.

## 10. Work Breakdown Structure (WBS)
- Toàn bộ dự án được phân rã thành 6 Epic và 11 Task chuẩn hóa, thời gian thực hiện mỗi task từ 0.5 – 1 ngày.

## 11. Danh sách Epic
1. Epic 1: Raw Data Pipeline
2. Epic 2: Google Sheets Engine
3. Epic 3: Apps Script & Formulas Engine
4. Epic 4: Dashboard Integration
5. Epic 5: Memory Optimization & GC
6. Epic 6: Monitoring & Alerting

## 12. Danh sách Task
- **T1.1:** Tách module cào thô (`cao_ton_phieu.py`), gỡ bỏ hàm render báo cáo cục bộ khỏi Python.
- **T1.2:** Viết Unit Test cho module cào thô và parse dữ liệu.
- **T2.1:** Tối ưu hóa API ghi tab `Chi_tiet` và `Ton_phieu` dạng Batch.
- **T2.2:** Kiểm thử tích hợp kết nối Google Sheets (Dry-run).
- **T3.1:** Thiết lập công thức `QUERY`/`FILTER` tự động cho tab `RP_AM` và `RP_Vùng`.
- **T3.2:** Kiểm chứng tự động hóa trigger trên Google Sheets.
- **T4.1:** Kiểm tra hiển thị Dashboard Cloudflare Pages với cấu trúc dữ liệu mới.
- **T5.1:** Xóa bỏ Global RAM Cache (`_cached_rows_ct`), thay bằng tệp nén tạm trên đĩa (`/tmp`).
- **T5.2:** Bổ sung chủ động gọi `gc.collect()` tại mốc `JOB_FINISH`.
- **T6.1:** Kích hoạt hệ thống log Memory Meter kết hợp cảnh báo GTalk (KN1/KN2) trên production.

## 13. Roadmap
- **Phase 1:** Giám sát hiện trạng & Tích hợp Memory Meter (Đã hoàn thành).
- **Phase 2:** Tối ưu hóa bộ nhớ & Loại bỏ Global RAM Cache (Đang chuẩn bị).
- **Phase 3:** Chuyển dịch kết xuất báo cáo sang Google Sheets/Apps Script (Chờ thực thi).
- **Phase 4:** Kiểm thử chịu tải mở rộng 20.000 phiếu (Hoàn thiện dự án).

## 14. Sprint Plan
- **Sprint hiện tại (Sprint 1):** Hoàn thành chuẩn bị kiến trúc, tài liệu SSOT, Unit test module đo lường bộ nhớ (100% coverage).
- **Sprint tiếp theo (Sprint 2):** Thực thi Epic 1 & Epic 5 (Raw Data Pipeline & Memory Optimization).

## 15. Risk Register
- **R1 (Lỗi 429 Google Sheets API):** Xác suất trung bình, ảnh hưởng cao $\rightarrow$ Áp dụng retry với backoff thời gian.
- **R2 (Công thức Sheets QUERY lệch cột):** Xác suất thấp, ảnh hưởng cao $\rightarrow$ Chạy test dữ liệu giả lập trước khi deploy.
- **R3 (OOM đột ngột):** Xác suất thấp, ảnh hưởng cao $\rightarrow$ Theo dõi sát sao qua log Memory Meter và sẵn sàng Rollback.

## 16. Test Plan
- Bao gồm Unit Test (unittest cho `memory_meter.py` và module cào), Integration Test (dry-run Google Sheets), Load Test (mô phỏng 5-10 chu kỳ liên tiếp trên local), Production Verification và Rollback Test.

## 17. Deployment Plan
- Quy trình deploy Zero-Downtime thông qua GitHub Actions / Render Auto-Deploy trên nhánh release.

## 18. Rollback Plan
- Khôi phục phiên bản mã nguồn ổn định từ thư mục backup `ControlCenter_backup_before_edit/` hoặc revert commit trên Render trong vòng dưới 3 phút.

## 19. Monitoring Plan
- Giám sát qua hệ thống log JSON chuẩn 17 trường (`memory_meter.py`) trên Render Logs kết hợp cơ chế cảnh báo tự động về GTalk Admin (`3049378`) khi cào lỗi 3 lần liên tiếp.

## 20. Coding Standards
- Python tuân thủ chuẩn PEP 8.
- Công cụ kiểm tra chất lượng bắt buộc: `black`, `isort`, `flake8`, `mypy` (0 lỗi, 0 warning).

## 21. Documentation Standards
- Toàn bộ tài liệu viết bằng Markdown chuẩn GitHub Flavored.
- Mỗi file tài liệu phải bắt buộc có các mục: Last Updated, Current Version, Current Phase, Progress, Next Action, Decision Log.

## 22. Definition of Done (DoD)
- Code hoàn thành kèm Unit Test pass 100% (Coverage tối thiểu 90%).
- Đã chạy kiểm tra qua Flake8, Mypy, Black, isort không có lỗi.
- Đã được review bởi Tech Lead / Admin Khoa và kiểm thử trên môi trường staging.

## 23. Checklist Trước Khi Merge
- [ ] Code không vi phạm chuẩn linter (Flake8, Mypy).
- [ ] Unit test mới đạt 100% pass.
- [ ] Không ảnh hưởng đến các luồng nghiệp vụ cốt lõi (Scheduler, GTalk).

## 24. Checklist Trước Khi Deploy
- [ ] Xác nhận biến môi trường đầy đủ trên Render (`GOOGLE_KEY_FILE`, `GTALK_OA_TOKEN`, v.v.).
- [ ] Kiểm tra tính toàn vẹn của nhánh release.
- [ ] Sẵn sàng phương án rollback.

## 25. Checklist Sau Khi Deploy
- [ ] Kiểm tra endpoint `/api/health` trả về HTTP 200.
- [ ] Theo dõi log JSON Memory Meter trên Render qua 3 chu kỳ liên tiếp.
- [ ] Xác nhận không có ngoại lệ hoặc hiện tượng tăng RAM bất thường.

## 26. Quy Trình Báo Cáo Tiến Độ
- Báo cáo ngắn gọn theo cấu trúc chuẩn: Trạng thái, Bằng chứng, File/Commit đã đổi, Test, Rủi ro, Bước tiếp theo.

## 27. Quy Trình Cập Nhật Tài Liệu
- Mọi thay đổi về kiến trúc hoặc tiến độ phải được cập nhật đồng thời vào `PROJECT_MASTER.md` và các file Markdown tương ứng trong cùng một phiên làm việc.

## 28. Danh Sách Toàn Bộ File Markdown Của Dự Án & Vai Trò
1. `PROJECT_MASTER.md`: Tài liệu điều hành duy nhất (SSOT) toàn dự án.
2. `TIEN_TRINH.md`: Nhật ký tiến độ và sự cố theo ngày.
3. `CHANGELOG.md`: Lịch sử phát hành phiên bản phần mềm.
4. `ARCHITECTURE_DECISION.md`: Quyết định kiến trúc chính thức (ADR).
5. `IMPLEMENTATION_PLAN.md`: Kế hoạch thực thi chi tiết các Epic và Task.
6. `PROJECT_STATUS.md`: Trạng thái tổng quan dự án.
7. `ROADMAP.md`: Lộ trình phát triển dài hạn.
8. `RISK_REGISTER.md`: Sổ đăng ký rủi ro và biện pháp xử lý.
9. `TEST_PLAN.md`: Kế hoạch kiểm thử toàn diện.
10. `DEPLOYMENT_PLAN.md`: Quy trình triển khai sản phẩm.
11. `ROLLBACK_PLAN.md`: Quy trình khẩn cấp khôi phục hệ thống.

## 29. Sprint Hiện Tại Và Sprint Tiếp Theo
- **Sprint Hiện Tại (Sprint 1):** Chuẩn hóa kiến trúc SSOT, thiết kế Memory Meter, Unit Test đạt 100% coverage.
- **Sprint Tiếp Theo (Sprint 2):** Thực thi Epic 1 & Epic 5 (Raw Data Pipeline & Memory Optimization).

## 30. Backlog Còn Lại
- Thực thi Task T1.1, T1.2, T2.1, T2.2, T3.1, T3.2, T4.1, T5.1, T5.2, T6.1 theo WBS đã định nghĩa.
