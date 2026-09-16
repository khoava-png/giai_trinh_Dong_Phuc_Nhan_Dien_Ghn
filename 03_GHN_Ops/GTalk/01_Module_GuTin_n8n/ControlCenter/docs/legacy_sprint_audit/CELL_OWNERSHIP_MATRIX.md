# CELL OWNERSHIP MATRIX — GHN CONTROL CENTER

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-CORE-001 (Generation-Based Data Commit Architecture)  

## 1. Ma trận Sở Hữu Cell/Range Tab `Chi_tiet` (Cell Ownership Matrix)

Tab `Chi_tiet` có cấu trúc 14 cột (từ A đến N). Dưới đây là phân định sở hữu chi tiết từng cột:

| Cột | Header Name | Meaning / Business Value | Writer | Reader | RAW / DERIVED | Formula Owner | Python Owner | Dashboard Dependency | GTalk Dependency |
|---|---|---|---|---|---|---|---|---|---|
| **A** | `ma_buu_cuc` | Mã bưu cục | Python (`cao_ton_phieu.py`) | Backend / Dashboard | RAW | None | `cao_ton_phieu.py` | Yes | Yes |
| **B** | `ten_buu_cuc` | Tên bưu cục | Python | Backend / Dashboard | RAW | None | `cao_ton_phieu.py` | Yes | Yes |
| **C** | `ma_ticket` | Mã ticket hối | Python | Backend / Dashboard | RAW | None | `cao_ton_phieu.py` | Yes | Yes |
| **D** | `ma_don` | Mã đơn hàng | Python | Backend / Dashboard | RAW | None | `cao_ton_phieu.py` | Yes | Yes |
| **E** | `loai_phieu` | Loại hối (giao/lấy/trả) | Python | Backend / Dashboard | RAW | None | `cao_ton_phieu.py` | Yes | Yes |
| **F** | `tien_phat` | Tiền phạt | Python | Backend / Dashboard | RAW | None | `cao_ton_phieu.py` | Yes | Yes |
| **G** | `hạn_đóng` | Hạn đóng ticket | Python | Backend / Dashboard | RAW | None | `cao_ton_phieu.py` | Yes | Yes |
| **H** | `trạng_thái` | Trạng thái xử lý | Python | Backend / Dashboard | RAW | None | `cao_ton_phieu.py` | Yes | Yes |
| **I** | `url` | Đường dẫn ticket | Python | Backend / Dashboard | RAW | None | `cao_ton_phieu.py` | Yes | No |
| **J** | `gdv_pgdv_id` | Mã GDV/PGDV | Python | Backend | RAW | None | `cao_ton_phieu.py` | No | No |
| **K** | `gdv_pgdv_name` | Tên GDV/PGDV | Python | Backend | RAW | None | `cao_ton_phieu.py` | No | No |
| **L** | `area_manager_id` | Mã Quản lý Khu vực | Python | Backend / Dashboard | RAW | None | `cao_ton_phieu.py` | Yes | Yes |
| **M** | `area_manager_name` | Tên Quản lý Khu vực | Python | Backend / Dashboard | RAW | None | `cao_ton_phieu.py` | Yes | Yes |
| **N** | `region_shortname` | Tên Vùng ngắn gọn | Python | Backend / Dashboard | RAW | None | `cao_ton_phieu.py` | Yes | Yes |

## 2. Giải quyết Mâu thuẫn Schema (Chi_tiet Columns & Formula)
- **A. Python thực tế ghi bao nhiêu cột?** Python ghi toàn bộ 14 cột (từ A đến N) trực tiếp từ dữ liệu cào web kết hợp bảng tra cứu `Co_Cau`.
- **B. I:M thuộc Python hay Formula?** Khảo sát thực tế trong `cao_ton_phieu.py` cho thấy hàm `rebuild_formulas()` không còn được gọi trong luồng cào chính; toàn bộ các cột J đến N (gdv, am, region) đều được ánh xạ bằng code Python (`cc = co_cau.get(...)`) và ghi trực tiếp vào các cột tương ứng. Do đó, I:M hiện hoàn toàn thuộc sở hữu của Python Backend (RAW values), không có ARRAYFORMULA ngoại lai ghi đè.
- **C. values.update(A1...) có overwrite I:M không?** Có, vì lệnh `values.update` ghi đè toàn bộ dải từ `A1` trở đi theo ma trận giá trị truyền vào từ Python.
- **D. rebuild_formulas() có overwrite dữ liệu vừa ghi không?** `rebuild_formulas()` hiện không kích hoạt trong luồng chuẩn.
- **E. Header/schema hiện tại đúng hay tài liệu cũ sai?** Schema 14 cột (A-N) trong code `cao_ton_phieu.py` là chuẩn xác và là Source of Truth hiện tại.
