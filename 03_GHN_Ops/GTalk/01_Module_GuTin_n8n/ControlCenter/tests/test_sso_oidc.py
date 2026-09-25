# -*- coding: utf-8 -*-
"""
tests/test_sso_oidc.py
Kiểm thử toàn diện module tích hợp GHN SSO v2 OpenID Connect (sso_oidc.py):
- State / Nonce generation & CSRF verification
- Authorization URL building
- Logout URL building
- Session token creation, HMAC verification, expiration
- Fail-closed khi thiếu env, state sai hoặc session hết hạn
- Token Exchange & UserInfo mock
"""

import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import sso_oidc


class TestSSOOIDC(unittest.TestCase):
    def setUp(self):
        self.orig_env = os.environ.copy()
        os.environ["GHN_SSO_CLIENT_ID"] = "test-client-id-123"
        os.environ["GHN_SSO_CLIENT_SECRET"] = "test-client-secret-xyz"
        os.environ["GHN_SSO_REDIRECT_URI"] = "https://ghn-control-center.run.app/auth/callback"
        os.environ["SESSION_SECRET"] = "test-super-secret-key-32charslong"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_env)

    def test_sso_configured(self):
        self.assertTrue(sso_oidc.is_sso_configured())

        del os.environ["GHN_SSO_CLIENT_ID"]
        self.assertFalse(sso_oidc.is_sso_configured())

    def test_state_and_nonce_lifecycle(self):
        state, nonce = sso_oidc.generate_state_and_nonce()
        self.assertEqual(len(state), 64) # 32 bytes hex
        self.assertEqual(len(nonce), 64)

        # Ký state payload
        token = sso_oidc.sign_state_payload(state, nonce)
        self.assertIn(".", token)

        # Xác thực thành công
        is_valid, ret_nonce = sso_oidc.verify_state_payload(token, state)
        self.assertTrue(is_valid)
        self.assertEqual(ret_nonce, nonce)

        # Xác thực thất bại do state mismatch (CSRF)
        is_valid_fake, _ = sso_oidc.verify_state_payload(token, "fake-state-attempt")
        self.assertFalse(is_valid_fake)

        # Xác thực thất bại do token bị chỉnh sửa
        tampered_token = token[:-4] + "abcd"
        is_valid_tamp, _ = sso_oidc.verify_state_payload(tampered_token, state)
        self.assertFalse(is_valid_tamp)

    def test_build_authorization_url(self):
        state, nonce = "state123", "nonce456"
        url = sso_oidc.build_authorization_url(state, nonce)
        self.assertIn("https://online-gateway.ghn.vn/sso-v2/public-api/oauth2/authorize", url)
        self.assertIn("client_id=test-client-id-123", url)
        self.assertIn("response_type=code", url)
        self.assertIn("state=state123", url)
        self.assertIn("nonce=nonce456", url)

    def test_build_logout_url(self):
        url = sso_oidc.build_logout_url(id_token_hint="sample-id-token", post_logout_redirect_uri="https://ghn-control-center.run.app/")
        self.assertIn("https://online-gateway.ghn.vn/sso-v2/public-api/oauth2/logout", url)
        self.assertIn("id_token_hint=sample-id-token", url)

    def test_session_token_creation_and_verification(self):
        user_info = {
            "sub": "12345",
            "employee_id": 3049378,
            "name": "Nguyễn Văn Khoa",
            "phone_number": "+84901234567",
            "jobtitle_name": "Quản Lý Vận Hành",
            "team_name": "Vận Hành Bưu Cục"
        }

        session_token = sso_oidc.create_session_token(user_info, id_token="jwt.id.token", ttl_seconds=3600)
        self.assertIn(".", session_token)

        # Verify hợp lệ
        decoded = sso_oidc.verify_session_token(session_token)
        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["employee_id"], 3049378)
        self.assertEqual(decoded["name"], "Nguyễn Văn Khoa")
        self.assertEqual(decoded["id_token"], "jwt.id.token")

        # Verify fail khi token hết hạn
        expired_token = sso_oidc.create_session_token(user_info, ttl_seconds=-10)
        self.assertIsNone(sso_oidc.verify_session_token(expired_token))

        # Verify fail khi token bị giả mạo
        tampered = session_token + "x"
        self.assertIsNone(sso_oidc.verify_session_token(tampered))

    @patch("sso_oidc.requests.post")
    def test_exchange_code_for_tokens_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "mock-access-token-123",
            "token_type": "Bearer",
            "expires_in": 604800,
            "id_token": "mock-id-token-xyz"
        }
        mock_post.return_value = mock_resp

        tokens = sso_oidc.exchange_code_for_tokens("test-auth-code")
        self.assertEqual(tokens["access_token"], "mock-access-token-123")
        self.assertEqual(tokens["id_token"], "mock-id-token-xyz")

    @patch("sso_oidc.requests.get")
    def test_fetch_userinfo_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "sub": "3049378",
            "name": "Trần Văn Test",
            "employee_id": 3049378,
            "jobtitle_name": "Developer"
        }
        mock_get.return_value = mock_resp

        uinfo = sso_oidc.fetch_userinfo("mock-bearer-token")
        self.assertEqual(uinfo["name"], "Trần Văn Test")
        self.assertEqual(uinfo["employee_id"], 3049378)


if __name__ == "__main__":
    unittest.main()
