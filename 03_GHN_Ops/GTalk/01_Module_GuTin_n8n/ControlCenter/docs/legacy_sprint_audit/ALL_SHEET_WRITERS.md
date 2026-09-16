# ALL SHEET WRITERS — ORDER-ROOT-002

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-ROOT-002  

## 1. Kiểm kê Toàn bộ Writer Ghi Google Sheets
Sau khi search toàn bộ repository (`values.update`, `values.append`, `write_tab`, `rebuild_formulas`, v.v.):
1. **`cao_ton_phieu.py` (hàm `write_tab`):** Ghi đè trực tiếp các tab `Chi_tiet`, `Ton_phieu`, `RP_theo_AM`, `RP_theo_TroLy`.
2. **`Cao_Ton_Phieu/ghi_rule_sheet.py`:** Script phụ trợ ghi rule (không chạy trong runtime production chính của Control Center).
3. **`Cao_Ton_Phieu/sinh_rp_am.py`:** Script phụ trợ độc lập (không chạy trong runtime production chính).

- **Kết luận:** `WRITER_COUNT_Chi_tiet = 1` (duy nhất Python Backend qua `cao_ton_phieu.py`).
