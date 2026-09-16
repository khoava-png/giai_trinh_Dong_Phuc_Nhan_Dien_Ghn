# FAILURE INJECTION MATRIX — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-CORE-001  

## 1. Ma trận Tiêm nhiễm Lỗi (Failure Injection Matrix)

| Điểm Inject (Failure Stage) | Visible Generation | Previous Generation | New Generation | Dashboard Result | GTalk Result | Next-Cycle Recovery |
|---|---|---|---|---|---|---|
| **1. Trước Chi_tiet** | Previous | Intact | Unwritten | Previous Data | Previous Data | Tự động chạy lại chu kỳ mới |
| **2. Sau Chi_tiet / Trước Ton_phieu** | Partial / Aborted | Intact | Aborted | Previous Data | Previous Data | Rollback / Abort generation |
| **3. Sau Ton_phieu** | Partial | Intact | Aborted | Previous Data | Previous Data | Abort generation |
| **4. Trước RP_AM** | Partial | Intact | Aborted | Previous Data | Previous Data | Abort generation |
| **5. Render Restart mid-cycle** | Previous | Intact | Lost in RAM | Previous Data | Previous Data | Khôi phục từ trạng thái Redis/Disk |
