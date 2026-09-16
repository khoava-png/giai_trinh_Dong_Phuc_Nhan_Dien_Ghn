# MEMORY OBJECT MAP — GHN CONTROL CENTER SPRINT-2

> **Prepared by:** Technical Lead  
> **Date:** 15/09/2026  
> **Version:** v2.0.0-PA2  
> **Order Reference:** ORDER-006 (Sprint-02 Hardening)  

## 1. Phân tích Runtime Memory Lifecycle theo Phase

| Phase | Object lớn / Biến (Large Objects) | Size ước tính | Owner | Lifetime | Last Use | Release Point | Retention Reason / Ghi chú |
|---|---|---|---|---|---|---|---|
| **START** | Runtime base (Python stdlib, modules) | ~180 MB | Process | Vĩnh viễn | Toàn bộ vòng đời | Server stop | Baseline memory footprint |
| **FETCH** | `buu_cuc`, `tickets`, `meta` từ `ctp.login_and_scrape_v2()` | ~15 – 35 MB | `action_scrape()` | Ngắn hạn (~5-10s) | Ghi Sheets & parse | Cuối hàm `action_scrape()` | Raw HTML parse results |
| **PARSE** | `rows_ton`, `rows_ct`, `co_cau_am_map`, `cnt_map` | ~10 – 25 MB | `action_scrape()` | Ngắn hạn (~5-10s) | Ghi Google Sheets | Cuối hàm `action_scrape()` | Dữ liệu thô chuyển đổi bảng |
| **PROCESS** | `_cached_chi_tiet`, `_cached_co_cau_am` | ~20 – 40 MB | Global Cache | 1 giờ (`ts < 3600`) | Gửi tin nhắn AM & Trợ lý Vùng | Hết thời gian cache hoặc clear | Tránh nghẽn I/O đọc lại Google Sheets |
| **WRITE** | Google Sheets API payloads & batch requests | ~5 – 10 MB | Google API Client | Tức thời | HTTP response | Sau khi gọi API | Network transport buffers |
| **NOTIFY** | `am_items`, `vres`, `results` | ~2 – 5 MB | `_sched_cycle()` | Thời gian gửi tin (~1-3 phút) | `_send_via_gtalk` | Cuối chu kỳ scheduler | Danh sách tin nhắn chờ gửi |
| **FINISH** | Trạng thái `_cycle_state`, activity log | < 1 MB | Global State | Vĩnh viễn | UI dashboard / activity log | Giới hạn 100 entries | Lịch sử trạng thái nhẹ |

## 2. Đánh giá `_cached_chi_tiet` & `_cached_co_cau_am`
- **Nơi tạo:** `_set_cached_data()` khi cào xong (`action_scrape()`) hoặc `_read_chi_tiet()` khi cache miss.
- **Nơi đọc:** `_am_summary()`, `_vung_summary()`, và các hàm preview/send tin nhắn.
- **Lifetime:** Giữ trong RAM tối đa 1 giờ hoặc cho đến khi có chu kỳ cào mới ghi đè.
- **Kết luận:** Cần thiết cho việc gửi tin nhắn nhanh chóng ngay sau khi cào mà không phải đọc lại toàn bộ Google Sheets (tránh lỗi API rate limit 429). Tuy nhiên, cần hỗ trợ cơ chế giải phóng rõ ràng hoặc thu gọn cấu trúc dữ liệu nếu Peak RSS vượt ngưỡng an toàn.
