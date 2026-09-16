# DURABLE GENERATION SCHEMA — ORDER-CORE-002

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-CORE-002  

## 1. Thiết kế Schema Control Plane (Upstash Redis)
- **Current Pointer Key:** `control_center:data:current_committed_generation`
  - Giá trị: `<generation_id>` (String)
- **Generation Metadata Key:** `control_center:data:generation:<id>`
  - Giá trị (JSON):
    ```json
    {
      "generation_id": "gen-1789465558",
      "status": "COMMITTED",
      "started_at": "2026-09-15T12:00:00+07:00",
      "committed_at": "2026-09-15T12:01:15+07:00",
      "source_count": 150,
      "ticket_count": 2500,
      "checksum": "sha256-hash-placeholder",
      "previous_generation": "gen-1789461958"
    }
    ```
- **Phân định Storage:**
  - **Control Plane:** Upstash Redis (lưu metadata generation & commit pointer).
  - **Data Plane:** Google Sheets (`Chi_tiet`, `Ton_phieu`, `RP_theo_AM`, `RP_theo_TroLy`).
