# BASELINE METRICS — GHN CONTROL CENTER PRODUCTION

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-002 (Baseline Freeze)  

## 1. Bảng Chỉ số Đo lường Baseline (Baseline Metrics Inventory)

Mọi chỉ số dưới đây được ghi nhận dựa trên cấu hình vận hành thực tế tại Render Free (512 MB RAM) và môi trường kiểm thử cục bộ.

| Metric ID | Chỉ số (Metric) | Giá trị Baseline (Baseline Value) | Đơn vị đo (Unit) | Phương pháp đo / Nguồn |
|---|---|---|---|---|
| **MET-001** | Memory Usage (Baseline RSS) | ~180 – 220 | Megabytes (MB) | `memory_meter.py` (RSS memory info) |
| **MET-002** | Memory Usage (Peak RSS) | ~380 – 460 | Megabytes (MB) | Ghi nhận lúc cào và xử lý 2500+ phiếu |
| **MET-003** | CPU Usage (Idle / Active) | 2% / 15% – 35% | Percent (%) | Render Metrics / System monitoring |
| **MET-004** | Startup Time | ~3.5 – 5.0 | Seconds (s) | Thời gian từ lúc khởi chạy container đến khi mở cổng HTTP |
| **MET-005** | Scheduler Cycle Time | 30 | Seconds (s) | Khoảng thời gian tick kiểm tra lịch trình |
| **MET-006** | API Response Time (Health) | < 50 | Milliseconds (ms) | Endpoint `/api/health` |
| **MET-007** | Google API Call Count | ~5 – 12 | Calls / Job Cycle | Số lần gọi Sheets API đọc/ghi mỗi chu kỳ cào |
| **MET-008** | Redis Operations | 2 – 4 | Operations / Tick | Đọc/ghi trạng thái lịch (`control_center:sched`) |
| **MET-009** | GTalk Throughput | 150 – 170 | Messages / Run Batch | Số tin nhắn gửi tối đa đến AM và Trợ lý Vùng mỗi đợt hối |
| **MET-010** | Error Rate (Normal State) | < 0.1 | Percent (%) | Tỷ lệ lỗi HTTP/API dưới điều kiện mạng ổn định |
| **MET-011** | Peak Load Capacity | ~3,000 | Tickets / Job Run | Sức chứa tối đa của RAM 512MB trước khi cần cơ chế PA2 |
