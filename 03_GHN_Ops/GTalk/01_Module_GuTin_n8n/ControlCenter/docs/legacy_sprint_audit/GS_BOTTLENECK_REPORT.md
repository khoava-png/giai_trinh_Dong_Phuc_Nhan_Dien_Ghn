# GS BOTTLENECK REPORT — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-GS-003  

## 1. Xếp hạng Điểm nghẽn Hiệu năng (Top Bottlenecks)

| Hạng | Điểm nghẽn (Bottleneck) | Thời lượng | % Tổng chu kỳ | Root Cause | Khả năng fix | Rủi ro | Lợi ích dự kiến |
|---|---|---|---|---|---|---|---|
| **1** | Đăng nhập & Cào web GHN (`login_and_scrape_v2`) | ~35 - 50s | ~80% | Tốc độ phản hồi của web vận hành GHN và số lượng request HTTP phân trang. | Thấp (Phụ thuộc bên thứ 3) | Trung bình | Tối ưu hóa parsing HTML/JSON |
| **2** | Ghi dữ liệu Google Sheets (`write_tab` cho Chi_tiet) | ~1.5 - 3.0s | ~5% | Kích thước payload lớn (~2500 dòng x 14 cột). | Cao | Thấp | Giảm thời gian I/O Sheets |
| **3** | Sinh báo cáo (`ghi_rp_theo_am`, `ghi_rp_theo_vung`) | ~1.0 - 2.0s | ~4% | Xử lý vòng lặp tính toán trên Python dictionary. | Trung bình | Thấp | Tối ưu hóa thuật toán gom nhóm |
