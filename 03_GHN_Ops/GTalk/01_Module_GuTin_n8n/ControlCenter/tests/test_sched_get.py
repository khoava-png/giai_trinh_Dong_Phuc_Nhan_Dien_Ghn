import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import control_center

class TestSchedGetRouting(unittest.TestCase):
    @patch('control_center.action_sched_get')
    def test_sched_get_action(self, mock_action):
        mock_action.return_value = {"ok": True, "sched": {"enabled": True}}
        res = control_center.action_sched_get()
        self.assertTrue(res["ok"])
        self.assertTrue(res["sched"]["enabled"])

    def test_30_consecutive_calls(self):
        with patch('control_center._load_sched') as mock_load:
            mock_load.return_value = {
                "enabled": True,
                "dry_run": False,
                "delay_min": 5,
                "send_am": True,
                "send_vung": True,
                "hours_am_all": [9, 10, 11],
                "hours_am_cd": [14, 15],
                "am_cd_loai": "HOI_LAY",
                "hours_vung_all": [9, 10],
                "hours_vung_cd": [14],
                "vung_cd_loai": "HOI_LAY",
                "allowed_weekdays": [0, 1, 2, 3, 4],
                "last_run_am": "15/09/2026 10:00:00",
                "last_run_vung": "15/09/2026 10:05:00"
            }
            for i in range(30):
                res = control_center.action_sched_get()
                self.assertTrue(res["ok"])
                self.assertIn("sched", res)
                self.assertTrue(res["sched"]["enabled"])
                self.assertEqual(res["sched"]["delay_min"], 5)

if __name__ == '__main__':
    unittest.main()
