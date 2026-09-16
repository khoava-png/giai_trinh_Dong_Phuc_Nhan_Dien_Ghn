# STALE TAIL RAW TEST — ORDER-ROOT-003

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-ROOT-003  

## 1. Kết quả Kiểm tra Stale Tail (Part C)
- **Kịch bản:** Generation A (2500 rows) chuyển sang Generation B (2000 rows).
- **Hiện tượng trước khi fix:** Do `values.update` chỉ ghi đè đến dòng 2000, các dòng từ 2001 đến 2500 của dataset A vẫn tồn tại.
- **Yêu cầu (Part D - Minimum Correct Snapshot Replace):** Cần bổ sung logic đo lường `old_last_row` và `new_last_row`, tiến hành clear phần đuôi thừa (`new_last_row + 1` đến `old_last_row`) trên các cột Python sở hữu (A-N) mà không làm ảnh hưởng đến dải công thức độc lập hay tab khác.
