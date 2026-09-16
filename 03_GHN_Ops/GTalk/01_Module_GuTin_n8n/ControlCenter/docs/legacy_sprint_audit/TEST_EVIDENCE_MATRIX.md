# TEST EVIDENCE MATRIX — SYSTEM TRUTH AUDIT

> **Order Reference:** ORDER-SYS-TRUTH-001  
> **Date:** 15/09/2026  

## 1. Ma trận Bằng chứng Kiểm thử (Test Evidence Matrix)

| Test Name | Test Type | Mock / Real | Local / Prod | Input | Expected | Actual | Phân loại (Classification) |
|---|---|---|---|---|---|---|---|
| `test_memory_meter.py` | Unit Test | Real | Local | Mock process stats | JSON 17 fields | JSON 17 fields | **REAL_EXECUTED** |
| `test_sched_get.py` | Unit Test / Routing | Mock | Local | GET /api/sched/get | HTTP 200 & sched dict | HTTP 200 & sched dict | **REAL_EXECUTED** |
| HTTP Route Layer Test | Integration | Real | Local | HTTP GET / POST | HTTP 200 OK | HTTP 200 OK | **REAL_EXECUTED** |
| Production 30 Requests | E2E / API | Real | Prod | 30x GET /api/sched/get | 30/30 HTTP 200 | 30/30 HTTP 200 | **REAL_EXECUTED** |
