# API CONTRACT — /api/sched/get

> **Order Reference:** ORDER-P0-003  
> **Date:** 15/09/2026  

## 1. Đặc tả Giao diện API (API Contract Specification)
- **Endpoint:** `/api/sched/get`
- **Supported Methods:** `GET`, `POST`
- **Response Format:** JSON (`application/json`)
- **Response Structure (Schema):**
  ```json
  {
    "ok": true,
    "sched": {
      "enabled": boolean,
      "dry_run": boolean,
      "delay_min": number,
      "send_am": boolean,
      "send_vung": boolean,
      "hours_am_all": array[number],
      "hours_am_cd": array[number],
      "am_cd_loai": string,
      "hours_vung_all": array[number],
      "hours_vung_cd": array[number],
      "vung_cd_loai": string,
      "allowed_weekdays": array[number],
      "last_run_am": string | null,
      "last_run_vung": string | null
    }
  }
  ```
