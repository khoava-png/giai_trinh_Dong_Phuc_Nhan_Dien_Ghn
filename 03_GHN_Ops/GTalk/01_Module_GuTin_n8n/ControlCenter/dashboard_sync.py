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
import zoneinfo
from datetime import datetime

import requests

# Timezone chuẩn Việt Nam
VN_TZ = zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")

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
    Nhận cached_data từ control_center hoặc deploy script (dict: hdr, rows, ton_hdr, ton_rows, bcs, ams),
    tổng hợp RAW object đầy đủ (tickets, bcs, ams, regions, am_list, total_phat, total,
    source_updated_at, snapshot_id, built_at, deployed_at)
    và nhét vào template HTML.
    Có validation fail-closed nếu thiếu cột bắt buộc, dữ liệu rỗng bất thường, hoặc mismatch 2 tab.
    Trả về: chuỗi HTML hoàn chỉnh.
    """
    hdr = cached_data.get("hdr", [])
    rows = cached_data.get("rows", [])

    if not hdr or not rows:
        raise ValueError("Dữ liệu Sheet Chi_tiet rỗng hoặc thiếu header, không thể build dashboard!")

    def ci_alt(names, header_list):
        if isinstance(names, str):
            names = [names]
        norm_names = [n.strip().lower() for n in names]
        # Ưu tiên 1: Exact match tuyệt đối
        for idx, h in enumerate(header_list):
            h_str = str(h).strip().lower()
            for n in norm_names:
                if n == h_str:
                    return idx
        # Ưu tiên 2: Substring nếu không trùng từ ngắn nguy hiểm như 'am' hay 'don'
        for idx, h in enumerate(header_list):
            h_str = str(h).strip().lower()
            for n in norm_names:
                if len(n) >= 4 and n in h_str:
                    return idx
        return -1

    def g(row, i):
        """Lấy giá trị an toàn từ row theo index i."""
        if i < 0 or i >= len(row) or row[i] is None:
            return ""
        return str(row[i]).strip()

    # 1. Map columns cho Chi_tiet & Fail-closed check
    i_bc   = ci_alt(["ma_buu_cuc", "buu_cuc", "ma_bc", "warehouse_id"], hdr)
    i_bl   = ci_alt(["ten_buu_cuc", "ten_bc", "warehouse_name", "buu_cuc_name"], hdr)
    i_tk   = ci_alt(["ma_ticket", "ticket", "number", "ticket_number", "ticket_id"], hdr)
    i_don  = ci_alt(["ma_don", "don", "order_code", "ma_don_hang"], hdr)
    i_loai = ci_alt(["loai_phieu", "loai", "ticket_type"], hdr)
    i_phat = ci_alt(["tien_phat", "phat", "penalty"], hdr)
    i_han  = ci_alt(["hạn_đóng", "han_dong", "han", "close_esc", "han_xu_ly"], hdr)
    i_tt   = ci_alt(["trạng_thái", "trang_thai", "tt", "status"], hdr)
    i_url  = ci_alt(["url", "link", "link_eform", "ticket_url"], hdr)
    i_gdv  = ci_alt(["gdv_pgdv_name", "gdv", "gdv_name"], hdr)
    i_amid = ci_alt(["area_manager_id", "am_id"], hdr)
    i_am   = ci_alt(["area_manager_name", "am", "am_name"], hdr)
    i_vung = ci_alt(["region_shortname", "vung", "region"], hdr)

    missing_cols = []
    if i_bc < 0: missing_cols.append("ma_buu_cuc")
    if i_tk < 0: missing_cols.append("ma_ticket")
    if i_don < 0: missing_cols.append("ma_don")
    if i_loai < 0: missing_cols.append("loai_phieu")
    if i_phat < 0: missing_cols.append("tien_phat")
    if i_han < 0: missing_cols.append("hạn_đóng")
    if i_tt < 0: missing_cols.append("trạng_thái")

    if missing_cols:
        raise ValueError(f"Thiếu cột bắt buộc trong Chi_tiet: {missing_cols}. Header hiện tại: {hdr}")

    tickets    = []
    total_phat = 0
    non_empty_tk = 0
    non_empty_phat = 0

    for row in rows:
        raw_phat = g(row, i_phat)
        cleaned_phat = re.sub(r'[^\d.]', '', raw_phat)
        try:
            phat = int(float(cleaned_phat or 0))
        except Exception:
            phat = 0
        total_phat += phat
        if phat > 0:
            non_empty_phat += 1

        url_val = g(row, i_url)
        tk_val = g(row, i_tk)
        don_val = g(row, i_don)
        
        # Trích xuất URL ID (ví dụ: /detail/4754747 hoặc /form/4754747) nếu có
        url_id = ""
        if url_val:
            m_id = re.search(r'/(?:detail|form)/(\d+)', url_val)
            if m_id:
                url_id = m_id.group(1)
        
        # Nếu tk rỗng nhưng có url_id, giữ url_id làm định danh
        final_tk = tk_val or url_id
        if final_tk:
            non_empty_tk += 1

        bc_val = g(row, i_bc)
        bl_val = g(row, i_bl)
        vung_val = g(row, i_vung)
        am_val = g(row, i_am)
        amid_val = g(row, i_amid)

        # Chuẩn hóa tên bưu cục: không để rỗng, không dùng mã kho thay cho tên
        if not bl_val:
            bl_val = f"Bưu cục {bc_val}" if bc_val else "Bưu cục chưa đặt tên"
        if not am_val:
            am_val = "Chưa gán AM"
        if not vung_val:
            vung_val = "(Chưa gán Vùng)"

        tickets.append({
            "bc":    bc_val,
            "bl":    bl_val,
            "tk":    final_tk,
            "id":    url_id or final_tk,
            "don":   don_val,
            "loai":  g(row, i_loai) or "Hối giao",
            "phat":  phat,
            "han":   g(row, i_han),
            "tt":    g(row, i_tt),
            "url":   url_val,
            "gdv":   g(row, i_gdv),
            "am_id": amid_val,
            "am":    am_val,
            "vung":  vung_val,
        })

    # Validation: nếu có trên 10 dòng mà toàn bộ tk và don đều rỗng
    if len(rows) > 10 and non_empty_tk == 0:
        raise ValueError("Dữ liệu Chi_tiet bất thường: 100% mã ticket/đơn rỗng. Chặn build để bảo vệ dashboard!")

    # 2. Xử lý bảng bưu cục (bcs) & Đối soát với Ton_phieu
    ton_hdr  = cached_data.get("ton_hdr", [])
    ton_rows = cached_data.get("ton_rows", [])
    bcs = cached_data.get("bcs", [])
    source_updated_at = cached_data.get("source_updated_at") or cached_data.get("updated_at") or ""

    if ton_hdr and ton_rows:
        tb_bc   = ci_alt(["ma_buu_cuc", "buu_cuc", "ma_bc"], ton_hdr)
        tb_bl   = ci_alt(["ten_buu_cuc", "ten_bc"], ton_hdr)
        tb_hg   = ci_alt(["Hối giao", "hoi_giao", "hg"], ton_hdr)
        tb_hl   = ci_alt(["Hối lấy", "hoi_lay", "hl"], ton_hdr)
        tb_ht   = ci_alt(["Hối trả", "hoi_tra", "ht"], ton_hdr)
        tb_tong = ci_alt(["Tổng", "tong", "total"], ton_hdr)
        tb_phat = ci_alt(["Tiền phạt", "tien_phat", "phat", "penalty"], ton_hdr)
        tb_cap  = ci_alt(["cap_nhat_luc", "cap_nhat"], ton_hdr)

        missing_ton = []
        if tb_bc < 0: missing_ton.append("ma_buu_cuc")
        if tb_tong < 0: missing_ton.append("Tổng")
        if tb_phat < 0: missing_ton.append("Tiền phạt")
        if missing_ton:
            raise ValueError(f"Thiếu cột bắt buộc trong Ton_phieu: {missing_ton}. Header: {ton_hdr}")

        ton_bcs = []
        ton_total_sum = 0
        ton_phat_sum = 0

        for r in ton_rows:
            def num_cell(idx):
                val = g(r, idx)
                c_val = re.sub(r'[^\d.]', '', val)
                try:
                    return int(float(c_val or 0))
                except Exception:
                    return 0

            bc_code = g(r, tb_bc)
            if not bc_code:
                continue
            t_tong = num_cell(tb_tong)
            t_phat = num_cell(tb_phat)
            ton_total_sum += t_tong
            ton_phat_sum += t_phat

            cap_val = g(r, tb_cap)
            if cap_val and not source_updated_at:
                source_updated_at = cap_val

            ton_bcs.append({
                "bc":       bc_code,
                "bl":       g(r, tb_bl) or f"Bưu cục {bc_code}",
                "hg":       num_cell(tb_hg),
                "hl":       num_cell(tb_hl),
                "ht":       num_cell(tb_ht),
                "tong":     t_tong,
                "phat":     t_phat,
                "cap_nhat": cap_val,
            })

        # Đối soát fail-closed: nếu cả Ton_phieu và Chi_tiet đều có dữ liệu nhưng tổng lệch nhau
        if len(rows) > 0 and len(ton_rows) > 0:
            if ton_total_sum != len(tickets):
                raise ValueError(
                    f"Đối soát thất bại (Data Mismatch): Chi_tiet có {len(tickets)} vé nhưng Ton_phieu tổng là {ton_total_sum} vé! Chặn build."
                )

        if not bcs:
            bcs = ton_bcs

    # Nếu không có Ton_phieu hoặc Ton_phieu rỗng, tự động tổng hợp từ tickets để bcs KHÔNG BAO GIỜ bị rỗng
    now_vn = datetime.now(VN_TZ)
    now_str = now_vn.strftime("%d/%m/%Y %H:%M:%S")

    if not bcs and tickets:
        bc_dict = {}
        for t in tickets:
            b_code = t["bc"]
            if not b_code:
                continue
            if b_code not in bc_dict:
                bc_dict[b_code] = {
                    "bc": b_code,
                    "bl": t["bl"] or f"Bưu cục {b_code}",
                    "hg": 0, "hl": 0, "ht": 0, "tong": 0, "phat": 0,
                    "cap_nhat": source_updated_at or now_str
                }
            l_str = str(t["loai"]).lower()
            if "giao" in l_str:
                bc_dict[b_code]["hg"] += 1
            elif "lấy" in l_str or "lay" in l_str:
                bc_dict[b_code]["hl"] += 1
            elif "trả" in l_str or "tra" in l_str:
                bc_dict[b_code]["ht"] += 1
            bc_dict[b_code]["tong"] += 1
            bc_dict[b_code]["phat"] += t["phat"]
        bcs = list(bc_dict.values())

    # 3. Xử lý danh sách AMs
    ams = cached_data.get("ams", [])
    if not ams and tickets:
        am_dict = {}
        for t in tickets:
            a_name = t["am"]
            if not a_name:
                continue
            if a_name not in am_dict:
                am_dict[a_name] = {
                    "ma": t["am_id"] or "",
                    "ten": a_name,
                    "tong": 0,
                    "gap": 0,
                    "phat": 0
                }
            am_dict[a_name]["tong"] += 1
            am_dict[a_name]["phat"] += t["phat"]
            if t["phat"] > 0 or "phạt" in str(t["tt"]).lower() or "trễ" in str(t["tt"]).lower():
                am_dict[a_name]["gap"] += 1
        ams = list(am_dict.values())

    # UNION: Co_Cau regions (18 vùng) + Chi_tiet regions + (Chưa gán Vùng)
    co_cau_regions = cached_data.get("co_cau_regions", [])
    if not co_cau_regions:
        co_cau_rows = cached_data.get("co_cau_rows", [])
        co_cau_hdr = cached_data.get("co_cau_hdr", [])
        if co_cau_rows and co_cau_hdr:
            i_cc_reg = ci_alt(["region_shortname", "vung", "region"], co_cau_hdr)
            if i_cc_reg >= 0:
                co_cau_regions = [r[i_cc_reg].strip() for r in co_cau_rows if len(r) > i_cc_reg and r[i_cc_reg].strip()]

    all_reg_set = set(co_cau_regions) | {t["vung"] for t in tickets if t.get("vung")}
    regions = sorted(all_reg_set)
    am_list = sorted({t["am"]   for t in tickets if t["am"]})

    snapshot_id = cached_data.get("snapshot_id", "N/A")
    built_at = now_str
    deployed_at = cached_data.get("deployed_at", "")

    raw_obj = {
        "updated":           built_at,
        "source_updated_at": source_updated_at,
        "snapshot_id":       snapshot_id,
        "built_at":          built_at,
        "deployed_at":       deployed_at,
        "tickets":           tickets,
        "bcs":               bcs,
        "ams":               ams,
        "total":             len(tickets),
        "total_phat":        total_phat,
        "regions":           regions,
        "am_list":           am_list,
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
