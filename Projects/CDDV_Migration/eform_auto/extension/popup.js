// ═══════════════════════════════════════════════════════════
// popup.js — EForm Auto Fill v4.1
// Popup Ở LẠI, hiện tiến trình realtime. Không tự đóng.
// ═══════════════════════════════════════════════════════════

function log(msg, type = '') {
  const el = document.getElementById('log');
  const time = new Date().toLocaleTimeString();
  el.innerHTML = `<span class="${type}">${time} ${msg}</span>\n` + el.innerHTML;
}

function setStatus(msg) {
  document.getElementById('status').textContent = msg;
}

// ── Nhận PROGRESS từ content.js (qua background forward) ──
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'PROGRESS') {
    const cls = { success: 'ok', error: 'err', warn: 'warn' }[msg.level] || '';
    log(msg.msg, cls);
  }
  if (msg.type === 'FILL_STATUS') {
    setStatus(msg.text);
    if (msg.done) {
      log('🎉 Hoàn tất!', 'ok');
      document.getElementById('btnGo').disabled = false;
      document.getElementById('btnGo').textContent = '⚡ Điền';
    }
  }
});

// ── Bấm Điền ──
document.getElementById('btnGo').addEventListener('click', async () => {
  const btn = document.getElementById('btnGo');
  const rowNum = parseInt(document.getElementById('rowInput').value);

  if (!rowNum || rowNum < 12) {
    log('⚠️ Nhập số dòng ≥ 12!', 'err');
    return;
  }

  btn.disabled = true;
  btn.textContent = '⏳ Đang xử lý...';
  setStatus('Đang đọc dòng ' + rowNum + '...');
  log('⚡ Gửi lệnh điền dòng ' + rowNum + '...');

  try {
    const result = await new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(
        { type: 'START_FILL', row: rowNum },
        (response) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
            return;
          }
          resolve(response);
        }
      );
    });

    if (result && result.success) {
      log('✅ ' + (result.message || 'Đang xử lý...'), 'ok');
      setStatus(result.message || 'Đang fill...');
      // Popup Ở LẠI — không đóng, không reset button
      // Button sẽ được enable lại khi nhận FILL_STATUS done
    } else {
      log('❌ ' + (result?.error || 'Lỗi không xác định'), 'err');
      setStatus('Lỗi!');
      btn.disabled = false;
      btn.textContent = '⚡ Điền';
    }
  } catch (e) {
    log('❌ ' + e.message, 'err');
    setStatus('Lỗi!');
    btn.disabled = false;
    btn.textContent = '⚡ Điền';
  }
});

// Enter = click
document.getElementById('rowInput').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') document.getElementById('btnGo').click();
});
