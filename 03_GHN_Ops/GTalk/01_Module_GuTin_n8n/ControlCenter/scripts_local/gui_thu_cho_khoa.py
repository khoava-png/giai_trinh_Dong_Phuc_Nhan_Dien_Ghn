# -*- coding: utf-8 -*-
"""Gửi thử 2 mẫu tin tới 3049378 (Khoa) để kiểm duyệt nội dung:
  1) Mẫu AM  = Lê Đắc Vinh (2041494) — AM đứng TOP bảng
  2) Mẫu Vùng = XBG — Vùng đứng TOP bảng (14 AM, 526 phiếu)
CHỈ gửi tới ADMIN_ID 3049378 — KHÔNG gửi cho người thật.
"""
import sys, os, io, json

BASE = r"E:\GHN\AntiGravity\Khua_Ho_Tro\03_GHN_Ops\GTalk\01_Module_GuTin_n8n\ControlCenter"
sys.path.insert(0, BASE)
os.chdir(BASE)

# stdout utf-8
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import control_center as cc

ADMIN = cc.ADMIN_ID  # 3049378

# ---- 1) Lấy RP mẫu AM Top: Lê Đắc Vinh ----
r1 = cc.action_rp_preview({"ma_nv": "2041494", "flow_mode": "ALL"})
if not r1.get("ok"):
    print("LOI RP AM:", r1); sys.exit(1)
print(f"[1] RP AM Top: {r1['ten']} ({r1['ma_nv']}) — {r1['total']} phiếu")
am_rp = r1["rp"]

# ---- 2) Lấy RP mẫu Vùng Top: XBG ----
r2 = cc.action_vung_preview({"flow_mode": "ALL", "vung_list": ["XBG"]})
if not r2.get("ok") or not r2.get("items"):
    print("LOI RP VUNG:", r2); sys.exit(1)
v = r2["items"][0]
print(f"[2] RP Vùng Top: {v['vung']} — {v['total']} phiếu, {len(v.get('rp',''))} chars")
vung_rp = v["rp"]

# ---- Gửi cả 2 tới 3049378 ----
print("\n== Gửi thử tới 3049378 (Khoa) ==")
res_am = cc._send_via_gtalk(ADMIN, am_rp)
print("[AM]  ", json.dumps(res_am, ensure_ascii=False))
res_vung = cc._send_via_gtalk(ADMIN, vung_rp)
print("[VUNG]", json.dumps(res_vung, ensure_ascii=False))

print("\nDONE")
