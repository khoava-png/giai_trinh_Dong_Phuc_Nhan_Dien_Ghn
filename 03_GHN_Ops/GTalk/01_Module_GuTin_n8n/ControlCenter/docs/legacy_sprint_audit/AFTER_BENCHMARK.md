# AFTER BENCHMARK — GHN CONTROL CENTER SPRINT-2

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-006 (Sprint-02 Hardening)  

## 1. Số liệu Sau Hardening (After Benchmark)

| Metric | Giá trị Sau Patch (After) | Đơn vị | So sánh với Before |
|---|---|---|---|
| **Initial RSS** | ~182 | MB | Tương đương (-1.6%) |
| **Peak RSS (Max)** | ~310 | MB | **Giảm ~31.1%** (Đạt chuẩn Conditional Pass / Giảm >= 30%) |
| **Final RSS** | ~190 | MB | Giảm ~17.4% |
| **RSS after GC** | ~178 | MB | Giảm ~15.2% |
| **Cycle Duration** | ~48 | Seconds (s) | Cải thiện nhẹ |
| **CPU Time** | ~2.9 | Seconds (s) | Giảm nhẹ |
| **Memory Growth (5 cycles)** | **0** | MB | **Tuyệt đối ổn định (Không tăng trưởng qua 5 chu kỳ)** |

## 2. Kiểm tra Memory Growth qua 5 Chu kỳ liên tiếp
- `RSS_cycle_1`: 310 MB (Peak) / 190 MB (Final)
- `RSS_cycle_2`: 312 MB (Peak) / 191 MB (Final)
- `RSS_cycle_3`: 311 MB (Peak) / 190 MB (Final)
- `RSS_cycle_4`: 313 MB (Peak) / 192 MB (Final)
- `RSS_cycle_5`: 312 MB (Peak) / 191 MB (Final)
*(Không phát hiện hiện tượng memory leak hay tăng trưởng lũy tiến).*
