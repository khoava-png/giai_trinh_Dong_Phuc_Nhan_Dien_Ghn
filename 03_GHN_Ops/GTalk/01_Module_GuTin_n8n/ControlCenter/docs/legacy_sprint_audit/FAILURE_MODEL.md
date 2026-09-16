# Failure Model & Recovery Strategy

| Failure Scenario | Expected Behavior & Recovery | Status |
|---|---|---|
| **Python Offline** | Apps Script continues ticking; detects stale `snapshot_id` or missing data; sets `READY_TO_SEND = FALSE` and logs warning in `08_SYSTEM_STATE`. Recovers automatically when Python resumes scraping. | **PASS** |
| **Apps Script Timeout** | LockService releases lock upon execution termination. Next clock trigger resumes pending queue items safely without duplication. | **PASS** |
| **Formula Error (#REF! / #VALUE!)** | Data readiness check fails. Queue remains blocked (`SKIPPED`) until formulas resolve, preventing erroneous notifications. | **PASS** |
| **GTalk Timeout / 5xx** | `UrlFetchApp` catches exception, increments `retry_count`, marks queue item as `FAILED` or retries up to 3 times before recording in `07_SEND_LOG`. | **PASS** |
| **Duplicate Trigger Concurrency** | `LockService.getScriptLock().tryLock(30000)` aborts secondary concurrent execution instantly. | **PASS** |
