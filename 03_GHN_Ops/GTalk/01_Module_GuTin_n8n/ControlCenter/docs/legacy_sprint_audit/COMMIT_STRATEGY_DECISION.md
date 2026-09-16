# COMMIT STRATEGY DECISION — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-CORE-001  

## 1. Đánh giá và Lựa chọn Phương án Commit (Commit Strategy Decision)

| Tiêu chí Đánh giá | Option A (Direct live + Tail cleanup) | Option B (Batch Update atomic) | Option C (Staging tab & Swap) |
|---|---|---|---|
| **Data Correctness** | Cao | Cao | Cao tuyệt đối |
| **Atomicity** | Trung bình | Khá | Cao |
| **Formula Safety** | An toàn | An toàn | An toàn |
| **Dashboard & GTalk Compatibility** | Cần cơ chế pointer | Cần pointer | Cần pointer |
| **Implementation Risk** | Thấp | Trung bình | Cao (phức tạp hóa nhiều tab) |

## 2. Quyết định Lựa chọn (Selected Strategy)
- Lựa chọn **Option A kết hợp deterministic tail cleanup** (hoặc kết hợp clear chính xác dải ô cũ trước khi ghi đè) để đảm bảo không còn stale rows khi số lượng dòng giảm từ A -> B, đồng thời duy trì RAM Cache ở trạng thái `COMMITTED` atomic trong memory trước khi public ra ngoài consumer.
