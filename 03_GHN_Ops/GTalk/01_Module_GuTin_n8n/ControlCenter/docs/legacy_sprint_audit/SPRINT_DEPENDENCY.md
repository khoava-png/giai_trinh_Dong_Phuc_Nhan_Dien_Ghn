# SPRINT DEPENDENCY — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-004 (Execution Readiness Gate)  

## 1. Sơ đồ Phụ thuộc Sprint (Sprint Dependency Graph)

```mermaid
graph TD
    S1[Sprint 1: Baseline & Architecture Validation <br/> Status: COMPLETED] --> S2[Sprint 2: Memory Optimization & Raw Data Pipeline <br/> Status: READY]
    S2 --> S3[Sprint 3: Google Sheets Batching & Apps Script Engine <br/> Status: PLANNED]
    S3 --> S4[Sprint 4: Dashboard Integration & Production Verification <br/> Status: PLANNED]

    subgraph Dependency Rules
        S2 -.->|Requires Baseline & Gate Pass| S1
        S3 -.->|Requires Memory Optimization Done| S2
        S4 -.->|Requires Sheets Engine Done| S3
    end
```

## 2. Sprint Bắt buộc Phải Thực Hiện Trước
- **Sprint 1 (Hoàn thành):** Đóng băng Baseline, kiểm định kiến trúc, lập Impact Analysis và Execution Gate. Không thể nhảy cóc sang Sprint 2 nếu chưa qua Sprint 1.
- **Sprint 2 (Tiếp theo):** Bắt buộc phải thực hiện trước Sprint 3 để giải quyết triệt để rủi ro OOM Peak Memory (loại bỏ Global RAM Cache).
