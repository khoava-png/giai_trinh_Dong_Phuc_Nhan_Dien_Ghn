# GOOGLE RETRY POLICY — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-CORE-001  

## 1. Chính sách Thử lại API Google Sheets (Google Retry Policy)
- **Retryable Errors:** HTTP 429 (Rate Limit), HTTP 500, 502, 503, 504 (Server Errors), Network Timeout, Connection Reset.
- **Non-Retryable Errors (Permanent Failures):** HTTP 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden / Permission denied), Invalid Range, Schema Violation $\rightarrow$ Lập tức **ABORT GENERATION**, không retry mù.
- **Chiến lược Thử lại:** Bounded Exponential Backoff kết hợp Jitter, tối đa 3-5 lần thử lại, timeout định mức mỗi lần gọi API.
