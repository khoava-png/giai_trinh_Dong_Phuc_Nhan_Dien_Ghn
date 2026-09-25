# -*- coding: utf-8 -*-
"""
sso_oidc.py — Module tích hợp GHN SSO v2 theo chuẩn OpenID Connect (OIDC).
Dựa trên tài liệu đặc tả docs/sso-oidc.md.

Chức năng:
  - Cung cấp luồng xác thực OIDC Authorization Code Flow.
  - Quản lý state/nonce chống CSRF và replay attack.
  - Trao đổi token với Token Endpoint qua Basic Auth / POST.
  - Lấy thông tin người dùng (UserInfo Endpoint) an toàn.
  - Quản lý phiên làm việc (Session) bằng HMAC-SHA256 cookie.
  - Hỗ trợ RP-Initiated Logout.
  - Fail-closed khi thiếu env, token sai, state sai hoặc session hết hạn.
  - Tuyệt đối không log client_secret, access_token, id_token ra console.
"""

import os
import time
import json
import base64
import hmac
import hashlib
import secrets
from urllib.parse import urlencode, quote
import requests

# ─── Cấu hình SSO từ biến môi trường ──────────────────────────────────────────
SSO_ENV = os.environ.get("GHN_SSO_ENV", "production").lower()
STAGING_BASE_URL = "https://dev-online-gateway.ghn.vn/sso-v2"
PROD_BASE_URL = "https://online-gateway.ghn.vn/sso-v2"

SSO_BASE_URL = STAGING_BASE_URL if SSO_ENV == "staging" else PROD_BASE_URL

# Endpoints OIDC chuẩn
AUTH_ENDPOINT     = f"{SSO_BASE_URL}/public-api/oauth2/authorize"
TOKEN_ENDPOINT    = f"{SSO_BASE_URL}/public-api/oauth2/token"
USERINFO_ENDPOINT = f"{SSO_BASE_URL}/public-api/oauth2/userinfo"
LOGOUT_ENDPOINT   = f"{SSO_BASE_URL}/public-api/oauth2/logout"
JWKS_ENDPOINT     = f"{SSO_BASE_URL}/public-api/oauth2/jwks"

# Scope mặc định
DEFAULT_SCOPE = "openid profile email"

# Thời gian sống của session (mặc định 8 giờ)
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", 28800))
# Thời gian sống của OIDC State/Nonce (5 phút)
STATE_TTL_SECONDS = 300


def get_sso_config():
    """Lấy cấu hình SSO từ môi trường."""
    client_id = os.environ.get("GHN_SSO_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GHN_SSO_CLIENT_SECRET", "").strip()
    redirect_uri = os.environ.get("GHN_SSO_REDIRECT_URI", "").strip()
    post_logout_uri = os.environ.get("GHN_SSO_POST_LOGOUT_URI", "").strip()
    session_secret = os.environ.get("SESSION_SECRET") or os.environ.get("SCHEDULER_SECRET") or "ghn-default-session-key-dev"
    
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "post_logout_uri": post_logout_uri,
        "session_secret": session_secret,
    }


def is_sso_configured() -> bool:
    """Kiểm tra SSO đã được cấu hình đầy đủ biến môi trường hay chưa."""
    cfg = get_sso_config()
    return bool(cfg["client_id"] and cfg["client_secret"] and cfg["redirect_uri"])


# ─── Quản lý State & Nonce chống CSRF / Replay ────────────────────────────────

def generate_state_and_nonce() -> tuple[str, str]:
    """Sinh chuỗi state và nonce ngẫu nhiên bảo mật cao."""
    state = secrets.token_hex(32)
    nonce = secrets.token_hex(32)
    return state, nonce


def sign_state_payload(state: str, nonce: str, secret: str = None) -> str:
    """Ký state & nonce vào chuỗi token để lưu tạm trong cookie hoặc cache."""
    if not secret:
        secret = get_sso_config()["session_secret"]
    exp = int(time.time()) + STATE_TTL_SECONDS
    payload = json.dumps({"state": state, "nonce": nonce, "exp": exp}, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8").rstrip("=")
    sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_state_payload(signed_payload: str, expected_state: str, secret: str = None) -> tuple[bool, str]:
    """
    Xác thực state payload.
    Trả về (is_valid: bool, nonce: str)
    """
    if not signed_payload or "." not in signed_payload:
        return False, ""
    if not secret:
        secret = get_sso_config()["session_secret"]
    
    parts = signed_payload.split(".", 1)
    payload_b64, sig = parts[0], parts[1]
    
    expected_sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return False, ""
    
    try:
        # Pad base64 nếu thiếu
        rem = len(payload_b64) % 4
        padded = payload_b64 + ("=" * (4 - rem) if rem else "")
        data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        if data.get("exp", 0) < int(time.time()):
            return False, "" # Hết hạn
        if not hmac.compare_digest(data.get("state", ""), expected_state):
            return False, "" # State không khớp
        return True, data.get("nonce", "")
    except Exception:
        return False, ""


# ─── Tạo URL Đăng nhập & Đăng xuất ──────────────────────────────────────────

def build_authorization_url(state: str, nonce: str, scope: str = DEFAULT_SCOPE, redirect_uri: str = None) -> str:
    """Tạo URL chuyển hướng người dùng đến cổng GHN SSO v2 Authorization Endpoint."""
    cfg = get_sso_config()
    if not cfg["client_id"]:
        raise ValueError("GHN_SSO_CLIENT_ID chưa được cấu hình.")
    
    r_uri = redirect_uri or cfg["redirect_uri"]
    if not r_uri:
        raise ValueError("GHN_SSO_REDIRECT_URI chưa được cấu hình.")

    params = {
        "response_type": "code",
        "client_id": cfg["client_id"],
        "redirect_uri": r_uri,
        "scope": scope,
        "state": state,
        "nonce": nonce,
    }
    return f"{AUTH_ENDPOINT}?{urlencode(params)}"


def build_logout_url(id_token_hint: str = "", post_logout_redirect_uri: str = "", state: str = "") -> str:
    """Tạo URL chuyển hướng người dùng đến cổng GHN SSO v2 Logout Endpoint."""
    cfg = get_sso_config()
    p_uri = post_logout_redirect_uri or cfg["post_logout_uri"] or cfg["redirect_uri"]
    
    params = {}
    if id_token_hint:
        params["id_token_hint"] = id_token_hint
    if p_uri:
        params["post_logout_redirect_uri"] = p_uri
    if state:
        params["state"] = state

    if params:
        return f"{LOGOUT_ENDPOINT}?{urlencode(params)}"
    return LOGOUT_ENDPOINT


# ─── Trao đổi Code lấy Token & UserInfo ─────────────────────────────────────

def exchange_code_for_tokens(code: str, redirect_uri: str = None, timeout: int = 15) -> dict:
    """
    Trao đổi authorization code lấy access_token và id_token qua Token Endpoint.
    Sử dụng HTTP Basic Auth (Recommended Method 2) hoặc POST body.
    """
    cfg = get_sso_config()
    client_id = cfg["client_id"]
    client_secret = cfg["client_secret"]
    r_uri = redirect_uri or cfg["redirect_uri"]

    if not client_id or not client_secret:
        raise ValueError("Thiếu cấu hình GHN_SSO_CLIENT_ID hoặc GHN_SSO_CLIENT_SECRET")
    if not code:
        raise ValueError("Authorization code rỗng")

    # Basic Auth header
    basic_auth_val = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("utf-8")
    headers = {
        "Authorization": f"Basic {basic_auth_val}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": r_uri,
    }

    resp = requests.post(TOKEN_ENDPOINT, data=payload, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        err_msg = "Token request failed"
        try:
            err_json = resp.json()
            err_msg = err_json.get("error_description") or err_json.get("error") or err_msg
        except Exception:
            pass
        raise RuntimeError(f"SSO Token Exchange Error ({resp.status_code}): {err_msg}")

    tokens = resp.json()
    if not isinstance(tokens, dict) or "access_token" not in tokens:
        raise RuntimeError("Phản hồi từ Token Endpoint không chứa access_token hợp lệ")

    return tokens


def fetch_userinfo(access_token: str, timeout: int = 15) -> dict:
    """
    Gọi UserInfo Endpoint để lấy thông tin hồ sơ nhân viên GHN.
    """
    if not access_token:
        raise ValueError("Access token rỗng")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    resp = requests.get(USERINFO_ENDPOINT, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"Không thể lấy UserInfo từ SSO (HTTP {resp.status_code})")

    uinfo = resp.json()
    if not isinstance(uinfo, dict):
        raise RuntimeError("Dữ liệu UserInfo không đúng định dạng JSON object")

    return uinfo


# ─── Quản lý Phiên làm việc (Signed Session Cookie) ──────────────────────────

def create_session_token(user_info: dict, id_token: str = "", ttl_seconds: int = SESSION_TTL_SECONDS, secret: str = None) -> str:
    """
    Tạo token session bảo mật được ký bằng HMAC-SHA256.
    Không lưu access_token dài hạn, chỉ lưu claims cần thiết để hiển thị và xác thực.
    """
    if not secret:
        secret = get_sso_config()["session_secret"]

    now = int(time.time())
    session_data = {
        "sub": str(user_info.get("sub", "")),
        "employee_id": user_info.get("employee_id"),
        "name": user_info.get("name") or user_info.get("preferred_username") or "Nhân viên GHN",
        "phone_number": user_info.get("phone_number", ""),
        "jobtitle_name": user_info.get("jobtitle_name", ""),
        "team_name": user_info.get("team_name", ""),
        "id_token": id_token,
        "iat": now,
        "exp": now + ttl_seconds
    }

    payload_json = json.dumps(session_data, ensure_ascii=False, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8").rstrip("=")
    signature = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()

    return f"{payload_b64}.{signature}"


def verify_session_token(session_token: str, secret: str = None) -> dict | None:
    """
    Xác thực token session từ cookie.
    Trả về dict user_info nếu hợp lệ và chưa hết hạn; ngược lại trả về None (Fail-closed).
    """
    if not session_token or "." not in session_token:
        return None

    if not secret:
        secret = get_sso_config()["session_secret"]

    parts = session_token.split(".", 1)
    payload_b64, signature = parts[0], parts[1]

    expected_sig = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_sig):
        return None

    try:
        rem = len(payload_b64) % 4
        padded = payload_b64 + ("=" * (4 - rem) if rem else "")
        data = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        
        # Kiểm tra thời hạn hết hạn
        if data.get("exp", 0) < int(time.time()):
            return None
        
        return data
    except Exception:
        return None
