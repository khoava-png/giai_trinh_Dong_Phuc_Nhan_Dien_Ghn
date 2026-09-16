# CORRECT WRITE MODEL — ORDER-ROOT-002

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-ROOT-002  

## 1. Mô hình Ghi Chính Xác (Correct Write Model)
- **Lựa chọn:** **OPTION A (Deterministic snapshot replace)** kết hợp nguyên lý Crash-Proof Generation Commit.
- **Lý do:** Nguồn dữ liệu từ GHN Vận Hành là Full Snapshot, và mô hình dữ liệu của các tab cốt lõi là `CURRENT_STATE_SNAPSHOT`. Do đó, chiến lược ghi đè toàn bộ (Full Snapshot Replacement) thông qua phương thức ghi nguyên tử là mô hình chính xác nhất và phù hợp nhất với nghiệp vụ vận hành bưu cục hiện tại.
