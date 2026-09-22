#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dashboard_sync.py — Build HTML từ cached_data và deploy lên Cloudflare Pages
bằng Direct Upload API 4 bước (không cần wrangler CLI, không cần Node).

Được gọi từ control_center.py sau khi Sheet write thành công:
    raw_data = dsync._build_raw(cached_data)
    cf_deployment_id = dsync._deploy_to_cloudflare(raw_data)

Env vars bắt buộc (Cloud Run):
    CF_ACCOUNT_ID   — Cloudflare Account ID
    CF_API_TOKEN    — Cloudflare API Token (Permission: Pages:Edit)

Env var tùy chọn:
    CF_PROJECT_NAME — tên Pages project (default: ghn-dashboard)
    DASHBOARD_TEMPLATE_PATH — đường dẫn tuyệt đối tới dashboard/index.html

Flow 4 bước (Cloudflare Pages Direct Upload):
    1. POST /accounts/{id}/pages/projects/{name}/upload-token  → JWT
    2. POST /pages/assets/upload                                → upload file (dùng JWT)
    3. POST /pages/assets/upsert-hashes                         → confirm hash (dùng JWT)
    4. POST /accounts/{id}/pages/projects/{name}/deployments    → tạo deployment
"""

import base64
import io
import json
import os
import re
import zipfile
from datetime import datetime

import requests

# ── Constants ──────────────────────────────────────────────────────────────
CF_PROJECT_NAME = os.environ.get("CF_PROJECT_NAME", "ghn-dashboard")
CF_BASE_URL = "https://api.cloudflare.com/client/v4"

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_TEMPLATE = os.path.join(_BASE_DIR, "dashboard", "index.html")
DASHBOARD_TEMPLATE_PATH = os.environ.get("DASHBOARD_TEMPLATE_PATH", _DEFAULT_TEMPLATE)


# ── Cloudflare asset hash (BLAKE3 của base64 bytes + extension) ─────────────

def _cf_asset_hash(data: bytes, rel_path: str) -> str:
    """
    Tính hash Cloudflare Pages theo định dạng wrangler:
        blake3( base64(file_bytes) + extension_without_dot ).hex()[:32]
    Cần package `blake3` (pip install blake3).
    """
    try:
        import blake3 as blake3_lib
        _blake3_available = True
    except ImportError:
        _blake3_available = False

    ext = os.path.splitext(rel_path)[1][1:]  # "index.html" → "html"
    b64_bytes = base64.b64encode(data)        # bytes
    payload = b64_bytes + ext.encode("ascii")

    if _blake3_available:
        import blake3 as blake3_lib
        return blake3_lib.blake3(payload).hexdigest()[:32]
    else:
        # Fallback: SHA-256 (sẽ deploy được nhưng asset có thể 404 — chỉ dùng khi blake3 chưa install)
        import hashlib
        return hashlib.sha256(payload).hexdigest()[:32]


# ── Internal helpers ────────────────────────────────────────────────────────

def _check_credentials():
    """Xác minh CF_ACCOUNT_ID và CF_API_TOKEN hiện diện (không in giá trị)."""
    account_id = os.environ.get("CF_ACCOUNT_ID", "")
    api_token  = os.environ.get("CF_API_TOKEN", "")
    if not account_id:
        raise EnvironmentError("CF_ACCOUNT_ID chưa được set trong environment.")
    if not api_token:
        raise EnvironmentError("CF_API_TOKEN chưa được set trong environment.")
    return account_id, api_token


def _build_raw(cached_data: dict) -> str:
    """
    Nhận cached_data từ control_center (dict với keys: hdr, rows, ci),
    tổng hợp thành object RAW và nhét vào template HTML.

    Trả về: chuỗi HTML hoàn chỉnh đã nhúng data mới.
    """
    hdr  = cached_data.get("hdr", [])
    rows = cached_data.get("rows", [])

    def ci(name):
        return hdr.index(name) if name in hdr else -1

    def g(row, idx):
        if 0 <= idx < len(row) and row[idx] is not None:
            return str(row[idx]).strip()
        return ""

    # Index các cột
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

    # Đọc template HTML
    if not os.path.exists(DASHBOARD_TEMPLATE_PATH):
        raise FileNotFoundError(
            f"Không tìm thấy template dashboard: {DASHBOARD_TEMPLATE_PATH}"
        )
    with open(DASHBOARD_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # Nhét data vào `var RAW = {...};`
    new_json = json.dumps(raw_obj, ensure_ascii=False, separators=(",", ":"))
    pattern  = re.compile(r"var RAW = \{.*?\};", re.DOTALL)
    rendered, count = pattern.subn("var RAW = " + new_json + ";", template, count=1)
    if count == 0:
        raise RuntimeError(
            "Không tìm thấy placeholder 'var RAW = {...};' trong template!"
        )

    return rendered


def _deploy_to_cloudflare(html_content: str) -> str:
    """
    Deploy HTML lên Cloudflare Pages bằng Direct Upload API 4 bước.

    Bước 1: Lấy upload JWT từ upload-token endpoint.
    Bước 2: Upload file index.html (multipart, dùng JWT).
    Bước 3: Upsert-hashes để Cloudflare confirm (dùng JWT).
    Bước 4: Tạo deployment với manifest (dùng API token).

    Trả về: deployment ID thật (string).
    Nếu API lỗi: raise Exception với status + response body để debug (rule #8).
    """
    account_id, api_token = _check_credentials()

    file_data    = html_content.encode("utf-8")
    rel_path     = "index.html"
    asset_hash   = _cf_asset_hash(file_data, rel_path)
    b64_content  = base64.b64encode(file_data).decode("ascii")

    auth_headers = {"Authorization": f"Bearer {api_token}"}

    # ── Bước 1: Lấy upload JWT ─────────────────────────────────────────────
    url_token = f"{CF_BASE_URL}/accounts/{account_id}/pages/projects/{CF_PROJECT_NAME}/upload-token"
    r1 = requests.post(url_token, headers=auth_headers, timeout=30)
    if not r1.ok:
        raise RuntimeError(
            f"CF_UPLOAD_TOKEN_ERROR status={r1.status_code} body={r1.text}"
        )
    r1_json = r1.json()
    if not r1_json.get("success"):
        raise RuntimeError(
            f"CF_UPLOAD_TOKEN_FAILED errors={r1_json.get('errors')} body={r1.text}"
        )
    jwt = r1_json["result"]["jwt"]
    jwt_headers = {"Authorization": f"Bearer {jwt}"}

    # ── Bước 2: Upload file (multipart JSON, không phải form) ──────────────
    # Cloudflare Pages asset upload nhận JSON array của {key, value, metadata.contentType}
    url_upload = f"{CF_BASE_URL}/pages/assets/upload"
    upload_payload = [
        {
            "key":   asset_hash,
            "value": b64_content,
            "metadata": {"contentType": "text/html; charset=UTF-8"},
            "base64": True,
        }
    ]
    r2 = requests.post(
        url_upload,
        headers={**jwt_headers, "Content-Type": "application/json"},
        json=upload_payload,
        timeout=120,
    )
    if not r2.ok:
        raise RuntimeError(
            f"CF_ASSET_UPLOAD_ERROR status={r2.status_code} body={r2.text}"
        )
    r2_json = r2.json()
    if not r2_json.get("success"):
        raise RuntimeError(
            f"CF_ASSET_UPLOAD_FAILED errors={r2_json.get('errors')} body={r2.text}"
        )

    # ── Bước 3: Upsert-hashes (confirm Cloudflare đã nhận) ─────────────────
    url_hashes = f"{CF_BASE_URL}/pages/assets/upsert-hashes"
    r3 = requests.post(
        url_hashes,
        headers={**jwt_headers, "Content-Type": "application/json"},
        json={"hashes": [asset_hash]},
        timeout=30,
    )
    if not r3.ok:
        raise RuntimeError(
            f"CF_UPSERT_HASHES_ERROR status={r3.status_code} body={r3.text}"
        )
    r3_json = r3.json()
    if not r3_json.get("success"):
        raise RuntimeError(
            f"CF_UPSERT_HASHES_FAILED errors={r3_json.get('errors')} body={r3.text}"
        )

    # ── Bước 4: Tạo deployment với manifest ───────────────────────────────
    url_deploy = (
        f"{CF_BASE_URL}/accounts/{account_id}"
        f"/pages/projects/{CF_PROJECT_NAME}/deployments"
    )
    manifest = {f"/{rel_path}": asset_hash}
    r4 = requests.post(
        url_deploy,
        headers={**auth_headers, "Content-Type": "application/json"},
        json={"manifest": manifest},
        timeout=60,
    )
    if not r4.ok:
        raise RuntimeError(
            f"CF_DEPLOY_ERROR status={r4.status_code} body={r4.text}"
        )
    r4_json = r4.json()
    if not r4_json.get("success"):
        raise RuntimeError(
            f"CF_DEPLOY_FAILED errors={r4_json.get('errors')} body={r4.text}"
        )

    deployment_id = r4_json["result"].get("id", "")
    if not deployment_id:
        raise RuntimeError(
            f"CF_DEPLOY_NO_ID result={r4_json.get('result')}"
        )

    return deployment_id
