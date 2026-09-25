# -*- coding: utf-8 -*-
"""
tests/test_sched_get.py
Kiểm thử endpoint health & schedule status trong Control Center V3.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import control_center as cc


class TestSchedGetRouting(unittest.TestCase):
    def test_health_check_status(self):
        handler = cc.ControlCenterHandler.__new__(cc.ControlCenterHandler)
        handler.path = "/health"
        handler.headers = {}
        handler.wfile = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_GET()
        handler.send_response.assert_called_with(200)


if __name__ == '__main__':
    unittest.main()
