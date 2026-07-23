// ═══════════════════════════════════════════════════════════
// background.js — EForm Auto Fill v5.0
// Bypass GAS → gọi thẳng Google Sheets API qua Service Account
// Tốc độ: 1-2s/request thay vì 20-60s timeout.
// ═══════════════════════════════════════════════════════════

importScripts('google-auth.js');

const EFORM_URL = "https://noibo.ghn.vn/eform/form/create?flowId=69d371b7af6a207f9ca7ce12";

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ── START_FILL: Gọi Sheets API trực tiếp → mở tab per group ──
async function handleStartFill(rowNum) {
  console.log(`[EForm BG v5] START_FILL dòng ${rowNum} (Sheets API)`);
  const t0 = Date.now();

  let data;
  try {
    data = await getRow(rowNum);
  } catch (e) {
    console.error('[EForm BG] Sheets API lỗi:', e.message);
    return { success: false, error: e.message };
  }

  const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
  if (!data || !data.success) {
    return { success: false, error: data?.error || 'Sheets API không phản hồi' };
  }

  const rowData = data.data;
  if (!rowData.groups || rowData.groups.length === 0) {
    return { success: false, error: `Dòng ${rowNum} không có tiêu chí nào!` };
  }

  const totalGroups = rowData.groups.length;
  console.log(`[EForm BG v5] Dòng ${rowNum}: ${rowData.buuCuc || '?'} | ${totalGroups} phiếu | API: ${elapsed}s`);

  // Mở tab EForm cho mỗi nhóm
  for (let i = 0; i < totalGroups; i++) {
    const storageKey = `_eform_${Date.now()}_${i}_${Math.random().toString(36).slice(2, 6)}`;

    await new Promise((resolve) => {
      chrome.storage.local.set(
        { [storageKey]: JSON.stringify({ row: rowData, group: rowData.groups[i], index: i, total: totalGroups }) },
        resolve
      );
    });

    chrome.tabs.create({
      url: EFORM_URL + '&_ck=' + storageKey,
      active: i === 0
    });

    console.log(`[EForm BG v5] Mở tab nhóm ${i + 1}/${totalGroups}: ${storageKey}`);

    if (i < totalGroups - 1) {
      await sleep(1200);
    }
  }

  return {
    success: true,
    message: `${totalGroups} tab đang mở — Sheets API ${elapsed}s (nhanh hơn GAS 20x!)`
  };
}

// ── FILL_DONE: Content báo fill xong → ghi Done + log lỗi ──
async function handleFillDone(msg) {
  const { rowNum, errors, groupLabel } = msg;
  console.log(`[EForm BG v5] FILL_DONE nhóm ${groupLabel} dòng ${rowNum}, lỗi: ${errors?.length || 0}`);

  if (errors && errors.length > 0) {
    try {
      await logError(rowNum, `Nhóm ${groupLabel}: ${errors.join('; ')}`);
    } catch (e) {
      console.error('[EForm BG] logError failed:', e.message);
    }
  }

  const doneKey = `_done_${rowNum}`;
  const existing = await new Promise(resolve => chrome.storage.local.get(doneKey, resolve));
  if (!existing[doneKey]) {
    try {
      await markDone(rowNum);
      await new Promise(resolve => chrome.storage.local.set({ [doneKey]: Date.now() }, resolve));
      console.log(`[EForm BG v5] Ghi Done dòng ${rowNum}`);
      setTimeout(() => chrome.storage.local.remove(doneKey), 5 * 60 * 1000);
    } catch (e) {
      console.error('[EForm BG] markDone failed:', e.message);
    }
  }
}

// ── Message Handler ──
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

  if (msg.type === 'START_FILL') {
    handleStartFill(msg.row)
      .then(result => sendResponse(result))
      .catch(e => sendResponse({ success: false, error: e.message }));
    return true;
  }

  if (msg.type === 'PROGRESS') {
    chrome.runtime.sendMessage(msg).catch(() => { });
    return false;
  }

  if (msg.type === 'FILL_DONE') {
    handleFillDone(msg)
      .then(() => {
        chrome.runtime.sendMessage({ type: 'FILL_STATUS', text: `✅ Xong nhóm ${msg.groupLabel}`, done: false }).catch(() => { });
        sendResponse({ success: true });
      })
      .catch(e => sendResponse({ success: false, error: e.message }));
    return true;
  }

  return false;
});

chrome.runtime.onInstalled.addListener((details) => {
  console.log('🚀 EForm Auto Fill v5.0 installed (Sheets API):', details.reason);
});
