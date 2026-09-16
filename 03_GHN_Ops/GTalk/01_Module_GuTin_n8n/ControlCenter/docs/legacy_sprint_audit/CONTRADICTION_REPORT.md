# CONTRADICTION REPORT — SYSTEM TRUTH AUDIT

> **Order Reference:** ORDER-SYS-TRUTH-001  
> **Date:** 15/09/2026  

## 1. Kiểm đếm Mâu thuẫn Giữa các Báo cáo Trước (Contradiction Audit)
- **Mâu thuẫn 1 (Formula Reality):** Các báo cáo ban đầu ghi nhận "không dùng formula", nhưng khảo sát sâu code quản lý bảng tính `cao_ton_phieu.py` đã phát hiện cơ chế chèn công thức `ARRAYFORMULA` tự động vào ô `I2` của tab `Chi_tiet`. $\rightarrow$ *Đã chuẩn hóa lại trong báo cáo thực tế.*
- **Mâu thuẫn 2 (Số lượng gc.collect):** Một số tài liệu nháp mô tả "gc.collect()" rải rác, nhưng source code thực tế chỉ bổ sung đúng 2 điểm (sau scrape và sau cycle). $\rightarrow$ *Đã chuẩn hóa lại.*
- **Mâu thuẫn 3 (Production Verification):** Tuyên bố "Production Verified" trước đó chỉ dựa trên giả lập local cho đến khi thực hiện thành công bài test 30 request qua HTTP layer thực tế. $\rightarrow$ *Đã bổ sung ma trận bằng chứng thực tế.*
