(() => {
  const $ = (selector) => document.querySelector(selector);
  const state = {
    config: {},
    tables: [],
    currentId: "",
    viewMode: localStorage.getItem("xinjian:viewMode") || "card",
    detailIndex: -1,
    currentTemplateId: "",
    currentThemeId: "",
  };

  const SERVICE_PRESETS = {
    custom: { label: "自定义", base_url: "", model: "" },
    deepseek: { label: "DeepSeek", base_url: "https://api.deepseek.com/v1", model: "deepseek-chat" },
    openai: { label: "OpenAI", base_url: "https://api.openai.com/v1", model: "gpt-4.1-mini" },
    minimax: { label: "MiniMax", base_url: "https://api.minimax.chat/v1", model: "MiniMax-Text-01" },
    openrouter: { label: "OpenRouter", base_url: "https://openrouter.ai/api/v1", model: "" },
    siliconflow: { label: "SiliconFlow", base_url: "https://api.siliconflow.cn/v1", model: "" },
  };


  const BUILTIN_THEME_IDS = new Set([
    "standard",
    "gufeng_paper",
    "time_card",
    "moon_white_letter",
    "cinnabar_dossier",
    "jade_slip",
    "midnight_archive",
    "storyboard_frame",
    "status_panel_pro",
  ]);

  const els = {
    status: $("#statusStrip"),
    updateSummaryText: $("#updateSummaryText"),
    tableList: $("#tableList"),
    currentTitle: $("#currentTableTitle"),
    currentDesc: $("#currentTableDesc"),
    rowsEditor: $("#rowsEditor"),
    fieldsEditor: $("#fieldsEditor"),
    schemaId: $("#schemaId"),
    schemaName: $("#schemaName"),
    schemaDesc: $("#schemaDesc"),
    primaryKey: $("#primaryKeySelect"),
    ruleNote: $("#ruleNote"),
    ruleInit: $("#ruleInit"),
    ruleInsert: $("#ruleInsert"),
    ruleUpdate: $("#ruleUpdate"),
    ruleDelete: $("#ruleDelete"),
    ruleIgnore: $("#ruleIgnore"),
    cfgEnabled: $("#cfgEnabled"),
    cfgAutoUpdate: $("#cfgAutoUpdate"),
    cfgNotify: $("#cfgNotify"),
    cfgMujianEnabled: $("#cfgMujianEnabled"),
    cfgMujianTitle: $("#cfgMujianTitle"),
    cfgMujianNote: $("#cfgMujianNote"),
    cfgMujianCollapsed: $("#cfgMujianCollapsed"),
    cfgMujianDisplayMode: $("#cfgMujianDisplayMode"),
    cfgMujianStyle: $("#cfgMujianStyle"),
    cfgMujianTitleStyle: $("#cfgMujianTitleStyle"),
    cfgMujianNoteStyle: $("#cfgMujianNoteStyle"),
    cfgMujianExpand: $("#cfgMujianExpand"),
    cfgMujianDensity: $("#cfgMujianDensity"),
    cfgMujianCharacterFilter: $("#cfgMujianCharacterFilter"),
    cfgMujianCharacterNames: $("#cfgMujianCharacterNames"),
    cfgBaseUrl: $("#cfgBaseUrl"),
    cfgApiKey: $("#cfgApiKey"),
    cfgModel: $("#cfgModel"),
    cfgTurns: $("#cfgTurns"),
    cfgTimeout: $("#cfgTimeout"),
    modelDatalist: $("#modelDatalist"),
    hookStatusText: $("#hookStatusText"),
    logBox: $("#logBox"),
    cardViewBtn: $("#cardViewBtn"),
    tableViewBtn: $("#tableViewBtn"),
    configDrawer: $("#configDrawer"),
    drawerMask: $("#drawerMask"),
    drawerTitle: $("#drawerTitle"),
    rowDetailDrawer: $("#rowDetailDrawer"),
    rowDetailMask: $("#rowDetailMask"),
    rowDetailTitle: $("#rowDetailTitle"),
    rowDetailBody: $("#rowDetailBody"),
    servicePreset: $("#servicePresetSelect"),
    cfgMujianTemplateSelect: $("#cfgMujianTemplateSelect"),
    cfgMujianThemeSelect: $("#cfgMujianThemeSelect"),
    themeSelect: $("#themeSelect"),
    themeName: $("#themeName"),
    themeDesc: $("#themeDesc"),
    themeAuthor: $("#themeAuthor"),
    themePreview: $("#themePreview"),
    exportThemeBtn: $("#exportThemeBtn"),
    deleteThemeBtn: $("#deleteThemeBtn"),
    importThemeInput: $("#importThemeInput"),
    templateSelect: $("#templateSelect"),
    templateName: $("#templateName"),
    templateDesc: $("#templateDesc"),
    templateNoteStyle: $("#templateNoteStyle"),
    templateFieldsEditor: $("#templateFieldsEditor"),
    templateOutput: $("#templateOutput"),
    templatePreview: $("#templatePreview"),
    importTemplateInput: $("#importTemplateInput"),
  };

  function setStatus(text, type = "") {
    if (!els.status) return;
    els.status.textContent = text;
    els.status.className = `status-strip ${type}`.trim();
  }

  let toastTimer = null;
  function pageToast(title, detail = "", type = "ok") {
    let toast = document.getElementById("xinjian-page-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "xinjian-page-toast";
      toast.className = "xinjian-page-toast";
      toast.innerHTML = "<strong></strong><span></span>";
      document.body.appendChild(toast);
    }
    toast.className = `xinjian-page-toast ${type}`;
    toast.querySelector("strong").textContent = title;
    toast.querySelector("span").textContent = detail;
    requestAnimationFrame(() => toast.classList.add("show"));
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => toast.classList.remove("show"), type === "error" ? 6200 : 3600);
  }

  async function requestJson(url, options = {}) {
    const response = await fetch(url, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || payload.message || `请求失败：${response.status}`);
    return payload;
  }

  function currentTable() { return state.tables.find((item) => item.schema.id === state.currentId) || state.tables[0] || null; }
  function escapeHtml(text) { return String(text ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#039;" }[ch])); }
  function escapeAttr(text) { return escapeHtml(text).replace(/`/g, "&#096;"); }
  function fieldLabel(field) { return field.label || field.key; }
  function textValue(value) { return typeof value === "boolean" ? (value ? "是" : "否") : String(value ?? ""); }
  function compactText(value, limit = 76) {
    const text = textValue(value).replace(/\s+/g, " ").trim();
    if (!text) return "—";
    return text.length > limit ? `${text.slice(0, limit)}…` : text;
  }


  function safeTemplateId(value) {
    return String(value || "").trim().toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "") || `template_${Date.now()}`;
  }

  const TEMPLATE_SAMPLE_VALUES = {
    name: "示例角色",
    emotion: "克制中带着松动",
    clothing: "袖口微乱，衣料被动作牵出细褶",
    posture: "半垂眼睫，指尖轻按掌心",
    scene: "泠音阁后楼，灯影与炭火之间",
    sensory_field: "灯影低垂，药气与夜雨潮意交叠",
    body_temperature: "指尖偏凉，掌心余温未散",
    body_motion: "重心微微后撤，肩线仍绷着",
    micro_reaction: "呼吸放缓，眼睫轻颤",
    visual_focus: "视线落在对方手背，又很快移开",
    interaction: "以平稳语气掩住关心，信任在沉默里加深",
    favor_level: "65/100（+2）",
    trust_level: "72/100（+1）",
    guard_level: "18/100（-1）",
    pulse_level: "48/100（-3）",
    summary: "她把情绪收得很轻，却没有再退开。",
  };

  function sampleValueForField(field) {
    const key = safeTemplateId(field?.key || "");
    if (TEMPLATE_SAMPLE_VALUES[key]) return TEMPLATE_SAMPLE_VALUES[key];
    const label = (field?.label || key || "字段").trim();
    const instruction = String(field?.instruction || "").replace(/\s+/g, " ").trim();
    if (instruction) return `${label}示例：${instruction.slice(0, 34)}${instruction.length > 34 ? "…" : ""}`;
    return `${label}示例：这里将显示 ${key || label} 的生成内容`;
  }

  function buildTemplateSample(template) {
    const sample = { ...TEMPLATE_SAMPLE_VALUES };
    (Array.isArray(template?.fields) ? template.fields : []).forEach((field) => {
      const key = safeTemplateId(field?.key || "");
      if (key && key !== "name" && !sample[key]) sample[key] = sampleValueForField(field);
    });
    return sample;
  }

  function mujianTemplates() {
    return Array.isArray(state.config?.mujian_templates) ? state.config.mujian_templates : [];
  }

  function activeTemplateId() {
    return state.currentTemplateId || state.config?.mujian_template_id || mujianTemplates()[0]?.id || "classic";
  }

  function activeTemplate() {
    const id = activeTemplateId();
    return mujianTemplates().find((item) => item.id === id) || mujianTemplates()[0] || { id: "classic", name: "简洁状态", note_style: "classic", fields: [], output_template: "" };
  }

  function renderTemplateText(template, sample = null) {
    const data = sample || buildTemplateSample(template);
    const tpl = String(template?.output_template || "【{name}】\n情绪：{emotion}\n衣着：{clothing}\n神态：{posture}\n互动：{interaction}");
    return tpl.replace(/\{([a-zA-Z0-9_]+)\}/g, (_, key) => textValue(data[key] ?? `（${key} 未生成）`));
  }

  function fieldOutputLine(field) {
    const key = safeTemplateId(field?.key || "");
    const label = String(field?.label || key || "字段").trim();
    return key ? `<${label}({${key}})>` : "";
  }

  function ensureTemplateOutputFields(template) {
    const next = { ...(template || {}) };
    let text = String(next.output_template || "").trim();
    (Array.isArray(next.fields) ? next.fields : []).forEach((field) => {
      const key = safeTemplateId(field?.key || "");
      if (!key || key === "name") return;
      const token = `{${key}}`;
      if (!text.includes(token)) {
        const line = fieldOutputLine(field);
        if (line) text = `${text}${text ? "\n" : ""}${line}`;
      }
    });
    next.output_template = text;
    return next;
  }

  function renderTemplateSelectors() {
    const templates = mujianTemplates();
    const active = activeTemplateId();
    const options = templates.map((item) => {
      const selected = item.id === active ? "selected" : "";
      return `<option value="${escapeAttr(item.id)}" ${selected}>${escapeHtml(item.name || item.id)}</option>`;
    }).join("");
    if (els.cfgMujianTemplateSelect) els.cfgMujianTemplateSelect.innerHTML = options;
    if (els.templateSelect) els.templateSelect.innerHTML = options;
  }


  function safeThemeId(value) {
    return String(value || "").trim().toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "") || `theme_${Date.now()}`;
  }

  function mujianThemePacks() {
    return Array.isArray(state.config?.mujian_theme_packs) ? state.config.mujian_theme_packs : [];
  }

  function activeThemeId() {
    return state.currentThemeId || state.config?.mujian_theme_id || mujianThemePacks()[0]?.id || "standard";
  }

  function activeThemePack() {
    const id = activeThemeId();
    return mujianThemePacks().find((item) => item.id === id) || mujianThemePacks()[0] || {
      id: "standard",
      name: "标准样式",
      description: "默认样式",
      style: { class_name: "theme-standard", accent: "#c98263" },
    };
  }


  function isBuiltinThemePack(packOrId) {
    const id = typeof packOrId === "string" ? safeThemeId(packOrId) : safeThemeId(packOrId?.id || "");
    return BUILTIN_THEME_IDS.has(id);
  }

  function fallbackThemeIdAfterDelete(packs) {
    const list = Array.isArray(packs) ? packs : mujianThemePacks();
    return list.find((item) => item?.id === "standard")?.id
      || list.find((item) => isBuiltinThemePack(item))?.id
      || "standard";
  }

  function normalizeThemePack(pack) {
    if (!pack || typeof pack !== "object") throw new Error("美化包必须是 JSON 对象。");
    const id = safeThemeId(pack?.id || pack?.name || `theme_${Date.now()}`);
    const rawStyle = (pack && typeof pack.style === "object" && pack.style)
      ? pack.style
      : ((pack && typeof pack.theme === "object" && pack.theme) ? pack.theme : {});
    const style = rawStyle || {};
    const className = String(style.class_name || style.class || `theme-${id}`).replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "") || `theme-${id}`;
    const safeStyle = {
      ...style,
      class_name: className,
      accent: String(style.accent || style.primary || "").trim(),
      title_card: (style.title_card && typeof style.title_card === "object") ? style.title_card : {},
      character_card: (style.character_card && typeof style.character_card === "object") ? style.character_card : {},
      relationship_card: (style.relationship_card && typeof style.relationship_card === "object") ? style.relationship_card : {},
      status_bar: (style.status_bar && typeof style.status_bar === "object") ? style.status_bar : {},
    };
    ["layout", "blocks", "tokens", "field_style", "media", "labels", "progress_bars"].forEach((key) => {
      if (pack[key] && typeof pack[key] === "object") safeStyle[key] = pack[key];
      else if (style[key] && typeof style[key] === "object") safeStyle[key] = style[key];
    });
    const normalized = {
      id,
      name: String(pack?.name || id).trim() || id,
      version: String(pack?.version || "1.0.0").trim() || "1.0.0",
      author: String(pack?.author || "").trim(),
      description: String(pack?.description || "").trim(),
      style: safeStyle,
    };
    if (pack.media && typeof pack.media === "object") normalized.media = pack.media;
    if (pack.labels && typeof pack.labels === "object") normalized.labels = pack.labels;
    return normalized;
  }

  function mergeThemePack(pack) {
    const packs = mujianThemePacks().filter((item) => item && item.id !== pack.id);
    return [...packs, pack];
  }

  async function persistImportedTheme(pack) {
    state.config = {
      ...state.config,
      mujian_theme_packs: mergeThemePack(pack),
      mujian_theme_id: pack.id,
    };
    state.currentThemeId = pack.id;
    renderThemeSelectors();
    renderThemePreview();
    const payload = await requestJson("./api/config", {
      method: "POST",
      body: JSON.stringify({ config: readConfig() }),
    });
    state.config = payload.config || state.config;
    state.currentThemeId = pack.id;
    renderThemeSelectors();
    renderThemePreview();
    window.xinjianChatBridge?.reloadConfig?.();
    return payload;
  }


  async function deleteActiveImportedTheme() {
    const pack = activeThemePack();
    if (!pack?.id) return;
    if (isBuiltinThemePack(pack)) {
      pageToast("内置外观包不可删除", "可以导出内置包作为模板，再导入为新的自定义外观包。", "error");
      return;
    }
    const ok = window.confirm(`确认删除导入的外观包“${pack.name || pack.id}”吗？\n删除后会自动切回标准样式。`);
    if (!ok) return;
    const nextPacks = mujianThemePacks().filter((item) => item && item.id !== pack.id);
    const nextThemeId = fallbackThemeIdAfterDelete(nextPacks);
    state.config = {
      ...state.config,
      mujian_theme_packs: nextPacks,
      mujian_theme_id: nextThemeId,
    };
    state.currentThemeId = nextThemeId;
    renderThemeSelectors();
    renderThemePreview();
    const payload = await requestJson("./api/config", {
      method: "POST",
      body: JSON.stringify({ config: readConfig() }),
    });
    state.config = payload.config || state.config;
    state.currentThemeId = state.config.mujian_theme_id || nextThemeId;
    renderThemeSelectors();
    renderThemePreview();
    window.xinjianChatBridge?.reloadConfig?.();
    pageToast("导入外观包已删除", `已切回：${activeThemePack().name || activeThemePack().id}`, "ok");
    setStatus(`已删除导入外观包：${pack.name || pack.id}`, "ok");
  }

  function renderThemeSelectors() {
    const packs = mujianThemePacks();
    const active = activeThemeId();
    const options = packs.map((item) => `<option value="${escapeAttr(item.id)}" ${item.id === active ? "selected" : ""}>${escapeHtml(item.name || item.id)}</option>`).join("");
    if (els.cfgMujianThemeSelect) els.cfgMujianThemeSelect.innerHTML = options;
    if (els.themeSelect) els.themeSelect.innerHTML = options;
  }

  function renderThemePreview() {
    const pack = activeThemePack();
    if (els.cfgMujianThemeSelect) els.cfgMujianThemeSelect.value = pack.id;
    if (els.themeSelect) els.themeSelect.value = pack.id;
    if (els.themeName) els.themeName.value = pack.name || "";
    if (els.themeAuthor) els.themeAuthor.value = pack.author || "";
    if (els.themeDesc) els.themeDesc.value = pack.description || "";
    if (els.deleteThemeBtn) {
      const builtin = isBuiltinThemePack(pack);
      els.deleteThemeBtn.disabled = builtin;
      els.deleteThemeBtn.title = builtin ? "内置外观包不可删除" : `删除导入外观包：${pack.name || pack.id}`;
      els.deleteThemeBtn.textContent = builtin ? "内置包不可删除" : "删除导入包";
    }
    const style = pack.style || {};
    const cls = String(style.class_name || "theme-standard");
    const accent = String(style.accent || "");
    if (els.themePreview) {
      els.themePreview.className = `theme-preview-card ${cls}`;
      if (accent) els.themePreview.style.setProperty("--xj-beauty-accent", accent);
      const isTimeCard = cls.includes("time-card");
      const isGufeng = cls.includes("gufeng");
      els.themePreview.innerHTML = isTimeCard ? `
        <div class="theme-preview-title"><span>Time</span><strong>第六笺 · 《旧雨入帘》</strong><em>📅 入夜　🧭 泠音阁后楼　🌦️ 小雨初歇</em></div>
        <div class="theme-preview-role"><h4>示例角色</h4><p><b>💗 情绪</b> 情绪稳定，状态字段按模板完整显示。</p><p><b>👘 衣着</b> 衣着与场景按当前模板输出。</p><p><b>🤝 互动</b> 关系变化与数值由心笺记录。</p></div>
        <div class="theme-preview-relation"><b>关系变化</b> 信任更深，状态条式展示。</div>
      ` : (isGufeng ? `
        <div class="theme-preview-title"><span>XINJIAN · 幕题</span><strong>第六笺 · 《旧雨入帘》</strong><em>一场旧约，在灯火与药香里重新落定。</em></div>
        <div class="theme-preview-role"><h4>示例角色</h4><p><b>情绪</b> 情绪稳定，状态字段按模板完整显示。</p><p><b>衣着</b> 衣着与场景按当前模板输出。</p></div>
        <div class="theme-preview-relation"><b>关系变化</b> 信任更深，关系变化与数值由心笺记录。</div>
      ` : `
        <div class="theme-preview-title"><span>XINJIAN · 幕题</span><strong>第六笺 · 《旧雨入帘》</strong><em>一场旧约，在灯火与药香里重新落定。</em></div>
        <div class="theme-preview-role"><h4>示例角色</h4><p><b>情绪</b> 情绪稳定，状态字段按模板完整显示。</p><p><b>衣着</b> 衣着与场景按当前模板输出。</p></div>
        <div class="theme-preview-relation"><b>关系变化</b> 信任更深，关系变化与数值由心笺记录。</div>
      `);
    }
  }

  function setActiveTheme(id) {
    state.currentThemeId = safeThemeId(id || activeThemeId());
    state.config = { ...state.config, mujian_theme_id: state.currentThemeId };
    renderThemeSelectors();
    renderThemePreview();
  }

  function bindTemplateEditor() {
    renderTemplateSelectors();
    let template = ensureTemplateOutputFields(activeTemplate());
    const templates = mujianTemplates().slice();
    const templatePos = templates.findIndex((item) => item.id === template.id);
    if (templatePos >= 0) { templates[templatePos] = template; state.config = { ...state.config, mujian_templates: templates }; }
    if (els.cfgMujianTemplateSelect) els.cfgMujianTemplateSelect.value = template.id;
    if (els.templateSelect) els.templateSelect.value = template.id;
    if (els.templateName) els.templateName.value = template.name || "";
    if (els.templateDesc) els.templateDesc.value = template.description || "";
    if (els.templateNoteStyle) els.templateNoteStyle.value = template.note_style || "classic";
    if (els.templateOutput) els.templateOutput.value = template.output_template || "";
    renderTemplateFields(template);
    updateTemplatePreview();
  }

  function renderTemplateFields(template) {
    if (!els.templateFieldsEditor) return;
    const fields = Array.isArray(template?.fields) ? template.fields : [];
    els.templateFieldsEditor.innerHTML = fields.map((field, index) => `
      <div class="template-field-card" data-template-field-index="${index}">
        <div class="template-field-head"><strong>${escapeHtml(field.label || field.key || "字段")}</strong><span>${escapeHtml(field.key || "")}</span></div>
        <div class="grid-two">
          <label>字段 Key<input data-tpl-key value="${escapeAttr(field.key || "")}" placeholder="emotion" /></label>
          <label>显示名<input data-tpl-label value="${escapeAttr(field.label || "")}" placeholder="情绪" /></label>
        </div>
        <label>生成说明<textarea data-tpl-instruction rows="2">${escapeHtml(field.instruction || "")}</textarea></label>
        <div class="template-field-actions">
          <button type="button" class="ghost-btn mini" data-tpl-up="${index}">上移</button>
          <button type="button" class="ghost-btn mini" data-tpl-down="${index}">下移</button>
          <button type="button" class="ghost-btn mini danger" data-tpl-delete="${index}">删除</button>
        </div>
      </div>
    `).join("") || `<div class="empty-state"><strong>暂无字段。</strong><span>点击“新增字段”开始配置。</span></div>`;
  }

  function readTemplateEditor() {
    const current = activeTemplate();
    const fields = [...document.querySelectorAll(".template-field-card")].map((card) => ({
      key: safeTemplateId(card.querySelector("[data-tpl-key]")?.value || ""),
      label: (card.querySelector("[data-tpl-label]")?.value || "").trim(),
      instruction: (card.querySelector("[data-tpl-instruction]")?.value || "").trim(),
    })).filter((field) => field.key && field.key !== "name").map((field) => ({ ...field, label: field.label || field.key, instruction: field.instruction || "根据本轮上下文生成该字段。" }));
    return ensureTemplateOutputFields({
      ...current,
      id: current.id || safeTemplateId(els.templateName?.value || "custom"),
      name: (els.templateName?.value || current.name || "自定义模板").trim(),
      description: (els.templateDesc?.value || "").trim(),
      note_style: els.templateNoteStyle?.value || "classic",
      fields,
      output_template: els.templateOutput?.value || "",
    });
  }

  function updateTemplatePreview() {
    if (!els.templatePreview) return;
    const template = readTemplateEditor();
    if (els.templateOutput && els.templateOutput.value !== (template.output_template || "")) els.templateOutput.value = template.output_template || "";
    els.templatePreview.textContent = renderTemplateText(template);
  }

  function commitTemplateEditorToState(options = {}) {
    const template = readTemplateEditor();
    const templates = mujianTemplates().slice();
    const index = templates.findIndex((item) => item.id === template.id);
    if (index >= 0) templates[index] = template; else templates.push(template);
    state.config = { ...state.config, mujian_templates: templates, mujian_template_id: template.id, mujian_note_style: template.note_style, mujian_style: template.note_style };
    state.currentTemplateId = template.id;
    if (options.rebind !== false) {
      bindTemplateEditor();
      bindConfig();
    }
    return template;
  }

  function bindConfig() {
    const cfg = state.config || {};
    els.cfgEnabled.checked = !!cfg.enabled;
    els.cfgAutoUpdate.checked = !!cfg.auto_update;
    els.cfgNotify.checked = !!cfg.notify_in_chat;
    if (els.cfgMujianEnabled) els.cfgMujianEnabled.checked = cfg.mujian_enabled !== false;
    if (els.cfgMujianTitle) els.cfgMujianTitle.checked = cfg.mujian_title_card !== false;
    if (els.cfgMujianNote) els.cfgMujianNote.checked = cfg.mujian_turn_note !== false;
    if (els.cfgMujianCollapsed) els.cfgMujianCollapsed.checked = cfg.mujian_default_collapsed !== false;
    if (els.cfgMujianDisplayMode) els.cfgMujianDisplayMode.value = cfg.mujian_chat_display_mode || (cfg.mujian_default_collapsed === false ? "expanded" : "collapsed");
    if (els.cfgMujianStyle) els.cfgMujianStyle.value = cfg.mujian_style || "classic";
    if (els.cfgMujianTitleStyle) els.cfgMujianTitleStyle.value = cfg.mujian_title_style || cfg.mujian_style || "classic";
    if (els.cfgMujianNoteStyle) els.cfgMujianNoteStyle.value = cfg.mujian_note_style || cfg.mujian_style || "classic";
    if (els.cfgMujianExpand) els.cfgMujianExpand.value = cfg.mujian_expand_level || "standard";
    if (els.cfgMujianDensity) els.cfgMujianDensity.value = cfg.mujian_note_density || "standard";
    if (els.cfgMujianCharacterFilter) els.cfgMujianCharacterFilter.value = cfg.mujian_character_filter || "turn";
    state.currentTemplateId = cfg.mujian_template_id || state.currentTemplateId || mujianTemplates()[0]?.id || "classic";
    state.currentThemeId = cfg.mujian_theme_id || state.currentThemeId || mujianThemePacks()[0]?.id || "standard";
    renderThemeSelectors();
    renderThemePreview();
    renderTemplateSelectors();
    if (els.cfgMujianTemplateSelect) els.cfgMujianTemplateSelect.value = state.currentTemplateId;
    if (els.cfgMujianCharacterNames) els.cfgMujianCharacterNames.value = cfg.mujian_character_names || "";
    bindTemplateEditor();
    updateMujianStyleHelp();
    els.cfgBaseUrl.value = cfg.api_base_url || "";
    els.cfgApiKey.value = cfg.api_key || "";
    els.cfgModel.value = cfg.model || "";
    els.cfgTurns.value = cfg.input_turn_count || 3;
    els.cfgTimeout.value = cfg.request_timeout || 120;
    syncPresetSelectFromBaseUrl();
  }

  function readConfig() {
    return {
      ...state.config,
      enabled: els.cfgEnabled.checked,
      auto_update: els.cfgAutoUpdate.checked,
      notify_in_chat: els.cfgNotify.checked,
      mujian_enabled: els.cfgMujianEnabled ? els.cfgMujianEnabled.checked : true,
      mujian_title_card: els.cfgMujianTitle ? els.cfgMujianTitle.checked : true,
      mujian_turn_note: els.cfgMujianNote ? els.cfgMujianNote.checked : true,
      mujian_default_collapsed: els.cfgMujianDisplayMode ? els.cfgMujianDisplayMode.value === "collapsed" : (els.cfgMujianCollapsed ? els.cfgMujianCollapsed.checked : true),
      mujian_chat_display_mode: els.cfgMujianDisplayMode ? els.cfgMujianDisplayMode.value : (els.cfgMujianCollapsed && !els.cfgMujianCollapsed.checked ? "expanded" : "collapsed"),
      mujian_style: els.cfgMujianNoteStyle ? els.cfgMujianNoteStyle.value : (els.cfgMujianStyle ? els.cfgMujianStyle.value : "classic"),
      mujian_title_style: els.cfgMujianTitleStyle ? els.cfgMujianTitleStyle.value : "classic",
      mujian_note_style: els.cfgMujianNoteStyle ? els.cfgMujianNoteStyle.value : "classic",
      mujian_expand_level: els.cfgMujianExpand ? els.cfgMujianExpand.value : "standard",
      mujian_note_density: els.cfgMujianDensity ? els.cfgMujianDensity.value : "standard",
      mujian_character_filter: els.cfgMujianCharacterFilter ? els.cfgMujianCharacterFilter.value : "turn",
      mujian_character_names: els.cfgMujianCharacterNames ? els.cfgMujianCharacterNames.value.trim() : "",
      mujian_template_id: activeTemplateId(),
      mujian_templates: mujianTemplates(),
      mujian_theme_id: activeThemeId(),
      mujian_theme_packs: mujianThemePacks(),
      api_base_url: els.cfgBaseUrl.value.trim(),
      api_key: els.cfgApiKey.value.trim(),
      model: els.cfgModel.value.trim(),
      input_turn_count: Number(els.cfgTurns.value || 3),
      request_timeout: Number(els.cfgTimeout.value || 120),
    };
  }

  function syncPresetSelectFromBaseUrl() {
    if (!els.servicePreset) return;
    const base = (els.cfgBaseUrl.value || "").trim().replace(/\/$/, "");
    const match = Object.entries(SERVICE_PRESETS).find(([key, preset]) => key !== "custom" && preset.base_url.replace(/\/$/, "") === base);
    els.servicePreset.value = match ? match[0] : "custom";
  }

  function applyServicePreset() {
    const preset = SERVICE_PRESETS[els.servicePreset.value] || SERVICE_PRESETS.custom;
    if (!preset.base_url) {
      pageToast("预设服务：自定义", "保留当前 API URL 和模型名。", "ok");
      return;
    }
    els.cfgBaseUrl.value = preset.base_url;
    if (preset.model && !els.cfgModel.value.trim()) els.cfgModel.value = preset.model;
    pageToast("已填入预设服务", `${preset.label} · ${preset.base_url}`, "ok");
  }

  const MUJIAN_TITLE_STYLE_PREVIEWS = {
    classic: {
      label: "经典标题",
      desc: "标题短，副标题说明本轮重点，适合稳定清晰的正文外标题卡。",
      sample: `标题卡：\n《本轮状态》\n地点：当前场景｜人物：本轮角色`,
    },
    gufeng: {
      label: "古风标题",
      desc: "标题和引语更偏古风意象，适合章节感、诗性和氛围感。",
      sample: `标题卡：\n《雨阁留灯》\n夜色压檐，灯影半昏。`,
    },
    chapter: {
      label: "章节标题",
      desc: "更像小说小节或章节标题，强调本轮冲突、转折和主题。",
      sample: `标题卡：\n第三幕 · 雨阁留灯\n本轮重点：病榻前的照料与试探。`,
    },
  };

  const MUJIAN_NOTE_STYLE_PREVIEWS = {
    classic: {
      label: "经典状态",
      desc: "角色附笺以清晰状态说明为主，适合常规角色状态卡。",
      sample: `角色附笺：\n情绪：克制而担忧\n衣着：衣袖微皱\n互动：语气平稳，仍有保护意味`,
    },
    gufeng: {
      label: "古风旁白",
      desc: "角色附笺更像小说旁白，字段仍保留，但措辞更含蓄。",
      sample: `角色附笺：\n情绪：旧事与病气压在眼底，声线仍稳。\n互动：不肯示弱，却也未曾真正退开。`,
    },
    sensory: {
      label: "感官标签",
      desc: "角色附笺改为标签式细节，重点生成感官场域、躯体温差、肢体动态、微生理反应、视觉焦点等字段。",
      sample: `<情绪(克制中带松动)>\n<衣着(袖口微乱)>\n<角色神态(视线短暂避开)>\n<感官场域(灯影与药香交叠)>\n<微生理反应(眼睫轻颤，呼吸稍乱)>`,
    },
  };

  function updateMujianStyleHelp() {
    const titleStyle = els.cfgMujianTitleStyle?.value || "classic";
    const noteStyle = els.cfgMujianNoteStyle?.value || els.cfgMujianStyle?.value || "classic";
    const titleItem = MUJIAN_TITLE_STYLE_PREVIEWS[titleStyle] || MUJIAN_TITLE_STYLE_PREVIEWS.classic;
    const noteItem = MUJIAN_NOTE_STYLE_PREVIEWS[noteStyle] || MUJIAN_NOTE_STYLE_PREVIEWS.classic;
    const descEl = document.getElementById("mujianStyleDesc");
    const previewEl = document.getElementById("mujianStylePreview");
    if (descEl) descEl.textContent = `标题：${titleItem.label}，${titleItem.desc} 附笺：${noteItem.label}，${noteItem.desc}`;
    if (previewEl) previewEl.textContent = `${titleItem.sample}\n\n${noteItem.sample}`;
  }

  function bindSchema(table) {
    if (!table) return;
    const schema = table.schema;
    els.schemaId.value = schema.id || "";
    els.schemaName.value = schema.name || "";
    els.schemaDesc.value = schema.description || "";
    const rules = schema.rules || {};
    els.ruleNote.value = rules.note || "";
    els.ruleInit.value = rules.init || "";
    els.ruleInsert.value = rules.insert || "";
    els.ruleUpdate.value = rules.update || "";
    els.ruleDelete.value = rules.delete || "";
    els.ruleIgnore.value = rules.ignore || "";
    refreshPrimaryOptions(schema.primary_key);
  }

  function readSchema() {
    const table = currentTable();
    const oldSchema = table?.schema || { fields: [] };
    const fields = [...document.querySelectorAll(".field-card")].map((card) => ({
      key: card.querySelector("[data-field-key]").value.trim(),
      label: card.querySelector("[data-field-label]").value.trim(),
      type: card.querySelector("[data-field-type]").value,
      required: card.querySelector("[data-field-required]").checked,
      options: card.querySelector("[data-field-options]").value.split(/[，,、\n]/).map((item) => item.trim()).filter(Boolean),
      note: card.querySelector("[data-field-note]").value.trim(),
    })).filter((field) => field.key);
    return {
      ...oldSchema,
      id: els.schemaId.value.trim(),
      name: els.schemaName.value.trim(),
      description: els.schemaDesc.value.trim(),
      primary_key: els.primaryKey.value || fields[0]?.key || "",
      fields,
      rules: {
        note: els.ruleNote.value.trim(),
        init: els.ruleInit.value.trim(),
        insert: els.ruleInsert.value.trim(),
        update: els.ruleUpdate.value.trim(),
        delete: els.ruleDelete.value.trim(),
        ignore: els.ruleIgnore.value.trim(),
      },
    };
  }

  function readRows() {
    return (currentTable()?.rows || []).map((row) => ({ ...row }));
  }

  function renderTableList() {
    els.tableList.innerHTML = "";
    state.tables.forEach((table) => {
      const button = document.createElement("button");
      button.className = `table-item ${table.schema.id === state.currentId ? "active" : ""}`;
      button.innerHTML = `<strong>${escapeHtml(table.schema.name || table.schema.id)}</strong><span>${escapeHtml(table.schema.id)} · ${table.rows.length} 行</span>`;
      button.addEventListener("click", () => { closeRowDetail(); state.currentId = table.schema.id; renderAll(); });
      els.tableList.appendChild(button);
    });
  }

  function renderFields(table) {
    els.fieldsEditor.innerHTML = "";
    (table.schema.fields || []).forEach((field) => {
      const card = document.createElement("div");
      card.className = "field-card";
      card.innerHTML = `
        <div class="field-card-head">
          <button class="expand-btn" type="button">展开</button>
          <span class="field-title"><strong>${escapeHtml(field.label || field.key)}</strong><small>${escapeHtml(field.key)} · ${escapeHtml(field.type || "text")}${field.required ? " · 必填" : ""}</small></span>
          <button class="delete-btn" type="button">删除</button>
        </div>
        <div class="field-card-body">
          <div class="field-grid">
            <label>字段 Key<input data-field-key value="${escapeAttr(field.key || "")}" /></label>
            <label>显示名<input data-field-label value="${escapeAttr(field.label || "")}" /></label>
            <label>类型<select data-field-type>${["text", "textarea", "number", "enum", "boolean"].map((type) => `<option value="${type}" ${field.type === type ? "selected" : ""}>${type}</option>`).join("")}</select></label>
            <label class="check-row"><input data-field-required type="checkbox" ${field.required ? "checked" : ""}/> 必填</label>
            <label>枚举项<input data-field-options value="${escapeAttr((field.options || []).join(", "))}" /></label>
            <label>字段说明<input data-field-note value="${escapeAttr(field.note || "")}" /></label>
          </div>
        </div>`;
      card.querySelector(".expand-btn").addEventListener("click", () => {
        card.classList.toggle("expanded");
        card.querySelector(".expand-btn").textContent = card.classList.contains("expanded") ? "收起" : "展开";
      });
      card.querySelector(".delete-btn").addEventListener("click", () => { card.remove(); refreshPrimaryOptions(); });
      card.querySelectorAll("[data-field-key], [data-field-label]").forEach((input) => input.addEventListener("input", refreshPrimaryOptions));
      els.fieldsEditor.appendChild(card);
    });
  }

  function makeRowInput(field, value) {
    let input;
    if (field.type === "textarea") {
      input = document.createElement("textarea"); input.rows = 4; input.value = value || "";
    } else if (field.type === "enum") {
      input = document.createElement("select");
      input.innerHTML = `<option value=""></option>${(field.options || []).map((item) => `<option value="${escapeAttr(item)}" ${value === item ? "selected" : ""}>${escapeHtml(item)}</option>`).join("")}`;
    } else if (field.type === "boolean") {
      input = document.createElement("input"); input.type = "checkbox"; input.checked = !!value;
    } else {
      input = document.createElement("input"); input.type = field.type === "number" ? "number" : "text"; input.value = value ?? "";
    }
    input.dataset.rowKey = field.key;
    return input;
  }

  function getDisplayFields(table) {
    const fields = table.schema.fields || [];
    const hiddenKeys = new Set(["updated_at"]);
    const preferredByTable = {
      character_status: [table.schema.primary_key, "location", "mood", "metrics_summary", "condition", "summary"],
      relationship: [table.schema.primary_key, "from", "to", "relation", "metrics_summary", "summary"],
      metric_history: ["character_name", "metric_label", "old_value", "new_value", "delta_display", "raw_value"],
    };
    const preferred = (preferredByTable[table.schema.id] || [table.schema.primary_key, "location", "mood", "condition", "metrics_summary", "summary"]).filter(Boolean);
    const selected = [];
    preferred.forEach((key) => {
      const field = fields.find((item) => item.key === key && !hiddenKeys.has(item.key));
      if (field && !selected.some((item) => item.key === field.key)) selected.push(field);
    });
    fields.forEach((field) => {
      if (selected.length < 6 && !hiddenKeys.has(field.key) && !selected.some((item) => item.key === field.key)) selected.push(field);
    });
    return selected;
  }

  function renderRowsAsCards(table) {
    const fields = table.schema.fields || [];
    const primary = table.schema.primary_key || fields[0]?.key;
    const displayFields = getDisplayFields(table).filter((field) => field.key !== primary);
    const list = document.createElement("div");
    list.className = "row-card-list";
    (table.rows || []).forEach((row, index) => {
      const card = document.createElement("article");
      card.className = "row-card";
      const title = primary ? (row[primary] || `第 ${index + 1} 行`) : `第 ${index + 1} 行`;
      const subtitleField = displayFields.find((field) => ["location", "mood", "summary", "condition"].includes(field.key)) || displayFields[0];
      const subtitle = subtitleField ? compactText(row[subtitleField.key], 56) : "";
      card.innerHTML = `
        <div class="row-card-head">
          <span class="row-card-title"><strong>${escapeHtml(title)}</strong><span class="row-card-subtitle">${escapeHtml(subtitle)}</span></span>
          <button class="ghost-btn small" type="button" data-edit-row="${index}">详情</button>
        </div>
        <div class="row-chip-grid">
          ${displayFields.slice(0, 4).map((field) => `<div class="row-chip"><span>${escapeHtml(fieldLabel(field))}</span><strong>${escapeHtml(compactText(row[field.key], field.type === "textarea" ? 88 : 54))}</strong></div>`).join("")}
        </div>
        <div class="row-card-actions">
          <button class="delete-btn" type="button" data-delete-row="${index}">删除</button>
        </div>`;
      list.appendChild(card);
    });
    els.rowsEditor.appendChild(list);
  }

  function renderRowsAsTable(table) {
    const fields = table.schema.fields || [];
    const displayFields = getDisplayFields(table);
    const primary = table.schema.primary_key || displayFields[0]?.key;
    const wrap = document.createElement("div");
    wrap.className = "rows-table-wrap";
    const tableEl = document.createElement("table");
    tableEl.className = "rows-table";
    tableEl.innerHTML = `<thead><tr>${displayFields.map((field) => `<th>${escapeHtml(fieldLabel(field))}</th>`).join("")}<th>操作</th></tr></thead><tbody></tbody>`;
    const tbody = tableEl.querySelector("tbody");
    (table.rows || []).forEach((row, index) => {
      const tr = document.createElement("tr");
      tr.tabIndex = 0;
      tr.title = "点击查看/编辑详情";
      displayFields.forEach((field) => {
        const td = document.createElement("td");
        const isLong = field.type === "textarea" || ["summary", "condition", "appearance", "attitude"].includes(field.key);
        td.innerHTML = `<span class="rows-table-cell ${isLong ? "long" : ""}">${escapeHtml(compactText(row[field.key], isLong ? 96 : 52))}</span>`;
        tr.appendChild(td);
      });
      const op = document.createElement("td");
      op.innerHTML = `<button class="ghost-btn small" type="button" data-edit-row="${index}">详情</button> <button class="delete-btn" type="button" data-delete-row="${index}">删除</button>`;
      tr.appendChild(op);
      tr.addEventListener("click", (event) => {
        if (event.target.closest("button")) return;
        openRowDetail(index);
      });
      tbody.appendChild(tr);
    });
    wrap.appendChild(tableEl);
    els.rowsEditor.appendChild(wrap);
  }

  function renderRows(table) {
    els.rowsEditor.innerHTML = "";
    const fields = table.schema.fields || [];
    if (!fields.length) {
      els.rowsEditor.innerHTML = `<div class="empty-state"><strong>这张表还没有字段。</strong><span>请打开“字段”设置，至少添加一个主键字段。</span></div>`;
      return;
    }
    if (!table.rows?.length) {
      els.rowsEditor.innerHTML = `<div class="empty-state"><strong>当前表暂无数据。</strong><span>心笺不会在加载角色卡时自动写入状态。你可以先聊天一轮，再点击“根据最近对话更新”；也可以开启“聊天后自动填表”。</span><span>后续版本会加入“从角色卡 / 记忆初始化”。</span></div>`;
      return;
    }
    if (state.viewMode === "table") renderRowsAsTable(table); else renderRowsAsCards(table);
  }

  function refreshPrimaryOptions(preferred) {
    const oldValue = preferred || els.primaryKey.value;
    const source = document.querySelectorAll(".field-card").length
      ? [...document.querySelectorAll(".field-card")].map((card) => ({ key: card.querySelector("[data-field-key]").value.trim(), label: card.querySelector("[data-field-label]").value.trim() })).filter((field) => field.key)
      : (currentTable()?.schema.fields || []).map((field) => ({ key: field.key, label: field.label }));
    els.primaryKey.innerHTML = "";
    source.forEach((field, index) => {
      const option = document.createElement("option"); option.value = field.key; option.textContent = `${field.label || field.key} (${field.key})`; option.selected = field.key === oldValue || (!oldValue && index === 0); els.primaryKey.appendChild(option);
    });
  }

  function updateViewButtons() {
    els.cardViewBtn.classList.toggle("active", state.viewMode === "card");
    els.tableViewBtn.classList.toggle("active", state.viewMode === "table");
  }

  function renderAll() {
    if (!state.currentId && state.tables[0]) state.currentId = state.tables[0].schema.id;
    const table = currentTable();
    renderTableList(); bindConfig(); updateViewButtons();
    if (!table) { els.currentTitle.textContent = "未选择表"; els.currentDesc.textContent = ""; els.rowsEditor.innerHTML = `<div class="empty-state"><strong>暂无表格。</strong><span>点击左侧“＋”新建表，或导入心笺 JSON。</span></div>`; return; }
    els.currentTitle.textContent = table.schema.name || table.schema.id;
    els.currentDesc.textContent = table.schema.description || "";
    bindSchema(table); renderFields(table); renderRows(table);
  }

  function openConfigDrawer(tab = "schema") {
    switchTab(tab);
    els.drawerTitle.textContent = { schema: "字段设置", rules: "规则设置", model: "模型设置", link: "聊天联动", mujian: "幕笺设置", template: "幕笺模板", log: "日志" }[tab] || "心笺设置";
    els.configDrawer.classList.add("open");
    els.configDrawer.setAttribute("aria-hidden", "false");
    els.drawerMask.hidden = false;
    if (tab === "link") refreshHookStatus();
  }

  function closeConfigDrawer() {
    els.configDrawer.classList.remove("open");
    els.configDrawer.setAttribute("aria-hidden", "true");
    els.drawerMask.hidden = true;
  }

  function switchTab(tab) {
    document.querySelectorAll(".tab-btn").forEach((item) => item.classList.toggle("active", item.dataset.tab === tab));
    document.querySelectorAll(".tab-page").forEach((item) => item.classList.toggle("active", item.dataset.page === tab));
  }

  function openRowDetail(index) {
    const table = currentTable();
    if (!table || !table.rows[index]) return;
    state.detailIndex = index;
    const fields = table.schema.fields || [];
    const row = table.rows[index] || {};
    const primary = table.schema.primary_key || fields[0]?.key;
    els.rowDetailTitle.textContent = row[primary] || `第 ${index + 1} 行`;
    els.rowDetailBody.innerHTML = "";
    fields.forEach((field) => {
      const wrap = document.createElement("label");
      wrap.className = "row-detail-field";
      const input = makeRowInput(field, row[field.key]);
      wrap.appendChild(document.createTextNode(fieldLabel(field)));
      const note = document.createElement("small");
      note.textContent = `${field.key} · ${field.type || "text"}${field.note ? `｜${field.note}` : ""}`;
      wrap.appendChild(note);
      wrap.appendChild(input);
      els.rowDetailBody.appendChild(wrap);
    });
    els.rowDetailDrawer.classList.add("open");
    els.rowDetailDrawer.setAttribute("aria-hidden", "false");
    els.rowDetailMask.hidden = false;
  }

  function closeRowDetail() {
    state.detailIndex = -1;
    els.rowDetailDrawer.classList.remove("open");
    els.rowDetailDrawer.setAttribute("aria-hidden", "true");
    els.rowDetailMask.hidden = true;
  }

  function saveRowDetail() {
    const table = currentTable();
    if (!table || state.detailIndex < 0) return;
    const row = {};
    (table.schema.fields || []).forEach((field) => {
      const input = els.rowDetailBody.querySelector(`[data-row-key="${CSS.escape(field.key)}"]`);
      row[field.key] = field.type === "boolean" ? !!input?.checked : (input?.value ?? "");
    });
    table.rows[state.detailIndex] = row;
    renderRows(table);
    pageToast("行已暂存", "点击“保存当前表”后写入 SQLite。", "ok");
    closeRowDetail();
  }

  function deleteRow(index) {
    const table = currentTable();
    if (!table || !table.rows[index]) return;
    table.rows.splice(index, 1);
    renderRows(table);
  }

  async function refreshHookStatus() {
    try {
      const payload = await requestJson("./api/hook/status");
      const hook = payload.hook || {};
      if (hook.loaded) {
        const base = `已加载 · ${hook.updated_at || "未知时间"} · ${hook.event || "ping"}`;
        els.hookStatusText.textContent = hook.message ? `${base}\n${hook.message}` : base;
      } else {
        els.hookStatusText.textContent = "未检测到聊天页脚本。打开 Chat 页后会自动上报。";
      }
    } catch (error) { els.hookStatusText.textContent = `检测失败：${error.message}`; }
  }

  async function loadState() {
    setStatus("正在载入心笺数据...");
    const payload = await requestJson("./api/state");
    state.config = payload.config || {}; state.tables = payload.tables || [];
    if (!state.tables.some((table) => table.schema.id === state.currentId)) state.currentId = state.tables[0]?.schema.id || "";
    renderAll(); await refreshHookStatus(); setStatus("心笺已就绪。", "ok");
  }

  async function saveCurrentTable() {
    const schema = readSchema(); const rows = readRows();
    const payload = await requestJson(`./api/table/${encodeURIComponent(state.currentId || schema.id)}`, { method: "POST", body: JSON.stringify({ schema, rows }) });
    const existing = state.tables.findIndex((item) => item.schema.id === payload.schema.id);
    if (existing >= 0) state.tables[existing] = { schema: payload.schema, rows: payload.rows }; else state.tables.push({ schema: payload.schema, rows: payload.rows });
    state.currentId = payload.schema.id; renderAll(); setStatus("当前表已保存。", "ok"); pageToast("当前表已保存", `${payload.schema.name || payload.schema.id} · ${payload.rows.length} 行`, "ok");
  }

  async function saveConfig(kind = "model") {
    if (kind === "template") commitTemplateEditorToState();
    const payload = await requestJson("./api/config", { method: "POST", body: JSON.stringify({ config: readConfig() }) });
    state.config = payload.config || {};
    bindConfig();
    const titles = {
      model: "模型配置已保存",
      link: "聊天联动设置已保存",
      mujian: "幕笺设置已保存",
      template: "幕笺模板已保存",
      theme: "幕笺美化已保存",
      all: "心笺配置已保存",
    };
    const details = {
      model: `${state.config.model || "未填写模型"} · ${state.config.api_base_url || "未填写 API URL"}`,
      link: `心笺${state.config.enabled === false ? "关闭" : "开启"}｜自动填表${state.config.auto_update ? "开启" : "关闭"}｜聊天提示${state.config.notify_in_chat ? "开启" : "关闭"}`,
      mujian: `幕笺${state.config.mujian_enabled === false ? "关闭" : "开启"}｜显示：${({ collapsed: "折叠", expanded: "展开", compact: "状态条", hidden: "不显示" }[state.config.mujian_chat_display_mode || "collapsed"] || "折叠")}｜标题：${state.config.mujian_title_style || "classic"}｜附笺：${state.config.mujian_note_style || state.config.mujian_style || "classic"}｜密度：${state.config.mujian_note_density || "standard"}`,
      template: `${activeTemplate().name || activeTemplate().id}｜字段 ${activeTemplate().fields?.length || 0} 个`,
      theme: `${activeThemePack().name || activeThemePack().id}｜${activeThemePack().description || "美化包已启用"}`,
      all: `${state.config.model || "未填写模型"} · 幕笺${state.config.mujian_enabled === false ? "关闭" : "开启"}`,
    };
    const title = titles[kind] || titles.all;
    setStatus(`${title}。`, "ok");
    pageToast(title, details[kind] || details.all, "ok");
    window.xinjianChatBridge?.reloadConfig?.();
  }

  async function fillFromMainConfig() {
    const payload = await requestJson("./api/main-config");
    const cfg = payload.config || {};
    els.cfgBaseUrl.value = cfg.api_base_url || "";
    els.cfgApiKey.value = cfg.api_key || "";
    els.cfgModel.value = cfg.model || "";
    if (cfg.request_timeout) els.cfgTimeout.value = cfg.request_timeout;
    syncPresetSelectFromBaseUrl();
    pageToast("已从本体配置填入", cfg.model ? `${cfg.model} · ${cfg.api_base_url || "未填写 API URL"}` : (payload.message || "未读到模型名。"), cfg.model || cfg.api_base_url ? "ok" : "error");
  }

  async function fetchModels() {
    setStatus("正在拉取模型列表...");
    const payload = await requestJson("./api/models", { method: "POST", body: JSON.stringify({ config: readConfig() }) });
    const models = payload.models || [];
    els.modelDatalist.innerHTML = models.map((id) => `<option value="${escapeAttr(id)}"></option>`).join("");
    const message = payload.message || (models.length ? `已拉取 ${models.length} 个模型，请直接在模型名输入框中选择。` : "接口返回为空。");
    setStatus(message, "ok");
    pageToast("模型列表已更新", message, "ok");
  }

  async function testConnection() {
    setStatus("正在测试连接...");
    const payload = await requestJson("./api/test-connection", { method: "POST", body: JSON.stringify({ config: readConfig() }) });
    setStatus(payload.message || "连接成功。", "ok"); pageToast("心笺连接测试成功", payload.message || "连接成功。", "ok");
  }

  async function manualWorkerUpdate() {
    await saveCurrentTable(); setStatus("心笺正在根据最近对话更新表格...");
    const history = await fetch("/api/history").then((res) => res.json()).catch(() => []);
    const result = await requestJson("./api/worker/update", { method: "POST", body: JSON.stringify({ manual: true, history, table_ids: [state.currentId] }) });
    await loadState();
    const count = result.summary?.total ?? result.result?.applied?.length ?? 0; const errors = result.result?.errors || [];
    const displayTitle = result.display?.title ? `｜幕笺：《${result.display.title}》` : "";
    const msg = (result.message || (count ? `心笺已应用 ${count} 条更新。` : "心笺判断本次无变化。")) + displayTitle;
    els.updateSummaryText.textContent = msg;
    if (errors.length || result.ok === false) { setStatus(msg, "error"); pageToast("心笺填表失败", msg, "error"); } else { setStatus(msg, "ok"); pageToast(count ? "心笺已更新" : "心笺无变化", msg, "ok"); }
  }

  async function loadLog() { const payload = await requestJson("./api/logs/latest"); els.logBox.textContent = JSON.stringify(payload.log || {}, null, 2); }
  async function exportDebugLog() {
    const payload = await requestJson("./api/logs/export?limit=120");
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `xinjian-debug-${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    pageToast("排查日志已导出", "已脱敏 API Key，可用于定位重 roll、编辑与幕笺恢复问题。", "ok");
  }
  function addField() { const table = currentTable(); if (!table) return; table.schema.fields.push({ key: `field_${table.schema.fields.length + 1}`, label: "新字段", type: "text", required: false, options: [], note: "" }); renderFields(table); refreshPrimaryOptions(); openConfigDrawer("schema"); }
  function addRow() { const table = currentTable(); if (!table) return; const row = {}; (table.schema.fields || []).forEach((field) => { row[field.key] = field.type === "boolean" ? false : ""; }); table.rows.push(row); renderRows(table); openRowDetail(table.rows.length - 1); }
  function newTable() { const id = `custom_table_${Date.now()}`; state.tables.push({ schema: { id, name: "新表", description: "", primary_key: "id", fields: [{ key: "id", label: "ID", type: "text", required: true, options: [], note: "主键字段" }], rules: { note: "", init: "", insert: "", update: "", delete: "", ignore: "" } }, rows: [] }); state.currentId = id; renderAll(); openConfigDrawer("schema"); }
  async function exportAll() { const payload = await requestJson("./api/export"); const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = `xinjian-export-${Date.now()}.json`; a.click(); URL.revokeObjectURL(url); pageToast("导出完成", "默认不包含 API Key，可放心分享表结构与数据。", "ok"); }
  async function importFile(file) { if (!file) return; const payload = JSON.parse(await file.text()); await requestJson("./api/import", { method: "POST", body: JSON.stringify(payload) }); await loadState(); setStatus("导入完成。", "ok"); pageToast("导入完成", "JSON 数据已写入心笺 SQLite。", "ok"); }

  document.querySelectorAll(".tab-btn").forEach((button) => button.addEventListener("click", () => { switchTab(button.dataset.tab); if (button.dataset.tab === "link") refreshHookStatus(); }));
  els.cardViewBtn.addEventListener("click", () => { state.viewMode = "card"; localStorage.setItem("xinjian:viewMode", state.viewMode); renderAll(); });
  els.tableViewBtn.addEventListener("click", () => { state.viewMode = "table"; localStorage.setItem("xinjian:viewMode", state.viewMode); renderAll(); });
  $("#openSchemaDrawerBtn").addEventListener("click", () => openConfigDrawer("schema"));
  $("#openRulesDrawerBtn").addEventListener("click", () => openConfigDrawer("rules"));
  $("#openModelDrawerBtn").addEventListener("click", () => openConfigDrawer("model"));
  $("#openLinkDrawerBtn").addEventListener("click", () => openConfigDrawer("link"));
  $("#openMujianDrawerBtn").addEventListener("click", () => openConfigDrawer("mujian"));
  $("#openTemplateDrawerBtn")?.addEventListener("click", () => openConfigDrawer("template"));
  $("#openLogDrawerBtn").addEventListener("click", () => { openConfigDrawer("log"); loadLog().catch(() => {}); });
  $("#closeConfigDrawerBtn").addEventListener("click", closeConfigDrawer);
  els.drawerMask.addEventListener("click", closeConfigDrawer);
  $("#closeRowDetailBtn").addEventListener("click", closeRowDetail);
  els.rowDetailMask.addEventListener("click", closeRowDetail);
  $("#saveRowDetailBtn").addEventListener("click", saveRowDetail);
  $("#deleteRowDetailBtn").addEventListener("click", () => { if (state.detailIndex >= 0) { deleteRow(state.detailIndex); closeRowDetail(); } });
  els.rowsEditor.addEventListener("click", (event) => {
    const edit = event.target.closest("[data-edit-row]");
    const del = event.target.closest("[data-delete-row]");
    if (edit) openRowDetail(Number(edit.dataset.editRow));
    if (del) deleteRow(Number(del.dataset.deleteRow));
  });
  $("#refreshBtn").addEventListener("click", () => loadState().catch((error) => setStatus(error.message, "error")));
  $("#saveBtn").addEventListener("click", () => saveCurrentTable().catch((error) => { setStatus(error.message, "error"); pageToast("保存失败", error.message, "error"); }));
  $("#saveConfigBtn").addEventListener("click", () => saveConfig("model").catch((error) => { setStatus(error.message, "error"); pageToast("保存模型配置失败", error.message, "error"); }));
  $("#saveLinkConfigBtn").addEventListener("click", () => saveConfig("link").catch((error) => { setStatus(error.message, "error"); pageToast("保存联动设置失败", error.message, "error"); }));
  $("#saveMujianConfigBtn").addEventListener("click", () => saveConfig("mujian").catch((error) => { setStatus(error.message, "error"); pageToast("保存幕笺设置失败", error.message, "error"); }));
  $("#saveTemplateConfigBtn")?.addEventListener("click", () => saveConfig("template").catch((error) => { setStatus(error.message, "error"); pageToast("保存模板设置失败", error.message, "error"); }));
  $("#saveThemeConfigBtn")?.addEventListener("click", () => saveConfig("theme").catch((error) => { setStatus(error.message, "error"); pageToast("保存美化设置失败", error.message, "error"); }));
  $("#refreshHookBtn").addEventListener("click", () => refreshHookStatus().catch((error) => pageToast("刷新 Hook 状态失败", error.message, "error")));
  $("#fillMainConfigBtn").addEventListener("click", () => fillFromMainConfig().catch((error) => pageToast("读取本体配置失败", error.message, "error")));
  $("#fetchModelsBtn").addEventListener("click", () => fetchModels().catch((error) => { setStatus(error.message, "error"); pageToast("拉取模型列表失败", error.message, "error"); }));
  $("#testConnectionBtn").addEventListener("click", () => testConnection().catch((error) => { setStatus(error.message, "error"); pageToast("测试连接失败", error.message, "error"); }));
  $("#applyPresetBtn").addEventListener("click", applyServicePreset);
  els.cfgMujianStyle?.addEventListener("change", updateMujianStyleHelp);
  els.cfgMujianTitleStyle?.addEventListener("change", updateMujianStyleHelp);
  els.cfgMujianNoteStyle?.addEventListener("change", updateMujianStyleHelp);
  els.cfgMujianTemplateSelect?.addEventListener("change", () => { state.currentTemplateId = els.cfgMujianTemplateSelect.value; if (els.templateSelect) els.templateSelect.value = state.currentTemplateId; const tmpl = activeTemplate(); if (els.cfgMujianNoteStyle) els.cfgMujianNoteStyle.value = tmpl.note_style || "classic"; bindTemplateEditor(); updateMujianStyleHelp(); });

  els.cfgMujianThemeSelect?.addEventListener("change", () => setActiveTheme(els.cfgMujianThemeSelect.value));
  els.themeSelect?.addEventListener("change", () => setActiveTheme(els.themeSelect.value));
  els.exportThemeBtn?.addEventListener("click", () => {
    const pack = activeThemePack();
    const blob = new Blob([JSON.stringify(pack, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob); const a = document.createElement("a");
    a.href = url; a.download = `xinjian-beauty-${pack.id || Date.now()}.json`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    pageToast("美化包已导出", pack.name || pack.id, "ok");
  });
  els.deleteThemeBtn?.addEventListener("click", () => deleteActiveImportedTheme().catch((error) => {
    setStatus(`删除外观包失败：${error.message}`, "error");
    pageToast("删除外观包失败", error.message, "error");
  }));
  els.importThemeInput?.addEventListener("change", async (event) => {
    const file = event.target.files?.[0]; if (!file) return;
    try {
      const payload = JSON.parse(await file.text());
      const pack = normalizeThemePack(payload);
      await persistImportedTheme(pack);
      pageToast("美化包已导入并启用", `${pack.name || pack.id} · 已写入配置`, "ok");
      setStatus(`美化包已导入并启用：${pack.name || pack.id}`, "ok");
    } catch (error) {
      pageToast("导入美化包失败", error.message, "error");
      setStatus(`导入美化包失败：${error.message}`, "error");
    }
    event.target.value = "";
  });

  els.templateSelect?.addEventListener("change", () => {
    const nextId = els.templateSelect.value;
    commitTemplateEditorToState({ rebind: false });
    state.currentTemplateId = nextId;
    state.config = { ...state.config, mujian_template_id: nextId };
    bindTemplateEditor();
    if (els.cfgMujianTemplateSelect) els.cfgMujianTemplateSelect.value = nextId;
  });
  els.templateFieldsEditor?.addEventListener("input", (event) => {
    const card = event.target.closest(".template-field-card");
    if (card) {
      const title = card.querySelector(".template-field-head strong");
      const keyText = card.querySelector(".template-field-head span");
      const key = safeTemplateId(card.querySelector("[data-tpl-key]")?.value || "");
      const label = (card.querySelector("[data-tpl-label]")?.value || key || "字段").trim();
      if (title) title.textContent = label;
      if (keyText) keyText.textContent = key;
    }
    updateTemplatePreview();
  });
  els.templateOutput?.addEventListener("input", updateTemplatePreview);
  els.templateName?.addEventListener("input", updateTemplatePreview);
  els.templateDesc?.addEventListener("input", updateTemplatePreview);
  els.templateNoteStyle?.addEventListener("change", updateTemplatePreview);
  els.templateFieldsEditor?.addEventListener("click", (event) => {
    const up = event.target.closest("[data-tpl-up]");
    const down = event.target.closest("[data-tpl-down]");
    const del = event.target.closest("[data-tpl-delete]");
    if (!up && !down && !del) return;
    const template = readTemplateEditor();
    let index = Number((up || down || del).dataset.tplUp ?? (up || down || del).dataset.tplDown ?? (up || down || del).dataset.tplDelete);
    if (del) template.fields.splice(index, 1);
    if (up && index > 0) [template.fields[index - 1], template.fields[index]] = [template.fields[index], template.fields[index - 1]];
    if (down && index < template.fields.length - 1) [template.fields[index + 1], template.fields[index]] = [template.fields[index], template.fields[index + 1]];
    const templates = mujianTemplates().slice();
    const pos = templates.findIndex((item) => item.id === template.id);
    if (pos >= 0) templates[pos] = template;
    state.config = { ...state.config, mujian_templates: templates };
    renderTemplateFields(template);
    updateTemplatePreview();
  });
  $("#addTemplateFieldBtn")?.addEventListener("click", () => {
    const template = readTemplateEditor();
    const used = new Set(template.fields.map((field) => safeTemplateId(field.key)));
    let n = template.fields.length + 1;
    while (used.has(`field_${n}`)) n += 1;
    const field = { key: `field_${n}`, label: "新字段", instruction: "根据本轮上下文生成该字段。" };
    template.fields.push(field);
    const token = `{${field.key}}`;
    if (!String(template.output_template || "").includes(token)) {
      const line = `<${field.label}(${token})>`;
      template.output_template = `${String(template.output_template || "").trimEnd()}${template.output_template ? "\n" : ""}${line}`;
      if (els.templateOutput) els.templateOutput.value = template.output_template;
    }
    const templates = mujianTemplates().slice();
    const pos = templates.findIndex((item) => item.id === template.id);
    if (pos >= 0) templates[pos] = template;
    state.config = { ...state.config, mujian_templates: templates };
    renderTemplateFields(template); updateTemplatePreview();
  });
  $("#newTemplateBtn")?.addEventListener("click", () => {
    const source = readTemplateEditor();
    const copy = { ...source, id: `custom_${Date.now()}`, name: `${source.name || "模板"} 副本` };
    state.config = { ...state.config, mujian_templates: [...mujianTemplates(), copy], mujian_template_id: copy.id };
    state.currentTemplateId = copy.id; bindTemplateEditor(); pageToast("已复制模板", "修改后点击保存模板设置。", "ok");
  });
  $("#exportTemplateBtn")?.addEventListener("click", () => {
    const template = readTemplateEditor();
    const blob = new Blob([JSON.stringify(template, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob); const a = document.createElement("a");
    a.href = url; a.download = `xinjian-template-${template.id || Date.now()}.json`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    pageToast("模板已导出", template.name || template.id, "ok");
  });
  els.importTemplateInput?.addEventListener("change", async (event) => {
    const file = event.target.files?.[0]; if (!file) return;
    try {
      const template = JSON.parse(await file.text());
      const id = safeTemplateId(template.id || template.name || `custom_${Date.now()}`);
      const normalized = { ...template, id, fields: Array.isArray(template.fields) ? template.fields : [] };
      state.config = { ...state.config, mujian_templates: [...mujianTemplates().filter((item) => item.id !== id), normalized], mujian_template_id: id };
      state.currentTemplateId = id; bindTemplateEditor(); pageToast("模板已导入", normalized.name || id, "ok");
    } catch (error) { pageToast("导入模板失败", error.message, "error"); }
    event.target.value = "";
  });
  $("#toggleApiKeyBtn").addEventListener("click", () => { const hidden = els.cfgApiKey.type === "password"; els.cfgApiKey.type = hidden ? "text" : "password"; $("#toggleApiKeyBtn").textContent = hidden ? "隐藏" : "显示"; });
  $("#manualWorkerBtn").addEventListener("click", () => manualWorkerUpdate().catch((error) => { setStatus(error.message, "error"); pageToast("心笺填表失败", error.message, "error"); }));
  $("#loadLogBtn").addEventListener("click", () => loadLog().catch((error) => { els.logBox.textContent = error.message; }));
  $("#exportDebugLogBtn")?.addEventListener("click", () => exportDebugLog().catch((error) => pageToast("导出排查日志失败", error.message, "error")));
  $("#exportDebugLogBtn")?.addEventListener("click", () => exportDebugLog().catch((error) => pageToast("导出排查日志失败", error.message, "error")));
  $("#addFieldBtn").addEventListener("click", addField); $("#addRowBtn").addEventListener("click", addRow); $("#newTableBtn").addEventListener("click", newTable);
  $("#exportBtn").addEventListener("click", () => exportAll().catch((error) => setStatus(error.message, "error")));
  $("#importInput").addEventListener("change", (event) => importFile(event.target.files?.[0]).catch((error) => { setStatus(error.message, "error"); pageToast("导入失败", error.message, "error"); }));
  window.addEventListener("xinjian:updated", (event) => { els.updateSummaryText.textContent = event.detail?.message || "聊天页自动填表已完成。"; loadState().catch(() => {}); });

  loadState().catch((error) => { setStatus(error.message, "error"); pageToast("心笺载入失败", error.message, "error"); });
})();
