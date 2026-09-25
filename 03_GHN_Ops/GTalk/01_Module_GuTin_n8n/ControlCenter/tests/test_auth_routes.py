# -*- coding: utf-8 -*-
"""
tests/test_auth_routes.py
Kiểm thử tích hợp các endpoint HTTP xác thực và route protection trong control_center.py:
- GET /auth/login -> Redirect 302 đến GHN SSO và Set-Cookie ghn_oidc_state
- GET /auth/callback -> Xử lý code/state, exchange token, Set-Cookie ghn_session
- GET /auth/me -> Trả về user info từ session cookie
- GET /auth/logout -> Xóa cookie session và redirect đến SSO logout
- GET /dashboard -> Redirect 302 đến /auth/login khi chưa đăng nhập và SSO bật
"""

import io
import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import control_center as cc
import sso_oidc


class MockRequest:
    def __init__(self, method="GET", path="/", headers=None):
        self.method = method
        self.path = path
        self.headers = headers or {}
        self.rfile = io.BytesIO()
        self.wfile = io.BytesIO()

    def makefile(self, *args, **kwargs):
        return self.rfile


class TestAuthRoutes(unittest.TestCase):
    def setUp(self):
        self.orig_env = os.environ.copy()
        os.environ["GHN_SSO_CLIENT_ID"] = "test-client-id"
        os.environ["GHN_SSO_CLIENT_SECRET"] = "test-secret"
        os.environ["GHN_SSO_REDIRECT_URI"] = "https://ghn-control-center.run.app/auth/callback"
        os.environ["SESSION_SECRET"] = "secret-session-key-32charslong"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_env)

    def _create_handler(self, path, headers=None):
        handler = cc.ControlCenterHandler.__new__(cc.ControlCenterHandler)
        handler.path = path
        handler.headers = headers or {}
        handler.wfile = io.BytesIO()
        handler.responses = {}
        handler._headers_buffer = []

        # Mock send_response / send_header / end_headers
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        return handler

    def test_auth_login_route(self):
        handler = self._create_handler("/auth/login")
        handler.do_GET()

        handler.send_response.assert_called_with(302)
        # Kiểm tra redirect Location và Set-Cookie
        call_headers = [call[0] for call in handler.send_header.call_args_list]
        header_keys = [h[0] for h in call_headers]
        self.assertIn("Location", header_keys)
        self.assertIn("Set-Cookie", header_keys)

    def test_auth_me_unauthenticated(self):
        handler = self._create_handler("/auth/me")
        handler.do_GET()

        handler.send_response.assert_called_with(200)
        output = handler.wfile.getvalue().decode("utf-8")
        data = json.loads(output)
        self.assertFalse(data["authenticated"])

    def test_auth_me_authenticated(self):
        user_info = {
            "sub": "3049378",
            "employee_id": 3049378,
            "name": "Nguyễn Văn Khoa",
            "jobtitle_name": "Admin"
        }
        token = sso_oidc.create_session_token(user_info)
        handler = self._create_handler("/auth/me", headers={"Cookie": f"ghn_session={token}"})
        handler.do_GET()

        handler.send_response.assert_called_with(200)
        output = handler.wfile.getvalue().decode("utf-8")
        data = json.loads(output)
        self.assertTrue(data["authenticated"])
        self.assertEqual(data["user"]["employee_id"], 3049378)
        self.assertEqual(data["user"]["name"], "Nguyễn Văn Khoa")

    def test_dashboard_route_protection_unauthenticated(self):
        """Khi chưa đăng nhập và SSO được cấu hình, /dashboard phải redirect 302 về /auth/login."""
        handler = self._create_handler("/dashboard")
        handler.do_GET()

        handler.send_response.assert_called_with(302)
        call_headers = [call[0] for call in handler.send_header.call_args_list]
        location_header = [h[1] for h in call_headers if h[0] == "Location"]
        self.assertEqual(location_header[0], "/auth/login")

    def test_dashboard_route_authenticated(self):
        """Khi đã đăng nhập hợp lệ, /dashboard trả về HTTP 200."""
        user_info = {"sub": "123", "employee_id": 3049378, "name": "Khoa"}
        token = sso_oidc.create_session_token(user_info)
        handler = self._create_handler("/dashboard", headers={"Cookie": f"ghn_session={token}"})
        handler.do_GET()

        handler.send_response.assert_called_with(200)


if __name__ == "__main__":
    unittest.main()
