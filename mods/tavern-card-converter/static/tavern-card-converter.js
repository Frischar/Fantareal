// ── 酒馆卡转换器 · Tavern Card Converter ──

(function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);

  // ── General Tab ──
  const genFileInput = $("#general-file-input");
  const genDropZone = $("#general-drop-zone");
  const genParsingHint = $("#general-parsing-hint");
  const genError = $("#general-error");
  const genPreview = $("#general-preview");
  const genPreviewImg = $("#general-preview-img");
  const genResult = $("#general-result");
  const genResultEmpty = $("#general-result-empty");
  const genPureHint = $("#general-pure-hint");
  const genSections = $("#general-sections");
  const genDlPngBtn = $("#general-download-png-btn");
  const genSavePathHint = $("#general-save-path-hint");
  const genSavePathLabel = $("#general-save-path-label");
  const genChangePath = $("#general-change-path");
  var genPngB64 = "", genPngFn = "";
  var genSectionsData = [];
  var genSaveMode = null;

  // ── Pure Card Tab ──
  const cardFileInput = $("#card-file-input");
  const cardDropZone = $("#card-drop-zone");
  const cardParsingHint = $("#card-parsing-hint");
  const cardError = $("#card-error");
  const cardPreview = $("#card-preview");
  const cardPreviewImg = $("#card-preview-img");
  const cardResult = $("#card-result");
  const cardResultEmpty = $("#card-result-empty");
  const cardResultName = $("#card-result-name");
  const cardResultPreserved = $("#card-result-preserved");
  const cardJsonOutput = $("#card-json-output");
  const cardDownloadBtn = $("#card-download-btn");
  const cardCopyBtn = $("#card-copy-btn");
  const cardDownloadPngBtn = $("#card-download-png-btn");
  const cardSavePathHint = $("#card-save-path-hint");
  const cardSavePathLabel = $("#card-save-path-label");
  const cardChangePath = $("#card-change-path");
  var cardJsonText = "", cardFilename = "", cardPngB64 = "", cardPngFn = "", cardSaveMode = null;

  // ── Worldbook Tab ──
  const wbFileInput = $("#wb-file-input");
  const wbDropZone = $("#wb-drop-zone");
  const wbParsingHint = $("#wb-parsing-hint");
  const wbError = $("#wb-error");
  const wbResult = $("#wb-result");
  const wbResultEmpty = $("#wb-result-empty");
  const wbResultName = $("#wb-result-name");
  const wbEntryCount = $("#wb-entry-count");
  const wbConversionInfo = $("#wb-conversion-info");
  const wbJsonOutput = $("#wb-json-output");
  const wbDownloadBtn = $("#wb-download-btn");
  const wbCopyBtn = $("#wb-copy-btn");
  const wbSavePathHint = $("#wb-save-path-hint");
  const wbSavePathLabel = $("#wb-save-path-label");
  const wbChangePath = $("#wb-change-path");
  var wbJsonText = "", wbFilename = "", wbSaveMode = null;

  // ── Save dialogs ──
  const cardSaveDialog = $("#card-save-dialog");
  const cardSaveFilename = $("#card-save-filename");
  const cardAssetsPath = $("#card-assets-path");
  const cardSaveToAssets = $("#card-save-to-assets");
  const cardSaveBrowse = $("#card-save-browse");
  const cardSaveCancel = $("#card-save-cancel");
  const wbSaveDialog = $("#wb-save-dialog");
  const wbSaveFilename = $("#wb-save-filename");
  const wbAssetsPath = $("#wb-assets-path");
  const wbSaveToAssets = $("#wb-save-to-assets");
  const wbSaveBrowse = $("#wb-save-browse");
  const wbSaveCancel = $("#wb-save-cancel");
  var currentSaveJson = "", currentSaveFn = "", currentSaveType = ""; // card|wb

  // ── Guide dialog ──
  const guideDialog = $("#tcc-guide-dialog");
  const guideTrigger = $("#tcc-guide-trigger");
  const guideClose = $("#tcc-guide-close");

  // ── Helpers ──
  function show(el) { el.hidden = false; }
  function hide(el) { el.hidden = true; }
  function clearError(errEl) { hide(errEl); errEl.textContent = ""; }
  function showError(errEl, msg) { errEl.textContent = msg; show(errEl); }
  function showWarning(el, msg, clickHandler) {
    el.innerHTML = msg;
    if (clickHandler) {
      var link = el.querySelector(".tcc-warning-link");
      if (link) link.addEventListener("click", clickHandler);
    }
    show(el);
  }
  // Switch to a specific tab
  function switchToTab(tabName) {
    var btn = document.querySelector('.tcc-tab[data-tab="' + tabName + '"]');
    if (btn) btn.click();
  }

  function toast(msg, type) {
    var el = document.createElement("div");
    el.className = "tcc-toast tcc-toast-" + (type || "success");
    el.textContent = msg;
    document.body.appendChild(el);
    requestAnimationFrame(function () { el.classList.add("show"); });
    setTimeout(function () { el.classList.remove("show"); setTimeout(function () { el.remove(); }, 350); }, 2200);
  }

  function downloadBlob(filename, base64, mime) {
    var bytes = new Uint8Array(atob(base64).length);
    for (var i = 0; i < bytes.length; i++) bytes[i] = atob(base64).charCodeAt(i);
    var blob = new Blob([bytes], { type: mime }), url = URL.createObjectURL(blob);
    var a = document.createElement("a"); a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
  }

  function downloadJSON(filename, text) {
    var blob = new Blob([text], { type: "application/json" }), url = URL.createObjectURL(blob);
    var a = document.createElement("a"); a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(url);
  }

  async function copyToClipboard(text) {
    try { await navigator.clipboard.writeText(text); toast("已复制到剪贴板", "success"); }
    catch (_) {
      var ta = document.createElement("textarea"); ta.value = text;
      ta.style.cssText = "position:fixed;left:-9999px"; document.body.appendChild(ta);
      ta.select(); document.execCommand("copy"); document.body.removeChild(ta);
      toast("已复制到剪贴板", "success");
    }
  }

  // ── Drop zone ──
  function setupDropZone(zoneEl, inputEl, onFiles) {
    zoneEl.addEventListener("click", function (e) { if (e.target !== inputEl) inputEl.click(); });
    inputEl.addEventListener("change", function () { if (inputEl.files && inputEl.files.length) onFiles(inputEl.files); });
    zoneEl.addEventListener("dragover", function (e) { e.preventDefault(); zoneEl.classList.add("drag-over"); });
    zoneEl.addEventListener("dragleave", function () { zoneEl.classList.remove("drag-over"); });
    zoneEl.addEventListener("drop", function (e) { e.preventDefault(); zoneEl.classList.remove("drag-over"); if (e.dataTransfer && e.dataTransfer.files.length) onFiles(e.dataTransfer.files); });
  }

  // ── Tabs ──
  document.querySelectorAll(".tcc-tab").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".tcc-tab").forEach(function (b) { b.classList.remove("active"); });
      document.querySelectorAll(".tcc-tab-panel").forEach(function (p) { p.classList.remove("active"); });
      btn.classList.add("active");
      var t = $("#tab-" + btn.dataset.tab); if (t) t.classList.add("active");
    });
  });

  // ── Guide dialog ──
  guideTrigger.addEventListener("click", function () { show(guideDialog); });
  guideClose.addEventListener("click", function () { hide(guideDialog); });
  guideDialog.addEventListener("click", function (e) { if (e.target === guideDialog) hide(guideDialog); });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") { if (!guideDialog.hidden) hide(guideDialog); }
  });

  // ── Save dialog ──
  function closeDlg(dlg) { hide(dlg); }
  cardSaveCancel.addEventListener("click", function () { closeDlg(cardSaveDialog); });
  wbSaveCancel.addEventListener("click", function () { closeDlg(wbSaveDialog); });
  [cardSaveDialog, wbSaveDialog].forEach(function (d) { d.addEventListener("click", function (e) { if (e.target === d) closeDlg(d); }); });

  function showSaveDialog(type) {
    currentSaveType = type;
    if (type === "card") { cardSaveFilename.textContent = currentSaveFn; cardAssetsPath.textContent = "Xuqi_LLM\\assets\\人设卡\\" + currentSaveFn; show(cardSaveDialog); }
    else { wbSaveFilename.textContent = currentSaveFn; wbAssetsPath.textContent = "Xuqi_LLM\\assets\\世界书\\" + currentSaveFn; show(wbSaveDialog); }
  }

  // Save-to-assets API
  function apiSave(kind, jsonStr, filename, cb) {
    var ep = kind === "card" ? "./api/save/card" : "./api/save/worldbook";
    var body = kind === "card" ? { card_json: jsonStr, filename: filename } : { worldbook_json: jsonStr, filename: filename };
    fetch(ep, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) { if (!res.ok) throw new Error(res.data.detail || "保存失败"); cb(null, res.data); })
      .catch(function (err) { cb(err); });
  }

  function executeSave(kind) {
    if (!currentSaveJson) return;
    apiSave(kind, currentSaveJson, currentSaveFn, function (err, data) {
      if (err) { toast(err.message, "error"); return; }
      toast("已保存到 " + data.saved_path, "success");
    });
  }

  cardSaveToAssets.addEventListener("click", function () { closeDlg(cardSaveDialog); executeSave("card"); });
  cardSaveBrowse.addEventListener("click", function () { closeDlg(cardSaveDialog); downloadJSON(currentSaveFn, currentSaveJson); });
  wbSaveToAssets.addEventListener("click", function () { closeDlg(wbSaveDialog); executeSave("wb"); });
  wbSaveBrowse.addEventListener("click", function () { closeDlg(wbSaveDialog); downloadJSON(currentSaveFn, currentSaveJson); });

  function updateSaveHint(hintEl, labelEl, label) { labelEl.textContent = label; show(hintEl); }

  // ═══════════════════════════════════════════════
  //  GENERAL CARD CONVERTER (sections-based)
  // ═══════════════════════════════════════════════

  function renderGeneralSections(sections) {
    genSectionsData = sections;
    var html = "";
    sections.forEach(function (sec, idx) {
      html += '<div class="tcc-section">';
      html += '<div class="tcc-section-header">';
      html += '<span class="tcc-section-title">' + escapeHtml(sec.title) + '</span>';
      if (sec.has_content && sec.entry_count != null) {
        html += '<span class="tcc-section-badge">' + sec.entry_count + ' 条</span>';
      }
      if (!sec.has_content) {
        html += '<span class="tcc-section-badge tcc-section-empty">无</span>';
      }
      html += '</div>';

      if (sec.has_content) {
        if (sec.json) {
          html += '<pre class="tcc-json-block tcc-section-json" id="gen-sec-json-' + idx + '">' + escapeHtml(String(sec.json).substring(0, 12000)) + '</pre>';
        } else if (sec.content) {
          html += '<div class="tcc-section-content">' + escapeHtml(sec.content) + '</div>';
        }
        html += '<div class="tcc-actions-inline">';
        if (sec.json) {
          html += '<button class="tcc-btn tcc-btn-sm gen-dl-btn" data-idx="' + idx + '">下载 JSON</button>';
          html += '<button class="tcc-btn tcc-btn-sm gen-copy-btn" data-idx="' + idx + '">复制</button>';
        }
        html += '</div>';
      } else {
        html += '<p class="tcc-section-reason">' + escapeHtml(sec.reason || "未检测到内容") + '</p>';
      }
      html += '</div>';
    });
    genSections.innerHTML = html;

    // Attach event listeners
    genSections.querySelectorAll(".gen-dl-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var i = parseInt(btn.dataset.idx);
        var s = genSectionsData[i];
        if (!s || !s.json) return;
        currentSaveJson = String(s.json);
        currentSaveFn = s.filename || (s.title + ".json");
        showSaveDialog(s.type === "worldbook" ? "wb" : "card");
      });
    });
    genSections.querySelectorAll(".gen-copy-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var i = parseInt(btn.dataset.idx);
        var s = genSectionsData[i];
        if (s && s.json) copyToClipboard(String(s.json));
      });
    });
  }

  function escapeHtml(str) {
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  setupDropZone(genDropZone, genFileInput, function (files) {
    var file = files[0]; if (!file) return;
    if (!file.name.toLowerCase().endsWith(".png")) { showError(genError, "请上传 PNG 格式的酒馆角色卡"); return; }
    clearError(genError); hide(genPreview); hide(genResult); show(genResultEmpty);
    hide(genPureHint); genSections.innerHTML = "";
    genDlPngBtn.disabled = true; genPngB64 = ""; genPngFn = ""; genSectionsData = [];
    show(genParsingHint);

    var form = new FormData(); form.append("file", file);
    fetch("./api/convert/card/general", { method: "POST", body: form })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        hide(genParsingHint);
        if (!res.ok) throw new Error(res.data.detail || "转换失败");
        var d = res.data;

        // Warning: completely empty card
        if (d.warning === "empty_card") {
          showWarning(genError, d.message || "这个PNG文件没有包含任何可识别的内容喵~");
          hide(genResultEmpty); hide(genPreview);
          return;
        }
        clearError(genError);

        genPreviewImg.src = d.preview_png; show(genPreview);
        genPngB64 = d.clean_png_base64; genPngFn = d.clean_png_filename;

        if (d.is_pure_character) show(genPureHint);

        hide(genResultEmpty);
        renderGeneralSections(d.sections);
        show(genResult);
        genDlPngBtn.disabled = false;

        var hasWb = d.sections.some(function (s) { return s.type === "worldbook" && s.has_content; });
        var hasCard = d.sections.some(function (s) { return s.type === "card" && s.has_content; });
        var msg = "解析完成";
        if (hasWb) msg += " · 含世界书";
        if (hasCard) msg += " · 含角色卡";
        if (!hasWb && !hasCard) msg += " · 未检测到角色卡或世界书";
        toast(msg, "success");
      })
      .catch(function (err) {
        hide(genParsingHint);
        showError(genError, err.message);
      });
  });

  genDlPngBtn.addEventListener("click", function () { if (genPngB64) { downloadBlob(genPngFn, genPngB64, "image/png"); toast("纯图片已下载", "success"); } });
  genChangePath.addEventListener("click", function (e) { e.preventDefault(); showSaveDialog("card"); });

  // ═══════════════════════════════════════════════
  //  PURE CARD CONVERTER
  // ═══════════════════════════════════════════════

  setupDropZone(cardDropZone, cardFileInput, function (files) {
    var file = files[0]; if (!file) return;
    if (!file.name.toLowerCase().endsWith(".png")) { showError(cardError, "请上传 PNG 格式的酒馆角色卡"); return; }
    clearError(cardError); hide(cardPreview); hide(cardResult); show(cardResultEmpty);
    cardDownloadBtn.disabled = true; cardCopyBtn.disabled = true; cardDownloadPngBtn.disabled = true;
    cardJsonText = ""; cardFilename = ""; cardPngB64 = ""; cardPngFn = "";
    show(cardParsingHint);

    var form = new FormData(); form.append("file", file);
    fetch("./api/convert/card", { method: "POST", body: form })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        hide(cardParsingHint);
        if (!res.ok) throw new Error(res.data.detail || "转换失败");
        var d = res.data;

        // Warning: worldbook-only card in pure converter
        if (d.warning === "worldbook_only") {
          showWarning(cardError,
            d.message + ' <a class="tcc-warning-link">点击前往角色卡通用转换 →</a>',
            function () { switchToTab("general"); });
          hide(cardResult);
          return;
        }

        cardJsonText = d.card_json; cardFilename = d.filename;
        cardPngB64 = d.clean_png_base64; cardPngFn = d.clean_png_filename;

        cardPreviewImg.src = d.preview_png; show(cardPreview);
        hide(cardResultEmpty); cardResultName.textContent = d.card.name || "未命名角色";

        var p = d.preserved_fields || [];
        if (p.length) { cardResultPreserved.textContent = "已保留: " + p.join(", "); cardResultPreserved.className = "tcc-preserved-badge tcc-preserved-has"; }
        else { cardResultPreserved.textContent = "无额外信息保留"; cardResultPreserved.className = "tcc-preserved-badge tcc-preserved-none"; }

        cardJsonOutput.textContent = cardJsonText;
        show(cardResult);
        cardDownloadBtn.disabled = false; cardCopyBtn.disabled = false; cardDownloadPngBtn.disabled = false;
        toast("角色卡转换成功" + (p.length ? " · 已保留 " + p.length + " 项" : ""), "success");
      })
      .catch(function (err) { hide(cardParsingHint); showError(cardError, err.message); });
  });

  cardDownloadBtn.addEventListener("click", function () {
    if (!cardJsonText) return;
    currentSaveJson = cardJsonText; currentSaveFn = cardFilename;
    if (cardSaveMode === "assets") apiSave("card", cardJsonText, cardFilename, function (err, data) { if (err) { toast(err.message, "error"); return; } toast("已保存到 assets\\人设卡\\" + data.filename, "success"); });
    else if (cardSaveMode === "browse") downloadJSON(cardFilename, cardJsonText);
    else showSaveDialog("card");
  });
  cardCopyBtn.addEventListener("click", function () { if (cardJsonText) copyToClipboard(cardJsonText); });
  cardDownloadPngBtn.addEventListener("click", function () { if (cardPngB64) { downloadBlob(cardPngFn, cardPngB64, "image/png"); toast("纯图片已下载", "success"); } });
  cardChangePath.addEventListener("click", function (e) { e.preventDefault(); currentSaveJson = cardJsonText; currentSaveFn = cardFilename; showSaveDialog("card"); });

  // ═══════════════════════════════════════════════
  //  WORLDBOOK CONVERTER
  // ═══════════════════════════════════════════════

  setupDropZone(wbDropZone, wbFileInput, function (files) {
    var file = files[0]; if (!file) return;
    var lower = file.name.toLowerCase();
    if (!lower.endsWith(".json") && !lower.endsWith(".jsonc")) { showError(wbError, "请上传 JSON 格式的酒馆世界书"); return; }
    clearError(wbError); hide(wbResult); hide(wbConversionInfo); show(wbResultEmpty);
    wbDownloadBtn.disabled = true; wbCopyBtn.disabled = true; wbJsonText = ""; wbFilename = "";
    show(wbParsingHint);

    var form = new FormData(); form.append("file", file);
    fetch("./api/convert/worldbook", { method: "POST", body: form })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        hide(wbParsingHint);
        if (!res.ok) throw new Error(res.data.detail || "转换失败");
        var d = res.data;

        // Warning: empty worldbook
        if (d.warning === "empty_worldbook") {
          showWarning(wbError, d.message || "这个世界书JSON没有任何条目喵~");
          hide(wbResult);
          return;
        }

        wbJsonText = d.worldbook_json; wbFilename = d.filename;
        hide(wbResultEmpty); wbResultName.textContent = d.filename.replace(/\.json$/i, "");
        wbEntryCount.textContent = "共 " + d.entry_count + " 个条目";

        var info = d.conversion_info;
        if (info) {
          var parts = ["已映射字段: " + info.fields_mapped_from_tavern.length + " 项"];
          if (info.fields_not_preserved_per_entry && info.fields_not_preserved_per_entry.length)
            parts.push("未保留(条目级): " + info.fields_not_preserved_per_entry.join(", "));
          if (info.fields_not_preserved_top_level && info.fields_not_preserved_top_level.length)
            parts.push("未保留(顶层): " + info.fields_not_preserved_top_level.join(", "));
          wbConversionInfo.innerHTML = "<strong>转换说明</strong><br>" + parts.join("<br>");
          show(wbConversionInfo);
        }
        wbJsonOutput.textContent = wbJsonText;
        show(wbResult); wbDownloadBtn.disabled = false; wbCopyBtn.disabled = false;
        toast("世界书转换成功 · " + d.entry_count + " 条", "success");
      })
      .catch(function (err) { hide(wbParsingHint); showError(wbError, err.message); });
  });

  wbDownloadBtn.addEventListener("click", function () {
    if (!wbJsonText) return;
    currentSaveJson = wbJsonText; currentSaveFn = wbFilename;
    if (wbSaveMode === "assets") apiSave("wb", wbJsonText, wbFilename, function (err, data) { if (err) { toast(err.message, "error"); return; } toast("已保存到 assets\\世界书\\" + data.filename, "success"); });
    else if (wbSaveMode === "browse") downloadJSON(wbFilename, wbJsonText);
    else showSaveDialog("wb");
  });
  wbCopyBtn.addEventListener("click", function () { if (wbJsonText) copyToClipboard(wbJsonText); });
  wbChangePath.addEventListener("click", function (e) { e.preventDefault(); currentSaveJson = wbJsonText; currentSaveFn = wbFilename; showSaveDialog("wb"); });

})();
