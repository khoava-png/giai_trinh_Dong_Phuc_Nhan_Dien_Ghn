# CHANGE MAP — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-003 (Change Impact Analysis)  

## 1. Inventory Change Units & Dependencies (CU-001 to CU-005)

| Change Unit ID | Tên Change Unit | Module Owner | Dependency | Upstream | Downstream | Runtime Dependency | Config Dependency | Data Dependency |
|---|---|---|---|---|---|---|---|---|
| **CU-001** | **Core HTTP Server & Handler** | Backend Team | Python stdlib (`http.server`, `threading`) | UptimeRobot / Client Requests | Scheduler, Scraper, GTalk Sender | Python Runtime, Network Port | PORT env var | Local / Redis state |
| **CU-002** | **Scheduler & Tick Loop** | Backend Team | Python `time`, `threading`, Redis client | Internal Tick Timer (30s) | Scraper, GTalk Sender, Google Sheets Sync | Upstash Redis REST API | `sched.json` config | Redis `control_center:sched` |
| **CU-003** | **Web Scraper Module** | Backend Team | `requests`, `bs4` (`cao_ton_phieu.py`) | Scheduler Trigger | Google Sheets API, In-memory Cache | GHN Vận Hành Web Server | `OP_WEB_USER`, `OP_WEB_PASS` | GHN HTML DOM / Raw Tickets |
| **CU-004** | **Google Sheets Sync Engine** | Backend Team | `googleapiclient.discovery.build` | Web Scraper, Scheduler | Cloudflare Dashboard, Google Sheets API | Google Sheets v4 API | `GOOGLE_KEY_FILE` | Spreadsheet `15Ph9h9pOf5...` |
| **CU-005** | **GTalk Notification Sender** | Backend Team | `gtalk_bulk_sender.py` | Scheduler, Scraper | GTalk OA API, Admin Alert (3049378) | GTalk OA Gateway | `GTALK_OA_TOKEN` | AM List, Vung List, Message Payload |
