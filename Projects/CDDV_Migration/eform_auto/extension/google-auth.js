// ═══════════════════════════════════════════════════════════
// google-auth.js — Service Account JWT → OAuth2 Access Token
// Pure JS, 0 dependency. Chạy trong Chrome Extension MV3 service worker.
// Sheet ID: 1OLTtcxnRBqCUEUM158R5sztx4MAaKkiJkiQKIJzEthE
// ═══════════════════════════════════════════════════════════

const SA = {
  client_email: "ghn-sheet-bot@ghn-sheets-automation.iam.gserviceaccount.com",
  token_uri: "https://oauth2.googleapis.com/token",
  private_key_pem: `-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQC5B65C+opjtIue
fu8D2xBmQjsUaCv6JapZuZFeQHm562AppkVBS3xlhbEo1PfXlYzIqiL/5CC7YsOq
D3jKuRS4B2pCsOrWylS4e7kMQ+Sxjy6vAHK7lUX5AZ8o1xClGPhfi0MBGGrLveME
DBvaG2kWgz1KYzbs9+12KDBBvuPIMhuMixmLqu5Eze0HYh45JILTxH7v9WnPBjVv
RYmlIBDjjlsNodeVYV/GHgQZta7nbc0Qh2gKktcDblcKRh0HDi/yx1XzgFfsIDi7
RLP3tTfrmDHtU+YFwhv6JiMJd8JdazndpqsT41IYJ3i1ZjJe7DxBKiSNTRKvpGX0
2xxky/UNAgMBAAECggEAGmyx4ufj/rRIokSPfvX4pBn+VP5BlZJufyzkyVic6cPn
MluIFXih1d/feqzbjmLRvdCqefALCqfiuLVH82+2OUf50XdxumYf7k7hERLbJM6F
hMGkIQ0C9rpYEB2Sx3lG82IwmgXyLpG6S5gtHBuBCRGKHccIj5QiyhaYObN41Vyw
LKpkaKRYsYXVCID1Epepc5rWE0zJzBAoWJ6Z50tjuXbuxwR4Qj0POFxJ5I8ySvne
LujHbPb7cAqgSzuPICdu0v7Pni6RYzR/l16gQd1Ww+ob/85LaDtwsrDprj1Nj7pH
hXEyLI3ajvNRQ+ZqkXPySUNTWmhp1/HjS+VIE6AGYwKBgQDuf8172EjUL0R3TZr2
QnXCsEAGutpsgB3v8Q9pVLXUdCH3NlFotzZCby8yPpPE5fagEFM6bxI9NfEvvSq3
DmbJcSf0OqJC0BMo6QBbUEUiC6d2Te2DrtH1eiw4jmDv0K8gTjKJ8kGmNFWqsvMp
/cuuu2DrC0su2FoH63qvSVWkRwKBgQDGm3YFOgeSVxzGjhVk43mlSRrRZfIqBNpy
kzSYCUPD30LO+tLoX3c8bVx3b08TeurNMXcx3h7SCZtJP65nqUpyFAGV6ORwm5wT
o/tMs5fWflas/eEGMLtO9qOtz2bcCj5GO848rnq0olsv9uNhqNfp0Nmo8lyU/Uak
EDnm3ePqCwKBgQCARssNjlH1lgq8JEhxpWNTOJrnQ77RVsNDV6OTYpV91IykO1nj
+Y68grKe0puF7q4Mf1tUdYMY2xeDNrpvxNYyCKOVr6ewSdvUSCYB9xWH7z692cIi
7ndNEc4RCTtIITTgKk7ydRMsQr/E1QUGk9Pmgi/pm6RvaLxbwCK3frkKZwKBgQCD
x5FWxHtTqYOJZ6tgZuNHPauSt38oTFIZ5fzmyHbzV4d/yMP6taVrLfFFulCQz2VO
w3ygVQ7ENOWZg6yYUab47LdkncQ9x7KXAZ5z9VJRW0DtxgLyVZFjQpm2cUCBzjYl
6fbdIrR+eJ/iwoF7QkoJda+Gv1GY9jlSEQYqXp6kowKBgQDC9csLk1GloKfF018J
d50mg6TELk87R2PTKlEWpToren1IRKwR0cMzrEWSSMWHXug3gM1mOhm7NMWLwvgY
J8fwWOMwGC5lVUutbF2f2AonQ4z/t08xG6uoUQfz4qYimX+wNc0LwiYNWu8oXOWX
PJtJjFVf1oYcImZMC6LmD1pHOg==
-----END PRIVATE KEY-----`,
  sheet_id: "1OLTtcxnRBqCUEUM158R5sztx4MAaKkiJkiQKIJzEthE",
  sheet_name: "Camera"
};

// ── Token cache ──
let _cachedToken = null;
let _tokenExpiry = 0;

// ── Helpers ──
function base64url(buf) {
  return btoa(String.fromCharCode(...new Uint8Array(buf)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function textToBuf(str) {
  return new TextEncoder().encode(str);
}

// ── Parse PEM → CryptoKey (RS256) ──
async function importPrivateKey(pem) {
  const pemBody = pem
    .replace('-----BEGIN PRIVATE KEY-----', '')
    .replace('-----END PRIVATE KEY-----', '')
    .replace(/\s/g, '');
  const binary = Uint8Array.from(atob(pemBody), c => c.charCodeAt(0));
  return crypto.subtle.importKey(
    'pkcs8', binary,
    { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
    false, ['sign']
  );
}

// ── Tạo JWT + exchange lấy access_token ──
async function getAccessToken() {
  // Dùng cache nếu còn hạn (> 5 phút)
  if (_cachedToken && Date.now() < _tokenExpiry - 5 * 60 * 1000) {
    return _cachedToken;
  }

  const key = await importPrivateKey(SA.private_key_pem);

  // JWT Header
  const header = { alg: 'RS256', typ: 'JWT' };
  const headerB64 = base64url(textToBuf(JSON.stringify(header)));

  // JWT Claim
  const now = Math.floor(Date.now() / 1000);
  const claim = {
    iss: SA.client_email,
    scope: 'https://www.googleapis.com/auth/spreadsheets',
    aud: SA.token_uri,
    exp: now + 3600,
    iat: now
  };
  const claimB64 = base64url(textToBuf(JSON.stringify(claim)));

  // Sign
  const sigInput = textToBuf(headerB64 + '.' + claimB64);
  const sig = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', key, sigInput);
  const sigB64 = base64url(sig);
  const jwt = headerB64 + '.' + claimB64 + '.' + sigB64;

  // Exchange JWT for access_token
  const resp = await fetch(SA.token_uri, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: 'grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=' + encodeURIComponent(jwt)
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error('OAuth2 token exchange failed: ' + resp.status + ' ' + errText.substring(0, 200));
  }

  const data = await resp.json();
  _cachedToken = data.access_token;
  _tokenExpiry = Date.now() + (data.expires_in || 3600) * 1000;
  console.log('[Auth] Token refreshed, expires in', data.expires_in, 's');
  return _cachedToken;
}

// ── Gọi Sheets API v4 ──
async function sheetsApi(method, path, body) {
  const token = await getAccessToken();
  const url = 'https://sheets.googleapis.com/v4/spreadsheets/' + SA.sheet_id + '/' + path;
  const opts = {
    method: method,
    headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' }
  };
  if (body) opts.body = JSON.stringify(body);
  const resp = await fetch(url, opts);
  const text = await resp.text();
  try {
    const json = JSON.parse(text);
    if (!resp.ok) throw new Error('Sheets API error: ' + (json.error?.message || text.substring(0, 200)));
    return json;
  } catch (e) {
    if (!resp.ok) throw new Error('Sheets API ' + resp.status + ': ' + text.substring(0, 200));
    return text;
  }
}

// ── Đọc 1 dòng từ sheet Camera ──
async function getRow(rowNum) {
  // A{row}:AJ{row} = cột 1-36 (0-indexed: A=0, AJ=35)
  const range = `'${SA.sheet_name}'!A${rowNum}:AJ${rowNum}`;
  const data = await sheetsApi('GET', 'values/' + encodeURIComponent(range));
  const values = data.values?.[0] || [];

  // Build row object
  const row = {
    row: rowNum,
    stt: values[0] || '',
    vung: values[1] || '',
    buuCuc: values[2] || '',
    maBC: values[3] || '',
    idNguoiCham: values[35] || '', // AJ
    ad: values[29] || '',           // AD
    groups: []
  };

  // Parse 4 groups: N-P, R-T, V-X, Z-AB
  const groupDefs = [
    { baiCham: 13, tieuChi: 14, anh: 15 },
    { baiCham: 17, tieuChi: 18, anh: 19 },
    { baiCham: 21, tieuChi: 22, anh: 23 },
    { baiCham: 25, tieuChi: 26, anh: 27 }
  ];

  for (let g = 0; g < groupDefs.length; g++) {
    const gd = groupDefs[g];
    const baiCham = (values[gd.baiCham] || '').trim();
    const tieuChi = (values[gd.tieuChi] || '').trim();
    const anh = (values[gd.anh] || '').trim();
    if (tieuChi) {
      const classified = classifyMauCham(baiCham, tieuChi);
      row.groups.push({
        group: g + 1,
        baiCham, tieuChi, anh,
        mauCham: classified.mauCham,
        radioGroup: classified.radioGroup
      });
    }
  }

  return { success: true, data: row };
}

// ── Ghi Done vào cột AD ──
async function markDone(rowNum) {
  const range = `'${SA.sheet_name}'!AD${rowNum}`;
  await sheetsApi('PUT', 'values/' + encodeURIComponent(range) + '?valueInputOption=RAW', {
    values: [['Done']]
  });
  return { success: true };
}

// ── Ghi log lỗi vào cột AI ──
async function logError(rowNum, errorMsg) {
  // Đọc giá trị hiện tại trước
  const range = `'${SA.sheet_name}'!AI${rowNum}`;
  try {
    const data = await sheetsApi('GET', 'values/' + encodeURIComponent(range));
    const existing = data.values?.[0]?.[0] || '';
    const now = new Date().toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
    const newMsg = '[' + now + '] ' + errorMsg;
    const finalMsg = existing ? existing + '\n' + newMsg : newMsg;
    await sheetsApi('PUT', 'values/' + encodeURIComponent(range) + '?valueInputOption=RAW', {
      values: [[finalMsg]]
    });
  } catch (e) {
    console.error('[Sheets] logError failed:', e.message);
  }
  return { success: true };
}

// ── classifyMauCham (clone từ Code.gs) ──
function classifyMauCham(baiChamText, tieuChiText) {
  const baiCham = (baiChamText || '').toLowerCase();
  const tieuChi = (tieuChiText || '').toLowerCase();

  function stripVN(s) {
    return s
      .replace(/[àáảãạăằắẳẵặâầấẩẫậ]/g, 'a')
      .replace(/[èéẻẽẹêềếểễệ]/g, 'e')
      .replace(/[ìíỉĩị]/g, 'i')
      .replace(/[òóỏõọôồốổỗộơờớởỡợ]/g, 'o')
      .replace(/[ùúủũụưừứửữự]/g, 'u')
      .replace(/[ỳýỷỹỵ]/g, 'y')
      .replace(/đ/g, 'd');
  }

  const bc = stripVN(baiCham);

  if (bc && /nhan dien thuong hieu|nhan dien|thuong hieu|hanh vi/i.test(bc)) {
    return { mauCham: 'NHẬN_DIỆN_THƯƠNG_HIỆU_VÀ_HÀNH_VI_BƯU_CỤC', radioGroup: 'nhan_dien_th' };
  }
  if (bc && /tieu chuan/i.test(bc)) {
    return { mauCham: 'TIÊU_CHUẨN_BƯU_CỤC', radioGroup: 'tieu_chuan_bc' };
  }

  const combined = bc + ' ' + stripVN(tieuChi);
  if (/nhan dien|thuong hieu|hanh vi|phong cach|an nhau|co bac|an uong|hut thuoc|choi game|xem phim|on ao|mat trat tu|di dung ngoi|ke gac|dam dap|coi tran|tu che/.test(combined)) {
    return { mauCham: 'NHẬN_DIỆN_THƯƠNG_HIỆU_VÀ_HÀNH_VI_BƯU_CỤC', radioGroup: 'nhan_dien_th' };
  }
  if (/tieu chuan|camera|dong phuc|tac phong|ve sinh|an toan|bang hieu|bien dinh vi|mat tien|san nha|bang thong bao|he thong dien/.test(combined)) {
    return { mauCham: 'TIÊU_CHUẨN_BƯU_CỤC', radioGroup: 'tieu_chuan_bc' };
  }

  return { mauCham: null, radioGroup: null };
}
