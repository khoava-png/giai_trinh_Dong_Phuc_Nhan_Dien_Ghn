/**
 * ============================================================================
 * GHN CONTROL CENTER V2 — GOOGLE APPS SCRIPT (Code.gs)
 * ============================================================================
 * Vai trò: Bộ não xử lý & gom phiếu vận hành
 * - Chạy định kỳ mỗi 1 phút (Time-driven trigger)
 * - Kiểm tra cờ B3 trên tab _Control_Center (Render cào xong mới chạy)
 * - Đọc lịch gửi đang kích hoạt (cột H "→ Chạy?" = TRUE)
 * - Lọc & gom phiếu từ Chi_tiet theo AM (BUU_CUC) và Trợ lý (VUNG_AM)
 * - Điền template nội dung và ghi hàng đợi gửi tin vào RP_Queue
 * - Cập nhật RP_theo_AM, RP_theo_TroLy phục vụ Dashboard
 * - Cập nhật cờ điều phối B3 = "PROCESSED", B4 = "DONE"
 * ============================================================================
 */

// CẤU HÌNH HỆ THỐNG
const CONFIG = {
  SHEET_ID: "15Ph9h9pOf5MfvtSaqsPPb0WA0hSdeWtgByY63teiUhg",
  TIMEZONE: "Asia/Ho_Chi_Minh",
  TABS: {
    CONTROL_CENTER: "_Control_Center",
    CHI_TIET: "Chi_tiet",
    CO_CAU: "Co_Cau",
    RP_QUEUE: "RP_Queue",
    RP_THEO_AM: "RP_theo_AM",
    RP_THEO_TROLY: "RP_theo_TroLy"
  },
  DEFAULT_TEMPLATES: {
    mau_am_all: "*🚨 [{loai_tieude}] Cần xử lý gấp — Anh/ Chị {ten_am}*\n\nHi Anh/ Chị *{ten_am}*, tính tới thời điểm _{ngay_gio}_\n{bcs}\n\n👉 *Xử lý phiếu tại:* https://g.ghn.studio/PhieuKhachHang\n📊 *Theo dõi Dashboard:* https://ghn-dashboard.pages.dev/\n👉 Nhờ AM {hanh_dong} nhé!\n👀 Cần hỗ trợ vui lòng liên hệ nhóm Gtalk \"*OE - Triển khai phiếu hối G/L/T*\"",
    mau_am_hoilay: "*📥 [ƯU TIÊN HỐI LẤY] — Anh/ Chị {ten_am}*\n\nHi Anh/ Chị *{ten_am}*, tính tới _{ngay_gio}_ còn phiếu hối lấy cần xử lý:\n{bcs}\n\n👉 Đôn đốc shipper đi lấy hàng trước khi đóng ca\n👉 *Xử lý tại:* https://g.ghn.studio/PhieuKhachHang",
    mau_am_hoigiao: "*🚚 [ƯU TIÊN HỐI GIAO] — Anh/ Chị {ten_am}*\n\nHi Anh/ Chị *{ten_am}*, tính tới _{ngay_gio}_:\n{bcs}\n\n👉 Đôn đốc nhân viên giao dứt điểm các đơn hối\n👉 *Xử lý tại:* https://g.ghn.studio/PhieuKhachHang",
    mau_am_hoitra: "*🔄 [ƯU TIÊN HỐI TRẢ] — Anh/ Chị {ten_am}*\n\nHi Anh/ Chị *{ten_am}*, tính tới _{ngay_gio}_:\n{bcs}\n\n👉 Xử lý dứt điểm các đơn hối trả",
    mau_vung_all: "*🚨 [{loai_tieude}] Báo cáo Vùng {vung}*\n\nHi Anh/Chị Trợ Lý/ HRBP vùng *{vung}*, tính tới thời điểm _{ngay_gio}_\n{bcs}\n\n📊 *Theo dõi Dashboard Vùng:* https://ghn-dashboard.pages.dev/\n👉 Nhờ Anh/ Chị {hanh_dong} nhé!\nCần hỗ trợ vui lòng liên hệ nhóm Gtalk \"*OE - Triển khai phiếu hối G/L/T*\"",
    mau_vung_hoilay: "*📥 [HỐI LẤY] Vùng {vung}*\n\nHi Anh/Chị Trợ Lý vùng *{vung}*, tính tới _{ngay_gio}_:\n{bcs}\n\n👉 Nhắc nhở các AM đôn đốc lấy hàng dứt điểm ca chiều",
    mau_vung_hoigiao: "*🚚 [HỐI GIAO] Vùng {vung}*\n\nHi Anh/Chị Trợ Lý vùng *{vung}*, tính tới _{ngay_gio}_:\n{bcs}\n\n👉 Nhắc nhở các AM đôn đốc giao dứt điểm các đơn hối",
    mau_vung_hoitra: "*🔄 [HỐI TRẢ] Vùng {vung}*\n\nHi Anh/Chị Trợ Lý vùng *{vung}*, tính tới _{ngay_gio}_:\n{bcs}\n\n👉 Nhắc nhở các AM đôn đốc xử lý đơn hối trả"
  }
};

/**
 * Lấy đối tượng Spreadsheet (hỗ trợ cả container-bound và standalone script)
 */
function getSpreadsheet_() {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    if (ss) return ss;
  } catch (e) {}
  return SpreadsheetApp.openById(CONFIG.SHEET_ID);
}

/**
 * Định dạng thời gian theo chuẩn Việt Nam
 */
function formatTime_(date, pattern) {
  return Utilities.formatDate(date || new Date(), CONFIG.TIMEZONE, pattern || "yyyy-MM-dd HH:mm:ss");
}

/**
 * HÀM TRIGGER CHÍNH: Time-driven chạy mỗi 1 phút
 */
function processQueueTrigger() {
  const ss = getSpreadsheet_();
  const ctrlSheet = ss.getSheetByName(CONFIG.TABS.CONTROL_CENTER);
  if (!ctrlSheet) {
    Logger.log("Không tìm thấy tab " + CONFIG.TABS.CONTROL_CENTER);
    return;
  }

  // 1. Kiểm tra cờ B3 (Trạng thái Render)
  const renderStatus = String(ctrlSheet.getRange("B3").getValue() || "").trim().toUpperCase();
  if (renderStatus !== "DONE") {
    // Không có đợt cào mới hoặc Render chưa cào xong -> Thoát ngay lập tức (< 1s)
    return;
  }

  // B3 = "DONE" -> Bắt đầu quy trình xử lý
  const startTime = new Date();
  const nowStr = formatTime_(startTime, "yyyy-MM-dd HH:mm:ss");
  const dotId = formatTime_(startTime, "yyyy-MM-dd_HH");

  // 2. Ghi nhận GAS RUNNING
  ctrlSheet.getRange("B4").setValue("RUNNING");
  ctrlSheet.getRange("C4").setValue(nowStr);
  ctrlSheet.getRange("D4").setValue("Đang xử lý gom phiếu và tạo queue...");
  SpreadsheetApp.flush();

  try {
    const result = runProcessingCore_(ss, ctrlSheet, dotId, startTime);

    // 6. Ghi B3 = "IDLE" (tránh GAS chạy lại đợt này, khớp Data Validation IDLE/RUNNING/DONE/FAILED)
    ctrlSheet.getRange("B3").setValue("IDLE");
    
    // 7. Ghi B4 = DONE
    const endTime = new Date();
    const endStr = formatTime_(endTime, "yyyy-MM-dd HH:mm:ss");
    ctrlSheet.getRange("B4").setValue("DONE");
    ctrlSheet.getRange("C4").setValue(endStr);
    ctrlSheet.getRange("D4").setValue(`Đã tạo ${result.totalQueue} tin (${result.details})`);

    // Ghi Log vào tab _Control_Center (dòng 83+)
    appendLog_(ctrlSheet, endStr, dotId, "2. Xử lý + sinh RP", "OK", result.totalQueue, result.details);
    Logger.log("✓ GAS Hoàn tất chu kỳ: " + result.details);

  } catch (err) {
    Logger.log("❌ LỖI GAS: " + err.toString());
    const errTimeStr = formatTime_(new Date(), "yyyy-MM-dd HH:mm:ss");
    ctrlSheet.getRange("B4").setValue("FAILED");
    ctrlSheet.getRange("D4").setValue(err.toString());
    appendLog_(ctrlSheet, errTimeStr, dotId, "2. Xử lý + sinh RP", "FAILED", 0, err.toString());
  }
}

/**
 * HÀM CHẠY THỬ / MANUAL TEST (Không cần chờ B3 = DONE)
 */
function manualRun() {
  const ss = getSpreadsheet_();
  const ctrlSheet = ss.getSheetByName(CONFIG.TABS.CONTROL_CENTER);
  const now = new Date();
  const dotId = formatTime_(now, "yyyy-MM-dd_HH");
  Logger.log("=== BẮT ĐẦU MANUAL RUN ===");
  const res = runProcessingCore_(ss, ctrlSheet, dotId, now);
  Logger.log("=== KẾT QUẢ MANUAL RUN ===");
  Logger.log(JSON.stringify(res, null, 2));
}

/**
 * LÕI XỬ LÝ DỮ LIỆU & SINH RP_QUEUE
 */
function runProcessingCore_(ss, ctrlSheet, dotId, runDate) {
  const ngayGioStr = formatTime_(runDate, "dd/MM/yyyy HH:mm");
  const timestampTao = formatTime_(runDate, "yyyy-MM-dd HH:mm:ss");

  // 1. Đọc lịch gửi (_Control_Center!A9:H58)
  const scheduleData = ctrlSheet.getRange("A9:H58").getValues();
  const activeSchedules = [];

  for (let i = 0; i < scheduleData.length; i++) {
    const row = scheduleData[i];
    const hour = row[0];
    const loaiPhieu = String(row[1] || "").trim().toUpperCase();
    const guiCho = String(row[2] || "").trim().toUpperCase();
    const gomTheo = String(row[3] || "").trim().toUpperCase();
    const tenMau = String(row[4] || "").trim();
    const isRun = row[7] === true || String(row[7]).trim().toUpperCase() === "TRUE";

    if (isRun && loaiPhieu && guiCho) {
      activeSchedules.push({
        rowIdx: i + 9,
        hour: hour,
        loaiPhieu: loaiPhieu, // ALL / HOI_LAY / HOI_GIAO / HOI_TRA
        guiCho: guiCho,       // AM / TRO_LY
        gomTheo: gomTheo,     // BUU_CUC / VUNG_AM
        tenMau: tenMau
      });
    }
  }

  if (activeSchedules.length === 0) {
    return { totalQueue: 0, details: "Không có lịch gửi nào đang kích hoạt (H=TRUE)" };
  }

  // 2. Đọc Templates (_Control_Center!A62:B80)
  const templateMap = loadTemplates_(ctrlSheet);

  // 3. Đọc DS Trợ lý từ Co_Cau!S3:W25
  const troLyMap = loadTroLyList_(ss);

  // 4. Đọc dữ liệu Chi_tiet
  const ctSheet = ss.getSheetByName(CONFIG.TABS.CHI_TIET);
  if (!ctSheet) throw new Error("Không tìm thấy tab " + CONFIG.TABS.CHI_TIET);
  const ctValues = ctSheet.getDataRange().getValues();
  if (ctValues.length <= 1) {
    return { totalQueue: 0, details: "Tab Chi_tiet không có dữ liệu" };
  }

  const ctHdr = ctValues[0];
  const colMap = {};
  for (let c = 0; c < ctHdr.length; c++) {
    colMap[String(ctHdr[c]).trim()] = c;
  }

  const requiredCols = ["ma_buu_cuc", "ten_buu_cuc", "loai_phieu", "tien_phat", "area_manager_id", "area_manager_name", "region_shortname"];
  for (let rc of requiredCols) {
    if (colMap[rc] === undefined) {
      throw new Error(`Cột thiếu trong Chi_tiet: ${rc}`);
    }
  }

  const ctRows = ctValues.slice(1);

  // 5. Chuẩn bị container dữ liệu
  const queueRows = [];
  const amSummaryRows = [];
  const trolySummaryRows = [];
  let summaryDetails = [];

  // 6. Xử lý từng dòng lịch gửi đang kích hoạt
  for (let sched of activeSchedules) {
    const loaiPhieu = sched.loaiPhieu;
    const guiCho = sched.guiCho;
    const gomTheo = sched.gomTheo;
    const tenMau = sched.tenMau;
    const rawTemplate = templateMap[tenMau] || CONFIG.DEFAULT_TEMPLATES[tenMau] || CONFIG.DEFAULT_TEMPLATES.mau_am_all;

    if (guiCho === "AM" || gomTheo === "BUU_CUC") {
      // GOM THEO AM (BUU_CUC)
      const amData = aggregateAM_(ctRows, colMap, loaiPhieu);
      let countAM = 0;

      for (let aid in amData) {
        const a = amData[aid];
        if (a.total <= 0) continue;

        const bcsTxt = buildBcsTextAM_(a.bcs, loaiPhieu);
        const rpContent = fillTemplate_(rawTemplate, {
          ten_am: a.ten,
          vung: a.vung || "",
          ngay_gio: ngayGioStr,
          bcs: bcsTxt,
          loai_phieu: loaiPhieu,
          kind: "am"
        });

        // Hàng ghi vào RP_Queue
        queueRows.push([
          dotId,
          loaiPhieu,
          "AM",
          aid,
          a.ten,
          rpContent,
          "PENDING",
          timestampTao,
          "", // timestamp_gui
          ""  // loi
        ]);

        // Hàng ghi vào RP_theo_AM (cho Dashboard)
        amSummaryRows.push([
          aid,
          a.ten,
          a.total,
          a.nz,
          a.np,
          rpContent,
          "SẴN SÀNG GỬI"
        ]);

        countAM++;
      }
      summaryDetails.push(`AM (${loaiPhieu}): ${countAM}`);

    } else if (guiCho === "TRO_LY" || gomTheo === "VUNG_AM") {
      // GOM THEO VÙNG (VUNG_AM)
      const vungData = aggregateVung_(ctRows, colMap, loaiPhieu);
      let countTroLy = 0;

      for (let reg in vungData) {
        const v = vungData[reg];
        if (v.total <= 0) continue;

        const bcsTxt = buildBcsTextVung_(v.ams, loaiPhieu);
        const troLyList = troLyMap[reg] || [];

        if (troLyList.length === 0) {
          // Nếu chưa có trợ lý map riêng, tạo 1 record giữ chỗ theo tên vùng
          const rpContent = fillTemplate_(rawTemplate, {
            ten_am: `Vùng ${reg}`,
            vung: reg,
            ngay_gio: ngayGioStr,
            bcs: bcsTxt,
            loai_phieu: loaiPhieu,
            kind: "vung"
          });
          trolySummaryRows.push([
            "",
            reg,
            v.total,
            v.nz,
            v.np,
            rpContent,
            "CHƯA GÁN TRỢ LÝ"
          ]);
        } else {
          for (let tl of troLyList) {
            const rpContent = fillTemplate_(rawTemplate, {
              ten_am: tl.ten || `Trợ lý ${reg}`,
              vung: reg,
              ngay_gio: ngayGioStr,
              bcs: bcsTxt,
              loai_phieu: loaiPhieu,
              kind: "vung"
            });

            // Hàng ghi vào RP_Queue
            queueRows.push([
              dotId,
              loaiPhieu,
              "TRO_LY",
              tl.ma_nv,
              tl.ten || `Trợ lý ${reg}`,
              rpContent,
              "PENDING",
              timestampTao,
              "",
              ""
            ]);

            // Hàng ghi vào RP_theo_TroLy (cho Dashboard)
            trolySummaryRows.push([
              tl.ma_nv,
              reg,
              v.total,
              v.nz,
              v.np,
              rpContent,
              "SẴN SÀNG GỬI"
            ]);

            countTroLy++;
          }
        }
      }
      summaryDetails.push(`Trợ lý (${loaiPhieu}): ${countTroLy}`);
    }
  }

  // 7. Ghi vào tab RP_Queue
  writeToRPQueue_(ss, queueRows);

  // 8. Cập nhật RP_theo_AM và RP_theo_TroLy
  if (amSummaryRows.length > 0) {
    writeSummarySheet_(ss, CONFIG.TABS.RP_THEO_AM, amSummaryRows, [
      "Mã NV", "Tên AM", "Tổng phiếu", "Cần xử lý ngay", "Đang phát sinh phạt", "Nội dung RP (gửi GTalk)", "Trạng thái"
    ]);
  }
  if (trolySummaryRows.length > 0) {
    writeSummarySheet_(ss, CONFIG.TABS.RP_THEO_TROLY, trolySummaryRows, [
      "Mã NV Trợ lý", "Vùng", "Tổng phiếu", "Cần xử lý ngay", "Đang phát sinh phạt", "Nội dung RP (gửi GTalk)", "Trạng thái"
    ]);
  }

  return {
    totalQueue: queueRows.length,
    details: summaryDetails.join(", ")
  };
}

/**
 * ĐỌC TEMPLATE TỪ SHEET
 */
function loadTemplates_(ctrlSheet) {
  const tplData = ctrlSheet.getRange("A62:B80").getValues();
  const map = {};
  for (let i = 0; i < tplData.length; i++) {
    const name = String(tplData[i][0] || "").trim();
    const content = String(tplData[i][1] || "").trim();
    if (name && content) {
      map[name] = content;
    }
  }
  return map;
}

/**
 * ĐỌC DANH SÁCH TRỢ LÝ TỪ TAB Co_Cau!S3:W25
 */
function loadTroLyList_(ss) {
  const ccSheet = ss.getSheetByName(CONFIG.TABS.CO_CAU);
  const result = {};
  if (!ccSheet) return result;

  const data = ccSheet.getRange("S3:W25").getValues();
  let currentVung = null;

  for (let i = 0; i < data.length; i++) {
    const row = data[i];
    const vungCell = String(row[0] || "").trim();
    if (vungCell) {
      currentVung = vungCell;
    }
    if (!currentVung || currentVung === "GH NẶNG") continue;

    const maNv = String(row[3] || "").trim();
    const tenNv = String(row[4] || "").trim();

    if (maNv && /^\d+$/.test(maNv)) {
      if (!result[currentVung]) {
        result[currentVung] = [];
      }
      // Tránh trùng mã NV trong cùng 1 vùng
      if (!result[currentVung].some(x => x.ma_nv === maNv)) {
        result[currentVung].push({
          ma_nv: maNv,
          ten: tenNv
        });
      }
    }
  }
  return result;
}

/**
 * GOM PHIẾU THEO AM (BUU_CUC)
 */
function aggregateAM_(ctRows, colMap, loaiPhieuFilter) {
  const amMap = {};

  for (let i = 0; i < ctRows.length; i++) {
    const r = ctRows[i];
    const loai = String(r[colMap["loai_phieu"]] || "").trim();

    if (loaiPhieuFilter === "HOI_LAY" && loai !== "Hối lấy") continue;
    if (loaiPhieuFilter === "HOI_GIAO" && loai !== "Hối giao") continue;
    if (loaiPhieuFilter === "HOI_TRA" && loai !== "Hối trả") continue;

    const aid = String(r[colMap["area_manager_id"]] || "").trim();
    if (!aid || aid === "0") continue;

    const aname = String(r[colMap["area_manager_name"]] || "").trim();
    const bcCode = String(r[colMap["ma_buu_cuc"]] || "").trim() || "?";
    const bcName = String(r[colMap["ten_buu_cuc"]] || "").trim();
    const reg = String(r[colMap["region_shortname"]] || "").trim();
    const penVal = Number(r[colMap["tien_phat"]]) || 0;

    if (!amMap[aid]) {
      amMap[aid] = {
        ten: aname || aid,
        vung: reg,
        bcs: {},
        total: 0,
        nz: 0,
        np: 0
      };
    }

    if (!amMap[aid].bcs[bcCode]) {
      amMap[aid].bcs[bcCode] = {
        ten: bcName,
        total: 0,
        nz: 0,
        np: 0,
        giao: 0,
        lay: 0,
        tra: 0
      };
    }

    const targetBc = amMap[aid].bcs[bcCode];
    targetBc.total++;
    amMap[aid].total++;

    if (penVal > 0) {
      targetBc.np++;
      amMap[aid].np++;
    } else {
      targetBc.nz++;
      amMap[aid].nz++;
    }

    if (loai === "Hối giao") targetBc.giao++;
    else if (loai === "Hối lấy") targetBc.lay++;
    else if (loai === "Hối trả") targetBc.tra++;
  }

  return amMap;
}

/**
 * GOM PHIẾU THEO VÙNG (VUNG_AM)
 */
function aggregateVung_(ctRows, colMap, loaiPhieuFilter) {
  const vungMap = {};

  for (let i = 0; i < ctRows.length; i++) {
    const r = ctRows[i];
    const reg = String(r[colMap["region_shortname"]] || "").trim();
    if (!reg || reg === "GH NẶNG") continue;

    const loai = String(r[colMap["loai_phieu"]] || "").trim();
    if (loaiPhieuFilter === "HOI_LAY" && loai !== "Hối lấy") continue;
    if (loaiPhieuFilter === "HOI_GIAO" && loai !== "Hối giao") continue;
    if (loaiPhieuFilter === "HOI_TRA" && loai !== "Hối trả") continue;

    const aid = String(r[colMap["area_manager_id"]] || "").trim() || "0";
    const aname = String(r[colMap["area_manager_name"]] || "").trim();
    const penVal = Number(r[colMap["tien_phat"]]) || 0;

    if (!vungMap[reg]) {
      vungMap[reg] = {
        ams: {},
        total: 0,
        nz: 0,
        np: 0
      };
    }

    if (!vungMap[reg].ams[aid]) {
      const fallbackName = (aid && aid !== "0") ? aid : "Chưa rõ AM";
      vungMap[reg].ams[aid] = {
        ten: (aname && aname !== "0") ? aname : fallbackName,
        total: 0,
        nz: 0,
        np: 0,
        giao: 0,
        lay: 0,
        tra: 0
      };
    }

    const targetAm = vungMap[reg].ams[aid];
    targetAm.total++;
    vungMap[reg].total++;

    if (penVal > 0) {
      targetAm.np++;
      vungMap[reg].np++;
    } else {
      targetAm.nz++;
      vungMap[reg].nz++;
    }

    if (loai === "Hối giao") targetAm.giao++;
    else if (loai === "Hối lấy") targetAm.lay++;
    else if (loai === "Hối trả") targetAm.tra++;
  }

  return vungMap;
}

/**
 * SINH DANH SÁCH BƯU CỤC CHO AM
 */
function buildBcsTextAM_(bcsDict, loaiPhieu) {
  const list = Object.keys(bcsDict).map(k => ({ ma: k, ...bcsDict[k] }));
  if (list.length === 0) {
    return "Hiện bưu cục của Anh/ Chị không còn phiếu tồn nào cần xử lý. Chúc một ngày làm việc hiệu quả!";
  }

  // Sắp xếp giảm dần theo tổng số phiếu
  list.sort((a, b) => b.total - a.total);

  const lines = list.map(item => {
    let hi = item.ma;
    if (item.ten) {
      if (item.ten.indexOf(" - ") >= 0) {
        hi = item.ten.split(" - ").slice(1).join(" - ");
      } else {
        hi = item.ten;
      }
    }

    if (loaiPhieu === "HOI_LAY") {
      return `📥 *Bưu cục ${hi}*: *${item.total}* phiếu Hối Lấy (*${item.nz}* cần ngay, *${item.np}* phạt)`;
    } else if (loaiPhieu === "HOI_GIAO") {
      return `🚚 *Bưu cục ${hi}*: *${item.total}* phiếu Hối Giao (*${item.nz}* cần ngay, *${item.np}* phạt)`;
    } else if (loaiPhieu === "HOI_TRA") {
      return `🔄 *Bưu cục ${hi}*: *${item.total}* phiếu Hối Trả (*${item.nz}* cần ngay, *${item.np}* phạt)`;
    } else {
      return `📦 *Bưu cục ${hi}*: *${item.total}* phiếu — _${item.nz} cần ngay, ${item.np} phạt_`;
    }
  });

  return lines.join("\n");
}

/**
 * SINH DANH SÁCH AM CHO TRỢ LÝ VÙNG
 */
function buildBcsTextVung_(amsDict, loaiPhieu) {
  const list = Object.keys(amsDict).map(k => ({ ma: k, ...amsDict[k] }));
  if (list.length === 0) {
    return "Hiện vùng không còn phiếu tồn nào cần xử lý. Chúc một ngày làm việc hiệu quả!";
  }

  // Sắp xếp giảm dần theo tổng số phiếu
  list.sort((a, b) => b.total - a.total);

  const lines = list.map(item => {
    const dispName = (item.ten && item.ten !== "0") ? item.ten : ((item.ma && item.ma !== "0") ? item.ma : "Chưa rõ AM");

    if (loaiPhieu === "HOI_LAY") {
      return `📥 *${dispName}* (AM): *${item.total}* phiếu Hối Lấy (*${item.nz}* cần ngay, *${item.np}* phạt)`;
    } else if (loaiPhieu === "HOI_GIAO") {
      return `🚚 *${dispName}* (AM): *${item.total}* phiếu Hối Giao (*${item.nz}* cần ngay, *${item.np}* phạt)`;
    } else if (loaiPhieu === "HOI_TRA") {
      return `🔄 *${dispName}* (AM): *${item.total}* phiếu Hối Trả (*${item.nz}* cần ngay, *${item.np}* phạt)`;
    } else {
      return `👤 *${dispName}* (AM): *${item.total}* phiếu — _${item.nz} cần ngay, ${item.np} phạt_`;
    }
  });

  return lines.join("\n");
}

/**
 * ĐIỀN BIẾN VÀO TEMPLATE
 */
function fillTemplate_(templateStr, ctx) {
  const tenAm = ctx.ten_am || "";
  const vung = ctx.vung || "";
  const ngayGio = ctx.ngay_gio || "";
  const bcs = ctx.bcs || "";
  const loaiPhieu = ctx.loai_phieu || "ALL";
  const kind = ctx.kind || "am";

  let loaiLuong = "TỔNG HỢP HỐI G/L/T";
  let loaiTieude = "CẢNH BÁO TỔNG HỢP HỐI G/L/T";
  let hanhDong = "xử lý dứt điểm các phiếu tồn ngay";

  if (loaiPhieu === "HOI_LAY") {
    loaiLuong = "ƯU TIÊN HỐI LẤY";
    loaiTieude = "ƯU TIÊN XỬ LÝ HỐI LẤY";
    hanhDong = kind === "am" ? "đôn đốc shipper đi lấy hàng trước khi đóng ca" : "nhắc nhở các AM đôn đốc lấy hàng dứt điểm ca chiều";
  } else if (loaiPhieu === "HOI_GIAO") {
    loaiLuong = "ƯU TIÊN HỐI GIAO";
    loaiTieude = "ƯU TIÊN XỬ LÝ HỐI GIAO";
    hanhDong = kind === "am" ? "đôn đốc nhân viên giao dứt điểm các đơn hối" : "nhắc nhở các AM đôn đốc giao dứt điểm các đơn hối";
  } else if (loaiPhieu === "HOI_TRA") {
    loaiLuong = "ƯU TIÊN HỐI TRẢ";
    loaiTieude = "ƯU TIÊN XỬ LÝ HỐI TRẢ";
    hanhDong = kind === "am" ? "xử lý dứt điểm các đơn hối trả" : "nhắc nhở các AM đôn đốc xử lý đơn hối trả";
  } else {
    hanhDong = kind === "am" ? "xử lý dứt điểm các phiếu tồn ngay" : "nhắc nhở AM đôn đốc xử lý ngay";
  }

  let out = templateStr
    .replace(/\{ten_am\}/g, tenAm)
    .replace(/\{vung\}/g, vung || tenAm)
    .replace(/\{ngay_gio\}/g, ngayGio)
    .replace(/\{bcs\}/g, bcs)
    .replace(/\{loai_luong\}/g, loaiLuong)
    .replace(/\{loai_tieude\}/g, loaiTieude)
    .replace(/\{hanh_dong\}/g, hanhDong)
    .replace(/\{hanh_dong_nhac_nho\}/g, hanhDong)
    .replace(/\{link\}/g, "https://g.ghn.studio/PhieuKhachHang");

  return out;
}

/**
 * GHI HÀNG ĐỢI VÀO TAB RP_Queue
 */
function writeToRPQueue_(ss, queueRows) {
  let queueSheet = ss.getSheetByName(CONFIG.TABS.RP_QUEUE);
  const headers = [
    "dot_id", "loai_phieu", "nguoi_nhan", "ma_nv", "ten", "noi_dung", "status", "timestamp_tao", "timestamp_gui", "loi"
  ];

  if (!queueSheet) {
    queueSheet = ss.insertSheet(CONFIG.TABS.RP_QUEUE);
    queueSheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    queueSheet.setFrozenRows(1);
  }

  // Xóa dữ liệu cũ (từ dòng 2 trở xuống)
  const lastRow = queueSheet.getLastRow();
  if (lastRow > 1) {
    queueSheet.getRange(2, 1, lastRow - 1, headers.length).clearContent();
  }

  // Ghi dữ liệu mới
  if (queueRows.length > 0) {
    queueSheet.getRange(2, 1, queueRows.length, headers.length).setValues(queueRows);
  }
}

/**
 * GHI DỮ LIỆU TỔNG HỢP VÀO TAB RP_theo_AM HOẶC RP_theo_TroLy
 */
function writeSummarySheet_(ss, sheetName, rows, headers) {
  let sheet = ss.getSheetByName(sheetName);
  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    sheet.setFrozenRows(1);
  }

  const lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    sheet.getRange(2, 1, lastRow - 1, headers.length).clearContent();
  }

  if (rows.length > 0) {
    sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
  }
}

/**
 * GHI LOG VÀO VÙNG LOG CỦA TAB _Control_Center (dòng 83+)
 */
function appendLog_(ctrlSheet, timestamp, dotId, step, status, count, detail) {
  const logRange = ctrlSheet.getRange("A83:F132");
  const logValues = logRange.getValues();
  let targetRow = -1;

  for (let i = 0; i < logValues.length; i++) {
    if (!logValues[i][0] && !logValues[i][1]) {
      targetRow = 83 + i;
      break;
    }
  }

  if (targetRow === -1) {
    // Đã đầy 50 dòng log -> dịch chuyển hoặc ghi đè dòng 83
    targetRow = 83;
  }

  ctrlSheet.getRange(targetRow, 1, 1, 6).setValues([[
    timestamp,
    dotId,
    step,
    status,
    count,
    String(detail || "").slice(0, 500)
  ]]);
}

/**
 * CÀI ĐẶT TRIGGER TỰ ĐỘNG CHẠY MỖI 1 PHÚT (Chỉ cần chạy 1 lần khi thiết lập)
 */
function setupMinuteTrigger() {
  const functionName = "processQueueTrigger";
  const triggers = ScriptApp.getProjectTriggers();

  for (let i = 0; i < triggers.length; i++) {
    if (triggers[i].getHandlerFunction() === functionName) {
      ScriptApp.deleteTrigger(triggers[i]);
    }
  }

  ScriptApp.newTrigger(functionName)
    .timeBased()
    .everyMinutes(1)
    .create();

  Logger.log("✓ Đã tạo Time-driven trigger chạy mỗi 1 phút cho hàm " + functionName);
}
