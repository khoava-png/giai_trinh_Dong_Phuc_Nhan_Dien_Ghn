# -*- coding: utf-8 -*-
"""
tests/test_vung_report.py
Kiểm thử chuyên biệt luồng Báo cáo Vùng / Trợ lý Vùng:
- Nguồn template chuẩn Version 3.2.0
- Mapping Vùng -> Trợ lý Vùng
- Danh sách AM và thống kê phiếu (GÁN KHẨN CẤP / GÁN NGAY)
- Link Dashboard Vùng chuẩn https://ghn-dashboard.pages.dev/
- Không còn fallback đoán mò hay file trung gian
"""

import os
import sys
import unittest
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import control_center as cc
from Cao_Ton_Phieu import cao_ton_phieu_api as ctp


class TestVungReport(unittest.TestCase):
    def setUp(self):
        self.vung_info = {
            "total": 25,
            "nz": 15,
            "np": 10,
            "ams": {
                "AM_Tuấn": {"total": 15, "nz": 10, "np": 5},
                "AM_Nam": {"total": 10, "nz": 5, "np": 5}
            }
        }
        self.now_str = "24/09/2026 18:00:00"

    def test_render_vung_message_v3_format(self):
        tpl = cc.DEFAULT_TEMPLATES["mau_vung_all"]
        msg = cc.render_vung_message("DNB", self.vung_info, "ALL", tpl, self.now_str)

        # Kiểm tra tiêu đề và nội dung Vùng
        self.assertIn("🚨 [BÁO CÁO PHIẾU TỒN VÙNG DNB]", msg)
        self.assertIn("Trợ lý/ HRBP vùng *DNB*", msg)
        self.assertIn(self.now_str, msg)

        # Kiểm tra thứ tự AM (sắp xếp AM_Tuấn trước AM_Nam)
        pos_tuan = msg.find("AM_Tuấn")
        pos_nam = msg.find("AM_Nam")
        self.assertGreater(pos_tuan, -1)
        self.assertGreater(pos_nam, -1)
        self.assertLess(pos_tuan, pos_nam)

        # Kiểm tra số liệu phân loại
        self.assertIn("*10* phiếu (GÁN KHẨN CẤP để không bị phạt)", msg)
        self.assertIn("*5* phiếu (GÁN NGAY để không tăng mức phạt)", msg)

        # Kiểm tra link xử lý chuẩn https://noibo.ghn.vn/ghn-ticket và link theo dõi Google Sheets
        self.assertIn("https://noibo.ghn.vn/ghn-ticket", msg)
        self.assertIn("https://docs.google.com/spreadsheets/d/1YmFgYyARiFh5vu63My24Sx0ffcy-RsxddEvVWSCgDds", msg)
        self.assertNotIn("g.ghn.studio", msg)

    def test_build_vung_rp_in_cao_ton_phieu_api(self):
        ams_list = [
            ("30001", "AM_Tuấn", 15, 10, 5),
            ("30002", "AM_Nam", 10, 5, 5)
        ]
        msg = ctp._build_vung_rp("HCM", self.now_str, ams_list)
        self.assertIn("🚨 [BÁO CÁO PHIẾU TỒN VÙNG HCM]", msg)
        self.assertIn("https://noibo.ghn.vn/ghn-ticket", msg)
        self.assertIn("https://docs.google.com/spreadsheets/d/1YmFgYyARiFh5vu63My24Sx0ffcy-RsxddEvVWSCgDds", msg)
        self.assertNotIn("g.ghn.studio", msg)


if __name__ == "__main__":
    unittest.main()
