#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dashboard_sync.py — Build HTML từ cached_data và deploy lên Cloudflare Pages
bằng Direct Upload API 4 bước (không cần wrangler CLI, không cần Node).

Official API docs:
  Step 1: GET  /accounts/{id}/pages/projects/{name}/upload-token   → JWT
  Step 2: POST /pages/assets/upload                                 → upload file (JWT auth)
  Step 3: POST /pages/assets/upsert-hashes                          → xác nhận hash (JWT auth)
  Step 4: POST /accounts/{id}/pages/projects/{name}/deployments     → tạo deployment (API Token, multipart/form-data)

Ref: https://developers.cloudflare.com/api/resources/pages/

Env vars bắt buộc (Cloud Run):
    CF_ACCOUNT_ID   — Cloudflare Account ID
    CF_API_TOKEN    — Cloudflare API Token (Permission: Pages Write)

Env var tùy chọn:
    CF_PROJECT_NAME         — tên Pages project (default: ghn-dashboard)
    DASHBOARD_TEMPLATE_PATH — đường dẫn tuyệt đối tới dashboard/index.html
"""

import base64
import json
import os
import re
from datetime import datetime

import requests

# ── Constants ──────────────────────────────────────────────────────────────
CF_PROJECT_NAME = os.environ.get("CF_PROJECT_NAME", "ghn-dashboard")
CF_BASE_URL = "https://api.cloudflare.com/client/v4"

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_TEMPLATE = os.path.join(_BASE_DIR, "dashboard", "index.html")
DASHBOARD_TEMPLATE_PATH = os.environ.get("DASHBOARD_TEMPLATE_PATH", _DEFAULT_TEMPLATE)


# ── Asset hash (BLAKE3 — wrangler-compatible) ───────────────────────────────

def _cf_asset_hash(data: bytes, rel_path: str) -> str:
    """
    Tính hash Cloudflare Pages theo wrangler hashFile():
        blake3( base64(file_bytes) + extension_without_dot ).hex()[:32]

    Requires: blake3>=0.4.1 (trong requirements.txt)
    """
    import blake3 as _blake3

    ext = os.path.splitext(rel_path)[1][1:]   # "index.html" → "html"
    b64_bytes = base64.b64encode(data)          # bytes
    payload = b64_bytes + ext.encode("ascii")
    return _blake3.blake3(payload).hexdigest()[:32]


# ── Credential check ────────────────────────────────────────────────────────

def _check_credentials():
    """Xác minh CF_ACCOUNT_ID và CF_API_TOKEN hiện diện (không in giá trị)."""
    account_id = os.environ.get("CF_ACCOUNT_ID", "")
    api_token  = os.environ.get("CF_API_TOKEN", "")
    if not account_id:
        raise EnvironmentError("CF_ACCOUNT_ID chưa được set trong environment.")
    if not api_token:
        raise EnvironmentError("CF_API_TOKEN chưa được set trong environment.")
    return account_id, api_token


# ── Build HTML ──────────────────────────────────────────────────────────────

def _build_raw(cached_data: dict) -> str:
    """
    Nhận cached_data từ control_center (dict: hdr, rows, ci),
    tổng hợp RAW object và nhét vào template HTML.
    Trả về: chuỗi HTML hoàn chỉnh.
    """
    hdr  = cached_data.get("hdr", [])
    rows = cached_data.get("rows", [])

    def ci(name):
        return hdr.index(name) if name in hdr else -1

    def g(row, idx):
        if 0 <= idx < len(row) and row[idx] is not None:
            return str(row[idx]).strip()
        return ""

    i_bc   = ci("ma_buu_cuc")
    i_bl   = ci("ten_buu_cuc")
    i_tk   = ci("ma_ticket")
    i_don  = ci("ma_don")
    i_loai = ci("loai_phieu")
    i_phat = ci("tien_phat")
    i_han  = ci("hạn_đóng")
    i_tt   = ci("trạng_thái")
    i_url  = ci("url")
    i_gdv  = ci("gdv_pgdv_name")
    i_amid = ci("area_manager_id")
    i_am   = ci("area_manager_name")
    i_vung = ci("region_shortname")

    tickets    = []
    total_phat = 0
    for row in rows:
        try:
            phat = int(float(g(row, i_phat) or 0))
        except Exception:
            phat = 0
        total_phat += phat
        tickets.append({
            "bc":    g(row, i_bc),
            "bl":    g(row, i_bl),
            "tk":    g(row, i_tk),
            "don":   g(row, i_don),
            "loai":  g(row, i_loai) or "Hối giao",
            "phat":  phat,
            "han":   g(row, i_han),
            "tt":    g(row, i_tt),
            "url":   g(row, i_url),
            "gdv":   g(row, i_gdv),
            "am_id": g(row, i_amid),
            "am":    g(row, i_am),
            "vung":  g(row, i_vung),
        })

    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    regions = sorted({t["vung"] for t in tickets if t["vung"]})
    am_list = sorted({t["am"]   for t in tickets if t["am"]})

    raw_obj = {
        "updated":    now_str,
        "tickets":    tickets,
        "bcs":        [],
        "ams":        [],
        "total":      len(tickets),
        "total_phat": total_phat,
        "regions":    regions,
        "am_list":    am_list,
    }

    if not os.path.exists(DASHBOARD_TEMPLATE_PATH):
        raise FileNotFoundError(
            f"Không tìm thấy template dashboard: {DASHBOARD_TEMPLATE_PATH}"
        )
    with open(DASHBOARD_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    new_json = json.dumps(raw_obj, ensure_ascii=False, separators=(",", ":"))
    pattern  = re.compile(r"var RAW = \{.*?\};", re.DOTALL)
    rendered, count = pattern.subn("var RAW = " + new_json + ";", template, count=1)
    if count == 0:
        raise RuntimeError(
            "Không tìm thấy placeholder 'var RAW = {...};' trong template!"
        )

    return rendered


# ── Deploy to Cloudflare Pages (Direct Upload, 4 steps) ────────────────────

def _deploy_to_cloudflare(html_content: str) -> str:
    """
    Deploy HTML lên Cloudflare Pages bằng Direct Upload API 4 bước.

    Official flow:
      Step 1 (GET)  upload-token endpoint → JWT
      Step 2 (POST) /pages/assets/upload  → upload file bytes (JWT auth, JSON body)
      Step 3 (POST) /pages/assets/upsert-hashes → xác nhận (JWT auth, JSON body)
      Step 4 (POST) /accounts/{id}/pages/projects/{name}/deployments
                    → multipart/form-data, manifest = JSON string (API Token auth)

    Trả về: deployment ID thật.
    Lỗi API: raise RuntimeError với full status + body (không nuốt lỗi).
    """
    account_id, api_token = _check_credentials()

    file_data   = html_content.encode("utf-8")
    rel_path    = "index.html"
    asset_hash  = _cf_asset_hash(file_data, rel_path)
    b64_content = base64.b64encode(file_data).decode("ascii")

    api_auth = {"Authorization": f"Bearer {api_token}"}

    # ── Step 1: GET upload-token → JWT ─────────────────────────────────────
    # Official: GET /accounts/{id}/pages/projects/{name}/upload-token
    r1 = requests.get(
        f"{CF_BASE_URL}/accounts/{account_id}/pages/projects/{CF_PROJECT_NAME}/upload-token",
        headers=api_auth,
        timeout=30,
    )
    if not r1.ok:
        raise RuntimeError(
            f"CF_UPLOAD_TOKEN_ERROR status={r1.status_code} body={r1.text}"
        )
    r1j = r1.json()
    if not r1j.get("success"):
        raise RuntimeError(
            f"CF_UPLOAD_TOKEN_FAILED errors={r1j.get('errors')} body={r1.text}"
        )
    jwt = r1j["result"]["jwt"]
    jwt_auth = {"Authorization": f"Bearer {jwt}"}

    # ── Step 2: POST /pages/assets/upload → upload file ───────────────────
    # Official: no /accounts/ prefix; JSON array; each item: key, value, base64, metadata
    r2 = requests.post(
        f"{CF_BASE_URL}/pages/assets/upload",
        headers={**jwt_auth, "Content-Type": "application/json"},
        json=[{
            "key":      asset_hash,
            "value":    b64_content,
            "base64":   True,
            "metadata": {"contentType": "text/html; charset=UTF-8"},
        }],
        timeout=120,
    )
    if not r2.ok:
        raise RuntimeError(
            f"CF_ASSET_UPLOAD_ERROR status={r2.status_code} body={r2.text}"
        )
    r2j = r2.json()
    if not r2j.get("success"):
        raise RuntimeError(
            f"CF_ASSET_UPLOAD_FAILED errors={r2j.get('errors')} body={r2.text}"
        )

    # ── Step 3: POST /pages/assets/upsert-hashes → xác nhận hash ──────────
    r3 = requests.post(
        f"{CF_BASE_URL}/pages/assets/upsert-hashes",
        headers={**jwt_auth, "Content-Type": "application/json"},
        json={"hashes": [asset_hash]},
        timeout=30,
    )
    if not r3.ok:
        raise RuntimeError(
            f"CF_UPSERT_HASHES_ERROR status={r3.status_code} body={r3.text}"
        )
    r3j = r3.json()
    if not r3j.get("success"):
        raise RuntimeError(
            f"CF_UPSERT_HASHES_FAILED errors={r3j.get('errors')} body={r3.text}"
        )

    # ── Step 4: POST deployments — multipart/form-data ────────────────────
    # manifest: JSON string mapping file paths → hashes
    # PATH phải có leading slash: "/index.html" (confirmed working)
    # Dùng files= để requests gửi đúng multipart/form-data
    manifest_str = json.dumps({"/index.html": asset_hash})
    r4 = requests.post(
        f"{CF_BASE_URL}/accounts/{account_id}/pages/projects/{CF_PROJECT_NAME}/deployments",
        headers=api_auth,
        files={"manifest": (None, manifest_str, "text/plain")},
        timeout=60,
    )
    if not r4.ok:
        raise RuntimeError(
            f"CF_DEPLOY_ERROR status={r4.status_code} body={r4.text}"
        )
    r4j = r4.json()
    if not r4j.get("success"):
        raise RuntimeError(
            f"CF_DEPLOY_FAILED errors={r4j.get('errors')} body={r4.text}"
        )

    deployment_id = r4j["result"].get("id", "")
    if not deployment_id:
        raise RuntimeError(
            f"CF_DEPLOY_NO_ID result={r4j.get('result')}"
        )

    return deployment_id
