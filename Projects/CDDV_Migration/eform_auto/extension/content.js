// ═══════════════════════════════════════════════════════════
// content.js — EForm Auto Fill v4.1
// Anh gõ số dòng → Enter → XONG. Không search, không tương tác.
// Select: React fiber set thẳng (tĩnh) hoặc mở dropdown click (động).
// Text: native setter. KHÔNG submit.
// ═══════════════════════════════════════════════════════════

(function () {
  'use strict';

  // ── Progress: gửi về popup window ──
  function log(msg, level = 'info') {
    const prefix = { info: 'ℹ️', success: '✅', warn: '⚠️', error: '❌' }[level] || '📋';
    console.log(`[EForm] ${prefix} ${msg}`);
    try { chrome.runtime.sendMessage({ type: 'PROGRESS', msg, level }); } catch (e) {}
  }

  // ── Normalize ──
  function norm(s) {
    return (s || '').toLowerCase()
      .replace(/[àáảãạăằắẳẵặâầấẩẫậ]/g, 'a')
      .replace(/[èéẻẽẹêềếểễệ]/g, 'e')
      .replace(/[ìíỉĩị]/g, 'i')
      .replace(/[òóỏõọôồốổỗộơờớởỡợ]/g, 'o')
      .replace(/[ùúủũụưừứửữự]/g, 'u')
      .replace(/[ỳýỷỹỵ]/g, 'y')
      .replace(/đ/g, 'd')
      .replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();
  }

  function wait(ms) { return new Promise(r => setTimeout(r, ms)); }

  // ── Tìm form item theo label ──
  function findItem(label) {
    const n2 = norm(label);
    for (const item of document.querySelectorAll('.ant-form-item')) {
      const el = item.querySelector('.ant-form-item-label label');
      if (el) {
        const n1 = norm(el.textContent.replace(/\*/g, ''));
        if (n1.includes(n2) || n2.includes(n1)) return item;
      }
    }
    return null;
  }

  // ═══════════════════════════════════════════
  //  SELECT — React fiber trước, fallback dropdown
  // ═══════════════════════════════════════════

  function setSelectViaFiber(formItem, targetText) {
    const sel = formItem.querySelector('.ant-select');
    if (!sel) return false;
    const fk = Object.keys(sel).find(k => k.startsWith('__reactFiber$') || k.startsWith('__reactInternalInstance$'));
    if (!fk) return false;

    let fiber = sel[fk];
    const tn = norm(targetText);
    let depth = 0;

    while (fiber && depth < 30) {
      const p = fiber.memoizedProps;
      if (p && typeof p.onChange === 'function' && Array.isArray(p.options) && p.options.length > 0) {
        for (const opt of p.options) {
          const label = String(opt.label || opt.children || opt.text || opt.title || '');
          const val = String(opt.value || '');
          if (norm(label).includes(tn) || tn.includes(norm(label)) ||
              norm(val).includes(tn) || tn.includes(norm(val))) {
            p.onChange(opt.value, opt);
            sel.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
          }
        }
        return false; // options có nhưng không khớp
      }
      fiber = fiber.return;
      depth++;
    }
    return false;
  }

  async function setSelectViaDropdown(formItem, targetText) {
    const selector = formItem.querySelector('.ant-select-selector') || formItem.querySelector('.ant-select');
    if (!selector) return false;

    formItem.scrollIntoView({ behavior: 'instant', block: 'nearest' });
    await wait(80);
    selector.click();
    await wait(250);

    // Đợi options load (150ms × 20 = 3s max)
    let items = [];
    for (let i = 0; i < 20; i++) {
      await wait(150);
      const dds = document.querySelectorAll('.ant-select-dropdown:not(.ant-select-dropdown-hidden)');
      const dd = dds.length > 0 ? dds[dds.length - 1] : null;
      if (dd) {
        items = dd.querySelectorAll('.ant-select-item-option');
        if (items.length > 0) break;
      }
    }

    if (items.length === 0) {
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
      return false;
    }

    const tn = norm(targetText);
    for (const item of items) {
      const c = item.querySelector('.ant-select-item-option-content');
      const text = c ? c.textContent.trim() : item.textContent.trim();
      const title = (item.getAttribute('title') || '').trim();
      if (norm(text).includes(tn) || tn.includes(norm(text)) ||
          norm(title).includes(tn) || tn.includes(norm(title))) {
        item.click();
        await wait(100);
        return true;
      }
    }

    // Fuzzy: match số đầu (VD: "12345" trong "12345 - Nguyễn Văn A")
    const num = targetText.match(/^(\d+)/);
    if (num) {
      for (const item of items) {
        const c = item.querySelector('.ant-select-item-option-content');
        const text = c ? c.textContent.trim() : item.textContent.trim();
        if (text.startsWith(num[1])) {
          item.click();
          await wait(100);
          return true;
        }
      }
    }

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    return false;
  }

  // ── SELECT API-Search (TÊN NGƯỜI CHẤM) ──
  // Gõ text vào search input → dispatch event → poll dropdown → click option
  async function setSelectViaAPISearch(formItem, targetText) {
    const searchInput = formItem.querySelector('.ant-select-selection-search input');
    if (!searchInput) return false;

    formItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
    await wait(200);

    // 1. Set value vào input search bằng native setter
    const proto = HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(searchInput, targetText);
    searchInput.dispatchEvent(new InputEvent('input', {
      bubbles: true, inputType: 'insertText', data: targetText
    }));
    searchInput.dispatchEvent(new Event('change', { bubbles: true }));
    searchInput.focus();

    // 2. Poll dropdown với retry (API cần ~500ms-2s để trả options)
    let items = [];
    for (let i = 0; i < 30; i++) {
      await wait(200);
      const dds = document.querySelectorAll('.ant-select-dropdown:not(.ant-select-dropdown-hidden)');
      if (dds.length === 0) continue;
      const dd = dds[dds.length - 1];
      if (dd.classList.contains('ant-select-dropdown-empty')) continue;
      items = dd.querySelectorAll('.ant-select-item-option');
      if (items.length > 0) break;
    }

    if (items.length === 0) {
      // Escape để đóng dropdown
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
      return false;
    }

    // 3. Click option đầu tiên (gần khớp nhất)
    const tn = norm(targetText);
    for (const item of items) {
      const c = item.querySelector('.ant-select-item-option-content');
      const text = c ? c.textContent.trim() : item.textContent.trim();
      if (norm(text).includes(tn) || tn.includes(norm(text)) || text.startsWith(targetText)) {
        item.click();
        await wait(200);
        return true;
      }
    }

    // Fallback: click option đầu tiên
    items[0].click();
    await wait(200);
    return true;
  }

  async function fillSelect(label, targetText) {
    if (!targetText) { log(`${label}: trống → skip`); return true; }
    const item = findItem(label);
    if (!item) { log(`${label}: không tìm thấy`, 'warn'); return false; }

    // Thử React fiber trước (instant, không mở dropdown)
    if (setSelectViaFiber(item, targetText)) {
      log(`${label}: ✅ (fiber) "${targetText.substring(0, 40)}"`, 'success');
      return true;
    }

    // API-search select — fallback khi fiber không có options
    const searchInput = item.querySelector('.ant-select-selection-search input');
    if (searchInput) {
      const ok = await setSelectViaAPISearch(item, targetText);
      if (ok) {
        log(`${label}: ✅ (API-search) "${targetText.substring(0, 40)}"`, 'success');
      } else {
        log(`${label}: ❌ API-search không tìm thấy "${targetText.substring(0, 40)}"`, 'error');
      }
      await wait(80);
      return ok;
    }

    // Fallback: mở dropdown → click (cho select động, API load options)
    const ok = await setSelectViaDropdown(item, targetText);
    if (ok) {
      log(`${label}: ✅ "${targetText.substring(0, 40)}"`, 'success');
    } else {
      log(`${label}: ❌ không khớp "${targetText.substring(0, 40)}"`, 'error');
    }
    // Đóng dropdown thừa
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await wait(80);
    return ok;
  }

  // ── TEXT — native setter ──
  function fillText(label, value) {
    if (value == null) value = '';
    const item = findItem(label);
    if (!item) { log(`${label}: không tìm thấy`, 'warn'); return false; }

    // Ưu tiên textarea, rồi input (CSS selector kết hợp đôi khi fail trên React DOM)
    const input = item.querySelector('textarea') || item.querySelector('input:not([type="hidden"])') || item.querySelector('input');
    if (!input) { log(`${label}: không có input`, 'warn'); return false; }

    item.scrollIntoView({ behavior: 'instant', block: 'nearest' });
    const proto = input.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(input, String(value));
    input.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertText', data: String(value) }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    log(`${label}: ✅ "${String(value).substring(0, 30)}"`, 'success');
    return true;
  }

  // ── Mapping mẫu chấm ──
  function mapMauCham(code) {
    if (!code) return null;
    const m = {
      'TIÊU_CHUẨN_BƯU_CỤC': 'Tiêu chuẩn Bưu cục',
      'TIEU_CHUAN_BUU_CUC': 'Tiêu chuẩn Bưu cục',
      'NHẬN_DIỆN_THƯƠNG_HIỆU_VÀ_HÀNH_VI_BƯU_CỤC': 'Nhận diện thương hiệu',
      'NHAN_DIEN_THUONG_HIEU_VA_HANH_VI_BUU_CUC': 'Nhận diện thương hiệu',
    };
    if (m[code]) return m[code];
    const cn = norm(code).replace(/_/g, ' ');
    for (const [k, v] of Object.entries(m)) {
      if (cn.includes(norm(k).replace(/_/g, ' '))) return v;
    }
    return code.replace(/_/g, ' ');
  }

  // ═══════════════════════════════════════════
  //  FILL FORM — tối giản, tối tốc
  // ═══════════════════════════════════════════

  async function fillEForm(row, group, idx) {
    const errors = [];
    const t0 = Date.now();

    log(`📋 Nhóm ${idx + 1}: "${(group.tieuChi || '').substring(0, 30)}"`);

    // Đợi form render
    const start = Date.now();
    while (!document.querySelector('#root .ant-form-item') && Date.now() - start < 8000) {
      await wait(200);
    }
    await wait(500);

    // Nhóm quy trình + Quy trình: MẶC ĐỊNH → SKIP
    log('Nhóm quy trình + Quy trình: mặc định → skip');

    // TÊN NGƯỜI CHẤM
    const id = (row.idNguoiCham || '').trim();
    if (id) {
      if (!await fillSelect('TÊN NGƯỜI CHẤM', id)) errors.push('TÊN NGƯỜI CHẤM');
    }

    // VÙNG + Mã BC + Tên BC — batch
    fillText('VÙNG', row.vung);
    fillText('Mã Bưu Cục', row.maBC);
    fillText('Tên Bưu Cục', row.buuCuc);

    // Mẫu chấm điểm
    if (group.mauCham) {
      if (!await fillSelect('Mẫu chấm điểm', mapMauCham(group.mauCham))) errors.push('Mẫu chấm điểm');
    } else {
      errors.push('Mẫu chấm điểm');
    }

    // Tiêu chí không đạt
    if (group.tieuChi) {
      const lbl = group.radioGroup === 'nhan_dien_th'
        ? 'Tiêu chí không đạt của Nhận diện thương hiệu và hành vi'
        : 'Tiêu chí không đạt của tiêu chuẩn Bưu cục';
      // Thử label đầy đủ trước
      let ok = await fillSelect(lbl, group.tieuChi);
      if (!ok) {
        // DOM có thể cắt ngắn label → fuzzy search với prefix
        ok = await fillSelect(lbl.substring(0, 35), group.tieuChi);
      }
      if (!ok) {
        // Fallback nhóm còn lại
        const fb = lbl.includes('Bưu cụ')
          ? 'Tiêu chí không đạt của Nhận diện thương hiệu và hành vi'
          : 'Tiêu chí không đạt của tiêu chuẩn Bưu cục';
        ok = await fillSelect(fb, group.tieuChi);
        if (!ok) ok = await fillSelect(fb.substring(0, 35), group.tieuChi);
      }
      if (!ok) errors.push('Tiêu chí');
    }

    // Mô tả lỗi
    if (group.tieuChi) {
      fillText('Mô tả chi tiết lỗi', 'Loi: ' + (group.tieuChi || '').substring(0, 250));
    }

    const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
    log(`⏱️ Nhóm ${idx + 1}: ${elapsed}s | Lỗi: ${errors.length || '0 ✅'}`, errors.length ? 'warn' : 'success');
    return errors;
  }

  // ═══════════════════════════════════════════
  //  INIT
  // ═══════════════════════════════════════════

  async function init() {
    log('EForm v4.1 loaded');
    const key = new URLSearchParams(location.search).get('_ck');
    if (!key) return;

    const res = await new Promise(r => chrome.storage.local.get(key, r));
    if (!res[key]) return;
    chrome.storage.local.remove(key);

    try {
      const d = JSON.parse(res[key]);
      const lbl = d.group.radioGroup || d.group.mauCham || `#${d.index + 1}`;
      log(`🤖 Điền nhóm ${lbl} (${d.index + 1}/${d.total})`);

      const errs = await fillEForm(d.row, d.group, d.index);
      log(`✅ Xong. Lỗi: ${errs.length}`, 'success');

      chrome.runtime.sendMessage({ type: 'FILL_DONE', rowNum: d.row.row, errors: errs, groupLabel: lbl });
    } catch (e) {
      log('Lỗi: ' + e.message, 'error');
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => setTimeout(init, 800));
  } else {
    setTimeout(init, 800);
  }

})();
