# INCIDENT REPORT — HTTP 502 ON /api/sched/get

> **Incident ID:** INC-P0-001  
> **Priority:** CRITICAL  
> **Date:** 15/09/2026  
> **Affected Endpoint:** `/api/sched/get`  
> **Status:** ROOT CAUSE IDENTIFIED (No code modified)  

## 1. Mô tả sự cố (Incident Description)
Người dùng ghi nhận HTTP 502 khi gọi endpoint `/api/sched/get` trên hệ thống production (Render). Theo chỉ thị `ORDER-P0-001`, tiến hành trace toàn bộ luồng request mà không sửa code.
