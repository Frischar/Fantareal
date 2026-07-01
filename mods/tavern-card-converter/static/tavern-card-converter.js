// 酒馆卡转换器 v0.3.0 · 反向模式（Fantareal → 酒馆卡）

(function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  const els = {
    tabs: $$(".tcc-tab"),
    panels: $$(".tcc-tab-panel"),

    guideDialog: $("#tcc-guide-dialog"),
    guideTrigger: $("#tcc-guide-trigger"),
    guideClose: $("#tcc-guide-close"),

    gen: {
      panel: $("#tab-general"),
      input: $("#general-file-input"),
      drop: $("#general-drop-zone"),
      parsing: $("#general-parsing-hint"),
      error: $("#general-error"),
      preview: $("#general-preview"),
      previewImg: $("#general-preview-img"),
      fileSummary: $("#general-file-summary"),
      empty: $("#general-result-empty"),
      result: $("#general-result"),
      pureHint: $("#general-pure-hint"),
      sections: $("#general-sections"),
      tools: $("#general-result-tools"),
      pngBtn: $("#general-download-png-btn")
    },

    card: {
      panel: $("#tab-card"),
      input: $("#card-file-input"),
      drop: $("#card-drop-zone"),
      parsing: $("#card-parsing-hint"),
      error: $("#card-error"),
      preview: $("#card-preview"),
      previewImg: $("#card-preview-img"),
      fileSummary: $("#card-file-summary"),
      empty: $("#card-result-empty"),
      result: $("#card-result"),
      resultName: $("#card-result-name"),
      preserved: $("#card-result-preserved"),
      body: $("#card-result-body"),
      jsonOutput: $("#card-json-output"),
      tools: $("#card-result-tools"),
      downloadBtn: $("#card-download-btn"),
      copyBtn: $("#card-copy-btn"),
      pngBtn: $("#card-download-png-btn")
    },

    wb: {
      panel: $("#tab-worldbook"),
      input: $("#wb-file-input"),
      drop: $("#wb-drop-zone"),
      parsing: $("#wb-parsing-hint"),
      error: $("#wb-error"),
      fileSummary: $("#wb-file-summary"),
      empty: $("#wb-result-empty"),
      result: $("#wb-result"),
      resultName: $("#wb-result-name"),
      entryCount: $("#wb-entry-count"),
      conversionInfo: $("#wb-conversion-info"),
      body: $("#wb-result-body"),
      jsonOutput: $("#wb-json-output"),
      tools: $("#wb-result-tools"),
      downloadBtn: $("#wb-download-btn"),
      copyBtn: $("#wb-copy-btn")
    },

    cardSaveDialog: $("#card-save-dialog"),
    cardSaveFilename: $("#card-save-filename"),
    cardAssetsPath: $("#card-assets-path"),
    cardSaveToAssets: $("#card-save-to-assets"),
    cardSaveBrowse: $("#card-save-browse"),
    cardSaveCancel: $("#card-save-cancel"),

    wbSaveDialog: $("#wb-save-dialog"),
    wbSaveFilename: $("#wb-save-filename"),
    wbAssetsPath: $("#wb-assets-path"),
    wbSaveToAssets: $("#wb-save-to-assets"),
    wbSaveBrowse: $("#wb-save-browse"),
    wbSaveCancel: $("#wb-save-cancel"),

    modeSwitch: $("#tcc-mode-switch"),
    modeLabel: $("#tcc-mode-label"),
    forwardWorkbench: $("#tcc-forward-workbench"),
    reverseWorkbench: $("#tcc-reverse-workbench"),

    rv: {
      drop: $("#reverse-drop-zone"),
      input: $("#reverse-file-input"),
      preview: $("#reverse-preview"),
      previewImg: $("#reverse-preview-img"),
      fileSummary: $("#reverse-file-summary"),
      jsonInput: $("#reverse-json-input"),
      jsonFile: $("#reverse-json-file"),
      jsonImportBtn: $("#reverse-json-import-btn"),
      jsonDropArea: $("#reverse-json-import-area"),
      cwLoadBtn: $("#reverse-cw-load-btn"),
      cwList: $("#reverse-cw-list"),
      form: $("#reverse-form"),
      validation: $("#reverse-validation"),
      generateBtn: $("#reverse-generate-btn"),
      result: $("#reverse-result"),
      resultBody: $("#reverse-result-body"),
      resultActions: $("#reverse-result-actions"),
      downloadBtn: $("#reverse-download-btn"),
      copyJsonBtn: $("#reverse-copy-json-btn"),
      name: $("#rv-name"),
      firstMes: $("#rv-first-mes"),
      description: $("#rv-description"),
      personality: $("#rv-personality"),
      scenario: $("#rv-scenario"),
      mesExample: $("#rv-mes-example"),
      creatorNotes: $("#rv-creator-notes"),
      tags: $("#rv-tags"),
      creator: $("#rv-creator"),
      charVersion: $("#rv-char-version"),

      wbJsonInput: $("#rv-wb-json-input"),
      wbFile: $("#rv-wb-file"),
      wbDropArea: $("#rv-wb-import-area"),
      wbGenerateBtn: $("#rv-wb-generate-btn"),
      wbCwLoadBtn: $("#rv-wb-cw-load-btn"),
      wbCwList: $("#rv-wb-cw-list"),
      wbError: $("#rv-wb-error"),
      wbResultEmpty: $("#rv-wb-result-empty"),
      wbResult: $("#rv-wb-result"),
      wbResultBody: $("#rv-wb-result-body"),
      wbDownloadBtn: $("#rv-wb-download-btn"),
      wbCopyBtn: $("#rv-wb-copy-btn"),
    },

    subTabs: $$(".tcc-sub-tab"),
    rvPanels: $$(".tcc-rv-panel"),
  };

  let genPngB64 = "";
  let genPngFn = "";
  let genSectionsData = [];
  let cardJsonText = "";
  let cardFilename = "";
  let cardPngB64 = "";
  let cardPngFn = "";
  let wbJsonText = "";
  let wbFilename = "";
  let currentSaveJson = "";
  let currentSaveFn = "";

  let currentWorkbenchMode = "forward";
  let modePortraitFile = null;
  let modePortraitPreviewUrl = "";
  let modeGeneratedPngB64 = "";
  let modeGeneratedFilename = "";
  let modeTavernJson = "";
  let rvWbJsonText = "";
  let rvWbFilename = "";

  function show(el) { if (el) el.hidden = false; }
  function hide(el) { if (el) el.hidden = true; }
  function setHtml(el, html) { if (el) el.innerHTML = html; }
  function setText(el, text) { if (el) el.textContent = text; }
  function clearError(el) { if (el) { el.textContent = ""; el.innerHTML = ""; hide(el); } }
  function showError(el, msg) { if (el) { el.textContent = msg || "发生未知错误"; show(el); } }
  function showWarning(el, html, clickHandler) {
    if (!el) return;
    el.innerHTML = html || "请检查文件。";
    const link = el.querySelector(".tcc-warning-link");
    if (link && clickHandler) link.addEventListener("click", clickHandler);
    show(el);
  }
  function escapeHtml(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
  function truncateText(str, max) {
    const s = String(str == null ? "" : str).trim();
    if (!s) return "未填写";
    return s.length > max ? s.slice(0, max) + "…" : s;
  }
  function parseJsonMaybe(text) {
    try { return JSON.parse(text); } catch (_) { return null; }
  }
  function textSize(text) {
    const len = String(text || "").length;
    if (len < 1000) return len + " 字符";
    return (len / 1000).toFixed(1) + "k 字符";
  }
  function toast(msg, type) {
    const el = document.createElement("div");
    el.className = "tcc-toast tcc-toast-" + (type || "success");
    el.textContent = msg;
    document.body.appendChild(el);
    requestAnimationFrame(() => el.classList.add("show"));
    setTimeout(() => {
      el.classList.remove("show");
      setTimeout(() => el.remove(), 300);
    }, 2200);
  }
  function switchToTab(tabName) {
    const btn = document.querySelector('.tcc-tab[data-tab="' + tabName + '"]');
    if (btn) btn.click();
  }

  function downloadBlob(filename, base64, mime) {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || "image.png";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
  function downloadJSON(filename, text) {
    const blob = new Blob([text || "{}"], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || "converted.json";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
  async function copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text || "");
      toast("已复制到剪贴板", "success");
    } catch (_) {
      const ta = document.createElement("textarea");
      ta.value = text || "";
      ta.style.cssText = "position:fixed;left:-9999px;top:-9999px";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      toast("已复制到剪贴板", "success");
    }
  }

  function setupDropZone(zoneEl, inputEl, onFiles) {
    if (!zoneEl || !inputEl) return;
    zoneEl.addEventListener("click", (e) => {
      if (e.target !== inputEl) inputEl.click();
    });
    inputEl.addEventListener("change", () => {
      if (inputEl.files && inputEl.files.length) onFiles(inputEl.files);
      inputEl.value = "";
    });
    zoneEl.addEventListener("dragover", (e) => {
      e.preventDefault();
      zoneEl.classList.add("drag-over");
    });
    zoneEl.addEventListener("dragleave", () => zoneEl.classList.remove("drag-over"));
    zoneEl.addEventListener("drop", (e) => {
      e.preventDefault();
      zoneEl.classList.remove("drag-over");
      if (e.dataTransfer && e.dataTransfer.files.length) onFiles(e.dataTransfer.files);
    });
  }

  function setPanelHasResult(panel, hasResult) {
    if (!panel) return;
    panel.classList.toggle("tcc-has-result", !!hasResult);
  }
  function setLoading(tab, loading) {
    if (!tab) return;
    if (tab.drop) tab.drop.classList.toggle("is-loading", !!loading);
    if (tab.input) tab.input.disabled = !!loading;
  }
  function renderFileSummary(el, title, chips) {
    if (!el) return;
    const chipHtml = (chips || []).map((chip) => {
      const label = typeof chip === "string" ? chip : chip.label;
      const cls = typeof chip === "string" ? "" : (chip.cls || "");
      return '<span class="tcc-chip ' + escapeHtml(cls) + '">' + escapeHtml(label) + '</span>';
    }).join("");
    el.innerHTML = '<strong class="tcc-file-summary-title">' + escapeHtml(title || "当前文件") + '</strong><div class="tcc-file-chips">' + chipHtml + '</div>';
    show(el);
  }

  function summaryItem(label, value) {
    return '<div class="tcc-summary-item"><span class="tcc-summary-label">' + escapeHtml(label) + '</span><span class="tcc-summary-value">' + escapeHtml(value) + '</span></div>';
  }
  function chip(label, cls) {
    return { label: label, cls: cls || "" };
  }
  function actionButton(label, cls, dataAttrs) {
    let attrs = "";
    Object.keys(dataAttrs || {}).forEach((key) => {
      attrs += " data-" + key + '="' + escapeHtml(dataAttrs[key]) + '"';
    });
    return '<button class="tcc-btn ' + escapeHtml(cls || "") + '" type="button"' + attrs + '>' + escapeHtml(label) + '</button>';
  }
  function detailsBlock(title, innerHtml, open) {
    return '<details class="tcc-details"' + (open ? " open" : "") + '><summary>' + escapeHtml(title) + '</summary><div class="tcc-details-body">' + innerHtml + '</div></details>';
  }
  function jsonDetails(text, title) {
    return detailsBlock(title || "完整 JSON", '<pre class="tcc-json-block tcc-json-mini">' + escapeHtml(String(text || "").slice(0, 300000)) + '</pre>', false);
  }
  function contentBlock(title, content, max) {
    return '<div class="tcc-detail-block"><h4>' + escapeHtml(title) + '</h4><pre class="tcc-detail-text">' + escapeHtml(truncateText(content, max || 12000)) + '</pre></div>';
  }
  function resultCard(options) {
    const badge = options.badge ? '<span class="tcc-result-badge">' + escapeHtml(options.badge) + '</span>' : "";
    const summary = (options.summary || []).join("");
    const actions = (options.actions || []).join("");
    const details = (options.details || []).join("");
    return '<article class="tcc-result-card ' + escapeHtml(options.extraClass || "") + '">' +
      '<div class="tcc-result-card-main">' +
        '<div class="tcc-result-card-head">' +
          '<div class="tcc-result-title"><span class="tcc-result-icon">' + escapeHtml(options.icon || "◇") + '</span><div><h3>' + escapeHtml(options.title || "转换结果") + '</h3><span class="tcc-result-subtitle">' + escapeHtml(options.subtitle || "") + '</span></div></div>' + badge +
        '</div>' +
        (summary ? '<div class="tcc-result-summary">' + summary + '</div>' : "") +
        (actions ? '<div class="tcc-result-actions">' + actions + '</div>' : "") +
      '</div>' + details +
    '</article>';
  }

  function buildWorldbookEntriesHtml(wb, limit) {
    const entries = wb && Array.isArray(wb.entries) ? wb.entries : [];
    if (!entries.length) return '<p class="tcc-detail-text">未检测到世界书条目。</p>';
    const max = Math.min(entries.length, limit || 60);
    let html = '<div class="tcc-entry-list">';
    for (let i = 0; i < max; i++) {
      const entry = entries[i] || {};
      const title = entry.note || entry.trigger || ("条目 " + (i + 1));
      const trigger = entry.trigger || "无主关键词";
      const second = entry.secondary_trigger ? " / " + entry.secondary_trigger : "";
      const meta = (entry.entry_type || "keyword") + " · 顺序 " + (entry.order == null ? "-" : entry.order);
      html += '<details class="tcc-entry">' +
        '<summary><span class="tcc-entry-title">' + escapeHtml(String(i + 1).padStart(2, "0") + ". " + title) + '</span><span class="tcc-entry-meta">' + escapeHtml(meta) + '</span></summary>' +
        '<div class="tcc-entry-body">' +
          '<div class="tcc-file-chips"><span class="tcc-chip">主：' + escapeHtml(trigger) + '</span>' + (second ? '<span class="tcc-chip">副：' + escapeHtml(second.slice(3)) + '</span>' : '') + '<span class="tcc-chip ' + (entry.enabled === false ? 'is-empty' : 'is-good') + '">' + (entry.enabled === false ? '停用' : '启用') + '</span></div>' +
          '<pre class="tcc-detail-text">' + escapeHtml(truncateText(entry.content || "", 1800)) + '</pre>' +
        '</div>' +
      '</details>';
    }
    html += '</div>';
    if (entries.length > max) html += '<p class="tcc-detail-text">已显示前 ' + max + ' 条，其余内容可在完整 JSON 中查看。</p>';
    return html;
  }

  function describeSection(sec) {
    if (!sec || !sec.has_content) return "未检测到内容";
    if (sec.type === "worldbook") return "已转换为 Fantareal 世界书格式";
    if (sec.type === "card") return "已转换为 Fantareal 人设卡格式";
    if (sec.type === "depth_prompt") return "来自酒馆扩展字段 depth_prompt";
    if (sec.type === "talkativeness") return "来自酒馆扩展字段 talkativeness";
    return "来自酒馆扩展字段";
  }
  function sectionIcon(type) {
    if (type === "worldbook") return "书";
    if (type === "card") return "卡";
    if (type === "depth_prompt") return "深";
    if (type === "talkativeness") return "量";
    if (type === "regex_scripts") return "正";
    return "◇";
  }
  function getSectionObject(sec) {
    if (!sec || !sec.json) return null;
    return parseJsonMaybe(sec.json);
  }
  function renderGeneralSections(sections) {
    genSectionsData = sections || [];
    if (!els.gen.sections) return;
    const cards = genSectionsData.map((sec, idx) => {
      const has = !!sec.has_content;
      const obj = getSectionObject(sec);
      const isWorldbook = sec.type === "worldbook";
      const isCard = sec.type === "card";
      const count = isWorldbook && obj && Array.isArray(obj.entries) ? obj.entries.length : (sec.entry_count != null ? sec.entry_count : null);
      const name = isCard && obj ? (obj.name || "未命名角色") : (sec.filename || sec.title || "转换结果");

      const summary = [
        summaryItem("类型", sec.title || sec.type || "未知"),
        summaryItem("状态", has ? "已识别" : "无内容"),
        summaryItem(isWorldbook ? "条目" : "大小", isWorldbook ? (count != null ? count + " 条" : "-") : (sec.json ? textSize(sec.json) : textSize(sec.content || "")))
      ];

      let actions = [];
      let details = [];
      if (has) {
        if (sec.json) {
          actions.push(actionButton(isWorldbook ? "保存 / 下载世界书" : "保存 / 下载 JSON", "tcc-btn-primary gen-save-btn", { idx: idx }));
          actions.push(actionButton("复制 JSON", "gen-copy-btn", { idx: idx }));
        }
        if (isWorldbook && obj) {
          details.push(detailsBlock("世界书条目列表", buildWorldbookEntriesHtml(obj, 80), false));
        } else if (isCard && obj) {
          const fieldHtml = '<div class="tcc-details-grid">' +
            contentBlock("基础描述", obj.description || "", 2600) +
            contentBlock("性格", obj.personality || "", 2200) +
            contentBlock("场景", obj.scenario || "", 1800) +
            contentBlock("开场白", obj.first_mes || "", 1400) +
            '</div>';
          details.push(detailsBlock("角色字段预览", fieldHtml, false));
        } else if (sec.content) {
          details.push(detailsBlock("内容预览", contentBlock(sec.title || "内容", sec.content, 4000), false));
        }
        if (sec.json) details.push(jsonDetails(sec.json, "高级：完整 JSON"));
      } else {
        details.push(detailsBlock("原因", '<p class="tcc-detail-text">' + escapeHtml(sec.reason || "未检测到内容") + '</p>', false));
      }

      return resultCard({
        icon: sectionIcon(sec.type),
        title: sec.title || "转换结果",
        subtitle: has ? describeSection(sec) : (sec.reason || "没有可转换内容"),
        badge: has ? (count != null ? count + " 条" : "可用") : "无",
        summary: summary,
        actions: actions,
        details: details,
        extraClass: has ? "" : "is-empty"
      });
    }).join("");
    els.gen.sections.innerHTML = cards;

    $$(".gen-save-btn", els.gen.sections).forEach((btn) => {
      btn.addEventListener("click", () => {
        const i = parseInt(btn.dataset.idx, 10);
        const s = genSectionsData[i];
        if (!s || !s.json) return;
        currentSaveJson = String(s.json);
        currentSaveFn = s.filename || ((s.title || "converted") + ".json");
        showSaveDialog(s.type === "worldbook" ? "wb" : "card");
      });
    });
    $$(".gen-copy-btn", els.gen.sections).forEach((btn) => {
      btn.addEventListener("click", () => {
        const i = parseInt(btn.dataset.idx, 10);
        const s = genSectionsData[i];
        if (s && s.json) copyToClipboard(String(s.json));
      });
    });
  }

  function renderCardResult(d) {
    const card = d.card || parseJsonMaybe(d.card_json) || {};
    const fields = [
      ["名称", card.name || "未命名角色"],
      ["描述", card.description ? "已填写" : "空"],
      ["性格", card.personality ? "已填写" : "空"],
      ["场景", card.scenario ? "已填写" : "空"],
      ["开场白", card.first_mes ? "已填写" : "空"],
      ["示例对话", card.mes_example ? "已填写" : "空"]
    ];
    const chips = fields.map((item) => chip(item[0] + "：" + item[1], item[1] === "空" ? "is-empty" : "is-good"));
    if (d.has_non_character_content) chips.unshift(chip("含附加内容：建议通用转换", "is-warn"));
    renderFileSummary(els.card.fileSummary, d.filename || "角色卡", chips);

    const preserved = d.preserved_fields || [];
    const summary = [
      summaryItem("角色名", card.name || "未命名角色"),
      summaryItem("保留字段", preserved.length ? preserved.length + " 项" : "无"),
      summaryItem("JSON 大小", textSize(d.card_json || ""))
    ];
    const detailHtml = '<div class="tcc-details-grid">' +
      contentBlock("description / 描述", card.description || "", 3200) +
      contentBlock("personality / 性格", card.personality || "", 2600) +
      contentBlock("scenario / 场景", card.scenario || "", 2200) +
      contentBlock("first_mes / 开场白", card.first_mes || "", 1800) +
      contentBlock("mes_example / 示例对话", card.mes_example || "", 2400) +
      (preserved.length ? contentBlock("额外保留字段", preserved.join("\n"), 1800) : "") +
      '</div>';
    const html = renderNonCharacterHint(d) + resultCard({
      icon: "卡",
      title: card.name || "纯角色卡",
      subtitle: d.has_non_character_content ? "已输出角色信息；附加内容建议使用通用转换拆分" : "已转换为 Fantareal 人设卡格式",
      badge: d.has_non_character_content ? "角色信息" : "可保存",
      summary: summary,
      actions: [
        actionButton("保存 / 下载角色卡", "tcc-btn-primary card-save-main", {}),
        actionButton("复制 JSON", "card-copy-main", {}),
        actionButton("下载纯图片", "card-png-main", {})
      ],
      details: [
        detailsBlock("角色字段预览", detailHtml, false),
        jsonDetails(d.card_json || "", "高级：完整 JSON")
      ]
    });
    els.card.body.innerHTML = html;
    $(".card-go-general")?.addEventListener("click", () => switchToTab("general"));
    $(".card-save-main")?.addEventListener("click", () => showSaveDialog("card"));
    $(".card-copy-main")?.addEventListener("click", () => copyToClipboard(cardJsonText));
    $(".card-png-main")?.addEventListener("click", () => {
      if (cardPngB64) {
        downloadBlob(cardPngFn, cardPngB64, "image/png");
        toast("纯图片已下载", "success");
      }
    });
  }

  function renderNonCharacterHint(d) {
    const items = Array.isArray(d.non_character_content) ? d.non_character_content : [];
    if (!d.has_non_character_content && !items.length) return "";
    const chips = items.length
      ? items.map((item) => {
          const label = (item.label || item.type || "附加内容") + (item.detail ? "：" + item.detail : "");
          return '<span class="tcc-chip is-warn">' + escapeHtml(label) + '</span>';
        }).join("")
      : '<span class="tcc-chip is-warn">检测到附加内容</span>';
    return '<article class="tcc-mixed-hint-card">' +
      '<div class="tcc-mixed-hint-icon">!</div>' +
      '<div class="tcc-mixed-hint-main">' +
        '<h3>这张卡不只是纯角色卡</h3>' +
        '<p>当前「纯角色卡转换」只会输出角色信息；检测到的世界书、深度提示、话量设定或其他扩展字段不会在这里拆分成独立结果。建议切换到「角色卡通用转换」重新上传，以获得完整拆分结果。</p>' +
        '<div class="tcc-file-chips">' + chips + '</div>' +
        '<div class="tcc-actions"><button class="tcc-btn tcc-btn-primary card-go-general" type="button">前往角色卡通用转换</button></div>' +
      '</div>' +
    '</article>';
  }

  function renderWorldbookResult(d) {
    const wb = d.worldbook || parseJsonMaybe(d.worldbook_json) || {};
    const entries = Array.isArray(wb.entries) ? wb.entries : [];
    const settings = wb.settings || {};
    const chips = [
      chip("条目：" + entries.length, entries.length ? "is-good" : "is-empty"),
      chip("max_hits：" + (settings.max_hits == null ? "-" : settings.max_hits)),
      chip("递归：" + (settings.recursive_scan_enabled ? "开" : "关"))
    ];
    renderFileSummary(els.wb.fileSummary, d.filename || "世界书", chips);

    const info = d.conversion_info || {};
    if (info && (info.fields_mapped_from_tavern || []).length) {
      els.wb.conversionInfo.innerHTML = '<strong>转换说明</strong>' +
        '<div>已映射字段：' + escapeHtml(info.fields_mapped_from_tavern.length) + ' 项</div>' +
        '<div>输入条目：' + escapeHtml(info.input_entries == null ? entries.length : info.input_entries) + '，输出条目：' + escapeHtml(info.output_entries == null ? entries.length : info.output_entries) + '</div>';
      show(els.wb.conversionInfo);
    } else {
      hide(els.wb.conversionInfo);
    }

    const summary = [
      summaryItem("条目数量", entries.length + " 条"),
      summaryItem("默认命中", settings.max_hits == null ? "-" : String(settings.max_hits)),
      summaryItem("JSON 大小", textSize(d.worldbook_json || ""))
    ];
    const mapText = (info.fields_mapped_from_tavern || []).join("\n");
    const dropText = [
      "条目级未保留：" + ((info.fields_not_preserved_per_entry || []).join(", ") || "无"),
      "顶层未保留：" + ((info.fields_not_preserved_top_level || []).join(", ") || "无")
    ].join("\n");
    const html = resultCard({
      icon: "书",
      title: (d.filename || "世界书").replace(/\.json$/i, ""),
      subtitle: "已转换为 Fantareal 世界书格式",
      badge: entries.length + " 条",
      summary: summary,
      actions: [
        actionButton("保存 / 下载世界书", "tcc-btn-primary wb-save-main", {}),
        actionButton("复制 JSON", "wb-copy-main", {})
      ],
      details: [
        detailsBlock("条目列表", buildWorldbookEntriesHtml(wb, 100), false),
        detailsBlock("字段映射说明", '<div class="tcc-details-grid">' + contentBlock("已映射", mapText || "无", 2500) + contentBlock("未保留字段", dropText, 2500) + '</div>', false),
        jsonDetails(d.worldbook_json || "", "高级：完整 JSON")
      ]
    });
    els.wb.body.innerHTML = html;
    $(".wb-save-main")?.addEventListener("click", () => showSaveDialog("wb"));
    $(".wb-copy-main")?.addEventListener("click", () => copyToClipboard(wbJsonText));
  }

  function closeDlg(dlg) { hide(dlg); }
  function showSaveDialog(type) {
    if (type === "card") {
      setText(els.cardSaveFilename, currentSaveFn);
      setText(els.cardAssetsPath, "Xuqi_LLM\\assets\\人设卡\\" + currentSaveFn);
      show(els.cardSaveDialog);
    } else {
      setText(els.wbSaveFilename, currentSaveFn);
      setText(els.wbAssetsPath, "Xuqi_LLM\\assets\\世界书\\" + currentSaveFn);
      show(els.wbSaveDialog);
    }
  }
  function apiSave(kind, jsonStr, filename, cb) {
    const ep = kind === "card" ? "./api/save/card" : "./api/save/worldbook";
    const body = kind === "card" ? { card_json: jsonStr, filename: filename } : { worldbook_json: jsonStr, filename: filename };
    fetch(ep, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then((r) => r.json().then((d) => ({ ok: r.ok, data: d })))
      .then((res) => {
        if (!res.ok) throw new Error(res.data.detail || "保存失败");
        cb(null, res.data);
      })
      .catch((err) => cb(err));
  }
  function executeSave(kind) {
    if (!currentSaveJson) return;
    apiSave(kind, currentSaveJson, currentSaveFn, (err, data) => {
      if (err) { toast(err.message, "error"); return; }
      toast("已保存到 " + data.saved_path, "success");
    });
  }

  els.tabs.forEach((btn) => {
    btn.addEventListener("click", () => {
      els.tabs.forEach((b) => b.classList.remove("active"));
      els.panels.forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const panel = $("#tab-" + btn.dataset.tab);
      if (panel) panel.classList.add("active");
    });
  });

  if (els.guideTrigger) els.guideTrigger.addEventListener("click", () => show(els.guideDialog));
  if (els.guideClose) els.guideClose.addEventListener("click", () => hide(els.guideDialog));
  if (els.guideDialog) els.guideDialog.addEventListener("click", (e) => { if (e.target === els.guideDialog) hide(els.guideDialog); });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      hide(els.guideDialog);
      hide(els.cardSaveDialog);
      hide(els.wbSaveDialog);
    }
  });

  [els.cardSaveDialog, els.wbSaveDialog].forEach((dlg) => {
    if (dlg) dlg.addEventListener("click", (e) => { if (e.target === dlg) closeDlg(dlg); });
  });
  els.cardSaveCancel?.addEventListener("click", () => closeDlg(els.cardSaveDialog));
  els.wbSaveCancel?.addEventListener("click", () => closeDlg(els.wbSaveDialog));
  els.cardSaveToAssets?.addEventListener("click", () => { closeDlg(els.cardSaveDialog); executeSave("card"); });
  els.cardSaveBrowse?.addEventListener("click", () => { closeDlg(els.cardSaveDialog); downloadJSON(currentSaveFn, currentSaveJson); });
  els.wbSaveToAssets?.addEventListener("click", () => { closeDlg(els.wbSaveDialog); executeSave("wb"); });
  els.wbSaveBrowse?.addEventListener("click", () => { closeDlg(els.wbSaveDialog); downloadJSON(currentSaveFn, currentSaveJson); });

  document.addEventListener("click", (e) => {
    const collapseBtn = e.target.closest(".tcc-collapse-all");
    const expandBtn = e.target.closest(".tcc-expand-all");
    if (collapseBtn) {
      const panel = $("#tab-" + collapseBtn.dataset.target);
      $$("details", panel).forEach((d) => { d.open = false; });
    }
    if (expandBtn) {
      const panel = $("#tab-" + expandBtn.dataset.target);
      $$(".tcc-result-card > .tcc-details", panel).forEach((d) => { d.open = true; });
    }
  });

  setupDropZone(els.gen.drop, els.gen.input, (files) => {
    const file = files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".png")) { showError(els.gen.error, "请上传 PNG 格式的酒馆角色卡"); return; }

    clearError(els.gen.error);
    hide(els.gen.preview);
    hide(els.gen.result);
    hide(els.gen.tools);
    hide(els.gen.fileSummary);
    show(els.gen.empty);
    hide(els.gen.pureHint);
    setHtml(els.gen.sections, "");
    setPanelHasResult(els.gen.panel, false);
    genPngB64 = "";
    genPngFn = "";
    genSectionsData = [];
    els.gen.pngBtn.disabled = true;
    show(els.gen.parsing);
    setLoading(els.gen, true);

    const form = new FormData();
    form.append("file", file);
    fetch("./api/convert/card/general", { method: "POST", body: form })
      .then((r) => r.json().then((d) => ({ ok: r.ok, data: d })))
      .then((res) => {
        hide(els.gen.parsing);
        setLoading(els.gen, false);
        if (!res.ok) throw new Error(res.data.detail || "转换失败");
        const d = res.data;
        if (d.warning === "empty_card") {
          showWarning(els.gen.error, d.message || "这个 PNG 文件没有包含任何可识别的内容。", null);
          hide(els.gen.empty);
          return;
        }
        clearError(els.gen.error);
        els.gen.previewImg.src = d.preview_png;
        show(els.gen.preview);
        genPngB64 = d.clean_png_base64;
        genPngFn = d.clean_png_filename;
        if (d.is_pure_character) show(els.gen.pureHint);
        const sections = d.sections || [];
        renderGeneralSections(sections);
        const chips = sections.map((s) => {
          if (!s.has_content) return chip((s.title || s.type) + "：无", "is-empty");
          if (s.entry_count != null) return chip((s.title || s.type) + "：" + s.entry_count + " 条", "is-good");
          return chip((s.title || s.type) + "：已识别", "is-good");
        });
        renderFileSummary(els.gen.fileSummary, file.name, chips);
        hide(els.gen.empty);
        show(els.gen.result);
        show(els.gen.tools);
        els.gen.pngBtn.disabled = false;
        setPanelHasResult(els.gen.panel, true);
        const hasWb = sections.some((s) => s.type === "worldbook" && s.has_content);
        const hasCard = sections.some((s) => s.type === "card" && s.has_content);
        let msg = "解析完成";
        if (hasWb) msg += " · 含世界书";
        if (hasCard) msg += " · 含角色卡";
        toast(msg, "success");
      })
      .catch((err) => {
        hide(els.gen.parsing);
        setLoading(els.gen, false);
        showError(els.gen.error, err.message);
      });
  });

  els.gen.pngBtn?.addEventListener("click", () => {
    if (!genPngB64) return;
    downloadBlob(genPngFn, genPngB64, "image/png");
    toast("纯图片已下载", "success");
  });

  setupDropZone(els.card.drop, els.card.input, (files) => {
    const file = files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".png")) { showError(els.card.error, "请上传 PNG 格式的酒馆角色卡"); return; }

    clearError(els.card.error);
    hide(els.card.preview);
    hide(els.card.result);
    hide(els.card.tools);
    hide(els.card.fileSummary);
    show(els.card.empty);
    setHtml(els.card.body, "");
    setPanelHasResult(els.card.panel, false);
    cardJsonText = "";
    cardFilename = "";
    cardPngB64 = "";
    cardPngFn = "";
    els.card.downloadBtn.disabled = true;
    els.card.copyBtn.disabled = true;
    els.card.pngBtn.disabled = true;
    show(els.card.parsing);
    setLoading(els.card, true);

    const form = new FormData();
    form.append("file", file);
    fetch("./api/convert/card", { method: "POST", body: form })
      .then((r) => r.json().then((d) => ({ ok: r.ok, data: d })))
      .then((res) => {
        hide(els.card.parsing);
        setLoading(els.card, false);
        if (!res.ok) throw new Error(res.data.detail || "转换失败");
        const d = res.data;
        if (d.warning === "worldbook_only") {
          showWarning(els.card.error, escapeHtml(d.message || "检测到世界书内容。") + ' <a class="tcc-warning-link">前往角色卡通用转换 →</a>', () => switchToTab("general"));
          return;
        }
        cardJsonText = d.card_json;
        cardFilename = d.filename;
        cardPngB64 = d.clean_png_base64;
        cardPngFn = d.clean_png_filename;
        currentSaveJson = cardJsonText;
        currentSaveFn = cardFilename;
        els.card.previewImg.src = d.preview_png;
        show(els.card.preview);
        hide(els.card.empty);
        renderCardResult(d);
        setText(els.card.resultName, (d.card && d.card.name) || "未命名角色");
        setText(els.card.preserved, (d.preserved_fields || []).length ? "已保留 " + d.preserved_fields.length + " 项" : "无额外信息保留");
        setText(els.card.jsonOutput, cardJsonText);
        show(els.card.result);
        show(els.card.tools);
        els.card.downloadBtn.disabled = false;
        els.card.copyBtn.disabled = false;
        els.card.pngBtn.disabled = false;
        setPanelHasResult(els.card.panel, true);
        if (d.has_non_character_content) {
          toast("检测到附加内容，建议试试角色卡通用转换", "warning");
        } else {
          toast("角色卡转换成功", "success");
        }
      })
      .catch((err) => {
        hide(els.card.parsing);
        setLoading(els.card, false);
        showError(els.card.error, err.message);
      });
  });

  els.card.downloadBtn?.addEventListener("click", () => {
    if (!cardJsonText) return;
    currentSaveJson = cardJsonText;
    currentSaveFn = cardFilename;
    showSaveDialog("card");
  });
  els.card.copyBtn?.addEventListener("click", () => { if (cardJsonText) copyToClipboard(cardJsonText); });
  els.card.pngBtn?.addEventListener("click", () => {
    if (!cardPngB64) return;
    downloadBlob(cardPngFn, cardPngB64, "image/png");
    toast("纯图片已下载", "success");
  });

  setupDropZone(els.wb.drop, els.wb.input, (files) => {
    const file = files[0];
    if (!file) return;
    const lower = file.name.toLowerCase();
    if (!lower.endsWith(".json") && !lower.endsWith(".jsonc")) { showError(els.wb.error, "请上传 JSON 格式的酒馆世界书"); return; }

    clearError(els.wb.error);
    hide(els.wb.result);
    hide(els.wb.tools);
    hide(els.wb.conversionInfo);
    hide(els.wb.fileSummary);
    show(els.wb.empty);
    setHtml(els.wb.body, "");
    setPanelHasResult(els.wb.panel, false);
    wbJsonText = "";
    wbFilename = "";
    els.wb.downloadBtn.disabled = true;
    els.wb.copyBtn.disabled = true;
    show(els.wb.parsing);
    setLoading(els.wb, true);

    const form = new FormData();
    form.append("file", file);
    fetch("./api/convert/worldbook", { method: "POST", body: form })
      .then((r) => r.json().then((d) => ({ ok: r.ok, data: d })))
      .then((res) => {
        hide(els.wb.parsing);
        setLoading(els.wb, false);
        if (!res.ok) throw new Error(res.data.detail || "转换失败");
        const d = res.data;
        if (d.warning === "empty_worldbook") {
          showWarning(els.wb.error, d.message || "这个世界书 JSON 没有任何条目。", null);
        }
        wbJsonText = d.worldbook_json;
        wbFilename = d.filename;
        currentSaveJson = wbJsonText;
        currentSaveFn = wbFilename;
        hide(els.wb.empty);
        setText(els.wb.resultName, d.filename.replace(/\.json$/i, ""));
        setText(els.wb.entryCount, "共 " + d.entry_count + " 个条目");
        setText(els.wb.jsonOutput, wbJsonText);
        renderWorldbookResult(d);
        show(els.wb.result);
        show(els.wb.tools);
        els.wb.downloadBtn.disabled = false;
        els.wb.copyBtn.disabled = false;
        setPanelHasResult(els.wb.panel, true);
        toast("世界书转换成功 · " + d.entry_count + " 条", "success");
      })
      .catch((err) => {
        hide(els.wb.parsing);
        setLoading(els.wb, false);
        showError(els.wb.error, err.message);
      });
  });

  els.wb.downloadBtn?.addEventListener("click", () => {
    if (!wbJsonText) return;
    currentSaveJson = wbJsonText;
    currentSaveFn = wbFilename;
    showSaveDialog("wb");
  });
  els.wb.copyBtn?.addEventListener("click", () => { if (wbJsonText) copyToClipboard(wbJsonText); });

  // ═══════════════════════════════════════════════════
  //  Reverse mode (Fantareal → Tavern PNG)
  // ═══════════════════════════════════════════════════

  function switchWorkbenchMode(mode) {
    currentWorkbenchMode = mode;
    if (mode === "reverse") {
      hide(els.forwardWorkbench);
      show(els.reverseWorkbench);
      setText(els.modeSwitch, "返回酒馆卡转换");
      setText(els.modeLabel, "当前：Fantareal → 酒馆卡");
    } else {
      show(els.forwardWorkbench);
      hide(els.reverseWorkbench);
      setText(els.modeSwitch, "模式转换：生成酒馆卡");
      setText(els.modeLabel, "当前：酒馆卡 → Fantareal");
    }
  }

  els.modeSwitch?.addEventListener("click", () => {
    switchWorkbenchMode(currentWorkbenchMode === "forward" ? "reverse" : "forward");
  });

  function collectReverseManualFields() {
    const card = {};
    const pairs = [
      ["name", els.rv.name],
      ["first_mes", els.rv.firstMes],
      ["description", els.rv.description],
      ["personality", els.rv.personality],
      ["scenario", els.rv.scenario],
      ["mes_example", els.rv.mesExample],
      ["creator_notes", els.rv.creatorNotes],
      ["creator", els.rv.creator],
      ["character_version", els.rv.charVersion],
    ];
    for (const [key, el] of pairs) {
      if (el) card[key] = el.value.trim();
    }
    const tagsVal = els.rv.tags ? els.rv.tags.value.trim() : "";
    if (tagsVal) {
      card.tags = tagsVal.split(/[,，]/).map(t => t.trim()).filter(Boolean);
    }
    return card;
  }

  function fillReverseFields(card) {
    if (!card || typeof card !== "object") return;
    const pairs = [
      ["name", els.rv.name],
      ["first_mes", els.rv.firstMes],
      ["description", els.rv.description],
      ["personality", els.rv.personality],
      ["scenario", els.rv.scenario],
      ["mes_example", els.rv.mesExample],
      ["creator_notes", els.rv.creatorNotes],
      ["creator", els.rv.creator],
      ["character_version", els.rv.charVersion],
    ];
    for (const [key, el] of pairs) {
      if (el && card[key] != null) el.value = String(card[key]);
    }
    if (els.rv.tags && Array.isArray(card.tags)) {
      els.rv.tags.value = card.tags.join(", ");
    }
    toast("已导入到表单", "success");
  }

  function parseReverseJsonImport() {
    const text = els.rv.jsonInput ? els.rv.jsonInput.value.trim() : "";
    if (!text) { toast("请先粘贴或输入 JSON", "warning"); return; }
    const obj = parseJsonMaybe(text);
    if (!obj || typeof obj !== "object") { toast("JSON 格式无效", "error"); return; }
    fillReverseFields(obj);
  }

  els.rv.jsonImportBtn?.addEventListener("click", parseReverseJsonImport);

  els.rv.jsonFile?.addEventListener("change", function () {
    if (!this.files || !this.files.length) return;
    const file = this.files[0];
    const reader = new FileReader();
    reader.onload = (e) => {
      if (els.rv.jsonInput) els.rv.jsonInput.value = e.target.result || "";
      parseReverseJsonImport();
    };
    reader.readAsText(file);
    this.value = "";
  });

  // Drag-and-drop for JSON import area
  const jsonDropArea = els.rv.jsonDropArea;
  if (jsonDropArea) {
    jsonDropArea.addEventListener("dragover", (e) => {
      e.preventDefault();
      jsonDropArea.classList.add("is-drag-over");
    });
    jsonDropArea.addEventListener("dragleave", () => {
      jsonDropArea.classList.remove("is-drag-over");
    });
    jsonDropArea.addEventListener("drop", (e) => {
      e.preventDefault();
      jsonDropArea.classList.remove("is-drag-over");
      if (!e.dataTransfer || !e.dataTransfer.files.length) return;
      const file = e.dataTransfer.files[0];
      const lower = file.name.toLowerCase();
      if (!lower.endsWith(".json") && !lower.endsWith(".jsonc")) {
        toast("请拖入 JSON 文件", "error");
        return;
      }
      const reader = new FileReader();
      reader.onload = (ev) => {
        if (els.rv.jsonInput) els.rv.jsonInput.value = ev.target.result || "";
        parseReverseJsonImport();
      };
      reader.readAsText(file);
    });
  }

  function loadCardWriterImports() {
    fetch("./api/card-writer/imports")
      .then((r) => r.json())
      .then((data) => {
        if (!data.success) throw new Error("读取失败");
        const sources = data.sources || [];
        if (!sources.length) { toast("没有找到缃笺项目", "warning"); return; }
        renderCwImportList(sources);
      })
      .catch((err) => toast(err.message, "error"));
  }

  function renderCwImportList(sources) {
    if (!els.rv.cwList) return;
    const html = sources.map((s) => {
      const nameLabel = s.character_name ? escapeHtml(s.character_name) : "未命名";
      const meta = escapeHtml(s.type === "workspace" ? "工作区" : "项目") +
        (s.updated_at ? " · " + escapeHtml(s.updated_at) : "");
      return '<div class="tcc-cw-import-item">' +
        '<div class="tcc-cw-import-item-info">' +
          '<span class="tcc-cw-import-item-name">' + escapeHtml(s.title || nameLabel) + '</span>' +
          '<span class="tcc-cw-import-item-meta">' + meta + '</span>' +
        '</div>' +
        '<button class="tcc-btn tcc-btn-sm" type="button" data-cw-id="' + escapeHtml(s.id) + '">导入</button>' +
      '</div>';
    }).join("");
    els.rv.cwList.innerHTML = html;
    show(els.rv.cwList);

    $$(".tcc-cw-import-item button", els.rv.cwList).forEach((btn) => {
      btn.addEventListener("click", () => importCardWriterSource(btn.dataset.cwId));
    });
  }

  function importCardWriterSource(sourceId) {
    fetch("./api/card-writer/imports/" + encodeURIComponent(sourceId))
      .then((r) => r.json().then((d) => ({ ok: r.ok, data: d })))
      .then((res) => {
        if (!res.ok) throw new Error(res.data.detail || "导入失败");
        fillReverseFields(res.data.card);
      })
      .catch((err) => toast(err.message, "error"));
  }

  els.rv.cwLoadBtn?.addEventListener("click", loadCardWriterImports);

  // Portrait drop zone
  setupDropZone(els.rv.drop, els.rv.input, (files) => {
    const file = files[0];
    if (!file) return;
    const lower = file.name.toLowerCase();
    if (!lower.endsWith(".png") && !lower.endsWith(".jpg") && !lower.endsWith(".jpeg") && !lower.endsWith(".webp")) {
      toast("请上传 PNG/JPEG/WebP 格式的立绘", "error");
      return;
    }
    modePortraitFile = file;
    if (modePortraitPreviewUrl) URL.revokeObjectURL(modePortraitPreviewUrl);
    modePortraitPreviewUrl = URL.createObjectURL(file);
    if (els.rv.previewImg) els.rv.previewImg.src = modePortraitPreviewUrl;
    show(els.rv.preview);
    renderFileSummary(els.rv.fileSummary, file.name, [
      chip(file.type || "图片", "is-good"),
      chip((file.size / 1024).toFixed(1) + " KB"),
    ]);
    toast("立绘已选择", "success");
  });

  function renderReverseValidation(errors, warnings) {
    if (!els.rv.validation) return;
    const parts = [];
    for (const e of (errors || [])) {
      parts.push('<div class="tcc-validation-error">' + escapeHtml(e.message) + '</div>');
    }
    if (parts.length) {
      els.rv.validation.innerHTML = parts.join("");
      show(els.rv.validation);
    } else {
      hide(els.rv.validation);
    }
  }

  function renderReverseResult(response) {
    if (!els.rv.resultBody) return;
    const card = response.card || {};
    const data = (card && card.data) ? card.data : {};
    const warnings = response.warnings || [];

    const summary = [
      summaryItem("角色名", data.name || "未命名"),
      summaryItem("规格", "chara_card_v2 · 2.0"),
      summaryItem("PNG 大小", response.png_base64 ? (response.png_base64.length * 0.75 / 1024).toFixed(1) + " KB" : "-"),
    ];

    const fieldsHtml = '<div class="tcc-details-grid">' +
      contentBlock("description", data.description || "", 2000) +
      contentBlock("first_mes", data.first_mes || "", 1500) +
      contentBlock("personality", data.personality || "", 1000) +
      contentBlock("scenario", data.scenario || "", 1000) +
      '</div>';

    let warningsHtml = "";
    if (warnings.length) {
      const items = warnings.map(w => escapeHtml(w.message)).join("；");
      warningsHtml = '<div class="tcc-conversion-info">提示：' + items + '</div>';
    }

    const html = warningsHtml + resultCard({
      icon: "酒",
      title: data.name || "酒馆角色卡",
      subtitle: "已生成 SillyTavern V2 PNG",
      badge: "可下载",
      summary: summary,
      details: [
        detailsBlock("字段预览", fieldsHtml, false),
        jsonDetails(response.tavern_json || "", "Tavern V2 JSON"),
      ],
    });
    els.rv.resultBody.innerHTML = html;
    show(els.rv.result);
    show(els.rv.resultActions);
  }

  function generateTavernCard() {
    // Front-end pre-validation
    if (!modePortraitFile) {
      renderReverseValidation([{ field: "image", message: "请先上传角色立绘图片" }], []);
      return;
    }
    const name = els.rv.name ? els.rv.name.value.trim() : "";
    const firstMes = els.rv.firstMes ? els.rv.firstMes.value.trim() : "";
    const errors = [];
    if (!name) errors.push({ field: "name", message: "请填写角色名" });
    if (!firstMes) errors.push({ field: "first_mes", message: "请填写开场白" });
    if (errors.length) {
      renderReverseValidation(errors, []);
      return;
    }
    hide(els.rv.validation);

    const form = new FormData();
    form.append("image", modePortraitFile);
    form.append("manual_fields", JSON.stringify(collectReverseManualFields()));

    if (els.rv.generateBtn) els.rv.generateBtn.disabled = true;
    toast("正在生成酒馆 PNG…", "success");

    fetch("./api/convert/fantareal-to-tavern", { method: "POST", body: form })
      .then((r) => r.json().then((d) => ({ ok: r.ok, status: r.status, data: d })))
      .then((res) => {
        if (els.rv.generateBtn) els.rv.generateBtn.disabled = false;
        if (res.status === 422 || !res.data.success) {
          renderReverseValidation(res.data.errors || [], res.data.warnings || []);
          return;
        }
        modeGeneratedPngB64 = res.data.png_base64 || "";
        modeGeneratedFilename = res.data.filename || "tavern_card.png";
        modeTavernJson = res.data.tavern_json || "";
        renderReverseResult(res.data);
        toast("酒馆 PNG 生成成功", "success");
      })
      .catch((err) => {
        if (els.rv.generateBtn) els.rv.generateBtn.disabled = false;
        toast(err.message || "生成失败", "error");
      });
  }

  els.rv.generateBtn?.addEventListener("click", generateTavernCard);

  els.rv.downloadBtn?.addEventListener("click", () => {
    if (!modeGeneratedPngB64) return;
    downloadBlob(modeGeneratedFilename, modeGeneratedPngB64, "image/png");
    toast("酒馆 PNG 已下载", "success");
  });

  els.rv.copyJsonBtn?.addEventListener("click", () => {
    if (modeTavernJson) copyToClipboard(modeTavernJson);
  });

  // ═══════════════════════════════════════════════════
  //  Sub-tab switching (reverse workbench)
  // ═══════════════════════════════════════════════════

  els.subTabs.forEach((btn) => {
    btn.addEventListener("click", () => {
      els.subTabs.forEach((b) => b.classList.remove("active"));
      els.rvPanels.forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const panel = $("#rv-panel-" + btn.dataset.rvTab);
      if (panel) panel.classList.add("active");
    });
  });

  // ═══════════════════════════════════════════════════
  //  Reverse worldbook (Fantareal → Tavern worldbook)
  // ═══════════════════════════════════════════════════

  function generateTavernWorldbookFromFile(file) {
    clearError(els.rv.wbError);
    hide(els.rv.wbResult);
    show(els.rv.wbResultEmpty);
    rvWbJsonText = "";
    rvWbFilename = "";

    const form = new FormData();
    form.append("file", file);
    toast("正在转换世界书…", "success");

    fetch("./api/convert/worldbook-to-tavern", { method: "POST", body: form })
      .then((r) => r.json().then((d) => ({ ok: r.ok, data: d })))
      .then((res) => {
        if (!res.ok) throw new Error(res.data.detail || "转换失败");
        const d = res.data;
        rvWbJsonText = d.tavern_json || "";
        rvWbFilename = d.filename || "tavern_worldbook.json";
        renderReverseWbResult(d);
        toast("世界书转换成功 · " + d.entry_count + " 条", "success");
      })
      .catch((err) => {
        showError(els.rv.wbError, err.message);
      });
  }

  function generateTavernWorldbookFromText(text) {
    clearError(els.rv.wbError);
    if (!text || !text.trim()) {
      showError(els.rv.wbError, "请输入或上传 Fantareal 世界书 JSON");
      return;
    }
    const obj = parseJsonMaybe(text);
    if (!obj || typeof obj !== "object") {
      showError(els.rv.wbError, "JSON 格式无效");
      return;
    }

    // Convert client-side by posting the JSON as a file
    const blob = new Blob([text], { type: "application/json" });
    const file = new File([blob], "worldbook.json", { type: "application/json" });
    generateTavernWorldbookFromFile(file);
  }

  function renderReverseWbResult(d) {
    if (!els.rv.wbResultBody) return;
    const entries = (d.tavern_wb && Array.isArray(d.tavern_wb.entries)) ? d.tavern_wb.entries : [];
    const info = d.conversion_info || {};

    const summary = [
      summaryItem("条目数量", d.entry_count + " 条"),
      summaryItem("映射字段", (info.fields_mapped || []).length + " 项"),
      summaryItem("JSON 大小", textSize(d.tavern_json || "")),
    ];

    // Build entry list using tavern field names
    let entryHtml = "";
    if (entries.length) {
      entryHtml = '<div class="tcc-entry-list">';
      const max = Math.min(entries.length, 80);
      for (let i = 0; i < max; i++) {
        const e = entries[i] || {};
        const name = e.name || e.comment || ("条目 " + (i + 1));
        const keys = Array.isArray(e.key) ? e.key : [];
        const mainKey = keys[0] || "无关键词";
        const meta = (e.constant ? "constant" : "keyword") + " · 位置 " + (e.position || "-");
        entryHtml += '<details class="tcc-entry">' +
          '<summary><span class="tcc-entry-title">' + escapeHtml(String(i + 1).padStart(2, "0") + ". " + name) + '</span><span class="tcc-entry-meta">' + escapeHtml(meta) + '</span></summary>' +
          '<div class="tcc-entry-body">' +
            '<div class="tcc-file-chips"><span class="tcc-chip">keys: ' + escapeHtml(keys.join(", ") || "无") + '</span><span class="tcc-chip ' + (e.disable ? 'is-empty' : 'is-good') + '">' + (e.disable ? '停用' : '启用') + '</span></div>' +
            '<pre class="tcc-detail-text">' + escapeHtml(truncateText(e.content || "", 1800)) + '</pre>' +
          '</div>' +
        '</details>';
      }
      entryHtml += '</div>';
      if (entries.length > max) entryHtml += '<p class="tcc-detail-text">已显示前 ' + max + ' 条。</p>';
    }

    const mappedText = (info.fields_mapped || []).join("\n");
    const defaultText = (info.tavern_defaults_added || []).join(", ");
    const lostText = (info.fields_not_preserved || []).join(", ");

    const html = resultCard({
      icon: "书",
      title: "酒馆世界书",
      subtitle: "已转换为 SillyTavern 世界书格式",
      badge: entries.length + " 条",
      summary: summary,
      details: [
        detailsBlock("条目列表", entryHtml || '<p class="tcc-detail-text">无条目</p>', false),
        detailsBlock("字段映射说明",
          '<div class="tcc-details-grid">' +
            contentBlock("已映射字段", mappedText || "无", 2500) +
            contentBlock("自动填充的 Tavern 默认字段", defaultText || "无", 1500) +
            contentBlock("未保留的 Fantareal 字段", lostText || "无", 1500) +
          '</div>', false),
        jsonDetails(d.tavern_json || "", "完整 JSON"),
      ],
    });
    els.rv.wbResultBody.innerHTML = html;
    hide(els.rv.wbResultEmpty);
    show(els.rv.wbResult);
  }

  // WB: Generate button (from textarea)
  els.rv.wbGenerateBtn?.addEventListener("click", () => {
    const text = els.rv.wbJsonInput ? els.rv.wbJsonInput.value.trim() : "";
    generateTavernWorldbookFromText(text);
  });

  // WB: File input
  els.rv.wbFile?.addEventListener("change", function () {
    if (!this.files || !this.files.length) return;
    const file = this.files[0];
    // Read into textarea first, then send
    const reader = new FileReader();
    reader.onload = (e) => {
      if (els.rv.wbJsonInput) els.rv.wbJsonInput.value = e.target.result || "";
      generateTavernWorldbookFromFile(file);
    };
    reader.readAsText(file);
    this.value = "";
  });

  // WB: Drag-and-drop on import area
  const wbDropArea = els.rv.wbDropArea;
  if (wbDropArea) {
    wbDropArea.addEventListener("dragover", (e) => {
      e.preventDefault();
      wbDropArea.classList.add("is-drag-over");
    });
    wbDropArea.addEventListener("dragleave", () => {
      wbDropArea.classList.remove("is-drag-over");
    });
    wbDropArea.addEventListener("drop", (e) => {
      e.preventDefault();
      wbDropArea.classList.remove("is-drag-over");
      if (!e.dataTransfer || !e.dataTransfer.files.length) return;
      const file = e.dataTransfer.files[0];
      const lower = file.name.toLowerCase();
      if (!lower.endsWith(".json") && !lower.endsWith(".jsonc")) {
        toast("请拖入 JSON 文件", "error");
        return;
      }
      const reader = new FileReader();
      reader.onload = (ev) => {
        if (els.rv.wbJsonInput) els.rv.wbJsonInput.value = ev.target.result || "";
        generateTavernWorldbookFromFile(file);
      };
      reader.readAsText(file);
    });
  }

  // WB: Card Writer import (reuse the same CW list pattern)
  els.rv.wbCwLoadBtn?.addEventListener("click", () => {
    fetch("./api/card-writer/imports")
      .then((r) => r.json())
      .then((data) => {
        if (!data.success) throw new Error("读取失败");
        const sources = data.sources || [];
        if (!sources.length) { toast("没有找到缃笺项目", "warning"); return; }
        if (!els.rv.wbCwList) return;
        const html = sources.map((s) => {
          const nameLabel = s.character_name ? escapeHtml(s.character_name) : "未命名";
          const meta = escapeHtml(s.type === "workspace" ? "工作区" : "项目") +
            (s.updated_at ? " · " + escapeHtml(s.updated_at) : "");
          return '<div class="tcc-cw-import-item">' +
            '<div class="tcc-cw-import-item-info">' +
              '<span class="tcc-cw-import-item-name">' + escapeHtml(s.title || nameLabel) + '</span>' +
              '<span class="tcc-cw-import-item-meta">' + meta + '</span>' +
            '</div>' +
            '<button class="tcc-btn tcc-btn-sm tcc-wb-cw-import" type="button" data-cw-id="' + escapeHtml(s.id) + '">导入世界书</button>' +
          '</div>';
        }).join("");
        els.rv.wbCwList.innerHTML = html;
        show(els.rv.wbCwList);
        $$(".tcc-wb-cw-import", els.rv.wbCwList).forEach((btn) => {
          btn.addEventListener("click", () => {
            const cwId = btn.dataset.cwId;
            fetch("./api/card-writer/imports/" + encodeURIComponent(cwId))
              .then((r) => r.json().then((d) => ({ ok: r.ok, data: d })))
              .then((res) => {
                if (!res.ok) throw new Error(res.data.detail || "导入失败");
                // Try to get worldbook from the project, not persona_card
                // Re-fetch the project to get worldbook
                return fetch("./api/card-writer/imports/" + encodeURIComponent(cwId));
              })
              .then((r) => r.json())
              .then((projData) => {
                // The CW import endpoint only returns persona_card.
                // We need to read the project directly to get worldbook.
                // Use the same endpoint but look for worldbook in the response.
                // Actually, let's just read the file from the CW import route
                // which returns the full card data.
                // For now, inform user that CW worldbook import needs direct file.
                toast("请从缃笺导出项目 JSON 后粘贴到输入框中", "warning");
              })
              .catch((err) => toast(err.message, "error"));
          });
        });
      })
      .catch((err) => toast(err.message, "error"));
  });

  // WB: Download & Copy
  els.rv.wbDownloadBtn?.addEventListener("click", () => {
    if (!rvWbJsonText) return;
    downloadJSON(rvWbFilename, rvWbJsonText);
    toast("酒馆世界书 JSON 已下载", "success");
  });
  els.rv.wbCopyBtn?.addEventListener("click", () => {
    if (rvWbJsonText) copyToClipboard(rvWbJsonText);
  });
})();
