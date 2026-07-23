// ============================================================
// Code.gs — Google Apps Script Web App Proxy
// Dùng cho EForm Auto-Fill Tampermonkey
// Deploy: Publish → Deploy as web app → Execute as: Me, Who: Anyone
// ============================================================

// ── Cấu hình ──
var SHEET_ID = "1OLTtcxnRBqCUEUM158R5sztx4MAaKkiJkiQKIJzEthE";
var SHEET_NAME = "Camera";
var DATA_START_ROW = 12;

// ── Cột (0-indexed) ──
var COL = {
  STT: 0,       // A
  VUNG: 1,      // B
  BUU_CUC: 2,   // C
  MA_BC: 3,     // D
  // 4=E, 5=F, 6=G, 7=H, 8=I, 9=J, 10=K, 11=L, 12=M
  BAI_CHAM_1: 13,      // N
  TIEU_CHI_LOI_1: 14,  // O
  ANH_1: 15,           // P
  // 16=Q (skip)
  BAI_CHAM_2: 17,      // R
  TIEU_CHI_LOI_2: 18,  // S
  ANH_2: 19,           // T
  // 20=U (skip)
  BAI_CHAM_3: 21,      // V
  TIEU_CHI_LOI_3: 22,  // W
  ANH_3: 23,           // X
  // 24=Y (skip)
  BAI_CHAM_4: 25,      // Z
  TIEU_CHI_LOI_4: 26,  // AA
  ANH_4: 27,           // AB
  // 28=AC (skip)
  AUTO_PHIEU: 29,      // AD
  CHECK_1: 30,         // AE (không ghi)
  CHECK_2: 31,         // AF (không ghi)
  CHECK_3: 32,         // AG (không ghi)
  CHECK_4: 33,         // AH (không ghi)
  LOG_LOI: 34,         // AI
  ID_NGUOI_CHAM: 35    // AJ
};

// Nhóm ảnh
var IMAGE_GROUPS = [
  { group: 1, baiCham: COL.BAI_CHAM_1, tieuChi: COL.TIEU_CHI_LOI_1, anh: COL.ANH_1 },
  { group: 2, baiCham: COL.BAI_CHAM_2, tieuChi: COL.TIEU_CHI_LOI_2, anh: COL.ANH_2 },
  { group: 3, baiCham: COL.BAI_CHAM_3, tieuChi: COL.TIEU_CHI_LOI_3, anh: COL.ANH_3 },
  { group: 4, baiCham: COL.BAI_CHAM_4, tieuChi: COL.TIEU_CHI_LOI_4, anh: COL.ANH_4 }
];

// ── Pre-compute Mẫu chấm điểm + Radio Group từ baiCham/tieuChi ──
function classifyMauCham(baiChamText, tieuChiText) {
  var baiCham = (baiChamText || '').toLowerCase();
  var tieuChi = (tieuChiText || '').toLowerCase();
  
  // Strip Vietnamese accents
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
  
  baiCham = stripVN(baiCham);
  tieuChi = stripVN(tieuChi);
  
  // B1: Ưu tiên baiCham — tín hiệu mạnh nhất
  if (baiCham && /nhan dien thuong hieu|nhan dien|thuong hieu|hanh vi/i.test(baiCham)) {
    return { mauCham: 'NHẬN_DIỆN_THƯƠNG_HIỆU_VÀ_HÀNH_VI_BƯU_CỤC', radioGroup: 'nhan_dien_th' };
  }
  if (baiCham && /tieu chuan/i.test(baiCham)) {
    return { mauCham: 'TIÊU_CHUẨN_BƯU_CỤC', radioGroup: 'tieu_chuan_bc' };
  }
  
  // B2: Fallback — dùng tieuChi nếu baiCham trống hoặc không rõ
  var combined = baiCham + ' ' + tieuChi;
  
  if (/nhan dien|thuong hieu|hanh vi|phong cach|an nhau|co bac|an uong|hut thuoc|choi game|xem phim|on ao|mat trat tu|di dung ngoi|ke gac|dam dap|coi tran|tu che/.test(combined)) {
    return { mauCham: 'NHẬN_DIỆN_THƯƠNG_HIỆU_VÀ_HÀNH_VI_BƯU_CỤC', radioGroup: 'nhan_dien_th' };
  }
  if (/tieu chuan|camera|dong phuc|tac phong|ve sinh|an toan|bang hieu|bien dinh vi|mat tien|san nha|bang thong bao|he thong dien/.test(combined)) {
    return { mauCham: 'TIÊU_CHUẨN_BƯU_CỤC', radioGroup: 'tieu_chuan_bc' };
  }
  
  return { mauCham: null, radioGroup: null };
}

// ── Web App Entry Point ──
function doGet(e) {
  return handleRequest(e);
}

function doPost(e) {
  return handleRequest(e);
}

function handleRequest(e) {
  e = e || {};
  e.parameter = e.parameter || {};
  var action = e.parameter.action || "";
  var result = { success: false, error: "Unknown action" };

  try {
    if (action === "find_on_rows") {
      result = findOnRows();
    } else if (action === "mark_done") {
      var postData = e.postData || {};
      var body = JSON.parse(postData.contents || "{}");
      result = markDone(body.row);
    } else if (action === "log_error") {
      var postData = e.postData || {};
      var body = JSON.parse(postData.contents || "{}");
      result = logError(body.row, body.error);
    } else if (action === "get_row") {
      result = getRow(parseInt(e.parameter.row));
    } else {
      result = { success: false, error: "Unknown action: " + action };
    }
  } catch (err) {
    result = { success: false, error: err.toString() };
  }

  return ContentService
    .createTextOutput(JSON.stringify(result))
    .setMimeType(ContentService.MimeType.JSON);
}

// ── Test trong GAS Editor ──
// Chọn hàm này rồi bấm Run để test trực tiếp, không cần deploy
function testFindOnRows() {
  var result = findOnRows();
  Logger.log(JSON.stringify(result, null, 2));
  return result;
}

// ── Đọc tất cả dòng ON ──
function findOnRows() {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var ws = ss.getSheetByName(SHEET_NAME);
  if (!ws) return { success: false, error: "Sheet not found: " + SHEET_NAME };

  var lastRow = ws.getLastRow();
  if (lastRow < DATA_START_ROW) return { success: true, rows: [] };

  // Đọc toàn bộ dữ liệu (tối ưu: đọc 1 lần)
  var range = ws.getRange(DATA_START_ROW, 1, lastRow - DATA_START_ROW + 1, 41);
  var data = range.getValues();

  var onRows = [];
  for (var i = 0; i < data.length; i++) {
    var row = data[i];
    var rowNum = DATA_START_ROW + i;
    var adValue = (row[COL.AUTO_PHIEU] || "").toString().trim().toUpperCase();

    if (adValue === "ON") {
      // Tìm nhóm ảnh có dữ liệu
      var groups = [];
      for (var g = 0; g < IMAGE_GROUPS.length; g++) {
        var grp = IMAGE_GROUPS[g];
         var baiCham = (row[grp.baiCham] || "").toString().trim();
         var tieuChi = (row[grp.tieuChi] || "").toString().trim();
         var anh = (row[grp.anh] || "").toString().trim();

         // Push nếu có tiêu chí lỗi (bỏ điều kiện ảnh)
         if (tieuChi) {
           var classified = classifyMauCham(baiCham, tieuChi);
           groups.push({
             group: grp.group,
             baiCham: baiCham,
             tieuChi: tieuChi,
             anh: anh,
             mauCham: classified.mauCham,
             radioGroup: classified.radioGroup
           });
         }
      }

      if (groups.length > 0) {
        onRows.push({
          row: rowNum,
          stt: (row[COL.STT] || "").toString().trim(),
          vung: (row[COL.VUNG] || "").toString().trim(),
          buuCuc: (row[COL.BUU_CUC] || "").toString().trim(),
          maBC: (row[COL.MA_BC] || "").toString().trim(),
          idNguoiCham: (row[COL.ID_NGUOI_CHAM] || "").toString().trim(),
          groups: groups
        });
      }
    }
  }

  return { success: true, rows: onRows };
}

// ── Đọc 1 dòng ──
function getRow(rowNum) {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var ws = ss.getSheetByName(SHEET_NAME);
  if (!ws) return { success: false, error: "Sheet not found" };

  var range = ws.getRange(rowNum, 1, 1, 41);
  var row = range.getValues()[0];

  var data = {
    row: rowNum,
    stt: (row[COL.STT] || "").toString().trim(),
    vung: (row[COL.VUNG] || "").toString().trim(),
    buuCuc: (row[COL.BUU_CUC] || "").toString().trim(),
    maBC: (row[COL.MA_BC] || "").toString().trim(),
    idNguoiCham: (row[COL.ID_NGUOI_CHAM] || "").toString().trim(),
    ad: (row[COL.AUTO_PHIEU] || "").toString().trim(),
    groups: []
  };

  for (var g = 0; g < IMAGE_GROUPS.length; g++) {
    var grp = IMAGE_GROUPS[g];
    var baiCham = (row[grp.baiCham] || "").toString().trim();
    var tieuChi = (row[grp.tieuChi] || "").toString().trim();
    var anh = (row[grp.anh] || "").toString().trim();
    if (tieuChi) {
      var classified = classifyMauCham(baiCham, tieuChi);
      data.groups.push({
        group: grp.group,
        baiCham: baiCham,
        tieuChi: tieuChi,
        anh: anh,
        mauCham: classified.mauCham,
        radioGroup: classified.radioGroup
      });
    }
  }

  return { success: true, data: data };
}

// ── Ghi Done ──
function markDone(rowNum) {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var ws = ss.getSheetByName(SHEET_NAME);
  if (!ws) return { success: false, error: "Sheet not found" };

  ws.getRange(rowNum, COL.AUTO_PHIEU + 1).setValue("Done");
  return { success: true };
}

// ── Ghi log lỗi ──
function logError(rowNum, errorMsg) {
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var ws = ss.getSheetByName(SHEET_NAME);
  if (!ws) return { success: false, error: "Sheet not found" };

  var now = Utilities.formatDate(new Date(), "Asia/Ho_Chi_Minh", "dd/MM HH:mm");
  var existing = ws.getRange(rowNum, COL.LOG_LOI + 1).getValue() || "";
  var newMsg = "[" + now + "] " + errorMsg;
  if (existing) newMsg = existing + "\n" + newMsg;

  ws.getRange(rowNum, COL.LOG_LOI + 1).setValue(newMsg);
  return { success: true };
}
