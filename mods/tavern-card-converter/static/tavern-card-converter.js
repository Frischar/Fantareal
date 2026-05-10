// ── 酒馆卡转换器 · Tavern Card Converter ──

(function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);

  // ── Card DOM ──
  const cardFileInput = $("#card-file-input");
  const cardDropZone = $("#card-drop-zone");
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

  // ── Worldbook DOM ──
  const wbFileInput = $("#wb-file-input");
  const wbDropZone = $("#wb-drop-zone");
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

  // ── Card Save Dialog DOM ──
  const cardSaveDialog = $("#card-save-dialog");
  const cardSaveFilename = $("#card-save-filename");
  const cardAssetsPath = $("#card-assets-path");
  const cardSaveToAssets = $("#card-save-to-assets");
  const cardSaveBrowse = $("#card-save-browse");
  const cardSaveCancel = $("#card-save-cancel");

  // ── Worldbook Save Dialog DOM ──
  const wbSaveDialog = $("#wb-save-dialog");
  const wbSaveFilename = $("#wb-save-filename");
  const wbAssetsPath = $("#wb-assets-path");
  const wbSaveToAssets = $("#wb-save-to-assets");
  const wbSaveBrowse = $("#wb-save-browse");
  const wbSaveCancel = $("#wb-save-cancel");

  // ── State ──
  let cardJsonText = "";
  let cardFilename = "";
  let cardCleanPngBase64 = "";
  let cardCleanPngFilename = "";
  let cardSaveMode = null;   // null | 'assets' | 'browse'

  let wbJsonText = "";
  let wbFilename = "";
  let wbSaveMode = null;

  // ── Helpers ──
  function show(el) { el.hidden = false; }
  function hide(el) { el.hidden = true; }
  function clearError(errEl) { hide(errEl); errEl.textContent = ""; }

  function showError(errEl, msg) {
    errEl.textContent = msg;
    show(errEl);
  }

  function toast(msg, type) {
    var el = document.createElement("div");
    el.className = "tcc-toast tcc-toast-" + (type || "success");
    el.textContent = msg;
    document.body.appendChild(el);
    requestAnimationFrame(function () { el.classList.add("show"); });
    setTimeout(function () {
      el.classList.remove("show");
      setTimeout(function () { el.remove(); }, 350);
    }, 2200);
  }

  function downloadBlob(filename, base64, mime) {
    var byteChars = atob(base64);
    var bytes = new Uint8Array(byteChars.length);
    for (var i = 0; i < byteChars.length; i++) { bytes[i] = byteChars.charCodeAt(i); }
    var blob = new Blob([bytes], { type: mime });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function downloadJSON(filename, text) {
    var blob = new Blob([text], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  async function copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      toast("已复制到剪贴板", "success");
    } catch (_e) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.cssText = "position:fixed;left:-9999px";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      toast("已复制到剪贴板", "success");
    }
  }

  // ── Drop zone ──
  function setupDropZone(zoneEl, inputEl, onFiles) {
    zoneEl.addEventListener("click", function (e) {
      if (e.target === inputEl) return;
      inputEl.click();
    });
    inputEl.addEventListener("change", function () {
      if (inputEl.files && inputEl.files.length) onFiles(inputEl.files);
    });
    zoneEl.addEventListener("dragover", function (e) {
      e.preventDefault();
      zoneEl.classList.add("drag-over");
    });
    zoneEl.addEventListener("dragleave", function () {
      zoneEl.classList.remove("drag-over");
    });
    zoneEl.addEventListener("drop", function (e) {
      e.preventDefault();
      zoneEl.classList.remove("drag-over");
      if (e.dataTransfer && e.dataTransfer.files.length) onFiles(e.dataTransfer.files);
    });
  }

  // ── Tabs ──
  document.querySelectorAll(".tcc-tab").forEach(function (btn) {
    btn.addEventListener("click", function () {
      document.querySelectorAll(".tcc-tab").forEach(function (b) { b.classList.remove("active"); });
      document.querySelectorAll(".tcc-tab-panel").forEach(function (p) { p.classList.remove("active"); });
      btn.classList.add("active");
      var target = $("#tab-" + btn.dataset.tab);
      if (target) target.classList.add("active");
    });
  });

  // ═══════════════════════════════════════════════
  //  Save dialog helpers
  // ═══════════════════════════════════════════════

  function showCardSaveDialog() {
    cardSaveFilename.textContent = cardFilename;
    cardAssetsPath.textContent = "Xuqi_LLM\\assets\\人设卡\\" + cardFilename;
    show(cardSaveDialog);
  }
  function showWbSaveDialog() {
    wbSaveFilename.textContent = wbFilename;
    wbAssetsPath.textContent = "Xuqi_LLM\\assets\\世界书\\" + wbFilename;
    show(wbSaveDialog);
  }

  function closeDialog(dlg) { hide(dlg); }

  // Close buttons
  cardSaveCancel.addEventListener("click", function () { closeDialog(cardSaveDialog); });
  wbSaveCancel.addEventListener("click", function () { closeDialog(wbSaveDialog); });

  // Click overlay background to close
  cardSaveDialog.addEventListener("click", function (e) {
    if (e.target === cardSaveDialog) closeDialog(cardSaveDialog);
  });
  wbSaveDialog.addEventListener("click", function (e) {
    if (e.target === wbSaveDialog) closeDialog(wbSaveDialog);
  });

  // Escape key to close
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      if (!cardSaveDialog.hidden) closeDialog(cardSaveDialog);
      if (!wbSaveDialog.hidden) closeDialog(wbSaveDialog);
    }
  });

  // ── Save-to-assets API calls ──
  function saveCardToAssets(callback) {
    fetch("./api/save/card", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ card_json: cardJsonText, filename: cardFilename })
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.data.detail || "保存失败");
        if (callback) callback(null, res.data);
      })
      .catch(function (err) { if (callback) callback(err); });
  }

  function saveWbToAssets(callback) {
    fetch("./api/save/worldbook", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ worldbook_json: wbJsonText, filename: wbFilename })
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok) throw new Error(res.data.detail || "保存失败");
        if (callback) callback(null, res.data);
      })
      .catch(function (err) { if (callback) callback(err); });
  }

  // ── Update save path hint ──
  function updateCardSaveHint(label) {
    cardSavePathLabel.textContent = label;
    show(cardSavePathHint);
  }
  function updateWbSaveHint(label) {
    wbSavePathLabel.textContent = label;
    show(wbSavePathHint);
  }

  // ═══════════════════════════════════════════════
  //  Card: download button → check save mode
  // ═══════════════════════════════════════════════

  cardDownloadBtn.addEventListener("click", function () {
    if (!cardJsonText) return;
    if (cardSaveMode === "assets") {
      saveCardToAssets(function (err, data) {
        if (err) { toast(err.message, "error"); return; }
        toast("已保存到 assets\\人设卡\\" + data.filename, "success");
      });
    } else if (cardSaveMode === "browse") {
      downloadJSON(cardFilename, cardJsonText);
    } else {
      showCardSaveDialog();
    }
  });

  // Card: save to assets
  cardSaveToAssets.addEventListener("click", function () {
    closeDialog(cardSaveDialog);
    saveCardToAssets(function (err, data) {
      if (err) { toast(err.message, "error"); return; }
      cardSaveMode = "assets";
      updateCardSaveHint("人设卡目录");
      toast("已保存到 assets\\人设卡\\" + data.filename, "success");
    });
  });

  // Card: browse download
  cardSaveBrowse.addEventListener("click", function () {
    closeDialog(cardSaveDialog);
    downloadJSON(cardFilename, cardJsonText);
    cardSaveMode = "browse";
    updateCardSaveHint("本地文件夹");
  });

  // Card: change save path
  cardChangePath.addEventListener("click", function (e) {
    e.preventDefault();
    showCardSaveDialog();
  });

  // ═══════════════════════════════════════════════
  //  Worldbook: download button → check save mode
  // ═══════════════════════════════════════════════

  wbDownloadBtn.addEventListener("click", function () {
    if (!wbJsonText) return;
    if (wbSaveMode === "assets") {
      saveWbToAssets(function (err, data) {
        if (err) { toast(err.message, "error"); return; }
        toast("已保存到 assets\\世界书\\" + data.filename, "success");
      });
    } else if (wbSaveMode === "browse") {
      downloadJSON(wbFilename, wbJsonText);
    } else {
      showWbSaveDialog();
    }
  });

  // Worldbook: save to assets
  wbSaveToAssets.addEventListener("click", function () {
    closeDialog(wbSaveDialog);
    saveWbToAssets(function (err, data) {
      if (err) { toast(err.message, "error"); return; }
      wbSaveMode = "assets";
      updateWbSaveHint("世界书目录");
      toast("已保存到 assets\\世界书\\" + data.filename, "success");
    });
  });

  // Worldbook: browse download
  wbSaveBrowse.addEventListener("click", function () {
    closeDialog(wbSaveDialog);
    downloadJSON(wbFilename, wbJsonText);
    wbSaveMode = "browse";
    updateWbSaveHint("本地文件夹");
  });

  // Worldbook: change save path
  wbChangePath.addEventListener("click", function (e) {
    e.preventDefault();
    showWbSaveDialog();
  });

  // ═══════════════════════════════════════════════
  //  Card conversion
  // ═══════════════════════════════════════════════

  setupDropZone(cardDropZone, cardFileInput, function (files) {
    var file = files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".png")) {
      showError(cardError, "请上传 PNG 格式的酒馆角色卡");
      return;
    }
    clearError(cardError);
    hide(cardPreview);
    hide(cardResult);
    show(cardResultEmpty);
    cardDownloadBtn.disabled = true;
    cardCopyBtn.disabled = true;
    cardDownloadPngBtn.disabled = true;
    cardJsonText = "";
    cardFilename = "";
    cardCleanPngBase64 = "";
    cardCleanPngFilename = "";

    var form = new FormData();
    form.append("file", file);

    fetch("./api/convert/card", { method: "POST", body: form })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok) { throw new Error(res.data.detail || "转换失败"); }
        var d = res.data;
        cardJsonText = d.card_json;
        cardFilename = d.filename;
        cardCleanPngBase64 = d.clean_png_base64;
        cardCleanPngFilename = d.clean_png_filename;

        cardPreviewImg.src = d.preview_png;
        show(cardPreview);

        hide(cardResultEmpty);
        cardResultName.textContent = d.card.name || "未命名角色";

        var preserved = d.preserved_fields || [];
        if (preserved.length > 0) {
          cardResultPreserved.textContent = "已保留: " + preserved.join(", ");
          cardResultPreserved.className = "tcc-preserved-badge tcc-preserved-has";
        } else {
          cardResultPreserved.textContent = "无额外信息保留";
          cardResultPreserved.className = "tcc-preserved-badge tcc-preserved-none";
        }

        cardJsonOutput.textContent = d.card_json;
        show(cardResult);
        cardDownloadBtn.disabled = false;
        cardCopyBtn.disabled = false;
        cardDownloadPngBtn.disabled = false;
        var toastMsg = "角色卡转换成功";
        if (preserved.length > 0) {
          toastMsg += " · 已保留 " + preserved.length + " 项额外信息";
        }
        toast(toastMsg, "success");
      })
      .catch(function (err) {
        showError(cardError, err.message);
      });
  });

  cardCopyBtn.addEventListener("click", function () {
    if (cardJsonText) copyToClipboard(cardJsonText);
  });

  cardDownloadPngBtn.addEventListener("click", function () {
    if (cardCleanPngBase64 && cardCleanPngFilename) {
      downloadBlob(cardCleanPngFilename, cardCleanPngBase64, "image/png");
      toast("纯图片已下载", "success");
    }
  });

  // ═══════════════════════════════════════════════
  //  Worldbook conversion
  // ═══════════════════════════════════════════════

  setupDropZone(wbDropZone, wbFileInput, function (files) {
    var file = files[0];
    if (!file) return;
    var lower = file.name.toLowerCase();
    if (!lower.endsWith(".json") && !lower.endsWith(".jsonc")) {
      showError(wbError, "请上传 JSON 格式的酒馆世界书");
      return;
    }
    clearError(wbError);
    hide(wbResult);
    hide(wbConversionInfo);
    show(wbResultEmpty);
    wbDownloadBtn.disabled = true;
    wbCopyBtn.disabled = true;
    wbJsonText = "";
    wbFilename = "";

    var form = new FormData();
    form.append("file", file);

    fetch("./api/convert/worldbook", { method: "POST", body: form })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (!res.ok) { throw new Error(res.data.detail || "转换失败"); }
        var d = res.data;
        wbJsonText = d.worldbook_json;
        wbFilename = d.filename;

        hide(wbResultEmpty);
        wbResultName.textContent = d.filename.replace(/\.json$/i, "");
        wbEntryCount.textContent = "共 " + d.entry_count + " 个条目";

        var info = d.conversion_info;
        if (info) {
          var parts = [];
          parts.push("已映射字段: " + info.fields_mapped_from_tavern.length + " 项");
          if (info.fields_not_preserved_per_entry && info.fields_not_preserved_per_entry.length > 0) {
            parts.push("未保留(条目级): " + info.fields_not_preserved_per_entry.join(", "));
          }
          if (info.fields_not_preserved_top_level && info.fields_not_preserved_top_level.length > 0) {
            parts.push("未保留(顶层): " + info.fields_not_preserved_top_level.join(", "));
          }
          wbConversionInfo.innerHTML = "<strong>转换说明</strong><br>" + parts.join("<br>");
          show(wbConversionInfo);
        }

        wbJsonOutput.textContent = d.worldbook_json;
        show(wbResult);
        wbDownloadBtn.disabled = false;
        wbCopyBtn.disabled = false;
        toast("世界书转换成功 · " + d.entry_count + " 条", "success");
      })
      .catch(function (err) {
        showError(wbError, err.message);
      });
  });

  wbCopyBtn.addEventListener("click", function () {
    if (wbJsonText) copyToClipboard(wbJsonText);
  });

})();
