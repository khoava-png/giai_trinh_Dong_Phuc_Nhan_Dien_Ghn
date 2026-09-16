# BEFORE BENCHMARK — GHN CONTROL CENTER SPRINT-2

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-006 (Sprint-02 Hardening)  

## 1. Số liệu Baseline Trước Hardening (Before Benchmark)

| Metric | Giá trị Baseline (Before) | Đơn vị | Ghi chú |
|---|---|---|---|
| **Initial RSS** | ~185 | MB | Khởi động server |
| **Peak RSS (Max)** | ~450 | MB | Đỉnh điểm lúc parse & ghi Sheets 2500+ phiếu |
| **Final RSS** | ~230 | MB | Sau khi hoàn tất chu kỳ |
| **RSS after GC** | ~210 | MB | Sau khi gom rác thủ công |
| **Cycle Duration** | ~52 | Seconds (s) | Thời gian hoàn thành 1 chu kỳ cào và gửi |
| **CPU Time** | ~3.4 | Seconds (s) | Thời gian CPU tích lũy |
| **Memory Growth (5 cycles)** | +35 | MB | Có xu hướng tăng nhẹ lũy tiến |
