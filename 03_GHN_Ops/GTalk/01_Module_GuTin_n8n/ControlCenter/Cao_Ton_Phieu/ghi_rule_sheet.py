# -*- coding: utf-8 -*-
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from collections import Counter

KEY = r'E:\GHN\AntiGravity\Khua_Ho_Tro\05_TaiLieu_Note\Keys\ghn-sheets-automation-90e4499c91ec.json'
SID = '15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg'
c = service_account.Credentials.from_service_account_file(KEY, scopes=[
    'https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive'])
s = build('sheets', 'v4', credentials=c)


def rd(tab):
    r = s.spreadsheets().values().get(spreadsheetId=SID, range="'%s'!A:ZZ" % tab).execute()
    v = r.get('values', [])
    return (v[0], v[1:]) if v else ([], [])


name = 'Ghi_chu_CapNhat'
meta = s.spreadsheets().get(spreadsheetId=SID).execute()
titles = [sh['properties']['title'] for sh in meta['sheets']]
if name not in titles:
    s.spreadsheets().batchUpdate(spreadsheetId=SID, body={
        'requests': [{'addSheet': {'properties': {'title': name}}}]}).execute()
    print('tao tab', name)
else:
    print('tab ton tai')

ch, cr = rd('Chi_tiet')
iv = ch.index('region_shortname')
tbc = Counter(cr[i][iv] if len(cr[i]) > iv else '(none)' for i in range(len(cr)))

rows = [
    ['GHN - RULE & DATA CAP NHAT DASHBOARD TON PHIEU', ''],
    ['', ''],
    ['QUY TAC CAP NHAT (RULE)', ''],
    ['1. FILE GOC', 'Dashboard_CloudForest - Copy.html (giu hero + chu ky anh chinh)'],
    ['2. NGUON DATA', 'Google Sheet nay (tab Chi_tiet / Ton_phieu / RP_theo_AM / Co_Cau)'],
    ['3. CHU KY CAP NHAT', 'Moi gio, luc HH:20 (cron Dashboard CloudForest realtime)'],
    ['4. QUY TRINH', 'Doc sheet -> thay phan data (var RAW) trong file goc -> deploy Cloudflare'],
    ['5. KHONG build de', 'Script chi doi data, KHONG dung layout/hero/chu ky'],
    ['6. LINK WEB', 'https://ghn-dashboard.pages.dev'],
    ['', ''],
    ['TONG HOP DATA (CHECK ~17:00 24/08/2026)', ''],
    ['Tong phieu ton', '2259'],
    ['Tong BC co phieu', '303'],
    ['Thoi diem data', '24/08/2026 17:00:20 (KHONG cu)'],
    ['So mien/vung', '14'],
    ['', ''],
    ['PHIEU THEO MIEN', ''],
]
for k, v in sorted(tbc.items()):
    rows.append(['  %s' % k, '%d phieu' % v])

s.spreadsheets().values().update(spreadsheetId=SID, range=name + '!A1',
                                  valueInputOption='RAW', body={'values': rows}).execute()
print('DA GHI', len(rows), 'dong vao tab', name)