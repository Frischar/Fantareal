(() => {
  const $ = (selector) => document.querySelector(selector);
  const state = {
    config: {},
    tables: [],
    currentId: "",
    viewMode: localStorage.getItem("state_journal:viewMode") || "card",
    detailIndex: -1,
    currentTemplateId: "",
    currentThemeId: "",
    expandedTemplateFieldIndex: null,
    metricCharacterFilter: localStorage.getItem("state_journal:metricCharacterFilter") || "all",
    metricLabelFilter: localStorage.getItem("state_journal:metricLabelFilter") || "all",
    metricSort: localStorage.getItem("state_journal:metricSort") || "newest",
    roleStateConfig: { version: 1, enabled: true, roles: [] },
    activeStageRows: [],
    currentRoleStateId: "",
    roleStateTab: "variables",
    themePreviewMode: localStorage.getItem("state_journal:themePreviewMode") || "role",
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
    "status_panel_pro",
  ]);

  const THEME_PACK_KIND = "state_journal_theme_pack";
  const THEME_PACK_SCHEMA_VERSION = 1;
  const THEME_PACK_MAX_DATA_URI_BYTES = 2 * 1024 * 1024;
  const THEME_PACK_DANGEROUS_KEYS = new Set(["script", "scripts", "javascript", "js", "html", "onload", "onclick", "onerror"]);

  const els = {
    status: $("#statusStrip"),
    updateSummaryText: $("#updateSummaryText"),
    runtimeOverview: $("#runtimeOverview"),
    runtimeEnabledBadge: $("#runtimeEnabledBadge"),
    runtimeAutoBadge: $("#runtimeAutoBadge"),
    runtimeTurnNoteBadge: $("#runtimeTurnNoteBadge"),
    runtimeModelBadge: $("#runtimeModelBadge"),
    runtimeLastRunText: $("#runtimeLastRunText"),
    runtimeFlowText: $("#runtimeFlowText"),
    dashboardEnabled: $("#dashboardEnabled"),
    dashboardAutoUpdate: $("#dashboardAutoUpdate"),
    dashboardTurnNote: $("#dashboardTurnNote"),
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
    cfgUiSyncGlobal: $("#cfgUiSyncGlobal"),
    cfgTurnNoteEnabled: $("#cfgTurnNoteEnabled"),
    cfgTurnNoteTitle: $("#cfgTurnNoteTitle"),
    cfgTurnNoteNote: $("#cfgTurnNoteNote"),
    cfgTurnNoteCollapsed: $("#cfgTurnNoteCollapsed"),
    cfgTurnNoteDisplayMode: $("#cfgTurnNoteDisplayMode"),
    cfgTurnNoteStyle: $("#cfgTurnNoteStyle"),
    cfgTurnNoteTitleStyle: $("#cfgTurnNoteTitleStyle"),
    cfgTurnNoteNoteStyle: $("#cfgTurnNoteNoteStyle"),
    cfgTurnNoteExpand: $("#cfgTurnNoteExpand"),
    cfgTurnNoteDensity: $("#cfgTurnNoteDensity"),
    cfgTurnNoteCharacterFilter: $("#cfgTurnNoteCharacterFilter"),
    cfgTurnNoteCharacterNames: $("#cfgTurnNoteCharacterNames"),
    cfgTurnNoteProtagonistEnabled: $("#cfgTurnNoteProtagonistEnabled"),
    cfgTurnNoteProtagonistMode: $("#cfgTurnNoteProtagonistMode"),
    cfgTurnNoteProtagonistName: $("#cfgTurnNoteProtagonistName"),
    cfgTurnNoteProtagonistAliases: $("#cfgTurnNoteProtagonistAliases"),
    cfgTurnNoteWorkerPromptEnabled: $("#cfgTurnNoteWorkerPromptEnabled"),
    cfgTurnNoteWorkerStylePrompt: $("#cfgTurnNoteWorkerStylePrompt"),
    cfgTurnNoteWorkerProtagonistPrompt: $("#cfgTurnNoteWorkerProtagonistPrompt"),
    resetWorkerPromptBtn: $("#resetWorkerPromptBtn"),
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
    cfgTurnNoteTemplateSelect: $("#cfgTurnNoteTemplateSelect"),
    cfgTurnNoteThemeSelect: $("#cfgTurnNoteThemeSelect"),
    themeSelect: $("#themeSelect"),
    themeName: $("#themeName"),
    themeDesc: $("#themeDesc"),
    themeAuthor: $("#themeAuthor"),
    themeMeta: $("#themeMeta"),
    themePreview: $("#themePreview"),
    themePreviewModeSelect: $("#themePreviewModeSelect"),
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
    let toast = document.getElementById("state-journal-page-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "state-journal-page-toast";
      toast.className = "state-journal-page-toast";
      toast.innerHTML = "<strong></strong><span></span>";
      document.body.appendChild(toast);
    }
    toast.className = `state-journal-page-toast ${type}`;
    toast.querySelector("strong").textContent = title;
    toast.querySelector("span").textContent = detail;
    requestAnimationFrame(() => toast.classList.add("show"));
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => toast.classList.remove("show"), type === "error" ? 6200 : 3600);
  }

  function workerErrorTitle(errorType = "") {
    const titles = {
      timeout: "心笺生成超时",
      empty_response: "心笺返回为空",
      invalid_json: "心笺解析失败",
      invalid_provider_response: "服务商返回异常",
      rate_limit: "服务商限流",
      auth_error: "鉴权失败",
      network_error: "连接失败",
      config_error: "配置不完整",
      provider_error: "服务商异常",
    };
    return titles[errorType] || "心笺生成失败";
  }

  function setManualWorkerBusy(busy) {
    const button = document.getElementById("manualWorkerBtn");
    if (!button) return;
    button.disabled = Boolean(busy);
    button.classList.toggle("is-busy", Boolean(busy));
    button.dataset.originalText = button.dataset.originalText || button.textContent || "根据最近对话更新";
    button.textContent = busy ? "心笺生成中……" : button.dataset.originalText;
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

  const ROLE_STATE_MODES = {
    default: { label: "默认幕笺模板", desc: "使用全局默认幕笺模板，不使用该角色专属变量、阶段或快照字段。" },
    snapshot_only: { label: "仅专属幕笺", desc: "只使用角色专属状态快照字段，不计算变量，不判断阶段。" },
    full: { label: "完整心笺：专属幕笺 + 变量阶段", desc: "启用角色专属幕笺、变量更新与阶段判断，并生成世界书 external_tag。" },
    disabled: { label: "不启用该角色", desc: "该角色不参与心笺记录与幕笺展示。" },
  };


  const ROLE_SOURCE_MODES = {
    auto: { label: "自动识别", desc: "没有多角色时读取主卡；有多角色时默认读取多角色。" },
    main_card: { label: "主卡就是角色", desc: "适合普通单角色卡，心笺会把主卡作为唯一角色记录。" },
    personas_only: { label: "主卡是旁白，只读取多角色", desc: "适合双女主、多角色卡，主卡只作为旁白或总设定。" },
  };

  function normalizeRoleSourceMode(value) {
    const raw = String(value || "").trim().toLowerCase().replace(/-/g, "_");
    const aliases = { main: "main_card", single: "main_card", single_role: "main_card", card: "main_card", persona: "personas_only", personas: "personas_only", multi: "personas_only", multi_role: "personas_only", narrator: "personas_only" };
    const mode = aliases[raw] || raw;
    return ROLE_SOURCE_MODES[mode] ? mode : "auto";
  }

  function roleSourceSummary(config = {}) {
    const summary = config.role_source_summary || {};
    const mode = normalizeRoleSourceMode(config.role_source_mode || summary.mode);
    const label = summary.mode_label || ROLE_SOURCE_MODES[mode]?.label || "自动识别";
    const detected = summary.detected_label || "";
    const message = summary.message || (mode === "auto" ? "自动识别角色来源。" : ROLE_SOURCE_MODES[mode]?.desc || "");
    return { mode, label, detected, message, roleCount: Number(summary.role_count ?? (config.roles || []).length) || 0 };
  }

  function normalizeRoleStateMode(value, role = {}) {
    const raw = String(value || "").trim().toLowerCase().replace(/-/g, "_");
    const aliases = { snapshot: "snapshot_only", snapshotfields: "snapshot_only", snapshot_fields: "snapshot_only", note_only: "snapshot_only", off: "disabled", none: "disabled", disable: "disabled" };
    const mode = aliases[raw] || raw;
    if (ROLE_STATE_MODES[mode]) return mode;
    if (role.enabled === false) return "disabled";
    if ((role.variables || []).length && (role.stages || []).length) return "full";
    if ((role.snapshotFields || []).length) return "snapshot_only";
    return "default";
  }

  function setRoleStateMode(role, mode) {
    const safeMode = ROLE_STATE_MODES[mode] ? mode : "default";
    role.mode = safeMode;
    role.stateJournalMode = safeMode;
    role.enabled = safeMode !== "disabled";
  }

  function roleStateModeLabel(role) {
    const mode = normalizeRoleStateMode(role?.mode || role?.stateJournalMode, role || {});
    return ROLE_STATE_MODES[mode]?.label || ROLE_STATE_MODES.default.label;
  }

  function roleStateModeShortLabel(role) {
    const mode = normalizeRoleStateMode(role?.mode || role?.stateJournalMode, role || {});
    const labels = {
      full: "完整心笺",
      snapshot_only: "专属幕笺",
      default: "默认幕笺",
      disabled: "未启用",
    };
    return labels[mode] || ROLE_STATE_MODES.default.label;
  }

  function roleStateConditionText(role, stage) {
    const variables = new Map((role?.variables || []).map((item) => [item.var_key, item.var_name || item.var_key]));
    const parts = (stage?.conditions || []).map((condition) => {
      const key = condition.var || condition.field || "";
      const label = variables.get(key) || key || "变量";
      const op = condition.op === ">=" ? "≥" : condition.op === "<=" ? "≤" : condition.op === "!=" ? "≠" : condition.op === "=" ? "=" : condition.op || "≥";
      return `${label} ${op} ${condition.value ?? 0}`;
    }).filter(Boolean);
    if (!parts.length) return "无条件";
    return parts.join(stage?.condition_mode === "any" ? " 或 " : " 且 ");
  }

  function roleStateConditionChips(role, stage) {
    const variables = new Map((role?.variables || []).map((item) => [item.var_key, item.var_name || item.var_key]));
    const conditions = Array.isArray(stage?.conditions) ? stage.conditions : [];
    if (!conditions.length) return `<span class="stage-condition-chip muted">无条件</span>`;
    const visible = conditions.slice(0, 3).map((condition) => {
      const key = condition.var || condition.field || "";
      const label = variables.get(key) || key || "变量";
      const op = condition.op === ">=" ? "≥" : condition.op === "<=" ? "≤" : condition.op === "!=" ? "≠" : condition.op === "=" ? "=" : condition.op || "≥";
      return `<span class="stage-condition-chip">${escapeHtml(label)} ${escapeHtml(op)} ${escapeHtml(condition.value ?? 0)}</span>`;
    });
    if (conditions.length > visible.length) visible.push(`<span class="stage-condition-chip muted">+${conditions.length - visible.length} 条</span>`);
    const mode = stage?.condition_mode === "any" ? "任一满足" : "全部满足";
    return `<span class="stage-condition-mode">${mode}</span>${visible.join("")}`;
  }

  function roleStateStageTagState(role, stage, isCurrent) {
    const active = activeStageForRole(role);
    const tag = stageActivationTag(role, stage);
    const activeTag = String(active?.active_tag || active?.tag || "").trim();
    if (isCurrent && activeTag && tag && activeTag === tag) return { label: "当前命中", cls: "is-active" };
    if (isCurrent) return { label: "当前阶段", cls: "is-current" };
    return { label: "世界书", cls: "" };
  }

  function confirmAction({ title, body, confirmText = "确认", danger = false }) {
    return new Promise((resolve) => {
      let modal = document.getElementById("state-journal-confirm-modal");
      if (!modal) {
        modal = document.createElement("div");
        modal.id = "state-journal-confirm-modal";
        modal.className = "state-journal-confirm-modal";
        modal.innerHTML = `<div class="state-journal-confirm-card"><h3></h3><div class="state-journal-confirm-body"></div><div class="state-journal-confirm-actions"><button type="button" data-confirm-cancel class="ghost-btn">取消</button><button type="button" data-confirm-ok class="primary-btn">确认</button></div></div>`;
        document.body.appendChild(modal);
      }
      modal.querySelector("h3").textContent = title || "确认操作";
      modal.querySelector(".state-journal-confirm-body").innerHTML = body || "";
      const ok = modal.querySelector("[data-confirm-ok]");
      ok.textContent = confirmText;
      ok.classList.toggle("danger", Boolean(danger));
      modal.classList.add("show");
      const cleanup = (value) => {
        modal.classList.remove("show");
        modal.querySelector("[data-confirm-cancel]").onclick = null;
        ok.onclick = null;
        resolve(value);
      };
      modal.querySelector("[data-confirm-cancel]").onclick = () => cleanup(false);
      ok.onclick = () => cleanup(true);
    });
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

  function turnNoteTemplates() {
    return Array.isArray(state.config?.turn_note_templates) ? state.config.turn_note_templates : [];
  }

  function activeTemplateId() {
    return state.currentTemplateId || state.config?.turn_note_template_id || turnNoteTemplates()[0]?.id || "classic";
  }

  function activeTemplate() {
    const id = activeTemplateId();
    return turnNoteTemplates().find((item) => item.id === id) || turnNoteTemplates()[0] || { id: "classic", name: "简洁状态", note_style: "classic", fields: [], output_template: "" };
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
    const templates = turnNoteTemplates();
    const active = activeTemplateId();
    const options = templates.map((item) => {
      const selected = item.id === active ? "selected" : "";
      return `<option value="${escapeAttr(item.id)}" ${selected}>${escapeHtml(item.name || item.id)}</option>`;
    }).join("");
    if (els.cfgTurnNoteTemplateSelect) els.cfgTurnNoteTemplateSelect.innerHTML = options;
    if (els.templateSelect) els.templateSelect.innerHTML = options;
  }


  function safeThemeId(value) {
    return String(value || "").trim().toLowerCase().replace(/[^a-z0-9_]+/g, "_").replace(/^_+|_+$/g, "") || `theme_${Date.now()}`;
  }

  function turnNoteThemePacks() {
    return Array.isArray(state.config?.turn_note_theme_packs) ? state.config.turn_note_theme_packs : [];
  }

  function activeThemeId() {
    return state.currentThemeId || state.config?.turn_note_theme_id || turnNoteThemePacks()[0]?.id || "standard";
  }

  function activeThemePack() {
    const id = activeThemeId();
    return turnNoteThemePacks().find((item) => item.id === id) || turnNoteThemePacks()[0] || {
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

  function themePackSourceLabel(pack) {
    return isBuiltinThemePack(pack) ? "内置外观包" : "外置美化包";
  }

  function themePackDisplayName(pack) {
    return String(pack?.name || pack?.id || "未命名外观包");
  }

  function fallbackThemeIdAfterDelete(packs) {
    const list = Array.isArray(packs) ? packs : turnNoteThemePacks();
    return list.find((item) => item?.id === "standard")?.id
      || list.find((item) => isBuiltinThemePack(item))?.id
      || "standard";
  }

  function validateThemePackSafety(value, path = "美化包") {
    if (!value || typeof value !== "object") return;
    Object.entries(value).forEach(([key, item]) => {
      const lowerKey = String(key || "").toLowerCase();
      if (THEME_PACK_DANGEROUS_KEYS.has(lowerKey) || lowerKey.startsWith("on")) {
        throw new Error(`${path} 包含不允许的字段：${key}`);
      }
      if (typeof item === "string") {
        const text = item.trim();
        if (/^https?:\/\//i.test(text)) {
          throw new Error(`${path}.${key} 引用了远程资源，外观包只允许内嵌 data URI 或本地样式标记。`);
        }
        if (/^data:/i.test(text) && text.length > THEME_PACK_MAX_DATA_URI_BYTES) {
          throw new Error(`${path}.${key} 的内嵌资源过大，请压缩后再导入。`);
        }
      }
      if (item && typeof item === "object") validateThemePackSafety(item, `${path}.${key}`);
    });
  }

  function themePackLayoutType(pack) {
    const layout = pack?.style?.layout || pack?.layout || {};
    return String(layout.layout_type || layout.type || layout.character_card || "standard").trim() || "standard";
  }

  function themePackProgressBars(pack) {
    const list = pack?.style?.progress_bars || pack?.progress_bars || [];
    return Array.isArray(list) ? list : [];
  }

  function themePackWarnings(pack) {
    const warnings = [];
    if (!pack?.kind) warnings.push("旧版包：已自动补充 kind。");
    if (!pack?.schema_version) warnings.push("旧版包：已自动补充 schema_version。");
    if (!pack?.style?.layout) warnings.push("未声明 layout，将使用默认预览布局。");
    if (!pack?.style?.class_name) warnings.push("未声明 class_name，将自动生成安全类名。");
    return warnings;
  }

  function normalizeThemePack(pack) {
    if (!pack || typeof pack !== "object") throw new Error("美化包必须是 JSON 对象。");
    const rawKind = String(pack.kind || pack.type || THEME_PACK_KIND).trim() || THEME_PACK_KIND;
    if (![THEME_PACK_KIND, "xinjian_theme_pack", "turn_note_theme_pack"].includes(rawKind)) {
      throw new Error(`这不是心笺外观模板包：${rawKind}`);
    }
    const schemaVersion = Number(pack.schema_version || pack.schemaVersion || THEME_PACK_SCHEMA_VERSION);
    if (!Number.isFinite(schemaVersion) || schemaVersion < 1) throw new Error("美化包 schema_version 无效。");
    if (schemaVersion > THEME_PACK_SCHEMA_VERSION) throw new Error(`美化包 schema_version=${schemaVersion} 高于当前支持版本 ${THEME_PACK_SCHEMA_VERSION}。`);
    validateThemePackSafety(pack);
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
    ["layout", "blocks", "tokens", "field_style", "media", "labels"].forEach((key) => {
      if (pack[key] && typeof pack[key] === "object" && !Array.isArray(pack[key])) safeStyle[key] = pack[key];
      else if (style[key] && typeof style[key] === "object" && !Array.isArray(style[key])) safeStyle[key] = style[key];
    });
    ["progress_bars"].forEach((key) => {
      if (Array.isArray(pack[key])) safeStyle[key] = pack[key];
      else if (Array.isArray(style[key])) safeStyle[key] = style[key];
    });
    const normalized = {
      kind: THEME_PACK_KIND,
      schema_version: THEME_PACK_SCHEMA_VERSION,
      id,
      name: String(pack?.name || id).trim() || id,
      version: String(pack?.version || "1.0.0").trim() || "1.0.0",
      author: String(pack?.author || "").trim(),
      description: String(pack?.description || "").trim(),
      style: safeStyle,
    };
    if (pack.media && typeof pack.media === "object") normalized.media = pack.media;
    if (pack.labels && typeof pack.labels === "object") normalized.labels = pack.labels;
    normalized.__warnings = themePackWarnings(pack);
    return normalized;
  }

  function mergeThemePack(pack) {
    const packs = turnNoteThemePacks().filter((item) => item && item.id !== pack.id);
    return [...packs, pack];
  }

  function persistableThemePack(pack) {
    const { __warnings, ...rest } = pack || {};
    return rest;
  }

  async function persistImportedTheme(pack) {
    const cleanPack = persistableThemePack(pack);
    state.config = {
      ...state.config,
      turn_note_theme_packs: mergeThemePack(cleanPack),
      turn_note_theme_id: cleanPack.id,
    };
    pack = cleanPack;
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
    window.stateJournalChatBridge?.reloadConfig?.();
    return payload;
  }


  async function deleteActiveImportedTheme() {
    const pack = activeThemePack();
    if (!pack?.id) return;
    if (isBuiltinThemePack(pack)) {
      pageToast("内置外观包不可删除", "可以导出内置包作为模板，再导入为新的自定义外观包。", "error");
      return;
    }
    const nextPacks = turnNoteThemePacks().filter((item) => item && item.id !== pack.id);
    const nextThemeId = fallbackThemeIdAfterDelete(nextPacks);
    const ok = await confirmAction({
      title: "删除外置美化包？",
      body: `
        <p>将删除：<strong>${escapeHtml(themePackDisplayName(pack))}</strong></p>
        <div class="sync-card-scope">
          <strong>不会影响</strong>
          <p>心笺数据、幕笺历史、角色变量、阶段规则、世界书标签。</p>
          <strong>删除后</strong>
          <p>如果当前正在使用该外观包，将自动切回「${escapeHtml(nextPacks.find((item) => item?.id === nextThemeId)?.name || "标准样式")}」。</p>
        </div>
      `,
      confirmText: "确认删除",
      danger: true,
    });
    if (!ok) return;
    state.config = {
      ...state.config,
      turn_note_theme_packs: nextPacks,
      turn_note_theme_id: nextThemeId,
    };
    state.currentThemeId = nextThemeId;
    renderThemeSelectors();
    renderThemePreview();
    const payload = await requestJson("./api/config", {
      method: "POST",
      body: JSON.stringify({ config: readConfig() }),
    });
    state.config = payload.config || state.config;
    state.currentThemeId = state.config.turn_note_theme_id || nextThemeId;
    renderThemeSelectors();
    renderThemePreview();
    window.stateJournalChatBridge?.reloadConfig?.();
    pageToast("导入外观包已删除", `已切回：${activeThemePack().name || activeThemePack().id}`, "ok");
    setStatus(`已删除导入外观包：${pack.name || pack.id}`, "ok");
  }

  function renderThemeSelectors() {
    const packs = turnNoteThemePacks();
    const active = activeThemeId();
    const option = (item) => `<option value="${escapeAttr(item.id)}" ${item.id === active ? "selected" : ""}>${escapeHtml(item.name || item.id)}</option>`;
    const builtins = packs.filter((item) => item && isBuiltinThemePack(item));
    const imports = packs.filter((item) => item && !isBuiltinThemePack(item));
    const options = [
      builtins.length ? `<optgroup label="内置外观包">${builtins.map(option).join("")}</optgroup>` : "",
      imports.length ? `<optgroup label="外置美化包">${imports.map(option).join("")}</optgroup>` : "",
    ].join("") || packs.map(option).join("");
    if (els.cfgTurnNoteThemeSelect) els.cfgTurnNoteThemeSelect.innerHTML = options;
    if (els.themeSelect) els.themeSelect.innerHTML = options;
  }

  function renderThemePackMeta(pack) {
    if (!els.themeMeta) return;
    const builtin = isBuiltinThemePack(pack);
    const progressCount = themePackProgressBars(pack).length;
    const layoutType = themePackLayoutType(pack);
    const style = pack.style || {};
    const chips = [
      themePackSourceLabel(pack),
      `schema v${pack.schema_version || THEME_PACK_SCHEMA_VERSION}`,
      `layout: ${layoutType}`,
      `class: ${style.class_name || "theme-standard"}`,
      progressCount ? `数值条 ${progressCount}` : "默认数值显示",
    ];
    const warnings = Array.isArray(pack.__warnings) ? pack.__warnings : [];
    els.themeMeta.innerHTML = `
      <div class="theme-pack-chip-row">${chips.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>
      ${warnings.length ? `<div class="theme-pack-warning">${warnings.map(escapeHtml).join(" · ")}</div>` : ""}
      <p>美化包只改变幕笺外观与字段呈现；不会修改变量计算、阶段判断、世界书标签或 worker 提示词。</p>
    `;
  }

  function renderThemePreview() {
    const pack = activeThemePack();
    if (els.cfgTurnNoteThemeSelect) els.cfgTurnNoteThemeSelect.value = pack.id;
    if (els.themeSelect) els.themeSelect.value = pack.id;
    if (els.themeName) els.themeName.value = pack.name || "";
    if (els.themeAuthor) els.themeAuthor.value = pack.author || "";
    if (els.themeDesc) els.themeDesc.value = pack.description || "";
    if (els.deleteThemeBtn) {
      const builtin = isBuiltinThemePack(pack);
      els.deleteThemeBtn.disabled = builtin;
      els.deleteThemeBtn.title = builtin ? "内置外观包不可删除" : `删除导入外观包：${pack.name || pack.id}`;
      els.deleteThemeBtn.textContent = "删除";
    }
    if (els.themePreviewModeSelect) els.themePreviewModeSelect.value = state.themePreviewMode || "role";
    renderThemePackMeta(pack);
    const style = pack.style || {};
    const cls = String(style.class_name || "theme-standard");
    const accent = String(style.accent || "");
    const tokens = style.tokens || pack.tokens || {};
    const progressBars = themePackProgressBars(pack);
    const layoutType = themePackLayoutType(pack);
    const normalizePreviewLabel = (value) => String(value || "").replace(/\s+/g, "").trim().toLowerCase();
    const fieldLabel = (key, fallback) => {
      const mark = String(tokens[key] || tokens[fallback] || "").trim();
      const label = String(fallback || key || "字段").trim();
      if (!mark || normalizePreviewLabel(mark) === normalizePreviewLabel(label)) return escapeHtml(label);
      return `<span class="theme-preview-field-token">${escapeHtml(mark)}</span><span class="theme-preview-field-name">${escapeHtml(label)}</span>`;
    };
    const previewMetricSets = {
      role: [
        { key: "trust", name: "信任", value: 43, delta: "+3" },
        { key: "warmth", name: "亲近", value: 31, delta: "+2" },
        { key: "worry", name: "担忧", value: 34, delta: "+0" },
        { key: "respect", name: "认可", value: 48, delta: "+1" },
      ],
      standard: [
        { key: "favor_level", name: "好感", value: 43, delta: "+3" },
        { key: "trust_level", name: "信任", value: 31, delta: "+2" },
        { key: "guard_level", name: "戒备", value: 64, delta: "-3" },
        { key: "pulse_level", name: "心绪", value: 48, delta: "+0" },
      ],
    };
    const previewMetrics = previewMetricSets[state.themePreviewMode || "role"] || previewMetricSets.role;
    const metricLabel = (bar, idx) => escapeHtml(bar.name || bar.display_name || bar.fallback_label || bar.label_cn || bar.cn || bar.title || ["信任", "亲近", "担忧", "认可"][idx] || bar.label || bar.key || "数值");
    const isHudPreview = ["status_panel", "status_panel_pro", "hud", "hud_rows"].includes(layoutType)
      || /(?:^|-)theme-status-(?:panel|pro)/.test(cls)
      || /status-panel|status_pro|status-panel-advanced/i.test(`${pack?.id || ""} ${pack?.name || ""} ${cls}`);
    const metricChipHtml = (metric, idx) => {
      const bar = progressBars[idx] || metric;
      const label = metricLabel({ ...bar, name: metric.name }, idx);
      return `<span class="theme-preview-metric-chip"><b>${label}</b>${metric.value}/100（${metric.delta}）</span>`;
    };
    const metricBarHtml = (metric, idx) => {
      const bar = progressBars[idx] || metric;
      const label = metricLabel({ ...bar, name: metric.name }, idx);
      return `<div class="theme-preview-metric"><span>${label}</span><b>${metric.value}/100（${metric.delta}）</b><i style="--xj-preview-value:${metric.value}%"></i></div>`;
    };
    // v1.19.4：进度条只作为 HUD / 状态面板类外观的特色；其他外观包恢复胶囊数值，避免朱砂、古风、月白等被强制进度条化。
    const progressHtml = isHudPreview
      ? `<div class="theme-preview-metrics is-meter-preview">${previewMetrics.map(metricBarHtml).join("")}</div>`
      : `<div class="theme-preview-metrics compact is-chip-preview">${previewMetrics.map(metricChipHtml).join("")}</div>`;
    if (els.themePreview) {
      els.themePreview.className = `theme-preview-card ${cls}`;
      if (accent) els.themePreview.style.setProperty("--xj-beauty-accent", accent);
      els.themePreview.innerHTML = `
        <div class="theme-preview-title"><span>${layoutType === "status_panel_pro" ? "STATUS" : layoutType === "storyboard" ? "SCENE" : layoutType === "paper_time" ? "TIME NOTE" : "XINJIAN"}</span><strong>第六笺 · 《旧雨入帘》</strong><em>入夜 · 霜庭书馆 · 小雨初歇 · ${state.themePreviewMode === "standard" ? "标准模板预览" : "角色变量预览"}</em></div>
        <div class="theme-preview-role"><h4>沈栖雪 · C阶段</h4><p><b>${fieldLabel("emotion", "情绪")}</b> 温静中带着担忧，主动递灯提醒用户休息。</p><p><b>${fieldLabel("focus", "关注点")}</b> 卷宗风险、用户状态与书馆规矩。</p><p><b>${fieldLabel("summary", "摘要")}</b> 信任稳定上升，照料动作更主动。</p>${progressHtml}</div>
        <div class="theme-preview-role"><h4>陆青鸢 · B阶段</h4><p><b>${fieldLabel("interaction", "互动")}</b> 仍然嘴硬，但开始承认用户的配合与判断。</p></div>
        <div class="theme-preview-relation"><b>阶段变化</b> 沈栖雪：B阶段 → C阶段；陆青鸢：维持 B阶段。</div>
      `;
    }
  }

  function setActiveTheme(id) {
    state.currentThemeId = safeThemeId(id || activeThemeId());
    state.config = { ...state.config, turn_note_theme_id: state.currentThemeId };
    renderThemeSelectors();
    renderThemePreview();
  }

  function bindTemplateEditor() {
    renderTemplateSelectors();
    let template = ensureTemplateOutputFields(activeTemplate());
    const templates = turnNoteTemplates().slice();
    const templatePos = templates.findIndex((item) => item.id === template.id);
    if (templatePos >= 0) { templates[templatePos] = template; state.config = { ...state.config, turn_note_templates: templates }; }
    if (els.cfgTurnNoteTemplateSelect) els.cfgTurnNoteTemplateSelect.value = template.id;
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
    if (state.expandedTemplateFieldIndex !== null && state.expandedTemplateFieldIndex >= fields.length) {
      state.expandedTemplateFieldIndex = null;
    }
    els.templateFieldsEditor.innerHTML = fields.map((field, index) => {
      const expanded = state.expandedTemplateFieldIndex === index;
      const key = safeTemplateId(field.key || "");
      const label = field.label || key || "字段";
      const instruction = String(field.instruction || "根据本轮上下文生成该字段。").replace(/\s+/g, " ").trim();
      return `
      <div class="template-field-card ${expanded ? "expanded" : ""}" data-template-field-index="${index}">
        <div class="template-field-head" data-tpl-toggle="${index}">
          <button type="button" class="ghost-btn mini template-field-toggle" data-tpl-toggle="${index}">${expanded ? "收起" : "展开"}</button>
          <span class="template-field-title"><strong>${escapeHtml(label)}</strong><small class="template-field-summary">${escapeHtml(instruction)}</small></span>
          <span class="template-field-key">${escapeHtml(key)}</span>
        </div>
        <div class="template-field-body">
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
      </div>`;
    }).join("") || `<div class="empty-state"><strong>暂无字段。</strong><span>点击“新增字段”开始配置。</span></div>`;
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
    const templates = turnNoteTemplates().slice();
    const index = templates.findIndex((item) => item.id === template.id);
    if (index >= 0) templates[index] = template; else templates.push(template);
    state.config = { ...state.config, turn_note_templates: templates, turn_note_template_id: template.id, turn_note_card_style: template.note_style, turn_note_style: template.note_style };
    state.currentTemplateId = template.id;
    if (options.rebind !== false) {
      bindTemplateEditor();
      bindConfig();
    }
    return template;
  }

  function applyAdminUiSyncMode(cfg = state.config || {}) {
    document.documentElement.dataset.stateJournalUiSync = cfg.ui_sync_global ? "global" : "native";
  }


  function statusText(enabled, onText = "开启", offText = "关闭") {
    return enabled ? onText : offText;
  }

  function setRuntimeBadge(el, enabled, onText, offText) {
    if (!el) return;
    el.textContent = statusText(enabled, onText, offText);
    el.classList.toggle("is-on", !!enabled);
    el.classList.toggle("is-off", !enabled);
  }

  function renderRuntimeOverview() {
    const cfg = state.config || {};
    const enabled = cfg.enabled !== false;
    const autoUpdate = !!cfg.auto_update;
    const turnNoteEnabled = cfg.turn_note_enabled !== false;
    setRuntimeBadge(els.runtimeEnabledBadge, enabled, "心笺启用", "心笺关闭");
    setRuntimeBadge(els.runtimeAutoBadge, autoUpdate, "自动填表", "手动填表");
    setRuntimeBadge(els.runtimeTurnNoteBadge, turnNoteEnabled, "幕笺展示", "幕笺关闭");
    if (els.runtimeModelBadge) els.runtimeModelBadge.textContent = cfg.model ? `模型 ${cfg.model}` : "模型未配置";
    if (els.runtimeLastRunText) els.runtimeLastRunText.textContent = els.updateSummaryText?.textContent || "暂无填表记录。";
    if (els.runtimeFlowText) {
      if (!enabled) els.runtimeFlowText.textContent = "当前不会在聊天后运行心笺，也不会写入结构化记录。";
      else if (!autoUpdate) els.runtimeFlowText.textContent = "心笺已启用，但聊天后自动填表关闭；可手动根据最近对话更新。";
      else if (!turnNoteEnabled) els.runtimeFlowText.textContent = "聊天后会自动填表并写入 SQLite，但 Chat 页面不显示幕笺。";
      else els.runtimeFlowText.textContent = "聊天回复完成 → Hook 直传 → 心笺 worker 填表 → 写入 SQLite → Chat 显示幕笺。";
    }
    if (els.dashboardEnabled) els.dashboardEnabled.checked = enabled;
    if (els.dashboardAutoUpdate) els.dashboardAutoUpdate.checked = autoUpdate;
    if (els.dashboardTurnNote) els.dashboardTurnNote.checked = turnNoteEnabled;
  }

  function bindConfig() {
    const cfg = state.config || {};
    els.cfgEnabled.checked = !!cfg.enabled;
    els.cfgAutoUpdate.checked = !!cfg.auto_update;
    els.cfgNotify.checked = !!cfg.notify_in_chat;
    if (els.cfgUiSyncGlobal) els.cfgUiSyncGlobal.checked = !!cfg.ui_sync_global;
    applyAdminUiSyncMode(cfg);
    if (els.cfgTurnNoteEnabled) els.cfgTurnNoteEnabled.checked = cfg.turn_note_enabled !== false;
    if (els.cfgTurnNoteTitle) els.cfgTurnNoteTitle.checked = cfg.turn_note_title_card !== false;
    if (els.cfgTurnNoteNote) els.cfgTurnNoteNote.checked = cfg.turn_note_card !== false;
    if (els.cfgTurnNoteCollapsed) els.cfgTurnNoteCollapsed.checked = cfg.turn_note_default_collapsed !== false;
    if (els.cfgTurnNoteDisplayMode) els.cfgTurnNoteDisplayMode.value = cfg.turn_note_chat_display_mode || (cfg.turn_note_default_collapsed === false ? "expanded" : "collapsed");
    if (els.cfgTurnNoteStyle) els.cfgTurnNoteStyle.value = cfg.turn_note_style || "classic";
    if (els.cfgTurnNoteTitleStyle) els.cfgTurnNoteTitleStyle.value = cfg.turn_note_title_style || cfg.turn_note_style || "classic";
    if (els.cfgTurnNoteNoteStyle) els.cfgTurnNoteNoteStyle.value = cfg.turn_note_card_style || cfg.turn_note_style || "classic";
    if (els.cfgTurnNoteExpand) els.cfgTurnNoteExpand.value = cfg.turn_note_expand_level || "standard";
    if (els.cfgTurnNoteDensity) els.cfgTurnNoteDensity.value = cfg.turn_note_density || "standard";
    if (els.cfgTurnNoteCharacterFilter) els.cfgTurnNoteCharacterFilter.value = cfg.turn_note_character_filter || "turn";
    state.currentTemplateId = cfg.turn_note_template_id || state.currentTemplateId || turnNoteTemplates()[0]?.id || "classic";
    state.currentThemeId = cfg.turn_note_theme_id || state.currentThemeId || turnNoteThemePacks()[0]?.id || "standard";
    renderThemeSelectors();
    renderThemePreview();
    renderTemplateSelectors();
    if (els.cfgTurnNoteTemplateSelect) els.cfgTurnNoteTemplateSelect.value = state.currentTemplateId;
    if (els.cfgTurnNoteCharacterNames) els.cfgTurnNoteCharacterNames.value = cfg.turn_note_character_names || "";
    if (els.cfgTurnNoteProtagonistEnabled) els.cfgTurnNoteProtagonistEnabled.checked = !!cfg.turn_note_protagonist_card_enabled;
    if (els.cfgTurnNoteProtagonistMode) els.cfgTurnNoteProtagonistMode.value = cfg.turn_note_protagonist_card_mode || "when_relevant";
    if (els.cfgTurnNoteProtagonistName) els.cfgTurnNoteProtagonistName.value = cfg.turn_note_protagonist_name || "";
    if (els.cfgTurnNoteProtagonistAliases) els.cfgTurnNoteProtagonistAliases.value = cfg.turn_note_protagonist_aliases || "";
    if (els.cfgTurnNoteWorkerPromptEnabled) els.cfgTurnNoteWorkerPromptEnabled.checked = !!cfg.turn_note_worker_custom_prompt_enabled;
    if (els.cfgTurnNoteWorkerStylePrompt) els.cfgTurnNoteWorkerStylePrompt.value = cfg.turn_note_worker_style_prompt || "";
    if (els.cfgTurnNoteWorkerProtagonistPrompt) els.cfgTurnNoteWorkerProtagonistPrompt.value = cfg.turn_note_worker_protagonist_prompt || "";
    bindTemplateEditor();
    updateTurnNoteStyleHelp();
    els.cfgBaseUrl.value = cfg.api_base_url || "";
    els.cfgApiKey.value = cfg.api_key || "";
    els.cfgModel.value = cfg.model || "";
    els.cfgTurns.value = cfg.input_turn_count || 3;
    els.cfgTimeout.value = cfg.request_timeout || 120;
    syncPresetSelectFromBaseUrl();
    renderRuntimeOverview();
  }

  function readConfig() {
    return {
      ...state.config,
      enabled: els.cfgEnabled.checked,
      auto_update: els.cfgAutoUpdate.checked,
      notify_in_chat: els.cfgNotify.checked,
      ui_sync_global: els.cfgUiSyncGlobal ? els.cfgUiSyncGlobal.checked : false,
      turn_note_enabled: els.cfgTurnNoteEnabled ? els.cfgTurnNoteEnabled.checked : true,
      turn_note_title_card: els.cfgTurnNoteTitle ? els.cfgTurnNoteTitle.checked : true,
      turn_note_card: els.cfgTurnNoteNote ? els.cfgTurnNoteNote.checked : true,
      turn_note_default_collapsed: els.cfgTurnNoteDisplayMode ? els.cfgTurnNoteDisplayMode.value === "collapsed" : (els.cfgTurnNoteCollapsed ? els.cfgTurnNoteCollapsed.checked : true),
      turn_note_chat_display_mode: els.cfgTurnNoteDisplayMode ? els.cfgTurnNoteDisplayMode.value : (els.cfgTurnNoteCollapsed && !els.cfgTurnNoteCollapsed.checked ? "expanded" : "collapsed"),
      turn_note_style: els.cfgTurnNoteNoteStyle ? els.cfgTurnNoteNoteStyle.value : (els.cfgTurnNoteStyle ? els.cfgTurnNoteStyle.value : "classic"),
      turn_note_title_style: els.cfgTurnNoteTitleStyle ? els.cfgTurnNoteTitleStyle.value : "classic",
      turn_note_card_style: els.cfgTurnNoteNoteStyle ? els.cfgTurnNoteNoteStyle.value : "classic",
      turn_note_expand_level: els.cfgTurnNoteExpand ? els.cfgTurnNoteExpand.value : "standard",
      turn_note_density: els.cfgTurnNoteDensity ? els.cfgTurnNoteDensity.value : "standard",
      turn_note_character_filter: els.cfgTurnNoteCharacterFilter ? els.cfgTurnNoteCharacterFilter.value : "turn",
      turn_note_character_names: els.cfgTurnNoteCharacterNames ? els.cfgTurnNoteCharacterNames.value.trim() : "",
      turn_note_protagonist_card_enabled: els.cfgTurnNoteProtagonistEnabled ? els.cfgTurnNoteProtagonistEnabled.checked : false,
      turn_note_protagonist_card_mode: els.cfgTurnNoteProtagonistMode ? els.cfgTurnNoteProtagonistMode.value : "when_relevant",
      turn_note_protagonist_name: els.cfgTurnNoteProtagonistName ? els.cfgTurnNoteProtagonistName.value.trim() : "",
      turn_note_protagonist_aliases: els.cfgTurnNoteProtagonistAliases ? els.cfgTurnNoteProtagonistAliases.value.trim() : "",
      turn_note_worker_custom_prompt_enabled: els.cfgTurnNoteWorkerPromptEnabled ? els.cfgTurnNoteWorkerPromptEnabled.checked : false,
      turn_note_worker_style_prompt: els.cfgTurnNoteWorkerStylePrompt ? els.cfgTurnNoteWorkerStylePrompt.value.trim() : "",
      turn_note_worker_protagonist_prompt: els.cfgTurnNoteWorkerProtagonistPrompt ? els.cfgTurnNoteWorkerProtagonistPrompt.value.trim() : "",
      turn_note_template_id: activeTemplateId(),
      turn_note_templates: turnNoteTemplates(),
      turn_note_theme_id: activeThemeId(),
      turn_note_theme_packs: turnNoteThemePacks(),
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

  function updateTurnNoteStyleHelp() {
    const titleStyle = els.cfgTurnNoteTitleStyle?.value || "classic";
    const noteStyle = els.cfgTurnNoteNoteStyle?.value || els.cfgTurnNoteStyle?.value || "classic";
    const titleItem = MUJIAN_TITLE_STYLE_PREVIEWS[titleStyle] || MUJIAN_TITLE_STYLE_PREVIEWS.classic;
    const noteItem = MUJIAN_NOTE_STYLE_PREVIEWS[noteStyle] || MUJIAN_NOTE_STYLE_PREVIEWS.classic;
    const descEl = document.getElementById("turnNoteStyleDesc");
    const previewEl = document.getElementById("turnNoteStylePreview");
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

  function pickField(fields, keys) {
    return keys.map((key) => fields.find((field) => field.key === key)).find(Boolean) || null;
  }

  function rowValue(row, key) {
    return key ? row?.[key] : "";
  }

  function cardSummaryForRow(table, row, fields, displayFields) {
    const summaryField = pickField(fields, ["summary", "status_summary", "description", "note"]);
    if (summaryField && textValue(rowValue(row, summaryField.key)).trim()) return summaryField;
    return displayFields.find((field) => field.type === "textarea") || displayFields[0] || null;
  }

  function relationTitle(row, primaryFallback) {
    const from = textValue(row.from || row.role_a || row.source || "").trim();
    const to = textValue(row.to || row.role_b || row.target || "").trim();
    if (from || to) return `${from || "未知角色"} → ${to || "未知角色"}`;
    return primaryFallback;
  }

  function renderRowsAsCards(table) {
    const fields = table.schema.fields || [];
    const primary = table.schema.primary_key || fields[0]?.key;
    const displayFields = getDisplayFields(table).filter((field) => field.key !== primary);
    const list = document.createElement("div");
    list.className = `row-card-list ${table.schema?.id === "relationship" ? "relationship-list" : ""}`;
    (table.rows || []).forEach((row, index) => {
      const card = document.createElement("article");
      card.className = `row-card readable-row-card ${table.schema?.id === "character_status" ? "character-row-card" : ""} ${table.schema?.id === "relationship" ? "relationship-row-card" : ""}`;
      const primaryTitle = primary ? (row[primary] || `第 ${index + 1} 行`) : `第 ${index + 1} 行`;
      const title = table.schema?.id === "relationship" ? relationTitle(row, primaryTitle) : primaryTitle;
      const summaryField = cardSummaryForRow(table, row, fields, displayFields);
      const summary = summaryField ? compactText(row[summaryField.key], 150) : "暂无摘要。";
      const chipFields = displayFields
        .filter((field) => field.key !== summaryField?.key)
        .filter((field) => !["from", "to", "role_a", "role_b", "source", "target"].includes(field.key))
        .slice(0, 5);
      const badgeField = pickField(fields, ["relation", "mood", "condition", "status", "state"]);
      const badgeText = badgeField ? compactText(row[badgeField.key], 18) : (table.schema?.name || "记录");
      card.innerHTML = `
        <div class="row-card-head readable-row-head">
          <span class="row-card-title"><strong>${escapeHtml(title)}</strong><small>${escapeHtml(table.schema?.name || table.schema?.id || "记录")}</small></span>
          <div class="row-card-head-actions">
            <span class="row-status-badge">${escapeHtml(badgeText)}</span>
            <button class="ghost-btn small" type="button" data-edit-row="${index}">详情</button>
          </div>
        </div>
        <div class="row-summary-block">
          <span>${escapeHtml(summaryField ? fieldLabel(summaryField) : "状态摘要")}</span>
          <p>${escapeHtml(summary)}</p>
        </div>
        <div class="row-chip-grid readable-chip-grid">
          ${chipFields.map((field) => `<div class="row-chip"><span>${escapeHtml(fieldLabel(field))}</span><strong>${escapeHtml(compactText(row[field.key], field.type === "textarea" ? 92 : 48))}</strong></div>`).join("")}
        </div>
        <div class="row-card-actions">
          <button class="delete-btn" type="button" data-delete-row="${index}">删除</button>
        </div>`;
      list.appendChild(card);
    });
    els.rowsEditor.appendChild(list);
  }

  function metricDeltaKind(value) {
    const text = String(value ?? "").trim();
    if (/^-/.test(text)) return "negative";
    if (/^\+/.test(text) && !/^\+?0(?:\.0+)?$/.test(text.replace(/[^+\-0-9.]/g, ""))) return "positive";
    const num = Number(text.replace(/[^\-0-9.]/g, ""));
    if (Number.isFinite(num) && num > 0) return "positive";
    if (Number.isFinite(num) && num < 0) return "negative";
    return "neutral";
  }

  function uniqueSorted(values) {
    return [...new Set(values.map((item) => String(item ?? "").trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, "zh-CN"));
  }

  function renderMetricSelect(label, className, value, options) {
    return `<label class="metric-filter-label"><span>${escapeHtml(label)}</span><select class="${className}"><option value="all">全部</option>${options.map((item) => `<option value="${escapeAttr(item)}" ${value === item ? "selected" : ""}>${escapeHtml(item)}</option>`).join("")}</select></label>`;
  }

  function metricRecordDate(row) {
    const value = row.created_at || row.updated_at || "";
    if (!value) return "未记录时间";
    return String(value).replace("T", " ").replace(/\.\d+.*$/, "");
  }

  function metricDisplayValue(value) {
    const text = String(value ?? "").trim();
    return text || "—";
  }

  function renderMetricHistory(table) {
    const rows = (table.rows || []).map((row, index) => ({ ...row, __index: index }));
    if (!rows.length) {
      els.rowsEditor.innerHTML = `<div class="empty-state"><strong>当前暂无数值变化记录。</strong><span>当 worker 识别到好感、信任、戒备、伤势、疲惫等数值变化后，会在这里按时间线显示。</span></div>`;
      return;
    }
    const characters = uniqueSorted(rows.map((row) => row.character_name));
    const metrics = uniqueSorted(rows.map((row) => row.metric_label));
    if (state.metricCharacterFilter !== "all" && !characters.includes(state.metricCharacterFilter)) state.metricCharacterFilter = "all";
    if (state.metricLabelFilter !== "all" && !metrics.includes(state.metricLabelFilter)) state.metricLabelFilter = "all";
    let filtered = rows.filter((row) => (state.metricCharacterFilter === "all" || row.character_name === state.metricCharacterFilter) && (state.metricLabelFilter === "all" || row.metric_label === state.metricLabelFilter));
    filtered.sort((a, b) => state.metricSort === "oldest" ? a.__index - b.__index : b.__index - a.__index);
    const latestByCharacter = new Map();
    rows.forEach((row) => {
      const name = row.character_name || "未命名角色";
      const current = latestByCharacter.get(name) || { count: 0, deltas: [] };
      current.count += 1;
      if (row.metric_label) current.deltas.push(`${row.metric_label} ${row.delta_display || ""}`.trim());
      latestByCharacter.set(name, current);
    });
    const summary = [...latestByCharacter.entries()].slice(0, 4).map(([name, data]) => `<span class="metric-summary-chip"><strong>${escapeHtml(name)}</strong><small>${data.count} 条 · ${escapeHtml(data.deltas.slice(-2).join(" / ") || "暂无变化值")}</small></span>`).join("");
    const cards = filtered.map((row) => {
      const delta = row.delta_display || "±0";
      const kind = metricDeltaKind(delta);
      const character = row.character_name || "未命名角色";
      const metric = row.metric_label || "未命名数值";
      const oldValue = metricDisplayValue(row.old_value);
      const newValue = metricDisplayValue(row.new_value);
      const rawValue = metricDisplayValue(row.raw_value) !== "—" ? metricDisplayValue(row.raw_value) : `${newValue} (${delta})`;
      const turn = row.turn_id || row.record_id || "未记录来源";
      return `
        <article class="metric-event-card ${kind}">
          <div class="metric-event-main">
            <div class="metric-event-title">
              <strong>${escapeHtml(character)}</strong>
              <span>${escapeHtml(metric)}</span>
            </div>
            <div class="metric-event-values">
              <span>${escapeHtml(oldValue)}</span>
              <b>→</b>
              <span>${escapeHtml(newValue)}</span>
              <em>${escapeHtml(rawValue)}</em>
            </div>
            <div class="metric-event-meta">
              <span>来源：${escapeHtml(turn)}</span>
              <span>${escapeHtml(metricRecordDate(row))}</span>
            </div>
          </div>
          <span class="metric-delta-badge">${escapeHtml(delta)}</span>
          <div class="metric-event-actions">
            <button class="ghost-btn small" type="button" data-edit-row="${row.__index}">详情</button>
            <button class="delete-btn" type="button" data-delete-row="${row.__index}">删除</button>
          </div>
        </article>`;
    }).join("");
    els.rowsEditor.innerHTML = `
      <section class="metric-history-view">
        <div class="metric-history-toolbar">
          <div>
            <strong>数值变化时间线</strong>
            <p>把系统记录从普通表格改成事件流，按角色、数值项和时间筛选。</p>
          </div>
          <div class="metric-filter-grid">
            ${renderMetricSelect("角色", "metric-character-filter", state.metricCharacterFilter, characters)}
            ${renderMetricSelect("数值项", "metric-label-filter", state.metricLabelFilter, metrics)}
            <label class="metric-filter-label"><span>排序</span><select class="metric-sort-filter"><option value="newest" ${state.metricSort === "newest" ? "selected" : ""}>最新优先</option><option value="oldest" ${state.metricSort === "oldest" ? "selected" : ""}>最早优先</option></select></label>
          </div>
        </div>
        ${summary ? `<div class="metric-summary-row">${summary}</div>` : ""}
        <div class="metric-event-list">${cards || `<div class="empty-state"><strong>当前筛选无记录。</strong><span>请调整角色或数值项筛选。</span></div>`}</div>
      </section>`;
    els.rowsEditor.querySelector(".metric-character-filter")?.addEventListener("change", (event) => {
      state.metricCharacterFilter = event.target.value;
      localStorage.setItem("state_journal:metricCharacterFilter", state.metricCharacterFilter);
      renderRows(table);
    });
    els.rowsEditor.querySelector(".metric-label-filter")?.addEventListener("change", (event) => {
      state.metricLabelFilter = event.target.value;
      localStorage.setItem("state_journal:metricLabelFilter", state.metricLabelFilter);
      renderRows(table);
    });
    els.rowsEditor.querySelector(".metric-sort-filter")?.addEventListener("change", (event) => {
      state.metricSort = event.target.value;
      localStorage.setItem("state_journal:metricSort", state.metricSort);
      renderRows(table);
    });
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
    if (table.schema?.id === "metric_history") {
      renderMetricHistory(table);
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
    const dataPanel = els.rowsEditor?.closest(".data-panel");
    if (dataPanel) dataPanel.dataset.tableKind = table?.schema?.id || "";
    if (!table) { els.currentTitle.textContent = "未选择表"; els.currentDesc.textContent = ""; els.rowsEditor.innerHTML = `<div class="empty-state"><strong>暂无表格。</strong><span>点击左侧“＋”新建表，或导入心笺 JSON。</span></div>`; return; }
    els.currentTitle.textContent = table.schema.name || table.schema.id;
    els.currentDesc.textContent = table.schema.description || "";
    bindSchema(table); renderFields(table); renderRows(table);
  }

  const WORKSPACE_DEFAULT_TAB = {
    journal: null,
    roleState: "roleState",
    turnNote: "turnNote",
    beauty: "template",
    settings: "model",
  };

  const TAB_WORKSPACE = {
    schema: "journal",
    rules: "journal",
    roleState: "roleState",
    log: "settings",
    turnNote: "turnNote",
    generate: "settings",
    template: "beauty",
    theme: "beauty",
    model: "settings",
    link: "settings",
  };

  const TAB_TITLES = {
    schema: "字段设置",
    rules: "规则设置",
    roleState: "角色配置",
    log: "调试与日志",
    turnNote: "幕笺显示",
    generate: "生成规则",
    template: "幕笺模板",
    theme: "外观模板",
    model: "模型设置",
    link: "聊天联动",
  };

  function setWorkspaceNav(workspace) {
    document.querySelectorAll(".workspace-nav-btn").forEach((item) => {
      item.classList.toggle("active", item.dataset.workspace === workspace);
    });
  }

  function switchWorkspace(workspace = "journal", tab = null) {
    const database = document.getElementById("databaseWorkspace");
    const showConfig = workspace !== "journal" || !!tab;
    setWorkspaceNav(workspace);
    if (database) database.classList.toggle("active", !showConfig);
    if (els.configDrawer) {
      els.configDrawer.classList.toggle("active", showConfig);
      els.configDrawer.dataset.activeWorkspace = workspace;
      els.configDrawer.setAttribute("aria-hidden", showConfig ? "false" : "true");
    }
    if (els.drawerMask) els.drawerMask.hidden = true;
    if (showConfig) {
      switchTab(tab || WORKSPACE_DEFAULT_TAB[workspace] || "schema");
    }
  }

  function openConfigDrawer(tab = "schema") {
    const workspace = TAB_WORKSPACE[tab] || "journal";
    switchWorkspace(workspace, tab);
    if (els.drawerTitle) els.drawerTitle.textContent = TAB_TITLES[tab] || "心笺设置";
    if (tab === "link") refreshHookStatus();
    if (tab === "log") loadLog().catch(() => {});
  }

  function closeConfigDrawer() {
    switchWorkspace("journal");
  }

  function switchTab(tab) {
    const workspace = TAB_WORKSPACE[tab] || "journal";
    if (els.configDrawer) els.configDrawer.dataset.activeWorkspace = workspace;
    if (els.drawerTitle) els.drawerTitle.textContent = TAB_TITLES[tab] || "心笺设置";
    document.querySelectorAll(".tab-btn").forEach((item) => item.classList.toggle("active", item.dataset.tab === tab));
    document.querySelectorAll(".tab-page").forEach((item) => item.classList.toggle("active", item.dataset.page === tab));
    setWorkspaceNav(workspace);
    if (tab === "roleState") loadRoleStateConfig().catch((error) => pageToast("角色配置载入失败", error.message, "error"));
  }

  function roleStateStageKey(index) {
    const letters = "abcdefghijklmnopqrstuvwxyz";
    const i = Math.max(1, Number(index || 1));
    return `stage_${letters[(i - 1) % letters.length]}${i > letters.length ? Math.ceil(i / letters.length) : ""}`;
  }

  function roleStateStageName(index) {
    const key = roleStateStageKey(index).replace(/^stage_/, "").toUpperCase();
    return `${key}阶段`;
  }

  function normalizeRoleStateConfig(config = {}) {
    const roles = Array.isArray(config.roles) ? config.roles : [];
    const roleSourceMode = normalizeRoleSourceMode(config.role_source_mode || config.roleSourceMode);
    return { version: 1, enabled: config.enabled !== false, role_source_mode: roleSourceMode, role_source_summary: config.role_source_summary || {}, roles: roles.map((role, index) => ({
      role_id: safeTemplateId(role.role_id || role.id || `role_${index + 1}`),
      role_name: String(role.role_name || role.name || `角色${index + 1}`).trim(),
      aliases: Array.isArray(role.aliases) ? role.aliases : [],
      enabled: role.enabled !== false,
      mode: normalizeRoleStateMode(role.mode || role.stateJournalMode, role),
      stateJournalMode: normalizeRoleStateMode(role.mode || role.stateJournalMode, role),
      use_default_variables: !!role.use_default_variables,
      source: String(role.source || role.role_source || "").trim(),
      initial_stage: safeTemplateId(role.initial_stage || "stage_a"),
      variables: Array.isArray(role.variables) ? role.variables.map((variable, varIndex) => ({
        var_key: safeTemplateId(variable.var_key || variable.key || `var_${varIndex + 1}`),
        var_name: String(variable.var_name || variable.label || `变量${varIndex + 1}`).trim(),
        enabled: variable.enabled !== false,
        default_value: Number(variable.default_value ?? 0) || 0,
        min_value: Number(variable.min_value ?? 0) || 0,
        max_value: Number(variable.max_value ?? 100) || 100,
        delta_min: Number(variable.delta_min ?? -2) || -2,
        delta_max: Number(variable.delta_max ?? 2) || 2,
        display: variable.display !== false,
        stage_relevant: variable.stage_relevant !== false,
        instruction: String(variable.instruction || ""),
      })) : [],
      stages: Array.isArray(role.stages) ? role.stages.map((stage, stageIndex) => ({
        stage_key: safeTemplateId(stage.stage_key || stage.key || roleStateStageKey(stageIndex + 1)),
        stage_name: String(stage.stage_name || stage.name || roleStateStageName(stageIndex + 1)).trim(),
        enabled: stage.enabled !== false,
        priority: Number(stage.priority ?? (stageIndex + 1) * 10) || (stageIndex + 1) * 10,
        condition_mode: stage.condition_mode === "any" ? "any" : "all",
        conditions: Array.isArray(stage.conditions) ? stage.conditions : [],
        allow_regression: !!stage.allow_regression,
        confirm_turns: Math.max(1, Number(stage.confirm_turns || 1) || 1),
        cooldown_turns: Math.max(0, Number(stage.cooldown_turns || 0) || 0),
      })) : [],
      snapshotFields: Array.isArray(role.snapshotFields) ? role.snapshotFields.map((field, fieldIndex) => ({
        key: safeTemplateId(field.key || field.field_key || `snapshot_${fieldIndex + 1}`),
        label: String(field.label || field.name || `快照字段${fieldIndex + 1}`).trim(),
        enabled: field.enabled !== false,
        display: field.display !== false,
        instruction: String(field.instruction || field.note || "根据本轮上下文生成该状态快照字段。"),
      })) : [],
      settings: role.settings || { allow_regression: false, confirm_turns: 1, cooldown_turns: 1 },
    })) };
  }

  function currentRoleState() {
    return (state.roleStateConfig.roles || []).find((role) => role.role_id === state.currentRoleStateId) || state.roleStateConfig.roles?.[0] || null;
  }

  function activeStageForRole(role) {
    if (!role) return null;
    const names = new Set([String(role.role_id || ""), String(role.role_name || ""), ...(Array.isArray(role.aliases) ? role.aliases.map(String) : [])].map((item) => item.trim()).filter(Boolean));
    return (state.activeStageRows || []).find((item) => names.has(String(item.role_id || "").trim()) || names.has(String(item.role_name || "").trim())) || null;
  }

  function roleCurrentStageName(role) {
    const active = activeStageForRole(role);
    if (active?.stage_name) return active.stage_name;
    const key = active?.stage_key || role?.initial_stage || "stage_a";
    const stage = (role?.stages || []).find((item) => item.stage_key === key);
    return stage?.stage_name || key || "未进入阶段";
  }

  function roleCurrentStageKey(role) {
    const active = activeStageForRole(role);
    return active?.stage_key || role?.initial_stage || "stage_a";
  }


  function stageActivationTag(role, stage) {
    const roleId = safeTemplateId(role?.role_id || "");
    const stageKey = safeTemplateId(stage?.stage_key || "");
    return stage?.activation_tag || (roleId && stageKey ? `state_journal.stage.${roleId}.${stageKey}` : "");
  }

  async function createWorldbookEntryForStage(stageIndex) {
    const role = currentRoleState();
    const stage = role?.stages?.[Number(stageIndex)];
    if (!role || !stage) return;
    const tag = stageActivationTag(role, stage);
    const ok = await confirmAction({
      title: "创建世界书阶段条目",
      body: `<p>将为「${escapeHtml(role.role_name || role.role_id)} · ${escapeHtml(stage.stage_name || stage.stage_key)}」创建一个 external_tag 世界书条目。</p><p><strong>机器标签：</strong><code>${escapeHtml(tag)}</code></p><p>世界书只负责阶段表现，不负责计算变量与条件。</p>`,
      confirmText: "创建条目",
    });
    if (!ok) return;
    const payload = await requestJson("./api/stage-tags/create-worldbook-entry", {
      method: "POST",
      body: JSON.stringify({ role_id: role.role_id, stage_key: stage.stage_key }),
    });
    if (payload.duplicate) {
      pageToast("世界书条目已存在", payload.message || "该阶段已绑定世界书条目，可前往世界书管理页查看。", "warn");
    } else {
      pageToast("已创建世界书条目", payload.message || "阶段表现草稿已写入世界书。", "ok");
    }
  }


  function renderRoleStateWorkspace() {
    const list = document.getElementById("roleStateRoleList");
    const detail = document.getElementById("roleStateDetail");
    if (!list || !detail) return;
    const roles = state.roleStateConfig.roles || [];
    if (!state.currentRoleStateId && roles[0]) state.currentRoleStateId = roles[0].role_id;
    const sourceInfo = roleSourceSummary(state.roleStateConfig);
    const sourceHintHtml = `<div class="role-state-source-hint"><span class="micro-badge">角色来源</span><strong>${escapeHtml(sourceInfo.label)}</strong>${sourceInfo.detected ? `<span>${escapeHtml(sourceInfo.detected)}</span>` : ""}<small>${escapeHtml(sourceInfo.message)}</small></div>`;
    list.innerHTML = sourceHintHtml + (roles.length ? roles.map((role) => {
      const stageName = roleCurrentStageName(role);
      const stageKey = roleCurrentStageKey(role);
      const stageShort = String(stageName || stageKey || "未进入阶段").replace(/^([A-Z])阶段$/i, "$1阶段");
      const mode = normalizeRoleStateMode(role.mode || role.stateJournalMode, role);
      return `
      <button type="button" class="role-state-role-card role-state-role-card-v115 ${role.role_id === state.currentRoleStateId ? "active" : ""}" data-role-id="${escapeAttr(role.role_id)}" title="${escapeAttr(roleStateModeLabel(role))}">
        <div class="role-state-card-head"><strong>${escapeHtml(role.role_name || role.role_id)}</strong><span class="role-stage-pill ${mode === "full" ? "" : "muted"}">${mode === "full" ? escapeHtml(stageShort) : escapeHtml(roleStateModeShortLabel(role))}</span></div>
        <div class="role-state-chip-row">
          <span class="role-state-chip">变量 ${role.variables?.length || 0}</span>
          <span class="role-state-chip">阶段 ${role.stages?.length || 0}</span>
          <span class="role-state-chip">快照 ${role.snapshotFields?.length || 0}</span>
        </div>
        <div class="role-state-chip-row muted-row">
          <span class="role-state-mode-badge ${mode === "disabled" ? "is-off" : "is-on"}">${escapeHtml(roleStateModeShortLabel(role))}</span>
        </div>
      </button>`;
    }).join("") : `<div class="role-state-role-card active"><strong>尚未读取角色配置</strong><div class="role-state-chip-row"><span class="role-state-chip">变量 0</span><span class="role-state-chip">阶段 0</span><span class="role-state-chip">快照 0</span></div><small>可从当前角色卡读取变量与阶段配置。</small></div>`);
    const role = currentRoleState();
    document.querySelectorAll("[data-role-state-tab]").forEach((btn) => btn.classList.toggle("active", btn.dataset.roleStateTab === state.roleStateTab));
    if (!role) {
      detail.innerHTML = `<strong>尚未选择角色</strong><p>可从当前角色卡读取变量与阶段配置。</p>`;
      return;
    }
    const roleMode = normalizeRoleStateMode(role.mode || role.stateJournalMode, role);
    const roleStats = {
      variables: role.variables?.length || 0,
      stages: role.stages?.length || 0,
      snapshots: role.snapshotFields?.length || 0,
    };
    const currentStageName = roleCurrentStageName(role);
    const currentStageKey = roleCurrentStageKey(role);
    const roleModeMeta = ROLE_STATE_MODES[roleMode] || ROLE_STATE_MODES.default;
    const overviewPanel = `<div class="role-state-overview-card compact-overview-card">
      <div class="role-state-overview-main">
        <div class="role-state-overview-title">
          <span class="micro-badge">当前角色</span>
          <strong>${escapeHtml(role.role_name || role.role_id || "未命名角色")}</strong>
        </div>
        <div class="role-state-mode-panel">
          <strong>使用方式</strong>
          <select data-role-mode-select>
            <option value="default" ${roleMode === "default" ? "selected" : ""}>默认幕笺模板</option>
            <option value="snapshot_only" ${roleMode === "snapshot_only" ? "selected" : ""}>仅专属幕笺</option>
            <option value="full" ${roleMode === "full" ? "selected" : ""}>完整心笺：专属幕笺 + 变量阶段</option>
            <option value="disabled" ${roleMode === "disabled" ? "selected" : ""}>不启用该角色</option>
          </select>
        </div>
        <p>${escapeHtml(roleModeMeta.desc || ROLE_STATE_MODES.default.desc)}</p>
      </div>
    </div>`;
    const wrapRoleStateEditor = (actionsHtml, tableHtml) => `${overviewPanel}<div class="role-state-editor-card"><div class="role-state-editor-head"><div><strong>${state.roleStateTab === "stages" ? "阶段规则" : state.roleStateTab === "snapshot" ? "状态快照字段" : "变量表"}</strong><small>${state.roleStateTab === "stages" ? "主表只展示摘要，条件编辑收在配置弹窗。" : state.roleStateTab === "snapshot" ? "只用于心笺 worker 与幕笺展示，不参与阶段判断。" : "记录可累计变量、变化范围与阶段用途。"}</small></div>${actionsHtml}</div>${tableHtml}</div>`;
    if (state.roleStateTab === "snapshot") {
      detail.innerHTML = wrapRoleStateEditor(`<button type="button" class="ghost-btn" data-add-snapshot-field>＋ 新增快照字段</button>`, `<div class="role-state-table-wrap"><table class="role-state-table role-state-snapshot-table"><thead><tr><th>启用</th><th>字段名</th><th>显示</th><th>生成说明</th><th>操作</th></tr></thead><tbody>
        ${(role.snapshotFields || []).map((field, index) => `<tr data-snapshot-index="${index}"><td><input type="checkbox" data-snapshot-field="enabled" ${field.enabled !== false ? "checked" : ""}></td><td><input data-snapshot-field="label" value="${escapeAttr(field.label)}"><details class="role-state-advanced"><summary>高级</summary><label>Key<input data-snapshot-field="key" value="${escapeAttr(field.key)}"></label></details></td><td><input type="checkbox" data-snapshot-field="display" ${field.display !== false ? "checked" : ""}></td><td><input data-snapshot-field="instruction" value="${escapeAttr(field.instruction || "")}"></td><td><button type="button" class="ghost-btn" data-delete-snapshot-field>删除</button></td></tr>`).join("") || `<tr><td colspan="5">暂无状态快照字段。未配置时会回落到当前全局幕笺模板。</td></tr>`}
        </tbody></table></div>`);
    } else if (state.roleStateTab === "stages") {
      detail.innerHTML = wrapRoleStateEditor(`<button type="button" class="ghost-btn" data-add-stage>＋ 新增阶段</button>`, `<div class="role-state-table-wrap"><table class="role-state-table role-state-stage-table stage-table-polish"><thead><tr><th>当前</th><th>启用</th><th>阶段</th><th>条件摘要</th><th>世界书</th><th>操作</th></tr></thead><tbody>
        ${(role.stages || []).map((stage, index) => {
          const isCurrent = stage.stage_key === roleCurrentStageKey(role);
          const tagState = roleStateStageTagState(role, stage, isCurrent);
          return `<tr data-stage-index="${index}" class="${isCurrent ? "current-stage-row" : ""}">
            <td><span class="current-stage-dot" title="${isCurrent ? "当前阶段" : ""}">${isCurrent ? "✓" : ""}</span></td>
            <td><input type="checkbox" data-stage-field="enabled" ${stage.enabled !== false ? "checked" : ""}></td>
            <td>
              <div class="stage-name-cell">
                <input data-stage-field="stage_name" value="${escapeAttr(stage.stage_name)}">
                <span class="stage-priority-pill">优先级 ${escapeHtml(stage.priority ?? 0)}</span>
              </div>
            </td>
            <td><div class="stage-condition-chip-row" title="${escapeAttr(roleStateConditionText(role, stage))}">${roleStateConditionChips(role, stage)}</div></td>
            <td><button type="button" class="stage-worldbook-pill ${tagState.cls}" data-create-stage-worldbook>${escapeHtml(tagState.label)}</button></td>
            <td>
              <div class="stage-row-actions">
                <button type="button" class="ghost-btn tiny" data-config-stage>配置</button>
                <details class="role-state-row-more">
                  <summary>⋯</summary>
                  <div class="role-state-row-menu">
                    <button type="button" data-delete-stage>删除阶段</button>
                    <code title="${escapeAttr(stageActivationTag(role, stage))}">${escapeHtml(stageActivationTag(role, stage))}</code>
                  </div>
                </details>
              </div>
            </td>
          </tr>`;
        }).join("") || `<tr><td colspan="6">暂无阶段。建议新增 A阶段。</td></tr>`}
        </tbody></table></div>`);
    } else {
      detail.innerHTML = wrapRoleStateEditor(`<button type="button" class="ghost-btn" data-add-variable>＋ 新增变量</button>`, `<div class="role-state-table-wrap"><table class="role-state-table role-state-variable-table"><thead><tr><th>启用</th><th>变量名</th><th>初始值</th><th>范围</th><th>每轮变化</th><th>显示</th><th>阶段</th><th>操作</th></tr></thead><tbody>
        ${(role.variables || []).map((variable, index) => `<tr data-variable-index="${index}"><td><input type="checkbox" data-var-field="enabled" ${variable.enabled !== false ? "checked" : ""}></td><td><input data-var-field="var_name" value="${escapeAttr(variable.var_name)}" placeholder="变量名"><details class="role-state-advanced"><summary>高级</summary><label>Key<input data-var-field="var_key" value="${escapeAttr(variable.var_key)}" placeholder="key"></label></details></td><td><input type="number" data-var-field="default_value" value="${escapeAttr(variable.default_value)}"></td><td><div class="role-state-range"><input class="mini" type="number" data-var-field="min_value" value="${escapeAttr(variable.min_value)}"><span>~</span><input class="mini" type="number" data-var-field="max_value" value="${escapeAttr(variable.max_value)}"></div></td><td><div class="role-state-range"><input class="mini" type="number" data-var-field="delta_min" value="${escapeAttr(variable.delta_min)}"><span>~</span><input class="mini" type="number" data-var-field="delta_max" value="${escapeAttr(variable.delta_max)}"></div></td><td><input type="checkbox" data-var-field="display" ${variable.display !== false ? "checked" : ""}></td><td><input type="checkbox" data-var-field="stage_relevant" ${variable.stage_relevant !== false ? "checked" : ""}></td><td><button type="button" class="ghost-btn" data-delete-variable>删除</button></td></tr>`).join("") || `<tr><td colspan="8">暂无变量。手动新增默认使用 var_1 / var_2，不自动拼音。</td></tr>`}
        </tbody></table></div>`);
    }
  }


  function renderRoleStateStageDialog(stageIndex) {
    const role = currentRoleState();
    const stage = role?.stages?.[Number(stageIndex)];
    if (!role || !stage) return;
    let modal = document.getElementById("roleStateStageDialog");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "roleStateStageDialog";
      modal.className = "role-state-modal";
      document.body.appendChild(modal);
    }
    const variables = role.variables || [];
    const conditionRows = (stage.conditions || []).map((condition, index) => `
      <div class="role-state-condition-line" data-condition-index="${index}">
        <select data-stage-condition-field="var">${variables.map((v) => `<option value="${escapeAttr(v.var_key)}" ${String(condition.var || condition.field || "") === String(v.var_key) ? "selected" : ""}>${escapeHtml(v.var_name || v.var_key)}</option>`).join("")}</select>
        <select data-stage-condition-field="op">
          <option value=">=" ${condition.op === ">=" ? "selected" : ""}>≥</option>
          <option value="<=" ${condition.op === "<=" ? "selected" : ""}>≤</option>
          <option value=">" ${condition.op === ">" ? "selected" : ""}>＞</option>
          <option value="<" ${condition.op === "<" ? "selected" : ""}>＜</option>
          <option value="=" ${condition.op === "=" ? "selected" : ""}>＝</option>
          <option value="!=" ${condition.op === "!=" ? "selected" : ""}>≠</option>
        </select>
        <input type="number" data-stage-condition-field="value" value="${escapeAttr(condition.value ?? 0)}">
        <button type="button" class="tiny-btn" data-delete-stage-condition>×</button>
      </div>`).join("");
    modal.innerHTML = `
      <div class="role-state-modal-mask" data-close-stage-dialog></div>
      <section class="role-state-modal-card" role="dialog" aria-modal="true">
        <header>
          <div><strong>${escapeHtml(role.role_name || role.role_id)} · 阶段配置</strong><small>主表只显示中文摘要，机器 Key 收在高级信息里。</small></div>
          <button type="button" class="ghost-btn" data-close-stage-dialog>关闭</button>
        </header>
        <div class="role-state-stage-form" data-stage-index="${Number(stageIndex)}">
          <label>阶段名<input data-stage-basic="stage_name" value="${escapeAttr(stage.stage_name || "")}"></label>
          <label>优先级<input type="number" data-stage-basic="priority" value="${escapeAttr(stage.priority ?? 10)}"></label>
          <label>条件关系<select data-stage-basic="condition_mode"><option value="all" ${stage.condition_mode !== "any" ? "selected" : ""}>全部满足</option><option value="any" ${stage.condition_mode === "any" ? "selected" : ""}>任一满足</option></select></label>
          <div class="role-state-condition-editor">
            <div class="stage-condition-summary">${escapeHtml(roleStateConditionText(role, stage))}</div>
            <div class="role-state-condition-list">${conditionRows || `<div class="role-state-empty-line">暂无条件。未设置条件时不会自动命中该阶段。</div>`}</div>
            <button type="button" class="ghost-btn" data-add-stage-condition>＋ 添加条件</button>
          </div>
          <details class="role-state-advanced"><summary>高级 / 调试信息</summary><label>阶段 Key<input data-stage-basic="stage_key" value="${escapeAttr(stage.stage_key || "")}"></label><code>${escapeHtml(`state_journal.stage.${role.role_id}.${stage.stage_key}`)}</code></details>
        </div>
      </section>`;
    const close = () => modal.remove();
    modal.querySelectorAll("[data-close-stage-dialog]").forEach((btn) => btn.addEventListener("click", close));
    const form = modal.querySelector("[data-stage-index]");
    const commitBasic = (input) => {
      const field = input.dataset.stageBasic;
      if (!field) return;
      if (field === "priority") stage.priority = Number(input.value || 0);
      else if (field === "stage_key") stage.stage_key = safeTemplateId(input.value || stage.stage_key);
      else if (field === "condition_mode") stage.condition_mode = input.value === "any" ? "any" : "all";
      else stage[field] = input.value;
      renderRoleStateWorkspace();
      renderRoleStateStageDialog(stageIndex);
    };
    form?.querySelectorAll("[data-stage-basic]").forEach((input) => input.addEventListener("change", () => commitBasic(input)));
    form?.addEventListener("change", (event) => {
      const input = event.target.closest("[data-stage-condition-field]");
      if (!input) return;
      const row = input.closest("[data-condition-index]");
      const condition = stage.conditions?.[Number(row?.dataset.conditionIndex ?? -1)];
      if (!condition) return;
      const field = input.dataset.stageConditionField;
      if (field === "value") condition.value = Number(input.value || 0);
      else condition[field] = input.value;
      renderRoleStateWorkspace();
      renderRoleStateStageDialog(stageIndex);
    });
    form?.addEventListener("click", (event) => {
      if (event.target.closest("[data-add-stage-condition]")) {
        stage.conditions = stage.conditions || [];
        stage.conditions.push({ var: variables[0]?.var_key || "var_1", op: ">=", value: 0 });
        renderRoleStateWorkspace();
        renderRoleStateStageDialog(stageIndex);
        return;
      }
      if (event.target.closest("[data-delete-stage-condition]")) {
        const row = event.target.closest("[data-condition-index]");
        const index = Number(row?.dataset.conditionIndex ?? -1);
        if (index >= 0) stage.conditions.splice(index, 1);
        renderRoleStateWorkspace();
        renderRoleStateStageDialog(stageIndex);
      }
    });
  }

  async function loadRoleStateConfig() {
    const payload = await requestJson("./api/role-state/config");
    state.roleStateConfig = normalizeRoleStateConfig(payload.config || {});
    state.activeStageRows = Array.isArray(payload.stages) ? payload.stages : [];
    renderRoleStateWorkspace();
  }

  async function saveRoleStateConfig() {
    const payload = await requestJson("./api/role-state/config", { method: "POST", body: JSON.stringify({ config: state.roleStateConfig }) });
    state.roleStateConfig = normalizeRoleStateConfig(payload.config || {});
    state.activeStageRows = Array.isArray(payload.stages) ? payload.stages : state.activeStageRows;
    renderRoleStateWorkspace();
    pageToast("心笺配置已保存", "变量与阶段配置已写入运行配置。", "ok");
  }

  async function readRoleStateFromCard() {
    const payload = await requestJson("./api/role-state/from-card", { method: "POST", body: JSON.stringify({}) });
    state.roleStateConfig = normalizeRoleStateConfig(payload.config || {});
    state.activeStageRows = Array.isArray(payload.stages) ? payload.stages : [];
    state.currentRoleStateId = state.roleStateConfig.roles?.[0]?.role_id || "";
    renderRoleStateWorkspace();
    pageToast("已读取角色卡配置", payload.message || "", "ok");
  }

  function roleStateTempKeyWarnings(config = {}) {
    const warnings = [];
    const roles = Array.isArray(config.roles) ? config.roles : [];
    roles.forEach((role) => {
      const roleName = role.role_name || role.role_id || "未命名角色";
      const tempVars = (role.variables || []).filter((item) => /^var_\d+$/i.test(String(item.var_key || "")));
      const tempSnapshots = (role.snapshotFields || []).filter((item) => /^snapshot_\d+$/i.test(String(item.key || "")));
      if (tempVars.length) warnings.push(`${roleName}：临时变量 ${tempVars.map((item) => item.var_name || item.var_key).join("、")}`);
      if (tempSnapshots.length) warnings.push(`${roleName}：临时快照字段 ${tempSnapshots.map((item) => item.label || item.key).join("、")}`);
    });
    return warnings;
  }

  function buildSyncRoleStateConfirmBody() {
    const config = normalizeRoleStateConfig(state.roleStateConfig || {});
    const roles = Array.isArray(config.roles) ? config.roles : [];
    const sourceInfo = roleSourceSummary(config);
    const roleRows = roles.length ? roles.map((role) => {
      const roleName = role.role_name || role.role_id || "未命名角色";
      const mode = roleStateModeShortLabel(role);
      return `<li><strong>${escapeHtml(roleName)}</strong><span>${escapeHtml(mode)} · 变量 ${role.variables?.length || 0} · 阶段 ${role.stages?.length || 0} · 快照 ${role.snapshotFields?.length || 0}</span></li>`;
    }).join("") : `<li><strong>暂无角色</strong><span>当前配置中没有可同步的心笺角色。</span></li>`;
    const warnings = roleStateTempKeyWarnings(config);
    const warningHtml = warnings.length ? `<div class="sync-card-warning"><strong>检测到可能的测试字段</strong><ul>${warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul><p>如果这些字段只是测试保存 / 放弃修改，可以先删除或改成正式 key 后再同步。</p></div>` : "";
    return `
      <p>即将把当前心笺角色配置写入角色卡 <code>stateJournal</code>。</p>
      <div class="sync-card-summary">
        <div><span>角色来源</span><strong>${escapeHtml(sourceInfo.label)}</strong>${sourceInfo.detected ? `<small>${escapeHtml(sourceInfo.detected)}</small>` : ""}</div>
        <div><span>同步角色</span><strong>${roles.length}</strong><small>只同步配置模板</small></div>
      </div>
      <div class="sync-card-role-list"><ul>${roleRows}</ul></div>
      ${warningHtml}
      <div class="sync-card-scope">
        <strong>会同步</strong>
        <p>角色来源、角色列表、变量配置、阶段规则、状态快照字段、阶段 activation_tag / 世界书标签。</p>
        <strong>不会同步</strong>
        <p>当前运行数值、幕笺历史、聊天记录、心笺数据库日志。</p>
      </div>
    `;
  }

  async function syncRoleStateToCard() {
    const ok = await confirmAction({
      title: "同步配置至角色卡",
      body: buildSyncRoleStateConfirmBody(),
      confirmText: "确认写入角色卡",
    });
    if (!ok) return;
    await requestJson("./api/role-state/sync-to-card", { method: "POST", body: JSON.stringify({ config: state.roleStateConfig }) });
    pageToast("已同步至角色卡", "只同步变量、阶段、快照与角色来源配置，不同步运行值和历史。", "ok");
  }

  async function resetDefaultTurnNote() {
    state.config = {
      ...state.config,
      turn_note_enabled: true,
      notify_in_chat: true,
      turn_note_template_id: "standard_metrics",
      turn_note_theme_id: "standard",
      turn_note_chat_display_mode: state.config.turn_note_chat_display_mode || "collapsed",
    };
    await saveConfig("turnNote");
    bindConfig();
    pageToast("已恢复默认幕笺", "已启用 Chat 幕笺，并切回标准状态模板与标准样式。", "ok");
  }

  async function initCurrentRoleState() {
    const roles = (state.roleStateConfig.roles || []).filter((role) => role.enabled !== false && normalizeRoleStateMode(role.mode || role.stateJournalMode, role) === "full");
    const ok = await confirmAction({
      title: "初始化当前状态",
      body: `<p>此操作会根据当前角色卡配置重建变量、阶段与快照状态，可能覆盖当前运行中的变量值和当前阶段，但不会删除历史记录。</p><p><strong>受影响角色：</strong>${escapeHtml(roles.map((role) => role.role_name || role.role_id).join("、") || "暂无完整心笺角色")}</p>`,
      confirmText: "确认初始化",
    });
    if (!ok) return;
    const payload = await requestJson("./api/role-state/init-current", { method: "POST", body: JSON.stringify({}) });
    state.activeStageRows = Array.isArray(payload.stages) ? payload.stages : state.activeStageRows;
    renderRoleStateWorkspace();
    pageToast("当前状态已初始化", payload.message || "", "ok");
  }

  async function debugAdvanceCurrentStage() {
    const role = currentRoleState();
    if (!role) {
      pageToast("未选择角色", "请先选择一个角色。", "warn");
      return;
    }
    const stages = (role.stages || []).filter((stage) => stage.enabled !== false).sort((a, b) => Number(a.priority || 0) - Number(b.priority || 0));
    const currentKey = roleCurrentStageKey(role);
    const idx = stages.findIndex((stage) => stage.stage_key === currentKey);
    const next = stages[Math.min(idx + 1, stages.length - 1)] || stages[0];
    const ok = await confirmAction({
      title: "调试推进阶段",
      body: `<p>这是测试功能，会强制把当前选中角色推进到下一阶段，用于测试世界书 external_tag 与幕笺显示。</p><p><strong>当前角色：</strong>${escapeHtml(role.role_name || role.role_id)}</p><p><strong>当前阶段：</strong>${escapeHtml(roleCurrentStageName(role))} · ${escapeHtml(currentKey)}</p><p><strong>目标阶段：</strong>${escapeHtml(next?.stage_name || "无")} · ${escapeHtml(next?.stage_key || "")}</p><p class="danger-text">不建议正式游玩时使用。</p>`,
      confirmText: "确认推进",
      danger: true,
    });
    if (!ok) return;
    const payload = await requestJson("./api/role-state/debug-advance-stage", { method: "POST", body: JSON.stringify({ role_id: role.role_id }) });
    state.activeStageRows = Array.isArray(payload.stages) ? payload.stages : state.activeStageRows;
    renderRoleStateWorkspace();
    pageToast("已推进调试阶段", payload.message || "", "ok");
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
      turnNote: "幕笺设置已保存",
      generate: "生成规则已保存",
      template: "幕笺模板已保存",
      theme: "幕笺美化已保存",
      all: "心笺配置已保存",
    };
    const details = {
      model: `${state.config.model || "未填写模型"} · ${state.config.api_base_url || "未填写 API URL"}`,
      link: `心笺${state.config.enabled === false ? "关闭" : "开启"}｜自动填表${state.config.auto_update ? "开启" : "关闭"}｜聊天提示${state.config.notify_in_chat ? "开启" : "关闭"}｜跟随全局UI${state.config.ui_sync_global ? "开启" : "关闭"}`,
      turnNote: `幕笺${state.config.turn_note_enabled === false ? "关闭" : "开启"}｜显示：${({ collapsed: "折叠", expanded: "展开", compact: "状态条", hidden: "不显示" }[state.config.turn_note_chat_display_mode || "collapsed"] || "折叠")}｜标题：${state.config.turn_note_title_style || "classic"}｜附笺：${state.config.turn_note_card_style || state.config.turn_note_style || "classic"}｜密度：${state.config.turn_note_density || "standard"}`,
      generate: `自动填表${state.config.auto_update ? "开启" : "关闭"}｜读取最近 ${state.config.input_turn_count || 3} 轮｜主角状态卡${state.config.turn_note_protagonist_card_enabled ? "开启" : "关闭"}`,
      template: `${activeTemplate().name || activeTemplate().id}｜字段 ${activeTemplate().fields?.length || 0} 个`,
      theme: `${activeThemePack().name || activeThemePack().id}｜${activeThemePack().description || "美化包已启用"}`,
      all: `${state.config.model || "未填写模型"} · 幕笺${state.config.turn_note_enabled === false ? "关闭" : "开启"}`,
    };
    const title = titles[kind] || titles.all;
    setStatus(`${title}。`, "ok");
    pageToast(title, details[kind] || details.all, "ok");
    window.stateJournalChatBridge?.reloadConfig?.();
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
    setManualWorkerBusy(true);
    try {
      setStatus("正在保存当前表，准备请求心笺辅助模型...");
      await saveCurrentTable();
      setStatus("正在读取最近聊天记录...");
      const history = await fetch("/api/history").then((res) => res.json()).catch(() => []);
      const timeoutSeconds = Number(els.cfgTimeout?.value || state.config?.request_timeout || 120);
      setStatus(`正在请求辅助模型，最多等待 ${timeoutSeconds} 秒...`);
      const result = await requestJson("./api/worker/update", { method: "POST", body: JSON.stringify({ manual: true, history, table_ids: [state.currentId] }) });
      setStatus("心笺已收到响应，正在刷新状态表...");
      await loadState();
      const count = result.summary?.total ?? result.result?.applied?.length ?? 0;
      const errors = result.result?.errors || [];
      const displayTitle = result.display?.title ? `｜幕笺：《${result.display.title}》` : "";
      const msg = (result.message || (count ? `心笺已应用 ${count} 条更新。` : "心笺判断本次无变化。")) + displayTitle;
      els.updateSummaryText.textContent = msg;
      if (errors.length || result.ok === false) {
        const title = workerErrorTitle(result.error_type);
        setStatus(msg, "error");
        pageToast(title, msg, "error");
      } else {
        setStatus(msg, "ok");
        pageToast(count ? "心笺已更新" : "心笺无变化", msg, "ok");
      }
    } catch (error) {
      const msg = error.message || "心笺请求异常。";
      els.updateSummaryText.textContent = msg;
      setStatus(msg, "error");
      pageToast("心笺填表失败", msg, "error");
    } finally {
      setManualWorkerBusy(false);
    }
  }

  async function loadLog() { const payload = await requestJson("./api/logs/latest"); els.logBox.textContent = JSON.stringify(payload.log || {}, null, 2); }
  async function exportDebugLog() {
    const payload = await requestJson("./api/logs/export?limit=120");
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `state-journal-debug-${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    pageToast("排查日志已导出", "已脱敏 API Key，可用于定位重 roll、编辑与幕笺恢复问题。", "ok");
  }
  function addField() { const table = currentTable(); if (!table) return; table.schema.fields.push({ key: `field_${table.schema.fields.length + 1}`, label: "新字段", type: "text", required: false, options: [], note: "" }); renderFields(table); refreshPrimaryOptions(); openConfigDrawer("schema"); }
  function addRow() { const table = currentTable(); if (!table) return; const row = {}; (table.schema.fields || []).forEach((field) => { row[field.key] = field.type === "boolean" ? false : ""; }); table.rows.push(row); renderRows(table); openRowDetail(table.rows.length - 1); }
  function newTable() { const id = `custom_table_${Date.now()}`; state.tables.push({ schema: { id, name: "新表", description: "", primary_key: "id", fields: [{ key: "id", label: "ID", type: "text", required: true, options: [], note: "主键字段" }], rules: { note: "", init: "", insert: "", update: "", delete: "", ignore: "" } }, rows: [] }); state.currentId = id; renderAll(); openConfigDrawer("schema"); }
  async function exportAll() { const payload = await requestJson("./api/export"); const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }); const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = `state-journal-export-${Date.now()}.json`; a.click(); URL.revokeObjectURL(url); pageToast("导出完成", "默认不包含 API Key，可放心分享表结构与数据。", "ok"); }
  async function importFile(file) { if (!file) return; const payload = JSON.parse(await file.text()); await requestJson("./api/import", { method: "POST", body: JSON.stringify(payload) }); await loadState(); setStatus("导入完成。", "ok"); pageToast("导入完成", "JSON 数据已写入心笺 SQLite。", "ok"); }

  document.querySelectorAll(".workspace-nav-btn").forEach((button) => button.addEventListener("click", () => {
    const workspace = button.dataset.workspace || "journal";
    const defaultTab = button.dataset.defaultTab || WORKSPACE_DEFAULT_TAB[workspace];
    if (workspace === "journal") switchWorkspace("journal"); else openConfigDrawer(defaultTab);
  }));
  document.querySelectorAll(".tab-btn").forEach((button) => button.addEventListener("click", () => openConfigDrawer(button.dataset.tab)));
  els.cardViewBtn.addEventListener("click", () => { state.viewMode = "card"; localStorage.setItem("state_journal:viewMode", state.viewMode); renderAll(); });
  els.tableViewBtn.addEventListener("click", () => { state.viewMode = "table"; localStorage.setItem("state_journal:viewMode", state.viewMode); renderAll(); });
  $("#openSchemaDrawerBtn")?.addEventListener("click", () => openConfigDrawer("schema"));
  $("#openRulesDrawerBtn")?.addEventListener("click", () => openConfigDrawer("rules"));
  $("#openModelDrawerBtn")?.addEventListener("click", () => openConfigDrawer("model"));
  $("#openLinkDrawerBtn")?.addEventListener("click", () => openConfigDrawer("link"));
  $("#openTurnNoteDrawerBtn")?.addEventListener("click", () => openConfigDrawer("turnNote"));
  $("#openTemplateDrawerBtn")?.addEventListener("click", () => openConfigDrawer("template"));
  $("#openLogDrawerBtn")?.addEventListener("click", () => { openConfigDrawer("log"); });
  $("#closeConfigDrawerBtn")?.addEventListener("click", closeConfigDrawer);
  els.drawerMask?.addEventListener("click", closeConfigDrawer);
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
  $("#saveConfigBtn")?.addEventListener("click", () => saveConfig("model").catch((error) => { setStatus(error.message, "error"); pageToast("保存模型配置失败", error.message, "error"); }));
  $("#saveLinkConfigBtn")?.addEventListener("click", () => saveConfig("link").catch((error) => { setStatus(error.message, "error"); pageToast("保存联动设置失败", error.message, "error"); }));
  $("#saveTurnNoteConfigBtn")?.addEventListener("click", () => saveConfig("turnNote").catch((error) => { setStatus(error.message, "error"); pageToast("保存幕笺设置失败", error.message, "error"); }));
  $("#saveGenerateConfigBtn")?.addEventListener("click", () => saveConfig("generate").catch((error) => { setStatus(error.message, "error"); pageToast("保存生成规则失败", error.message, "error"); }));
  function bindRuntimeToggle(input, target, kind) {
    input?.addEventListener("change", () => {
      if (target) target.checked = input.checked;
      saveConfig(kind).catch((error) => pageToast("运行状态保存失败", error.message, "error"));
    });
  }
  bindRuntimeToggle(els.dashboardEnabled, els.cfgEnabled, "link");
  bindRuntimeToggle(els.dashboardAutoUpdate, els.cfgAutoUpdate, "generate");
  bindRuntimeToggle(els.dashboardTurnNote, els.cfgTurnNoteEnabled, "turnNote");
  els.resetWorkerPromptBtn?.addEventListener("click", () => {
    if (els.cfgTurnNoteWorkerPromptEnabled) els.cfgTurnNoteWorkerPromptEnabled.checked = false;
    if (els.cfgTurnNoteWorkerStylePrompt) els.cfgTurnNoteWorkerStylePrompt.value = "";
    if (els.cfgTurnNoteWorkerProtagonistPrompt) els.cfgTurnNoteWorkerProtagonistPrompt.value = "";
    pageToast("已恢复默认附加提示词", "保存幕笺设置后生效。", "ok");
  });
  $("#saveTemplateConfigBtn")?.addEventListener("click", () => saveConfig("template").catch((error) => { setStatus(error.message, "error"); pageToast("保存模板设置失败", error.message, "error"); }));
  $("#saveThemeConfigBtn")?.addEventListener("click", () => saveConfig("theme").catch((error) => { setStatus(error.message, "error"); pageToast("保存美化设置失败", error.message, "error"); }));
  $("#refreshHookBtn").addEventListener("click", () => refreshHookStatus().catch((error) => pageToast("刷新 Hook 状态失败", error.message, "error")));
  $("#fillMainConfigBtn").addEventListener("click", () => fillFromMainConfig().catch((error) => pageToast("读取本体配置失败", error.message, "error")));
  $("#fetchModelsBtn").addEventListener("click", () => fetchModels().catch((error) => { setStatus(error.message, "error"); pageToast("拉取模型列表失败", error.message, "error"); }));
  $("#testConnectionBtn").addEventListener("click", () => testConnection().catch((error) => { setStatus(error.message, "error"); pageToast("测试连接失败", error.message, "error"); }));
  $("#applyPresetBtn").addEventListener("click", applyServicePreset);
  els.cfgTurnNoteStyle?.addEventListener("change", updateTurnNoteStyleHelp);
  els.cfgTurnNoteTitleStyle?.addEventListener("change", updateTurnNoteStyleHelp);
  els.cfgTurnNoteNoteStyle?.addEventListener("change", updateTurnNoteStyleHelp);
  els.cfgTurnNoteTemplateSelect?.addEventListener("change", () => { state.currentTemplateId = els.cfgTurnNoteTemplateSelect.value; state.expandedTemplateFieldIndex = null; if (els.templateSelect) els.templateSelect.value = state.currentTemplateId; const tmpl = activeTemplate(); if (els.cfgTurnNoteNoteStyle) els.cfgTurnNoteNoteStyle.value = tmpl.note_style || "classic"; bindTemplateEditor(); updateTurnNoteStyleHelp(); });

  els.cfgTurnNoteThemeSelect?.addEventListener("change", () => setActiveTheme(els.cfgTurnNoteThemeSelect.value));
  els.themeSelect?.addEventListener("change", () => setActiveTheme(els.themeSelect.value));
  els.themePreviewModeSelect?.addEventListener("change", () => {
    state.themePreviewMode = els.themePreviewModeSelect.value || "role";
    localStorage.setItem("state_journal:themePreviewMode", state.themePreviewMode);
    renderThemePreview();
  });
  els.exportThemeBtn?.addEventListener("click", () => {
    const pack = activeThemePack();
    const blob = new Blob([JSON.stringify(pack, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob); const a = document.createElement("a");
    a.href = url; a.download = `state-journal-beauty-${pack.id || Date.now()}.json`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
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
      const warnings = Array.isArray(pack.__warnings) ? pack.__warnings : [];
      const warningText = warnings.length ? `；兼容处理：${warnings.join(" · ")}` : "";
      await persistImportedTheme(pack);
      const detail = `${themePackSourceLabel(pack)} · schema v${pack.schema_version || THEME_PACK_SCHEMA_VERSION} · layout: ${themePackLayoutType(pack)} · class: ${pack.style?.class_name || "theme-standard"}${themePackProgressBars(pack).length ? ` · 数值条 ${themePackProgressBars(pack).length}` : ""}`;
      pageToast("美化包已导入并启用", `${pack.name || pack.id}｜${detail}${warningText}`, "ok");
      setStatus(`美化包已导入并启用：${pack.name || pack.id}｜${detail}${warningText}`, "ok");
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
    state.expandedTemplateFieldIndex = null;
    state.config = { ...state.config, turn_note_template_id: nextId };
    bindTemplateEditor();
    if (els.cfgTurnNoteTemplateSelect) els.cfgTurnNoteTemplateSelect.value = nextId;
  });
  els.templateFieldsEditor?.addEventListener("input", (event) => {
    const card = event.target.closest(".template-field-card");
    if (card) {
      const title = card.querySelector(".template-field-title strong");
      const keyText = card.querySelector(".template-field-key");
      const summary = card.querySelector(".template-field-summary");
      const key = safeTemplateId(card.querySelector("[data-tpl-key]")?.value || "");
      const label = (card.querySelector("[data-tpl-label]")?.value || key || "字段").trim();
      const instruction = (card.querySelector("[data-tpl-instruction]")?.value || "根据本轮上下文生成该字段。").replace(/\s+/g, " ").trim();
      if (title) title.textContent = label;
      if (keyText) keyText.textContent = key;
      if (summary) summary.textContent = instruction;
    }
    updateTemplatePreview();
  });
  els.templateOutput?.addEventListener("input", updateTemplatePreview);
  els.templateName?.addEventListener("input", updateTemplatePreview);
  els.templateDesc?.addEventListener("input", updateTemplatePreview);
  els.templateNoteStyle?.addEventListener("change", updateTemplatePreview);
  els.templateFieldsEditor?.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-tpl-toggle]");
    const up = event.target.closest("[data-tpl-up]");
    const down = event.target.closest("[data-tpl-down]");
    const del = event.target.closest("[data-tpl-delete]");
    if (!toggle && !up && !down && !del) return;
    const template = readTemplateEditor();
    if (toggle && !up && !down && !del) {
      const index = Number(toggle.dataset.tplToggle);
      state.expandedTemplateFieldIndex = state.expandedTemplateFieldIndex === index ? null : index;
      renderTemplateFields(template);
      updateTemplatePreview();
      return;
    }
    let index = Number((up || down || del).dataset.tplUp ?? (up || down || del).dataset.tplDown ?? (up || down || del).dataset.tplDelete);
    if (del) {
      template.fields.splice(index, 1);
      state.expandedTemplateFieldIndex = null;
    }
    if (up && index > 0) {
      [template.fields[index - 1], template.fields[index]] = [template.fields[index], template.fields[index - 1]];
      state.expandedTemplateFieldIndex = index - 1;
    }
    if (down && index < template.fields.length - 1) {
      [template.fields[index + 1], template.fields[index]] = [template.fields[index], template.fields[index + 1]];
      state.expandedTemplateFieldIndex = index + 1;
    }
    const templates = turnNoteTemplates().slice();
    const pos = templates.findIndex((item) => item.id === template.id);
    if (pos >= 0) templates[pos] = template;
    state.config = { ...state.config, turn_note_templates: templates };
    renderTemplateFields(template);
    updateTemplatePreview();
  });
  $("#collapseTemplateFieldsBtn")?.addEventListener("click", () => {
    state.expandedTemplateFieldIndex = null;
    renderTemplateFields(readTemplateEditor());
    updateTemplatePreview();
  });
  $("#addTemplateFieldBtn")?.addEventListener("click", () => {
    const template = readTemplateEditor();
    const used = new Set(template.fields.map((field) => safeTemplateId(field.key)));
    let n = template.fields.length + 1;
    while (used.has(`field_${n}`)) n += 1;
    const field = { key: `field_${n}`, label: "新字段", instruction: "根据本轮上下文生成该字段。" };
    template.fields.push(field);
    state.expandedTemplateFieldIndex = template.fields.length - 1;
    const token = `{${field.key}}`;
    if (!String(template.output_template || "").includes(token)) {
      const line = `<${field.label}(${token})>`;
      template.output_template = `${String(template.output_template || "").trimEnd()}${template.output_template ? "\n" : ""}${line}`;
      if (els.templateOutput) els.templateOutput.value = template.output_template;
    }
    const templates = turnNoteTemplates().slice();
    const pos = templates.findIndex((item) => item.id === template.id);
    if (pos >= 0) templates[pos] = template;
    state.config = { ...state.config, turn_note_templates: templates };
    renderTemplateFields(template); updateTemplatePreview();
  });
  $("#newTemplateBtn")?.addEventListener("click", () => {
    const source = readTemplateEditor();
    const copy = { ...source, id: `custom_${Date.now()}`, name: `${source.name || "模板"} 副本` };
    state.config = { ...state.config, turn_note_templates: [...turnNoteTemplates(), copy], turn_note_template_id: copy.id };
    state.currentTemplateId = copy.id; state.expandedTemplateFieldIndex = null; bindTemplateEditor(); pageToast("已复制模板", "修改后点击保存模板设置。", "ok");
  });
  $("#exportTemplateBtn")?.addEventListener("click", () => {
    const template = readTemplateEditor();
    const blob = new Blob([JSON.stringify(template, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob); const a = document.createElement("a");
    a.href = url; a.download = `state-journal-template-${template.id || Date.now()}.json`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
    pageToast("模板已导出", template.name || template.id, "ok");
  });
  els.importTemplateInput?.addEventListener("change", async (event) => {
    const file = event.target.files?.[0]; if (!file) return;
    try {
      const template = JSON.parse(await file.text());
      const id = safeTemplateId(template.id || template.name || `custom_${Date.now()}`);
      const normalized = { ...template, id, fields: Array.isArray(template.fields) ? template.fields : [] };
      state.config = { ...state.config, turn_note_templates: [...turnNoteTemplates().filter((item) => item.id !== id), normalized], turn_note_template_id: id };
      state.currentTemplateId = id; state.expandedTemplateFieldIndex = null; bindTemplateEditor(); pageToast("模板已导入", normalized.name || id, "ok");
    } catch (error) { pageToast("导入模板失败", error.message, "error"); }
    event.target.value = "";
  });
  $("#toggleApiKeyBtn").addEventListener("click", () => { const hidden = els.cfgApiKey.type === "password"; els.cfgApiKey.type = hidden ? "text" : "password"; $("#toggleApiKeyBtn").textContent = hidden ? "隐藏" : "显示"; });

  document.getElementById("roleStateReadCardBtn")?.addEventListener("click", () => readRoleStateFromCard().catch((error) => pageToast("读取角色卡失败", error.message, "error")));
  document.getElementById("roleStateSaveBtn")?.addEventListener("click", () => saveRoleStateConfig().catch((error) => pageToast("保存心笺配置失败", error.message, "error")));
  document.getElementById("roleStateSyncCardBtn")?.addEventListener("click", () => syncRoleStateToCard().catch((error) => pageToast("同步角色卡失败", error.message, "error")));
  document.getElementById("roleStateInitBtn")?.addEventListener("click", () => initCurrentRoleState().catch((error) => pageToast("初始化失败", error.message, "error")));
  document.getElementById("roleStateDebugNextStageBtn")?.addEventListener("click", () => debugAdvanceCurrentStage().catch((error) => pageToast("调试推进失败", error.message, "error")));
  document.getElementById("roleStateRoleList")?.addEventListener("click", (event) => {
    const card = event.target.closest("[data-role-id]");
    if (!card) return;
    state.currentRoleStateId = card.dataset.roleId;
    renderRoleStateWorkspace();
  });
  document.querySelectorAll("[data-role-state-tab]").forEach((btn) => btn.addEventListener("click", () => {
    state.roleStateTab = btn.dataset.roleStateTab || "variables";
    renderRoleStateWorkspace();
  }));
  document.getElementById("resetDefaultTurnNoteBtn")?.addEventListener("click", () => resetDefaultTurnNote().catch((error) => pageToast("恢复默认幕笺失败", error.message, "error")));

  document.getElementById("roleStateDetail")?.addEventListener("change", (event) => {
    const role = currentRoleState();
    const modeSelect = event.target.closest("[data-role-mode-select]");
    if (role && modeSelect) {
      setRoleStateMode(role, modeSelect.value);
      renderRoleStateWorkspace();
      return;
    }
    const conditionInput = event.target.closest("[data-stage-condition-field]");
    if (role && conditionInput) {
      const tr = conditionInput.closest("[data-stage-index]");
      const row = conditionInput.closest("[data-condition-index]");
      const stage = role.stages?.[Number(tr?.dataset.stageIndex ?? -1)];
      const condition = stage?.conditions?.[Number(row?.dataset.conditionIndex ?? -1)];
      if (!condition) return;
      const field = conditionInput.dataset.stageConditionField;
      if (field === "value") condition.value = Number(conditionInput.value || 0);
      else condition[field] = conditionInput.value;
      renderRoleStateWorkspace();
    }
  });

  document.getElementById("roleStateDetail")?.addEventListener("click", (event) => {
    const role = currentRoleState();
    if (!role) return;
    const hit = (selector) => event.target.closest(selector);
    if (hit("[data-add-variable]")) {
      event.preventDefault();
      const next = (role.variables || []).length + 1;
      role.variables = role.variables || [];
      role.variables.push({ var_key: `var_${next}`, var_name: `变量${next}`, enabled: true, default_value: 0, min_value: 0, max_value: 100, delta_min: -2, delta_max: 2, display: true, stage_relevant: true, instruction: "" });
      renderRoleStateWorkspace();
      return;
    }
    if (hit("[data-delete-variable]")) {
      event.preventDefault();
      const tr = event.target.closest("[data-variable-index]");
      const index = Number(tr?.dataset.variableIndex ?? -1);
      if (index >= 0) role.variables.splice(index, 1);
      renderRoleStateWorkspace();
      return;
    }
    if (hit("[data-add-snapshot-field]")) {
      event.preventDefault();
      const next = (role.snapshotFields || []).length + 1;
      role.snapshotFields = role.snapshotFields || [];
      role.snapshotFields.push({ key: `snapshot_${next}`, label: `快照字段${next}`, enabled: true, display: true, instruction: "根据本轮上下文生成该状态快照字段。" });
      renderRoleStateWorkspace();
      return;
    }
    if (hit("[data-delete-snapshot-field]")) {
      event.preventDefault();
      const tr = event.target.closest("[data-snapshot-index]");
      const index = Number(tr?.dataset.snapshotIndex ?? -1);
      if (index >= 0) role.snapshotFields.splice(index, 1);
      renderRoleStateWorkspace();
      return;
    }
    if (hit("[data-add-stage]")) {
      event.preventDefault();
      const next = (role.stages || []).length + 1;
      role.stages = role.stages || [];
      role.stages.push({ stage_key: roleStateStageKey(next), stage_name: roleStateStageName(next), enabled: true, priority: next * 10, condition_mode: "all", conditions: [], allow_regression: false, confirm_turns: 1, cooldown_turns: 1 });
      renderRoleStateWorkspace();
      return;
    }
    if (hit("[data-config-stage]")) {
      event.preventDefault();
      const tr = event.target.closest("[data-stage-index]");
      renderRoleStateStageDialog(Number(tr?.dataset.stageIndex ?? -1));
      return;
    }
    if (hit("[data-create-stage-worldbook]")) {
      event.preventDefault();
      const tr = event.target.closest("[data-stage-index]");
      createWorldbookEntryForStage(Number(tr?.dataset.stageIndex ?? -1));
      return;
    }
    if (hit("[data-delete-stage]")) {
      event.preventDefault();
      const tr = event.target.closest("[data-stage-index]");
      const index = Number(tr?.dataset.stageIndex ?? -1);
      if (index >= 0) role.stages.splice(index, 1);
      renderRoleStateWorkspace();
      return;
    }
  });
  document.getElementById("roleStateDetail")?.addEventListener("input", (event) => {
    const role = currentRoleState();
    if (!role) return;
    const varInput = event.target.closest("[data-var-field]");
    if (varInput) {
      const tr = varInput.closest("[data-variable-index]");
      const variable = role.variables?.[Number(tr?.dataset.variableIndex ?? -1)];
      if (!variable) return;
      const field = varInput.dataset.varField;
      if (["enabled", "display", "stage_relevant"].includes(field)) variable[field] = !!varInput.checked;
      else if (["default_value", "min_value", "max_value", "delta_min", "delta_max"].includes(field)) variable[field] = Number(varInput.value || 0);
      else if (field === "var_key") variable[field] = safeTemplateId(varInput.value || variable.var_key);
      else variable[field] = varInput.value;
    }
    const snapshotInput = event.target.closest("[data-snapshot-field]");
    if (snapshotInput) {
      const tr = snapshotInput.closest("[data-snapshot-index]");
      const fieldItem = role.snapshotFields?.[Number(tr?.dataset.snapshotIndex ?? -1)];
      if (!fieldItem) return;
      const field = snapshotInput.dataset.snapshotField;
      if (["enabled", "display"].includes(field)) fieldItem[field] = !!snapshotInput.checked;
      else if (field === "key") fieldItem[field] = safeTemplateId(snapshotInput.value || fieldItem.key);
      else fieldItem[field] = snapshotInput.value;
    }
    const conditionInput = event.target.closest("[data-stage-condition-field]");
    if (conditionInput) {
      const tr = conditionInput.closest("[data-stage-index]");
      const row = conditionInput.closest("[data-condition-index]");
      const stage = role.stages?.[Number(tr?.dataset.stageIndex ?? -1)];
      const condition = stage?.conditions?.[Number(row?.dataset.conditionIndex ?? -1)];
      if (!condition) return;
      const field = conditionInput.dataset.stageConditionField;
      if (field === "value") condition.value = Number(conditionInput.value || 0);
      else condition[field] = conditionInput.value;
    }
    const stageInput = event.target.closest("[data-stage-field]");
    if (stageInput) {
      const tr = stageInput.closest("[data-stage-index]");
      const stage = role.stages?.[Number(tr?.dataset.stageIndex ?? -1)];
      if (!stage) return;
      const field = stageInput.dataset.stageField;
      if (field === "enabled") stage.enabled = !!stageInput.checked;
      else if (field === "priority") stage.priority = Number(stageInput.value || 0);
      else if (field === "stage_key") stage.stage_key = safeTemplateId(stageInput.value || stage.stage_key);
      else if (field === "conditions_text") {
        stage.conditions = String(stageInput.value || "").split(";").map((part) => {
          const match = part.trim().match(/^([a-zA-Z0-9_\-]+)\s*(>=|<=|!=|>|<|=)\s*(-?\d+(?:\.\d+)?)$/);
          return match ? { var: match[1], op: match[2], value: Number(match[3]) } : null;
        }).filter(Boolean);
      } else stage[field] = stageInput.value;
    }
  });

  $("#manualWorkerBtn").addEventListener("click", () => manualWorkerUpdate());
  $("#loadLogBtn").addEventListener("click", () => loadLog().catch((error) => { els.logBox.textContent = error.message; }));
  $("#exportDebugLogBtn")?.addEventListener("click", () => exportDebugLog().catch((error) => pageToast("导出排查日志失败", error.message, "error")));
  $("#addFieldBtn").addEventListener("click", addField); $("#addRowBtn").addEventListener("click", addRow); $("#newTableBtn").addEventListener("click", newTable);
  $("#exportBtn").addEventListener("click", () => exportAll().catch((error) => setStatus(error.message, "error")));
  $("#importInput").addEventListener("change", (event) => importFile(event.target.files?.[0]).catch((error) => { setStatus(error.message, "error"); pageToast("导入失败", error.message, "error"); }));
  window.addEventListener("state_journal:updated", (event) => { els.updateSummaryText.textContent = event.detail?.message || "聊天页自动填表已完成。"; loadState().catch(() => {}); });

  loadState().catch((error) => { setStatus(error.message, "error"); pageToast("心笺载入失败", error.message, "error"); });
})();
