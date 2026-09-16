# -*- coding: utf-8 -*-
"""test_md_gtalk.py — Gửi 1 tin test Markdown cho chính Khoa (3049378) để xem
định dạng (in đậm / ngắt dòng / emoji) có hiển thị trên GTalk hay không.
Chạy:  python test_md_gtalk.py"""
import os, sys, io
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "GuTin_Theo_MaNV"))
import gtalk_bulk_sender as gs

MA_NV = "3049378"   # Vũ Anh Khoa (người test chuẩn)

md = """**ĐÂY LÀ DÒNG IN ĐẬM** dùng dấu sao kép.
*Dòng này in nghiêng* dùng 1 sao.
- Bullet 1
- Bullet 2
🔴 Có emoji đỏ
🟠 Có emoji cam
1. Số 1
2. Số 2
Dòng bình thường với
ngắt dòng xuống tiếp."""

def main():
    oa_id, oa_token = gs._load_oa_token()
    print(f"[i] OA {oa_id} | test 1 tin MD -> {MA_NV} (chính anh Khoa xem kết quả trên GTalk)")
    ch, err = gs.create_direct_channel(oa_id, oa_token, MA_NV)
    if not ch:
        print("Kênh lỗi:", err)
        return
    msg, serr, _cid = gs.send_message(oa_id, oa_token, ch, md)
    if msg:
        print("✅ Đã gửi, msg_id:", msg)
        print("\n--- NỘI DUNG ĐÃ GỬI (nguyên văn) ---")
        print(md)
    else:
        print("❌ Lỗi gửi:", serr)

if __name__ == "__main__":
    main()