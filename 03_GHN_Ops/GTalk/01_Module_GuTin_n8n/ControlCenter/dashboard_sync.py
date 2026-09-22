#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dashboard_sync.py — Build HTML từ cached_data và deploy lên Cloudflare Pages
bằng Direct Upload API (không cần wrangler CLI).

Được gọi từ control_center.py sau khi Sheet write thành công:
    raw_data = dsync._build_raw(cached_data)
    cf_deployment_id = dsync._deploy_to_cloudflare(raw_data)

Env vars bắt buộc (Cloud Run):
    CF_ACCOUNT_ID   — Cloudflare Account ID
    CF_API_TOKEN    — Cloudflare API Token (Permission: Pages:Edit)

Env var tùy chọn:
    CF_PROJECT_NAME — tên Pages project (default: ghn-dashboard)
    DASHBOARD_TEMPLATE_PATH — đường dẫn tuyệt đối tới dashboard/index.html
                              (default: <thư mục app>/dashboard/index.html)
"""

import io
import json
import os
import re
import zipfile
from datetime import datetime

import requests

# ── Constants ──────────────────────────────────────────────────────────────
CF_PROJECT_NAME = os.environ.get("CF_PROJECT_NAME", "ghn-dashboard")

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_TEMPLATE = os.path.join(_BASE_DIR, "dashboard", "index.html")
DASHBOARD_TEMPLATE_PATH = os.environ.get("DASHBOARD_TEMPLATE_PATH", _DEFAULT_TEMPLATE)


# ── Internal helpers ────────────────────────────────────────────────────────

def _check_credentials():
    """Xác minh CF_ACCOUNT_ID và CF_API_TOKEN hiện diện (không in giá trị)."""
    account_id = os.environ.get("CF_ACCOUNT_ID", "")
    api_token = os.environ.get("CF_API_TOKEN", "")
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
    hdr = cached_data.get("hdr", [])
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

    tickets = []
    total_phat = 0
    for row in rows:
        try:
            phat = int(float(g(row, i_phat) or 0))
        except Exception:
            phat = 0
        total_phat += phat
        bc   = g(row, i_bc)
        vung = g(row, i_vung)
        am   = g(row, i_am)
        tickets.append({
            "bc":    bc,
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
            "am":    am,
            "vung":  vung,
        })

    now_str  = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    regions  = sorted({t["vung"] for t in tickets if t["vung"]})
    am_list  = sorted({t["am"]   for t in tickets if t["am"]})

    raw_obj = {
        "updated":    now_str,
        "tickets":    tickets,
        "bcs":        [],   # bưu cục summary — không có trong cached_data, bỏ qua
        "ams":        [],   # AM summary      — không có trong cached_data, bỏ qua
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
    Deploy HTML lên Cloudflare Pages bằng Direct Upload API.

    Endpoint:
      POST /accounts/{account_id}/pages/projects/{project_name}/deployments

    Payload: multipart/form-data với file manifest.json + index.html trong zip

    Trả về: deployment ID thật (string).
    Nếu API lỗi: raise Exception với status + response body để debug.
    """
    account_id, api_token = _check_credentials()

    # Bước 1: Tạo upload session (lấy upload_url + jwt)
    # Cloudflare Pages Direct Upload dùng form-data multipart với "file" là zip
    url_deploy = (
        f"https://api.cloudflare.com/client/v4"
        f"/accounts/{account_id}/pages/projects/{CF_PROJECT_NAME}/deployments"
    )
    headers = {
        "Authorization": f"Bearer {api_token}",
    }

    # Đóng gói index.html thành zip (Cloudflare Pages Direct Upload yêu cầu zip)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", html_content.encode("utf-8"))
    zip_bytes = zip_buffer.getvalue()

    # Multipart: field "file" = zip archive
    files_payload = {
        "file": ("pages.zip", zip_bytes, "application/zip"),
    }

    resp = requests.post(
        url_deploy,
        headers=headers,
        files=files_payload,
        timeout=120,
    )

    # Giữ nguyên HTTP status + body để debug nếu lỗi (rule #8)
    if not resp.ok:
        raise RuntimeError(
            f"CLOUDFLARE_API_ERROR status={resp.status_code} body={resp.text}"
        )

    resp_json = resp.json()
    if not resp_json.get("success"):
        errors = resp_json.get("errors", [])
        raise RuntimeError(
            f"CLOUDFLARE_API_FAILED success=False errors={errors} body={resp.text}"
        )

    deployment_id = resp_json["result"].get("id", "")
    if not deployment_id:
        raise RuntimeError(
            f"CLOUDFLARE_API_NO_ID result={resp_json.get('result')}"
        )

    return deployment_id
