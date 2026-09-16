# OVERWRITE ROOT CAUSE — ORDER-ROOT-002

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-ROOT-002  

## 1. Nguyên nhân Gốc rễ Hiện tượng Overwrite
- **Phân loại nguyên nhân:** **BUSINESS_REQUIRED** (Yêu cầu nghiệp vụ cốt lõi).
- **Giải thích:** Dữ liệu tồn phiếu lấy từ GHN Vận Hành là một **Full Current Snapshot**. Mỗi chu kỳ cào là một trạng thái tồn đọng mới nhất. Do đó, việc ghi đè toàn bộ dữ liệu cũ bằng dữ liệu mới là hành vi hoàn toàn chính xác theo thiết kế snapshot, không phải là lỗi kiến trúc (không phải historical ledger).
