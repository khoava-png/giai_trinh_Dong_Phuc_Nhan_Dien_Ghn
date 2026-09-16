# OVERWRITE REPRODUCTION — ORDER-ROOT-002

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-ROOT-002  

## 1. Tái hiện Hiện tượng Overwrite
- **Kịch bản:** Chuyển đổi dữ liệu từ 2500 dòng sang 2000 dòng.
- **Trước khi áp dụng Atomic Write (P0 fix trước đó):** Dùng `batchClear` rồi `update`, hoặc dùng `update` đè lên A1 nhưng không xóa các dòng thừa từ 2001-2500 gây stale rows.
- **Sau khi áp dụng Atomic Write:** Hàm `write_tab` ghi đè trực tiếp nguyên tử từ `A1` bằng dữ liệu mới (`values.update` với `RAW`), đồng thời cơ chế Generation Commit đảm bảo chỉ public khi hoàn tất.
- **Phân loại:** **EXPECTED_REPLACE** (đúng theo mô hình `CURRENT_STATE_SNAPSHOT`).
