# ARCHITECTURE DECISION RECORD (ADR) — GHN CONTROL CENTER

> **Last Updated:** 15/09/2026
> **Current Version:** v2.0.0-PA2
> **Current Phase:** Phase 2
> **Progress:** 78%
> **Next Action:** Triển khai theo ADR-001.
> **Decision Log:** Lựa chọn phương án PA2 làm chuẩn kiến trúc duy nhất của dự án.

## ADR-001: Lựa chọn Phương án Kiến trúc PA2 (Tách biệt tính toán báo cáo sang Google Sheets/Apps Script)
- **Bối cảnh:** Server Render Free 512MB RAM bị OOM Kill liên tục do lưu trữ Global RAM Cache và tự render báo cáo nặng trên Python Heap.
- **Quyết định:** Chọn PA2. Server chỉ cào, parse thô và ghi Sheets. Mọi bảng báo cáo phụ trợ do Google Sheets tự tổng hợp.
- **Hệ quả:** Giảm RAM từ ~480MB xuống còn 80-150MB, vận hành bền vững, dễ mở rộng lên 20.000 phiếu.
