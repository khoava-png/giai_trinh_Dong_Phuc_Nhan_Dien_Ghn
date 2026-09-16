# RISK REGISTER — GHN CONTROL CENTER

> **Last Updated:** 15/09/2026
> **Current Version:** v2.0.0-PA2
> **Current Phase:** Phase 2
> **Progress:** 78%
> **Next Action:** Giám sát rủi ro khi triển khai Epic 1-5.
> **Decision Log:** Quản lý rủi ro và biện pháp giảm thiểu.

- **R1 (Lỗi 429 Google Sheets API):** Xác suất trung bình, ảnh hưởng cao $\rightarrow$ Áp dụng retry với backoff.
- **R2 (Công thức Sheets QUERY lệch cột):** Xác suất thấp, ảnh hưởng cao $\rightarrow$ Chạy test dữ liệu giả lập trước khi deploy.
- **R3 (OOM đột ngột):** Xác suất thấp, ảnh hưởng cao $\rightarrow$ Theo dõi sát sao qua log Memory Meter và sẵn sàng Rollback.
