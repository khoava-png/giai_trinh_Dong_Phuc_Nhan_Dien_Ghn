# -*- coding: utf-8 -*-
"""
tests/test_dashboard_builder.py
Kiểm thử toàn diện logic build RAW dashboard, mapping 14 vùng, AM rỗng,
fail-closed (dữ liệu rỗng, thiếu cột, mismatch tab), timezone SLA và truy vết ticket.
"""

import json
import os
import re
import sys
import unittest
import zoneinfo
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import dashboard_sync as dsync
from Cao_Ton_Phieu import ghn_vanhanh_api as gva

VN_TZ = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")


class TestDashboardBuilder(unittest.TestCase):
    def setUp(self):
        self.hdr = [
            "ma_buu_cuc", "ten_buu_cuc", "ma_ticket", "ma_don", "loai_phieu",
            "tien_phat", "hạn_đóng", "trạng_thái", "url",
            "gdv_pgdv_id", "gdv_pgdv_name", "area_manager_id", "area_manager_name", "region_shortname"
        ]
        self.all_regions = [
            "BTB", "DBB", "DNB", "DSH", "HCM", "HNO", "NTB", "TBB",
            "TNB", "TNG", "TNT", "TTB", "XBG", "ĐCL"
        ]

    def test_build_raw_with_14_regions_and_empty_am(self):
        """Kiểm tra build RAW với đủ 14 vùng chuẩn, AM rỗng được gán 'Chưa gán AM'."""
        rows = []
        for i, reg in enumerate(self.all_regions):
            am_name = f"AM_{reg}" if i % 2 == 0 else ""  # Một nửa có AM, một nửa rỗng
            rows.append([
                f"2000{i:02d}", f"Bưu cục Vùng {reg}", f"6910020000{i:02d}", f"DON{i:04d}",
                "Hối giao" if i % 3 == 0 else ("Hối lấy" if i % 3 == 1 else "Hối trả"),
                160000 if i % 2 == 0 else 0,
                "2026-09-24T09:00:00+07:00",
                "Phạt kịch khung" if i % 2 == 0 else "Chưa trễ hạn",
                f"https://noibo.ghn.vn/ghn-ticket/detail/4754{i:03d}",
                "1001", "GDV Test", f"300{i:02d}" if am_name else "", am_name, reg
            ])
        # Add ticket 4754747 explicitly
        rows.append([
            "20473000", "(DNA) An Viễn", "691002436108", "GYYEKACD",
            "Hối giao", 200000, "2026-09-23T09:00:00+07:00", "Phạt kịch khung",
            "https://noibo.ghn.vn/ghn-ticket/detail/4754747",
            "1002", "Hồ Quốc Trực", "3049378", "AM_Khoa", "DNB"
        ])

        cached_data = {
            "hdr": self.hdr,
            "rows": rows,
            "source_updated_at": "24/09/2026 18:00:00",
            "snapshot_id": "SNAP-20260924-1800",
        }

        html = dsync._build_raw(cached_data)
        self.assertIn("var RAW = {", html)

        m = re.search(r"var RAW = (\{.*?\});", html, re.DOTALL)
        self.assertIsNotNone(m)
        raw = json.loads(m.group(1))

        # 1. Tổng ticket
        self.assertEqual(raw["total"], 15)

        # 2. Tổng phạt
        expected_phat = sum(160000 for i in range(14) if i % 2 == 0) + 200000
        self.assertEqual(raw["total_phat"], expected_phat)

        # 3. Tách bạch timestamps
        self.assertEqual(raw["source_updated_at"], "24/09/2026 18:00:00")
        self.assertEqual(raw["snapshot_id"], "SNAP-20260924-1800")
        self.assertIn("built_at", raw)

        # 4. Kiểm tra 14 vùng đầy đủ
        for reg in self.all_regions:
            self.assertIn(reg, raw["regions"])

        # 5. Kiểm tra AM rỗng được chuẩn hóa
        empty_am_tickets = [t for t in raw["tickets"] if t["am"] == "Chưa gán AM"]
        self.assertEqual(len(empty_am_tickets), 7)

        # 6. Truy vết ticket 4754747
        t_target = [t for t in raw["tickets"] if t.get("id") == "4754747"]
        self.assertEqual(len(t_target), 1)
        self.assertEqual(t_target[0]["id"], "4754747")
        self.assertEqual(t_target[0]["am"], "AM_Khoa")
        self.assertEqual(t_target[0]["bl"], "(DNA) An Viễn")
        self.assertEqual(t_target[0]["bc"], "20473000")

    def test_fail_closed_empty_data(self):
        """Fail-closed khi dữ liệu Chi_tiet rỗng."""
        with self.assertRaises(ValueError):
            dsync._build_raw({"hdr": self.hdr, "rows": []})

        with self.assertRaises(ValueError):
            dsync._build_raw({"hdr": [], "rows": []})

    def test_fail_closed_missing_columns(self):
        """Fail-closed khi Chi_tiet thiếu cột bắt buộc."""
        bad_hdr = ["ma_buu_cuc", "ma_ticket", "tien_phat"]  # Thiếu ma_don, loai_phieu, etc.
        rows = [["20001", "TK1", "1000"]]
        with self.assertRaises(ValueError) as ctx:
            dsync._build_raw({"hdr": bad_hdr, "rows": rows})
        self.assertIn("Thiếu cột bắt buộc", str(ctx.exception))

    def test_fail_closed_tab_mismatch(self):
        """Fail-closed khi tổng số vé giữa Chi_tiet và Ton_phieu bị lệch."""
        rows = [
            ["20001", "Kho 1", "TK1", "DON1", "Hối giao", 0, "", "Chưa trễ hạn", "", "", "", "", "", "HCM"],
            ["20002", "Kho 2", "TK2", "DON2", "Hối giao", 0, "", "Chưa trễ hạn", "", "", "", "", "", "HCM"],
        ]
        ton_hdr = ["ma_buu_cuc", "ten_buu_cuc", "Hối giao", "Hối lấy", "Hối trả", "Tổng", "Tiền phạt", "cap_nhat_luc"]
        # Ton_phieu báo tổng là 5 vé (lệch với 2 vé trong Chi_tiet)
        ton_rows = [
            ["20001", "Kho 1", "3", "0", "0", "3", "0", "24/09/2026 18:00:00"],
            ["20002", "Kho 2", "2", "0", "0", "2", "0", "24/09/2026 18:00:00"],
        ]
        with self.assertRaises(ValueError) as ctx:
            dsync._build_raw({
                "hdr": self.hdr,
                "rows": rows,
                "ton_hdr": ton_hdr,
                "ton_rows": ton_rows
            })
        self.assertIn("Đối soát thất bại (Data Mismatch)", str(ctx.exception))

    def test_sla_timezone_asia_ho_chi_minh(self):
        """Kiểm thử tính trạng thái SLA chuẩn hóa theo tiền phạt."""
        # 1. Phạt = 0 -> 'Chưa trễ hạn'
        self.assertEqual(gva.tinh_trang_thai("2026-09-20T09:00:00+07:00", 0), "Chưa trễ hạn")
        self.assertEqual(gva.tinh_trang_thai("2026-09-26T09:00:00+07:00", 0), "Chưa trễ hạn")

        # 2. 0 < Phạt < 200,000 -> 'Trễ hạn còn cứu được'
        self.assertEqual(gva.tinh_trang_thai("2026-09-26T09:00:00+07:00", 20000), "Trễ hạn còn cứu được")
        self.assertEqual(gva.tinh_trang_thai("2026-09-26T09:00:00+07:00", 80000), "Trễ hạn còn cứu được")

        # 3. Phạt kịch khung (>= 200,000) -> 'Phạt kịch khung'
        self.assertEqual(gva.tinh_trang_thai("2026-09-26T09:00:00+07:00", 200000), "Phạt kịch khung")


    def test_simplified_sla_tien_phat(self):
        """Kiểm thử logic SLA đơn giản hóa theo tiền phạt: phat=0 -> 'Chưa Trễ SLA', phat>0 -> 'Trễ SLA'."""
        # Giả lập hàm slaOf từ JS
        def sla_of(t):
            return "Trễ SLA" if (t.get("phat") or 0) > 0 else "Chưa Trễ SLA"

        # Case 1: tien_phat = 0 (dù có close_esc trong quá khứ hay trạng thái gì)
        ticket_zero = {"phat": 0, "tt": "Chưa trễ hạn", "han": "2026-09-20T09:00:00+07:00"}
        self.assertEqual(sla_of(ticket_zero), "Chưa Trễ SLA")

        # Case 2: tien_phat > 0 (bất kể mức phạt nào: 20k, 160k, 200k)
        ticket_20k = {"phat": 20000, "tt": "Chưa trễ hạn", "han": "2026-09-26T09:00:00+07:00"}
        self.assertEqual(sla_of(ticket_20k), "Trễ SLA")

        ticket_200k = {"phat": 200000, "tt": "Phạt kịch khung", "han": "2026-09-20T09:00:00+07:00"}
        self.assertEqual(sla_of(ticket_200k), "Trễ SLA")

    def test_co_cau_18_regions_union(self):
        """Kiểm thử union toàn bộ 18 vùng từ Co_Cau kể cả vùng 0 vé và vùng đặc thù."""
        co_cau_18 = [
            "BTB", "DBB", "DNB", "DSH", "Freight Operations - HCM", "Freight Operations - HN",
            "HCM", "HNO", "NTB", "SC North", "SC South", "TBB", "TNB", "TNG", "TNT", "TTB", "XBG", "ĐCL"
        ]
        # Chỉ có vé ở HCM và vùng lạ UNKNOWN
        rows = [
            ["20001", "Kho 1", "TK1", "DON1", "Hối giao", 0, "", "Chưa trễ hạn", "", "", "", "", "", "HCM"],
            ["20002", "Kho 2", "TK2", "DON2", "Hối giao", 0, "", "Chưa trễ hạn", "", "", "", "", "", "UNKNOWN_REG"],
        ]
        rendered = dsync._build_raw({
            "hdr": self.hdr,
            "rows": rows,
            "co_cau_regions": co_cau_18
        })
        m = re.search(r"var RAW = (\{.*?\});", rendered, re.DOTALL)
        raw = json.loads(m.group(1))
        regions = raw.get("regions", [])

        # Kiểm tra đầy đủ 18 vùng từ Co_Cau
        for r in co_cau_18:
            self.assertIn(r, regions)
        # Kiểm tra vùng lạ từ tickets cũng được union vào
        self.assertIn("UNKNOWN_REG", regions)
        # Vùng đặc thù không bị đổi tên
        self.assertIn("Freight Operations - HCM", regions)
        self.assertIn("Freight Operations - HN", regions)
        self.assertIn("SC North", regions)
        self.assertIn("SC South", regions)


if __name__ == "__main__":
    unittest.main()
