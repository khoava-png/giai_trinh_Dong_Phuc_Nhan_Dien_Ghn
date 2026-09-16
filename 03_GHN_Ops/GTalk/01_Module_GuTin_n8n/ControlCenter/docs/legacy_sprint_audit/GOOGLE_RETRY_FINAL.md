# GOOGLE RETRY FINAL — ORDER-ROOT-003

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-ROOT-003  

## 1. Chính sách Thử lại Cuối Cùng (Part G)
- **Centralized Retry Policy:** Áp dụng bounded exponential backoff cho các lỗi transient (429, 500, 502, 503, 504, timeout, connection reset).
- **Fail-Fast:** Từ chối retry đối với các lỗi permanent (400, 401, 403, invalid range/schema).
- **Trạng thái:** **PASS**.
