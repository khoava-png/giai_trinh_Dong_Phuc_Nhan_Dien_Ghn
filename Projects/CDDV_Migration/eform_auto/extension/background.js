// ═══════════════════════════════════════════════════════════
// background.js — EForm Auto Fill v4
// Bộ não trung tâm: nhận START_FILL → gọi GAS → mở tab per group
// Popup đóng không ảnh hưởng — mọi xử lý ở đây.
// ═══════════════════════════════════════════════════════════

const GAS_URL = "https://script.google.com/macros/s/AKfycbxfCQ4NAGEcpyJNGPyIAIkIaFbJlFz16WZNhWNMIEGRJBa9-gfp9ag51LRkfbzNdcip/exec";
const EFORM_URL = "https://noibo.ghn.vn/eform/form/create?flowId=69d371b7af6a207f9ca7ce12";

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ── GAS API Call ──
async function gasCall(action, payload, params) {
  let url = GAS_URL + '?action=' + encodeURIComponent(action);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      url += '&' + k + '=' + encodeURIComponent(v);
    }
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);

  const opts = {
    method: payload ? 'POST' : 'GET',
    redirect: 'follow',
    signal: controller.signal
  };

  if (payload) {
    opts.headers = { 'Content-Type': 'application/json' };
    opts.body = JSON.stringify(payload);
  }

  try {
    const resp = await fetch(url, opts);
    clearTimeout(timeout);
    const text = await resp.text();
    try {
      return JSON.parse(text);
    } catch (e) {
      return { success: false, error: 'GAS trả về không phải JSON: ' + text.substring(0, 200) };
    }
  } catch (e) {
    clearTimeout(timeout);
    if (e.name === 'AbortError') {
      return { success: false, error: 'Timeout 20s — GAS phản hồi chậm' };
    }
    return { success: false, error: e.message };
  }
}

// ── START_FILL: Nhận lệnh từ popup → gọi GAS → mở tab per group ──
async function handleStartFill(rowNum) {
  console.log(`[EForm BG] START_FILL dòng ${rowNum}`);

  // 1. Gọi GAS get_row
  const data = await gasCall('get_row', null, { row: rowNum });

  if (!data || !data.success) {
    console.error('[EForm BG] GAS lỗi:', data?.error);
    return { success: false, error: data?.error || 'GAS không phản hồi' };
  }

  const rowData = data.data;
  if (!rowData.groups || rowData.groups.length === 0) {
    return { success: false, error: `Dòng ${rowNum} không có tiêu chí nào!` };
  }

  const totalGroups = rowData.groups.length;
  console.log(`[EForm BG] Dòng ${rowNum}: ${rowData.buuCuc || '?'} | ${totalGroups} phiếu`);

  // 2. Mở tab EForm cho MỖI nhóm (mỗi tab = 1 nhóm, tự fill)
  for (let i = 0; i < totalGroups; i++) {
    const storageKey = `_eform_${Date.now()}_${i}_${Math.random().toString(36).slice(2, 6)}`;

    // Lưu payload vào storage
    await new Promise((resolve) => {
      chrome.storage.local.set(
        { [storageKey]: JSON.stringify({ row: rowData, group: rowData.groups[i], index: i, total: totalGroups }) },
        resolve
      );
    });

    // Mở tab (chỉ tab đầu active, các tab sau mở nền)
    chrome.tabs.create({
      url: EFORM_URL + '&_ck=' + storageKey,
      active: i === 0
    });

    console.log(`[EForm BG] Mở tab nhóm ${i + 1}/${totalGroups}: ${storageKey}`);

    // Đợi 1.5s giữa các tab để tránh overload
    if (i < totalGroups - 1) {
      await sleep(1500);
    }
  }

  return {
    success: true,
    message: `${totalGroups} tab EForm đang mở và tự điền...`
  };
}

// ── FILL_DONE: Content báo fill xong → ghi Done + log lỗi ──
async function handleFillDone(msg) {
  const { rowNum, errors, groupLabel } = msg;
  console.log(`[EForm BG] FILL_DONE nhóm ${groupLabel} dòng ${rowNum}, lỗi: ${errors?.length || 0}`);

  // Ghi lỗi nếu có
  if (errors && errors.length > 0) {
    await gasCall('log_error', { row: rowNum, error: `Nhóm ${groupLabel}: ${errors.join('; ')}` });
  }

  // Ghi Done (chỉ ghi 1 lần cho dòng, không ghi per group)
  // Dùng storage để track xem đã ghi Done chưa
  const doneKey = `_done_${rowNum}`;
  const existing = await new Promise(resolve => chrome.storage.local.get(doneKey, resolve));
  if (!existing[doneKey]) {
    await gasCall('mark_done', { row: rowNum });
    await new Promise(resolve => chrome.storage.local.set({ [doneKey]: Date.now() }, resolve));
    console.log(`[EForm BG] Ghi Done dòng ${rowNum}`);

    // Xóa key sau 5 phút (cleanup)
    setTimeout(() => chrome.storage.local.remove(doneKey), 5 * 60 * 1000);
  }
}

// ── Message Handler ──
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {

  if (msg.type === 'START_FILL') {
    handleStartFill(msg.row)
      .then(result => sendResponse(result))
      .catch(e => sendResponse({ success: false, error: e.message }));
    return true; // async
  }

  // Forward PROGRESS từ content.js → popup
  if (msg.type === 'PROGRESS') {
    // Broadcast đến tất cả extension pages (popup sẽ nhận)
    chrome.runtime.sendMessage(msg).catch(() => { });
    return false;
  }

  if (msg.type === 'FILL_DONE') {
    handleFillDone(msg)
      .then(() => {
        // Báo popup biết tiến trình
        chrome.runtime.sendMessage({ type: 'FILL_STATUS', text: `✅ Xong nhóm ${msg.groupLabel}`, done: false }).catch(() => { });
        sendResponse({ success: true });
      })
      .catch(e => sendResponse({ success: false, error: e.message }));
    return true;
  }

  // Giữ GAS_CALL cho backward compatibility (content.js vẫn có thể gọi trực tiếp)
  if (msg.type === 'GAS_CALL') {
    gasCall(msg.action, msg.payload, msg.params)
      .then(result => sendResponse(result))
      .catch(e => sendResponse({ success: false, error: e.message }));
    return true;
  }

  return false;
});

// ── Install/Update log ──
chrome.runtime.onInstalled.addListener((details) => {
  console.log('🚀 EForm Auto Fill v4 installed:', details.reason);
});
