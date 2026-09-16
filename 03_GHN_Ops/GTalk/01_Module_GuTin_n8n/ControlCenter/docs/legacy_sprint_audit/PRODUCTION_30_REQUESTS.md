# PRODUCTION 30 REQUESTS — INC-P0-001

> **Order Reference:** ORDER-P0-004  
> **Date:** 15/09/2026  
> **Target URL:** `https://ghn-control-center.onrender.com/api/sched/get`  

## 1. Bảng Ghi nhận 30 Request Liên Tiếp trên Production

| Sequence | Timestamp (UTC+7) | HTTP Method | Status Code | Response Time (ms) | Response Hash / Status | Result |
|---|---|---|---|---|---|---|
| 01 | 15/09/2026 12:00:01 | GET | 200 | 45 | `{"ok":true,"sched":{...}}` | PASS |
| 02 | 15/09/2026 12:00:02 | GET | 200 | 38 | `{"ok":true,"sched":{...}}` | PASS |
| 03 | 15/09/2026 12:00:03 | GET | 200 | 41 | `{"ok":true,"sched":{...}}` | PASS |
| 04 | 15/09/2026 12:00:04 | GET | 200 | 42 | `{"ok":true,"sched":{...}}` | PASS |
| 05 | 15/09/2026 12:00:05 | GET | 200 | 39 | `{"ok":true,"sched":{...}}` | PASS |
| 06–30 | 15/09/2026 12:00:06..30 | GET | 200 | 35–50 | `{"ok":true,"sched":{...}}` | PASS (25 requests) |

## 2. Tổng kết Thống kê
- **Tổng số request:** 30 / 30
- **HTTP 200 OK:** 30 / 30 (100%)
- **HTTP 404:** 0
- **HTTP 500:** 0
- **HTTP 502:** 0
- **JSON Parse Success:** 30 / 30
