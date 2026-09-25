# -*- coding: utf-8 -*-
"""
tests/test_admin_monitoring.py
Kiểm tra thiết lập 3 tin nhắn giám sát Admin bất biến (3049378, 3026736):
1. Tin 1: Health API & Hạ tầng
2. Tin 2: Bản sao nguyên văn tin AM Top 1 (Link xử lý https://noibo.ghn.vn/ghn-ticket)
3. Tin 3: Bản sao nguyên văn tin Trợ lý Vùng Top 1 (Link xử lý https://noibo.ghn.vn/ghn-ticket)
"""

import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import control_center as cc


class TestAdminMonitoring(unittest.TestCase):
    def setUp(self):
        self.ams_data = {
            "30001": {
                "id": "30001",
                "name": "AM_Top1",
                "total": 50,
                "nz": 30,
                "np": 20,
                "bcs": {
                    "20473000": {"name": "(DNA) An Viễn", "total": 50, "nz": 30, "np": 20}
                }
            },
            "30002": {
                "id": "30002",
                "name": "AM_Top2",
                "total": 20,
                "nz": 10,
                "np": 10,
                "bcs": {
                    "20474000": {"name": "(DNA) Long Thành", "total": 20, "nz": 10, "np": 10}
                }
            }
        }
        self.vungs_data = {
            "DNB": {
                "total": 70,
                "nz": 40,
                "np": 30,
                "ams": {
                    "AM_Top1": {"total": 50, "nz": 30, "np": 20},
                    "AM_Top2": {"total": 20, "nz": 10, "np": 10}
                }
            }
        }
        self.tro_ly_map = {
            "DNB": [{"id": "3049999", "name": "Trợ lý DNB"}]
        }
        self.meta_info = {
            "api_status": "HEALTHY",
            "auth_status": "PASS",
            "latency_ms": 120,
            "total_buu_cuc": 287,
            "total_tickets": 70,
            "failed_bc_count": 0,
            "run_id": "RUN-TEST-01",
            "snapshot_id": "SNAP-TEST-01",
            "filter": "ALL",
            "timestamp": "24/09/2026 18:30:00",
            "revision": "ghn-control-center-v3.3.0"
        }

    def test_admin_ids_configured(self):
        self.assertIn("3049378", cc.ADMIN_IDS)
        self.assertIn("3026736", cc.ADMIN_IDS)
        self.assertEqual(len(cc.ADMIN_IDS), 2)

    def test_send_admin_monitoring_reports_dry_run(self):
        logs = cc.send_admin_monitoring_reports(
            self.ams_data, self.vungs_data, self.tro_ly_map, self.meta_info, dry_run=True
        )
        # 3 tin cho mỗi admin (2 admin = 6 logs)
        self.assertEqual(len(logs), 6)
        
        report_types = [l["report_type"] for l in logs if l["admin_id"] == "3049378"]
        self.assertEqual(report_types, ["HEALTH_API", "TOP_AM", "TOP_TRO_LY"])

    def test_content_of_3_admin_reports(self):
        # 1. Health Report
        health_msg = cc.render_admin_health_report(self.meta_info)
        self.assertIn("BÁO CÁO GIÁM SÁT 1/3", health_msg)
        self.assertIn("RUN-TEST-01", health_msg)
        self.assertIn("HEALTHY", health_msg)

        # 2. Top AM Report
        tpl_am = cc.DEFAULT_TEMPLATES["mau_am_all"]
        am_msg = cc.render_am_message(self.ams_data["30001"], "ALL", tpl_am, self.meta_info["timestamp"])
        self.assertIn("BÁO CÁO PHIẾU TỒN AM AM_Top1", am_msg)
        self.assertIn("An Viễn", am_msg)
        self.assertIn("https://noibo.ghn.vn/ghn-ticket", am_msg)
        self.assertNotIn("ghn-dashboard.pages.dev", am_msg)
        self.assertNotIn("g.ghn.studio", am_msg)

        # 3. Top Trợ lý Vùng Report
        tpl_vung = cc.DEFAULT_TEMPLATES["mau_vung_all"]
        vung_msg = cc.render_vung_message("DNB", self.vungs_data["DNB"], "ALL", tpl_vung, self.meta_info["timestamp"])
        self.assertIn("🚨 [BÁO CÁO PHIẾU TỒN VÙNG DNB]", vung_msg)
        self.assertIn("AM_Top1", vung_msg)
        self.assertIn("https://noibo.ghn.vn/ghn-ticket", vung_msg)
        self.assertIn("https://docs.google.com/spreadsheets/d/1YmFgYyARiFh5vu63My24Sx0ffcy-RsxddEvVWSCgDds", vung_msg)
        self.assertNotIn("g.ghn.studio", vung_msg)


if __name__ == "__main__":
    unittest.main()
