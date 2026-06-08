(() => {
  "use strict";

  const tabMeta = {
    overview: ["总览", "插件运行状态、数据摘要和快捷操作。"],
    settings: ["生成设置", "承接模型与回复设置。"],
    workbench: ["工作台", "在插件后台完成角色草稿、Prompt 预览和模型生成测试。"],
    groups: ["群聊管理", "编辑群聊资料、成员和群级自动行为。"],
    roles: ["角色管理", "维护小手机独立角色资料库。"],
    "role-generator": ["人物生成", "从背景资料生成小手机边缘角色草稿。"],
    stickers: ["表情包", "编辑 mod 内 PNG 表情包 manifest。"],
    automation: ["自动行为", "自动插话、空闲触发和频率限制。"],
    prompt: ["Prompt 配置", "管理小手机独立 prompt blocks 与输出契约。"],
    apps: ["应用管理", "管理小手机桌面的轻应用注册表。"],
    channels: ["频道生成", "动态、论坛、直播、邮箱、日记、日程的 seed 与事件。"],
    ui: ["UI 设置", "悬浮球、面板位置和主题设置。"],
    diagnostics: ["诊断", "数据隔离、生成 guard 和运行状态。"],
    data: ["数据工具", "导出、清理和备份工具。"],
  };


  const channelTokenRows = [
    ["default", "默认频道"],
    ["forum", "论坛"],
    ["feed", "动态"],
    ["live", "直播"],
    ["mail", "邮箱"],
    ["diary", "日记"],
    ["calendar", "日程"],
  ];
  const promptScopes = [
    ["group_chat", "群聊"],
    ["feed", "动态"],
    ["forum", "论坛"],
    ["live", "直播"],
    ["mail", "邮箱"],
    ["diary", "日记"],
    ["calendar", "日程"],
    ["phone", "电话"],
    ["notification", "通知"],
  ];
  const apiPresets = {
    openai: {
      base_url: "https://api.openai.com/v1",
      model: "gpt-4.1-mini",
      hint: "OpenAI 官方 OpenAI-compatible Base URL。",
    },
    gemini: {
      base_url: "https://generativelanguage.googleapis.com/v1beta/openai",
      model: "gemini-3.5-flash",
      hint: "Google Gemini 官方 OpenAI-compatible Base URL。",
    },
    claude: {
      base_url: "https://api.anthropic.com/v1",
      model: "claude-sonnet-4-6",
      hint: "Claude 官方 OpenAI-compatible Base URL。",
    },
    minimax: {
      base_url: "https://api.minimaxi.com/v1",
      model: "MiniMax-M3",
      hint: "MiniMax 国内官方 OpenAI-compatible Base URL。",
    },
    glm: {
      base_url: "https://open.bigmodel.cn/api/paas/v4",
      model: "glm-5.1",
      hint: "智谱 GLM 官方 OpenAI-compatible Base URL。",
    },
    deepseek: {
      base_url: "https://api.deepseek.com/v1",
      model: "deepseek-chat",
      hint: "DeepSeek 官方 OpenAI-compatible Base URL。",
    },
    siliconflow: {
      base_url: "https://api.siliconflow.cn/v1",
      model: "",
      hint: "SiliconFlow OpenAI-compatible Base URL。",
    },
  };

  const state = {
    summary: null,
    groups: [],
    roles: [],
    availableRoles: [],
    user: null,
    stickerPacks: [],
    stickers: [],
    manifestRows: [],
    automation: null,
    promptBlocks: [],
    promptPreview: null,
    promptScope: "group_chat",
    promptTestResult: null,
    promptTestBusy: false,
    apps: [],
    channels: [],
    diagnostics: null,
    dataOverview: null,
    generationControl: null,
    workbench: null,
    workbenchRoleDraft: null,
    workbenchPreview: null,
    workbenchResult: null,
    roleGeneratorForm: {},
    roleGeneratorDrafts: [],
    roleGeneratorSaved: [],
    roleGeneratorSelectedIndex: 0,
    roleGeneratorBusy: false,
    roleAppPools: null,
    roleAppFilter: "",
    fetchedModels: [],
    selectedGroupId: "",
    selectedRoleId: "",
    selectedPackId: "",
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function tagsToText(tags) {
    return Array.isArray(tags) ? tags.join(", ") : "";
  }

  function appAliasMap() {
    const rows = roleGeneratorAppOptions();
    const aliases = new Map([
      ["\u7fa4\u804a", "group_chat"], ["\u804a\u5929", "group_chat"],
      ["\u52a8\u6001", "feed"], ["\u670b\u53cb\u5708", "feed"],
      ["\u8bba\u575b", "forum"], ["\u5e16\u5b50", "forum"],
      ["\u76f4\u64ad", "live"],
      ["\u7535\u8bdd", "phone"],
      ["\u90ae\u7bb1", "mail"], ["\u90ae\u4ef6", "mail"],
      ["\u65e5\u8bb0", "diary"],
      ["\u65e5\u7a0b", "calendar"], ["\u65e5\u5386", "calendar"],
      ["\u901a\u77e5", "notifications"],
    ]);
    rows.forEach((app) => {
      aliases.set(String(app.app_id || "").toLowerCase(), app.app_id);
      if (app.label) aliases.set(String(app.label).trim().toLowerCase(), app.app_id);
    });
    return aliases;
  }

  function normalizeAppInput(value) {
    const raw = String(value || "").trim();
    if (!raw) return "";
    const aliases = appAliasMap();
    const key = raw.toLowerCase();
    if (aliases.has(key)) return aliases.get(key);
    return key.replace(/[^a-z0-9_-]+/g, "_").replace(/^_+|_+$/g, "");
  }

  function appScopeToTags(value) {
    const seen = new Set();
    return String(value || "")
      .split(/[,\uFF0C\u3001\s]+/)
      .map(normalizeAppInput)
      .filter((item) => {
        if (!item || seen.has(item)) return false;
        seen.add(item);
        return true;
      })
      .slice(0, 12);
  }


  function textToTags(value) {
    return String(value || "")
      .split(/[,，\s]+/)
      .map((item) => item.trim().toLowerCase().replace(/[^a-z0-9_-]+/g, "_").replace(/^_+|_+$/g, ""))
      .filter(Boolean)
      .slice(0, 12);
  }

  function roleGeneratorAppOptions() {
    const scopeAppIds = new Set(["group_chat", "feed", "forum", "live", "notifications", "phone", "mail", "diary", "calendar"]);
    const fallback = [
      { app_id: "group_chat", label: "群聊" },
      { app_id: "feed", label: "动态" },
      { app_id: "forum", label: "论坛" },
      { app_id: "live", label: "直播" },
      { app_id: "notifications", label: "通知" },
      { app_id: "phone", label: "电话" },
      { app_id: "mail", label: "邮箱" },
      { app_id: "diary", label: "日记" },
      { app_id: "calendar", label: "日程" },
    ];
    const rows = Array.isArray(state.apps) && state.apps.length ? state.apps : fallback;
    const seen = new Set();
    return rows
      .filter((app) => app && scopeAppIds.has(String(app.app_id || "")) && app.app_id !== "assist" && app.page !== "assist")
      .map((app) => ({ app_id: String(app.app_id || ""), label: String(app.label || app.app_id || "") }))
      .filter((app) => {
        if (!app.app_id || seen.has(app.app_id)) return false;
        seen.add(app.app_id);
        return true;
      });
  }

  function appLabelMap() {
    const rows = roleGeneratorAppOptions();
    return new Map(rows.map((app) => [app.app_id, app.label || app.app_id]));
  }

  function appDisplayLabel(appId) {
    const safeAppId = normalizeAppInput(appId);
    const labels = appLabelMap();
    return labels.get(safeAppId) || safeAppId || "";
  }

  function appScopeLabelText(values, emptyText) {
    const rows = Array.isArray(values) ? values : [];
    return rows.length ? rows.map(appDisplayLabel).filter(Boolean).join("、") : emptyText;
  }

  function roleAppBindingOptions(role) {
    const labels = appLabelMap();
    const seen = new Set();
    const extras = [
      ...(Array.isArray(role?.suitable_apps) ? role.suitable_apps : []),
      ...(Array.isArray(role?.blocked_apps) ? role.blocked_apps : []),
      ...Object.keys(role?.app_roles && typeof role.app_roles === "object" ? role.app_roles : {}),
    ];
    const rows = [...roleGeneratorAppOptions(), ...extras.map((appId) => {
      const safeAppId = normalizeAppInput(appId);
      return { app_id: safeAppId, label: labels.get(safeAppId) || safeAppId };
    })];
    return rows.filter((app) => {
      if (!app?.app_id || seen.has(app.app_id)) return false;
      seen.add(app.app_id);
      return true;
    });
  }

  function roleAppSelectedSet(role, field) {
    return new Set(Array.isArray(role?.[field]) ? role[field].map(normalizeAppInput).filter(Boolean) : []);
  }

  function roleAppScopeControls(role, field) {
    const selected = roleAppSelectedSet(role, field);
    const oppositeSelected = roleAppSelectedSet(role, field === "suitable_apps" ? "blocked_apps" : "suitable_apps");
    return roleAppBindingOptions(role).map((app) => `
      <label class="fmca-check fmca-chip-check fmca-role-app-check${oppositeSelected.has(app.app_id) ? " is-conflict-peer" : ""}">
        <input type="checkbox" name="${esc(field)}" value="${esc(app.app_id)}" data-role-app-scope="${esc(field)}" ${selected.has(app.app_id) ? "checked" : ""}>
        <span>${esc(app.label || app.app_id)}</span>
      </label>
    `).join("");
  }

  const fallbackRoleUsageHints = {
    group_chat: ["active_chat_member", "friend", "topic_starter"],
    feed: ["poster", "commenter", "friend", "bystander"],
    forum: ["thread_author", "floor_reply", "moderator", "bystander"],
    live: ["streamer", "viewer", "highlight_sender", "contributor"],
    mail: ["sender", "recipient", "contact", "organization", "system_notice"],
    diary: ["writer", "related_person", "memory_subject"],
    calendar: ["participant", "organizer", "location_contact", "organization"],
    phone: ["caller", "callee", "phone_contact"],
    notifications: ["source", "system_notice", "related_person"],
  };

  const roleUsageAliasMap = new Map([
    ["活跃成员", "active_chat_member"], ["活跃群成员", "active_chat_member"], ["好友", "friend"], ["话题发起人", "topic_starter"],
    ["发动态", "poster"], ["发布动态", "poster"], ["发布者", "poster"], ["评论者", "commenter"], ["路人", "bystander"], ["旁观者", "bystander"], ["路人 / 旁观者", "bystander"],
    ["发帖人", "thread_author"], ["楼层回复", "floor_reply"], ["楼层回复者", "floor_reply"], ["回复者", "floor_reply"], ["版主", "moderator"],
    ["主播", "streamer"], ["观众", "viewer"], ["醒目留言", "highlight_sender"], ["醒目留言发送者", "highlight_sender"], ["打赏者", "contributor"], ["打赏", "contributor"], ["贡献者", "contributor"], ["打赏 / 贡献者", "contributor"],
    ["发件人", "sender"], ["收件人", "recipient"], ["联系人", "contact"], ["组织", "organization"], ["系统通知", "system_notice"],
    ["作者", "writer"], ["记录者", "writer"], ["相关人物", "related_person"], ["记忆对象", "memory_subject"],
    ["参与者", "participant"], ["组织者", "organizer"], ["地点联系人", "location_contact"],
    ["呼叫方", "caller"], ["接听方", "callee"], ["通话联系人", "phone_contact"],
    ["来源", "source"], ["通知来源", "source"],
  ]);

  const roleUsageLabelMap = new Map([
    ["active_chat_member", "活跃群成员"], ["friend", "好友"], ["topic_starter", "话题发起人"],
    ["poster", "发布动态"], ["commenter", "评论者"], ["bystander", "路人 / 旁观者"],
    ["thread_author", "发帖人"], ["floor_reply", "楼层回复者"], ["moderator", "版主"],
    ["streamer", "主播"], ["viewer", "观众"], ["highlight_sender", "醒目留言发送者"], ["contributor", "打赏 / 贡献者"],
    ["sender", "发件人"], ["recipient", "收件人"], ["contact", "联系人"], ["organization", "组织"], ["system_notice", "系统通知"],
    ["writer", "记录者"], ["related_person", "相关人物"], ["memory_subject", "记忆对象"],
    ["participant", "参与者"], ["organizer", "组织者"], ["location_contact", "地点联系人"],
    ["caller", "呼叫方"], ["callee", "接听方"], ["phone_contact", "通话联系人"],
    ["source", "通知来源"],
  ]);

  function roleUsageDisplay(value) {
    const raw = String(value || "").trim();
    if (!raw) return "";
    const normalized = normalizeRoleUsageInput(raw);
    return roleUsageLabelMap.get(normalized) || raw;
  }

  function roleUsageListDisplay(values, separator = "、") {
    const rows = Array.isArray(values) ? values : [];
    return rows.map(roleUsageDisplay).filter(Boolean).join(separator);
  }

  function roleAppUsagePlaceholder(appId) {
    const safeAppId = normalizeAppInput(appId);
    const policyUsages = state.roleAppPools?.pools?.[safeAppId]?.policy?.preferred_usages;
    const usages = Array.isArray(policyUsages) && policyUsages.length ? policyUsages : fallbackRoleUsageHints[safeAppId];
    return Array.isArray(usages) ? roleUsageListDisplay(usages) : "相关人物";
  }

  function roleAppUsageText(role, appId) {
    const rows = role?.app_roles && typeof role.app_roles === "object" ? role.app_roles : {};
    const values = rows[normalizeAppInput(appId)];
    return Array.isArray(values) ? roleUsageListDisplay(values) : roleUsageDisplay(values);
  }

  function roleAppUsageInputs(role) {
    return roleAppBindingOptions(role).map((app) => `
      <label class="fmca-role-app-usage-row">
        <span>${esc(app.label || app.app_id)}：</span>
        <input data-role-app-usage="${esc(app.app_id)}" value="${esc(roleAppUsageText(role, app.app_id))}" placeholder="${esc(roleAppUsagePlaceholder(app.app_id))}">
      </label>
    `).join("");
  }

  function normalizeRoleUsageInput(value) {
    const raw = String(value || "").trim();
    if (!raw) return "";
    const alias = roleUsageAliasMap.get(raw) || roleUsageAliasMap.get(raw.toLowerCase());
    if (alias) return alias;
    return raw.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_-]+/g, "_").replace(/^_+|_+$/g, "");
  }

  function roleGeneratorField(name) {
    const value = state.roleGeneratorForm && state.roleGeneratorForm[name];
    return typeof value === "string" ? value : "";
  }

  function roleGeneratorSelectedValues(name) {
    const value = state.roleGeneratorForm && state.roleGeneratorForm[name];
    return new Set(Array.isArray(value) ? value.map(String) : []);
  }

  function roleGeneratorScopeControls(name) {
    const selected = roleGeneratorSelectedValues(name);
    return roleGeneratorAppOptions().map((app) => `
      <label class="fmca-check fmca-chip-check">
        <input type="checkbox" name="${esc(name)}" value="${esc(app.app_id)}" ${selected.has(app.app_id) ? "checked" : ""}>
        <span>${esc(app.label)}</span>
      </label>
    `).join("");
  }

  function roleGeneratorPayloadFrom(form) {
    const data = new FormData(form);
    const count = Number.parseInt(data.get("count") || "1", 10);
    return {
      known_info: data.get("known_info") || "",
      overall_request: data.get("overall_request") || "",
      real_name: data.get("real_name") || "",
      nickname: data.get("nickname") || "",
      identity: data.get("identity") || "",
      impression: data.get("impression") || "",
      hair_color: data.get("hair_color") || "",
      hairstyle: data.get("hairstyle") || "",
      speech_style: data.get("speech_style") || "",
      suitable_apps: data.getAll("suitable_apps").map(String),
      blocked_apps: data.getAll("blocked_apps").map(String),
      count: Number.isFinite(count) ? count : 1,
      source: "admin_role_generator",
    };
  }

  function setError(message = "") {
    const box = byId("fmca-error");
    if (!box) return;
    box.textContent = message;
    box.hidden = !message;
  }

  function setToast(message = "") {
    const box = byId("fmca-toast");
    if (!box) return;
    box.textContent = message;
    box.hidden = !message;
    if (message) window.setTimeout(() => setToast(), 2200);
  }

  function pageScrollTop() {
    return window.scrollY || document.documentElement.scrollTop || document.body.scrollTop || 0;
  }

  function restorePageScroll(scrollTop) {
    if (!Number.isFinite(scrollTop)) return;
    const apply = () => window.scrollTo({ top: scrollTop, left: 0, behavior: "auto" });
    apply();
    requestAnimationFrame(apply);
    window.setTimeout(apply, 80);
  }

  function renderRoleGeneratorKeepingScroll(scrollTop = pageScrollTop()) {
    renderRoleGenerator();
    restorePageScroll(scrollTop);
  }

  function mainChatUrl() {
    let origin = window.location.origin;
    try {
      if (window.parent && window.parent !== window && window.parent.location?.origin) {
        origin = window.parent.location.origin;
      }
    } catch (_error) {
      origin = window.location.origin;
    }
    try {
      const url = new URL(origin);
      if (/^(127\.0\.0\.1|localhost)$/.test(url.hostname) && url.port && url.port !== "8000") {
        return "http://127.0.0.1:8000/chat";
      }
    } catch (_error) {
      return "http://127.0.0.1:8000/chat";
    }
    return `${origin}/chat`;
  }

  function backToChat() {
    const embedded = window.parent && window.parent !== window;
    const targetUrl = mainChatUrl();
    const messages = [
      { type: "fantareal:mobile-chat:back-to-chat", source: "mobile-chat-admin", targetUrl },
      { type: "fantareal:plugin:back-to-chat", source: "mobile-chat-admin", targetUrl },
    ];
    if (embedded) {
      messages.forEach((message) => {
        try {
          window.parent.postMessage(message, "*");
        } catch (_error) {
          // Ignore cross-frame messaging failures; standalone fallback is below.
        }
      });
      return;
    }
    window.location.href = targetUrl;
  }

  async function request(path, options = {}) {
    const response = await fetch(`./api${path}`, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(formatApiError(payload, response.status));
    return payload;
  }

  function formatApiError(payload = {}, status = 0) {
    const raw = String(payload.detail || payload.error || `请求失败 (${status})`).trim();
    const lower = raw.toLowerCase();
    const lines = [];
    const suggestions = [];
    const context = payload.model_context || {};
    const structuredSuggestions = Array.isArray(payload.suggestions) ? payload.suggestions.filter(Boolean) : [];
    let title = raw || `请求失败 (${status})`;
    if (/模型服务返回\s*http\s*\d+/i.test(raw) || /拉取模型列表失败/i.test(raw) || lower.includes("upstream=")) {
      const matched = raw.match(/HTTP\s*\d+/i);
      title = matched ? `模型上游拒绝：${matched[0].toUpperCase()}` : "模型上游拒绝请求";
      suggestions.push("检查 API Key、Base URL 和模型名是否匹配当前供应商。", "先点击模型列表拉取，确认当前配置可访问。", "如果是 422/400，尝试降低 max_tokens、temperature 或切换模型。");
    } else if (lower.includes("超时") || lower.includes("timeout")) {
      title = "请求超时";
      suggestions.push("调大 Timeout 或稍后重试。", "如果是真实生成，可降低输出 token。");
    } else if (lower.includes("无法连接") || lower.includes("network") || lower.includes("connect")) {
      title = "无法连接服务";
      suggestions.push("检查 Base URL 、网络、代理和供应商状态。", "确认小手机独立 API 是否已启用。");
    } else if (lower.includes("无法解析") || lower.includes("不是合法 json") || lower.includes("parser")) {
      title = "返回内容无法解析";
      suggestions.push("查看 diagnostics 中的 raw/parse 摘要。", "保留 Prompt JSON contract，或降低 temperature。");
    }
    lines.push(title);
    if (raw && raw !== title) lines.push(`诊断：${raw}`);
    const contextParts = [];
    if (context.model_source) contextParts.push(`\u6765\u6e90=${context.model_source}`);
    if (context.provider) contextParts.push(`Provider=${context.provider}`);
    if (context.model) contextParts.push(`Model=${context.model}`);
    if (context.base_url_host) contextParts.push(`Host=${context.base_url_host}`);
    if (contextParts.length) lines.push(`\u6a21\u578b\u4e0a\u4e0b\u6587\uff1a${contextParts.join(" / ")}`);
    const finalSuggestions = structuredSuggestions.length ? structuredSuggestions : suggestions;
    if (finalSuggestions.length) lines.push(`\u5efa\u8bae\uff1a${finalSuggestions.join(" ")}`);
    return lines.join("\n");
  }

  function setTab(name) {
    const tabName = tabMeta[name] ? name : "overview";
    document.querySelectorAll("[data-tab]").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.tab === tabName);
    });
    document.querySelectorAll("[data-panel]").forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.panel === tabName);
    });
    const [title, copy] = tabMeta[tabName];
    byId("fmca-page-title").textContent = title;
    byId("fmca-page-copy").textContent = copy;
    if (window.location.hash.slice(1) !== tabName) {
      window.history.replaceState(null, "", `#${tabName}`);
    }
  }

  function setText(id, value) {
    const element = byId(id);
    if (element) element.textContent = value;
  }

  function renderFacts(containerId, rows) {
    const container = byId(containerId);
    if (!container) return;
    container.innerHTML = rows
      .map(([label, value]) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`)
      .join("");
  }

  function readablePromptPreview(preview) {
    if (!preview) return "-";
    const blocks = (preview.blocks || []).map((item) => `${item.label || item.block_id} (${item.block_id})`).join(", ") || "-";
    const contractBlocks = (preview.contract_blocks || []).map((item) => `${item.label || item.block_id} (${item.block_id})`).join(", ") || "-";
    const schema = (preview.schemas || [])[0] || {};
    const context = preview.context_preview || {};
    const mode = preview.settings?.prompt_mode || (preview.settings?.use_custom_prompt ? "override" : "default");
    const modeLabel = mode === "override" ? "\u7f16\u8f91\u5b8c\u6574 Prompt" : mode === "additive" ? "\u8ffd\u52a0\u8bf4\u660e" : "\u9ed8\u8ba4\u63d0\u793a\u8bcd";
    const bodyPrompt = preview.prompt_body || preview.editable_default_prompt || preview.custom_prompt || "";
    const lockedContract = preview.locked_contract_text || "";
    const sections = [
      `Scope: ${preview.scope_label || preview.scope || "-"}`,
      `Mode: ${modeLabel}`,
      `Active blocks: ${blocks}`,
      `Locked contract: ${contractBlocks}`,
      `Context: ${context.role_count ?? 0} enabled roles, ${context.sticker_count ?? 0} stickers, ${context.block_count ?? 0} prompt blocks.`,
      `Output contract: root=${schema.root || "-"}; required=${(schema.required_fields || []).join(", ") || "-"}; notes=${schema.notes || "-"}`,
      `\u6700\u7ec8\u4f1a\u7ed9\u6a21\u578b\u7684 Prompt\uff1a\n\n--- \u4f60\u7f16\u8f91\u7684\u4e3b\u4f53 Prompt ---\n${bodyPrompt || "-"}`,
    ];
    if (lockedContract) {
      sections.push(`--- \u7cfb\u7edf\u9501\u5b9a\u8f93\u51fa\u5951\u7ea6\uff08\u4f1a\u81ea\u52a8\u8ffd\u52a0\uff0c\u4e0d\u9700\u8981\u5728\u4e0a\u9762\u91cd\u590d\u5199\uff09---\n${lockedContract}`);
    }
    sections.push(`--- \u5408\u6210\u540e\u5b9e\u9645\u53d1\u9001\u7ed9\u6a21\u578b ---\n${preview.assembled_prompt || "-"}`);
    return sections.join("\n\n");
  }


  function readablePromptTest(result) {
    if (!result) return "\u5c1a\u672a\u6d4b\u8bd5\u3002";
    const sections = [
      `Mode: ${result.mode || "-"}`,
      `Scope: ${result.scope_label || result.scope || "-"}`,
      `Root key: ${result.root_key || "-"}`,
      `Saved: ${result.save ? "yes" : "no"}`,
      `Provider strategy:\n${JSON.stringify(result.provider_strategy || {}, null, 2)}`,
      `Model context:\n${JSON.stringify(result.model_context || {}, null, 2)}`,
      `Messages:\n${JSON.stringify(result.messages || [], null, 2)}`,
    ];
    if (result.raw_reply) sections.push(`Raw reply:\n${result.raw_reply}`);
    if (Object.prototype.hasOwnProperty.call(result, "parsed")) sections.push(`Parsed JSON:\n${JSON.stringify(result.parsed, null, 2)}`);
    if (result.parse_error) sections.push(`Parse error: ${result.parse_error}`);
    if (result.diagnostics) sections.push(`Recent diagnostics:\n${JSON.stringify(result.diagnostics, null, 2)}`);
    return sections.join("\n\n---\n\n");
  }

  function readableWorkbenchPreview(preview) {
    if (!preview) return "-";
    const schema = preview.schema || {};
    return [
      `Scope: ${preview.scope || "-"}`,
      `Blocks: ${(preview.blocks || []).join(", ") || "-"}`,
      `Schema: root=${schema.root || "-"}; required=${(schema.required_fields || []).join(", ") || "-"}; notes=${schema.notes || "-"}`,
      `Context preview:\n${JSON.stringify(preview.context_preview || {}, null, 2)}`,
      `Assembled prompt:\n${preview.assembled_prompt || "-"}`,
    ].join("\n\n");
  }

  function selectedGroup() {
    return state.groups.find((item) => item.group_id === state.selectedGroupId) || null;
  }

  function selectedRole() {
    return state.roles.find((item) => item.role_id === state.selectedRoleId) || null;
  }

  function selectedPack() {
    return state.stickerPacks.find((item) => item.pack_id === state.selectedPackId) || null;
  }

  function memberCandidates(group) {
    const rows = state.roles
      .filter((role) => role.enabled)
      .map((role) => ({
        role_id: role.role_id,
        name: role.display_name,
        type: "character",
        summary: role.summary || "",
        avatar: role.avatar || "",
      }));
    const seen = new Set(rows.map((item) => item.role_id));
    (group?.members || []).forEach((member) => {
      if (member.type !== "character" || seen.has(member.role_id)) return;
      rows.push(member);
      seen.add(member.role_id);
    });
    return rows.sort((a, b) => a.name.localeCompare(b.name, "zh-Hans-CN"));
  }

  function renderGroups() {
    const container = byId("fmca-group-list");
    if (!container) return;
    if (!state.groups.length) {
      container.innerHTML = '<div class="fmca-empty">暂无群聊。可以先在小手机前台创建，或导入角色后再创建。</div>';
      state.selectedGroupId = "";
      renderGroupEditor();
      return;
    }
    if (!state.selectedGroupId || !state.groups.some((group) => group.group_id === state.selectedGroupId)) {
      state.selectedGroupId = state.groups[0].group_id;
    }
    container.innerHTML = state.groups
      .map((group) => `
        <article class="fmca-list-card">
          <header>
            <div>
              <strong>${esc(group.name)}</strong>
              <span>${esc(group.group_id)} · ${group.members?.length || 0} 人 · 回复 ${esc(group.reply_count || "1-2")}</span>
            </div>
            <button class="fmca-button" type="button" data-action="edit-group" data-group-id="${esc(group.group_id)}">编辑</button>
          </header>
          <p>${esc(group.description || "暂无群聊简介。")}</p>
        </article>
      `)
      .join("");
    renderGroupEditor();
  }

  function renderGroupEditor() {
    const container = byId("fmca-group-editor");
    if (!container) return;
    const group = selectedGroup();
    if (!group) {
      container.innerHTML = '<h3>群聊详情</h3><div class="fmca-placeholder">选择一个群聊后编辑。</div>';
      return;
    }
    const selectedMemberIds = new Set((group.members || []).filter((item) => item.type === "character").map((item) => item.role_id));
    const candidates = memberCandidates(group);
    container.innerHTML = `
      <div class="fmca-editor-header">
        <div>
          <h3>群聊详情</h3>
          <p>${esc(group.group_id)}</p>
        </div>
        <button class="fmca-button fmca-danger" type="button" data-action="delete-group" data-group-id="${esc(group.group_id)}">删除群聊</button>
      </div>
      <form class="fmca-form-grid" data-form="group">
        <label class="fmca-field">
          <span>群名</span>
          <input name="name" maxlength="80" value="${esc(group.name)}" required>
        </label>
        <label class="fmca-field">
          <span>每轮回复角色数</span>
          <select name="reply_count">
            <option value="1" ${group.reply_count === "1" ? "selected" : ""}>1 人</option>
            <option value="1-2" ${group.reply_count !== "1" ? "selected" : ""}>1-2 人</option>
          </select>
        </label>
        <label class="fmca-field is-wide">
          <span>简介</span>
          <textarea name="description" maxlength="500">${esc(group.description || "")}</textarea>
        </label>
        <label class="fmca-check">
          <input type="checkbox" name="allow_role_to_role_reply" ${group.allow_role_to_role_reply !== false ? "checked" : ""}>
          <span>允许角色互相回复</span>
        </label>
        <label class="fmca-check">
          <input type="checkbox" name="allow_auto_interject" ${group.allow_auto_interject ? "checked" : ""}>
          <span>允许本群自动插话</span>
        </label>
        <div class="fmca-member-grid">
          <span>群成员</span>
          <div class="fmca-member-list">
            ${candidates.map((role) => `
              <label>
                <input type="checkbox" name="member" value="${esc(role.role_id)}" ${selectedMemberIds.has(role.role_id) ? "checked" : ""}>
                <span><strong>${esc(role.name)}</strong><br><small class="fmca-muted">${esc(role.summary || role.role_id)}</small></span>
              </label>
            `).join("") || '<div class="fmca-empty">角色库暂无可用角色。</div>'}
          </div>
        </div>
        <div class="fmca-actions">
          <button class="fmca-button fmca-primary" type="submit">保存群聊</button>
        </div>
      </form>
    `;
  }


  function displayPackLabel(pack) {
    if (!pack) return "";
    if (pack.pack_id === "default") return "\u9ed8\u8ba4\u5185\u7f6e\u8868\u60c5\u5305";
    return pack.label || pack.pack_id || "";
  }

  function stickersForPack(packId) {
    return (state.stickers || []).filter((item) => String(item.pack_id || "") === String(packId || ""));
  }

  function selectedRoleAppPool() {
    const pools = state.roleAppPools?.pools || {};
    return state.roleAppFilter ? pools[state.roleAppFilter] || null : null;
  }

  function renderRoleAppPools() {
    const pools = state.roleAppPools?.pools || {};
    const entries = Object.values(pools);
    const selected = state.roleAppFilter || "";
    if (!entries.length) return '<div class="fmca-empty">暂无 App 角色池数据。</div>';
    return `
      <section class="fmca-role-app-pools">
        <div class="fmca-role-app-pools-head">
          <div>
            <h4>App 角色池</h4>
            <p>点击 App 卡片可过滤左侧角色列表；再次查看全部可取消筛选。</p>
          </div>
          <button class="fmca-button" type="button" data-action="filter-role-app" data-app-id="" ${selected ? "" : "disabled"}>全部角色</button>
        </div>
        <div class="fmca-role-app-pool-grid">
          ${entries.map((pool) => `
            <button class="fmca-mini-card fmca-role-app-pool-card${selected === pool.app_id ? " is-active" : ""}" type="button" data-action="filter-role-app" data-app-id="${esc(pool.app_id)}" title="${esc(roleUsageListDisplay(pool.policy?.preferred_usages || []) || '相关人物')}">
              <header><strong>${esc(pool.label || pool.app_id)}</strong><span>${esc(pool.count || 0)} 个候选</span></header>
              <p class="fmca-role-app-pool-stats">适合 ${esc(pool.suitable_count || 0)} · 可用 ${esc(pool.neutral_count || 0)} · 排除 ${esc(pool.blocked_count || 0)}</p>
              <div class="fmca-chip-line">
                ${(pool.roles || []).slice(0, 8).map((role) => `<span title="${esc(roleUsageListDisplay(role.usage || []) || '未指定用途')}">${esc(role.display_name)}${(role.usage || []).length ? ` · ${esc(roleUsageListDisplay(role.usage, '/'))}` : ''}</span>`).join('') || '<em>暂无候选</em>'}
              </div>
            </button>
          `).join('')}
        </div>
      </section>
    `;
  }

  function renderRoles() {
    const container = byId("fmca-role-list");
    if (!container) return;
    const selectedPool = selectedRoleAppPool();
    const roleById = new Map(state.roles.map((role) => [role.role_id, role]));
    const poolRoles = selectedPool?.roles || [];
    const visibleRoles = selectedPool
      ? poolRoles.map((poolRole) => roleById.get(poolRole.role_id)).filter(Boolean)
      : state.roles;
    const filterNotice = selectedPool
      ? `<div class="fmca-role-filter-notice"><strong>当前筛选：${esc(selectedPool.label || selectedPool.app_id)}</strong><span>${esc(poolRoles.length)} 个候选角色</span></div>`
      : "";
    if (!visibleRoles.length) {
      container.innerHTML = `${filterNotice}<div class="fmca-empty">${selectedPool ? "该 App 暂无候选角色。" : "角色库为空。可以同步当前角色卡，或手动新建角色。"}</div>${renderRoleAppPools()}`;
    } else {
      container.innerHTML = `${filterNotice}${visibleRoles
        .map((role) => `
          <article class="fmca-list-card${role.enabled ? "" : " is-disabled"}">
            <header>
              <div>
                <strong>${esc(role.display_name)}</strong>
                <span>${esc(role.role_id)} ? ${esc(role.source)} ? ${role.enabled ? "启用" : "禁用"}</span>
              </div>
              <div class="fmca-actions">
                ${role.enabled ? "" : `<button class="fmca-button" type="button" data-action="restore-role" data-role-id="${esc(role.role_id)}">恢复</button>`}
                <button class="fmca-button" type="button" data-action="edit-role" data-role-id="${esc(role.role_id)}">编辑</button>
              </div>
            </header>
            <p>${esc(role.summary || "暂无摘要。")}</p>
            <div class="fmca-role-app-summary">
              <span>适合：${esc(appScopeLabelText(role.suitable_apps, "未限定"))}</span>
              <span>避免：${esc(appScopeLabelText(role.blocked_apps, "无"))}</span>
            </div>
          </article>
        `)
        .join("")}${renderRoleAppPools()}`;
    }
    renderRoleEditor();
  }

  function renderRoleEditor() {
    const container = byId("fmca-role-editor");
    if (!container) return;
    const role = selectedRole();
    container.innerHTML = `
      <div class="fmca-editor-header">
        <div>
          <h3>${role ? "编辑角色" : "新建角色"}</h3>
          <p>角色资料只进入小手机 prompt，不写回角色卡。</p>
        </div>
        ${role ? '<button class="fmca-button" type="button" data-action="new-role">新建</button>' : ""}
      </div>
      <form class="fmca-form-grid" data-form="role" data-role-id="${esc(role?.role_id || "")}">
        <label class="fmca-field">
          <span>显示名</span>
          <input name="display_name" maxlength="80" value="${esc(role?.display_name || "")}" required>
        </label>
        <label class="fmca-field">
          <span>Role ID ${role ? "（不可改）" : "（可留空）"}</span>
          <input name="role_id" maxlength="120" value="${esc(role?.role_id || "")}" ${role ? "disabled" : ""}>
        </label>
        <label class="fmca-field">
          <span>别名，逗号分隔</span>
          <input name="aliases" value="${esc(tagsToText(role?.aliases || []))}">
        </label>
        <label class="fmca-field">
          <span>状态</span>
          <input name="status" maxlength="80" value="${esc(role?.status || "online")}">
        </label>
        <label class="fmca-field is-wide">
          <span>摘要</span>
          <textarea name="summary" maxlength="500">${esc(role?.summary || "")}</textarea>
        </label>
        <label class="fmca-field is-wide">
          <span>聊天风格</span>
          <textarea name="chat_style" maxlength="500">${esc(role?.chat_style || "")}</textarea>
        </label>
        <section class="fmca-role-app-bind-panel">
          <header>
            <strong>\u89d2\u8272 / App \u7ed1\u5b9a</strong>
            <span>\u52fe\u9009\u89d2\u8272\u9002\u5408\u6216\u6392\u9664\u7684 App\uff1b\u4e0b\u65b9\u7684\u7528\u9014\u5c0f\u6846\u53ef\u9009\uff0c\u76f4\u63a5\u5199\u4e2d\u6587\u5373\u53ef\uff0c\u4e5f\u53ef\u5148\u7559\u7a7a\u3002</span>
          </header>
          <div class="fmca-role-app-scope-grid">
            <div class="fmca-role-app-scope-group">
              <strong>\u9002\u5408\u51fa\u73b0\u7684 App</strong>
              <p>\u52fe\u9009\u540e\uff0c\u751f\u6210\u65f6\u4f1a\u4f18\u5148\u8ba9\u8fd9\u4e2a\u89d2\u8272\u5728\u8be5 App \u51fa\u573a\u3002</p>
              <div class="fmca-chip-checks">${roleAppScopeControls(role, "suitable_apps")}</div>
            </div>
            <div class="fmca-role-app-scope-group">
              <strong>\u6392\u9664 / \u4e0d\u8981\u51fa\u73b0\u7684 App</strong>
              <p>\u52fe\u9009\u540e\uff0c\u8be5\u89d2\u8272\u4f1a\u4ece\u5bf9\u5e94 App \u7684\u5019\u9009\u6c60\u91cc\u6392\u9664\u3002</p>
              <div class="fmca-chip-checks">${roleAppScopeControls(role, "blocked_apps")}</div>
            </div>
          </div>
          <div class="fmca-role-app-usage-panel">
            <div>
              <strong>App \u5185\u7528\u9014</strong>
              <p>\u4f8b\u5982\u76f4\u64ad\u5199\u201c\u4e3b\u64ad\u3001\u89c2\u4f17\u201d\uff0c\u8bba\u575b\u5199\u201c\u53d1\u5e16\u4eba\u3001\u697c\u5c42\u56de\u590d\u8005\u201d\u3002\u8fd9\u4e0d\u662f\u5fc5\u586b\uff0c\u53ea\u662f\u5e2e AI \u7406\u89e3\u201c\u8fd9\u4e2a\u4eba\u5728\u8fd9\u4e2a App \u91cc\u5e72\u4ec0\u4e48\u201d\u3002</p>
            </div>
            <div class="fmca-role-app-usage-grid">${roleAppUsageInputs(role)}</div>
          </div>
        </section>
        <label class="fmca-field">
          <span>偏好 tags</span>
          <input name="preferred_tags" value="${esc(tagsToText(role?.sticker_preferences?.preferred_tags || []))}" placeholder="happy, shy, soft">
        </label>
        <label class="fmca-field">
          <span>屏蔽 tags</span>
          <input name="blocked_tags" value="${esc(tagsToText(role?.sticker_preferences?.blocked_tags || []))}" placeholder="angry">
        </label>
        <label class="fmca-field">
          <span>主动发言权重</span>
          <input name="auto_speak_weight" type="number" min="0" max="10" step="0.1" value="${esc(role?.auto_speak_weight ?? 1)}">
        </label>
        <label class="fmca-check">
          <input type="checkbox" name="enabled" ${role?.enabled === false ? "" : "checked"}>
          <span>启用角色</span>
        </label>
        <div class="fmca-actions">
          <button class="fmca-button fmca-primary" type="submit">${role ? "保存角色" : "创建角色"}</button>
          ${role && role.enabled ? `<button class="fmca-button fmca-danger" type="button" data-action="disable-role" data-role-id="${esc(role.role_id)}">禁用角色</button>` : ""}
          ${role && !role.enabled ? `<button class="fmca-button" type="button" data-action="restore-role" data-role-id="${esc(role.role_id)}">恢复角色</button>` : ""}
          ${role ? `<button class="fmca-button fmca-danger" type="button" data-action="delete-role" data-role-id="${esc(role.role_id)}">删除角色</button>` : ""}
        </div>
      </form>
    `;
  }

  function roleGeneratorChips(values) {
    const rows = Array.isArray(values) ? values : [];
    return rows.length ? rows.map((item) => `<span>${esc(item)}</span>`).join("") : "<span>未限定</span>";
  }

  function roleGeneratorDraftField(index, field, label, value, options = {}) {
    const tag = options.multiline ? "textarea" : "input";
    const attrs = [
      `data-role-generator-draft-field="${esc(field)}"`,
      `data-index="${index}"`,
      options.maxlength ? `maxlength="${options.maxlength}"` : "",
      options.placeholder ? `placeholder="${esc(options.placeholder)}"` : "",
    ].filter(Boolean).join(" ");
    return `
      <label class="${options.wide ? "fmca-wide" : ""}">
        <span>${esc(label)}</span>
        ${tag === "textarea"
          ? `<textarea ${attrs}>${esc(value || "")}</textarea>`
          : `<input ${attrs} value="${esc(value || "")}">`}
      </label>
    `;
  }

  function roleGeneratorDraftScopeEditor(draft, index, field, label) {
    const selected = new Set(Array.isArray(draft?.[field]) ? draft[field].map(String) : []);
    return `
      <div class="fmca-field is-wide">
        <span>${esc(label)}</span>
        <div class="fmca-chip-checks">
          ${roleGeneratorAppOptions().map((app) => `
            <label class="fmca-check fmca-chip-check">
              <input type="checkbox" data-role-generator-draft-scope="${esc(field)}" data-index="${index}" value="${esc(app.app_id)}" ${selected.has(app.app_id) ? "checked" : ""}>
              <span>${esc(app.label)}</span>
            </label>
          `).join("")}
        </div>
      </div>
    `;
  }

  function roleGeneratorDraftEditor(draft, index) {
    if (!draft) return '<div class="fmca-empty">暂无选中草稿。</div>';
    return `
      <div class="fmca-role-draft-editor">
        <p class="fmca-muted">这里可以直接改草稿内容，保存时会写入修改后的版本。</p>
        <div class="fmca-form-grid">
          ${roleGeneratorDraftField(index, "display_name", "名字", draft.display_name, { maxlength: 80 })}
          ${roleGeneratorDraftField(index, "role_id", "角色 ID", draft.role_id, { maxlength: 120, placeholder: "留空则按名字生成" })}
          ${roleGeneratorDraftField(index, "identity", "身份", draft.identity, { maxlength: 160, wide: true })}
          ${roleGeneratorDraftField(index, "appearance", "外观", draft.appearance, { maxlength: 260, multiline: true, wide: true })}
          ${roleGeneratorDraftField(index, "summary", "摘要", draft.summary, { maxlength: 500, multiline: true, wide: true })}
          ${roleGeneratorDraftField(index, "chat_style", "说话风格", draft.chat_style, { maxlength: 500, multiline: true, wide: true })}
          ${roleGeneratorDraftScopeEditor(draft, index, "suitable_apps", "适合出现的 App")}
          ${roleGeneratorDraftScopeEditor(draft, index, "blocked_apps", "禁止出现的 App")}
        </div>
      </div>
    `;
  }

  function updateRoleGeneratorDraftField(index, field, value) {
    const draft = (state.roleGeneratorDrafts || [])[index];
    if (!draft) return;
    draft[field] = String(value || "");
  }

  function updateRoleGeneratorDraftScope(index, field) {
    const draft = (state.roleGeneratorDrafts || [])[index];
    if (!draft) return;
    const checked = [...document.querySelectorAll(`[data-role-generator-draft-scope="${CSS.escape(field)}"][data-index="${index}"]:checked`)]
      .map((item) => String(item.value || ""))
      .filter(Boolean);
    draft[field] = checked;
  }

  function roleGeneratorDraftCard(draft, index, selectedIndex) {
    return `
      <article class="fmca-list-card${index === selectedIndex ? " is-selected" : ""}">
        <header>
          <div>
            <strong>${esc(draft.display_name || `草稿 ${index + 1}`)}</strong>
            <span>${esc(draft.role_id || "保存时生成 ID")} · ${esc(draft.source || "role_generator")}</span>
          </div>
          <button class="fmca-button" type="button" data-action="select-role-generator-draft" data-index="${index}">预览</button>
        </header>
        <p>${esc(draft.summary || draft.identity || "暂无摘要。")}</p>
        <div class="fmca-chip-line"><em>适合</em>${roleGeneratorChips(draft.suitable_apps)}</div>
        <div class="fmca-chip-line is-muted"><em>避免</em>${roleGeneratorChips(draft.blocked_apps)}</div>
      </article>
    `;
  }

  function renderRoleGenerator() {
    const container = byId("fmca-role-generator");
    if (!container) return;
    const drafts = state.roleGeneratorDrafts || [];
    const selectedIndex = Math.max(0, Math.min(state.roleGeneratorSelectedIndex || 0, Math.max(0, drafts.length - 1)));
    const selectedDraft = drafts[selectedIndex] || null;
    const countValue = String(state.roleGeneratorForm?.count || 1);
    container.innerHTML = `
      <div class="fmca-editor-header">
        <div>
          <h3>AI \u751f\u6210\u89d2\u8272\u8349\u7a3f</h3>
          <p>\u4e0a\u534a\u533a\u7528\u4e8e\u586b\u5199\u751f\u6210\u6761\u4ef6\uff0cAI \u4f1a\u5148\u751f\u6210\u4e00\u4e2a\u6216\u591a\u4e2a\u5019\u9009\u8349\u7a3f\uff1b\u8349\u7a3f\u4e0d\u4f1a\u76f4\u63a5\u5165\u5e93\uff0c\u9700\u8981\u5728\u4e0b\u65b9\u5ba1\u6838\u5e76\u4fdd\u5b58\u3002</p>
        </div>
        <div class="fmca-actions">
          <button class="fmca-button" type="button" data-action="extract-event-role-drafts" ${state.roleGeneratorBusy ? "disabled" : ""}>\u4ece\u4e8b\u4ef6\u63d0\u53d6\u8349\u7a3f</button>
          <button class="fmca-button" type="button" data-action="extract-chat-role-drafts" ${state.roleGeneratorBusy ? "disabled" : ""}>\u4ece\u4e3b Chat \u63d0\u53d6\u8349\u7a3f</button>
          <button class="fmca-button" type="button" data-action="clear-role-generator" ${state.roleGeneratorBusy ? "disabled" : ""}>清空</button>
        </div>
      </div>
      <form class="fmca-form-grid" data-form="role-generator">
        <label class="fmca-wide"><span>已知信息</span><textarea name="known_info" maxlength="1000" placeholder="例如：论坛里经常提到的茶馆老板，知道一点主角的过去。">${esc(roleGeneratorField("known_info"))}</textarea></label>
        <label class="fmca-wide"><span>整体要求</span><textarea name="overall_request" maxlength="1000" placeholder="这个人物需要承担的关系、气质或剧情功能。">${esc(roleGeneratorField("overall_request"))}</textarea></label>
        <label><span>真实姓名</span><input name="real_name" maxlength="80" value="${esc(roleGeneratorField("real_name"))}"></label>
        <label><span>网名 / 昵称</span><input name="nickname" maxlength="80" value="${esc(roleGeneratorField("nickname"))}"></label>
        <label><span>身份</span><input name="identity" maxlength="160" value="${esc(roleGeneratorField("identity"))}"></label>
        <label><span>生成数量</span><select name="count">${[1, 3, 5, 10].map((count) => `<option value="${count}" ${countValue === String(count) ? "selected" : ""}>${count}</option>`).join("")}</select></label>
        <label><span>发色</span><input name="hair_color" maxlength="80" value="${esc(roleGeneratorField("hair_color"))}"></label>
        <label><span>发型</span><input name="hairstyle" maxlength="120" value="${esc(roleGeneratorField("hairstyle"))}"></label>
        <label class="fmca-wide"><span>整体印象</span><textarea name="impression" maxlength="300">${esc(roleGeneratorField("impression"))}</textarea></label>
        <label class="fmca-wide"><span>说话风格</span><textarea name="speech_style" maxlength="240">${esc(roleGeneratorField("speech_style"))}</textarea></label>
        <div class="fmca-field is-wide">
          <span>适合出现的 App</span>
          <div class="fmca-chip-checks">${roleGeneratorScopeControls("suitable_apps")}</div>
        </div>
        <div class="fmca-field is-wide">
          <span>禁止出现的 App</span>
          <div class="fmca-chip-checks">${roleGeneratorScopeControls("blocked_apps")}</div>
        </div>
        <div class="fmca-actions fmca-wide">
          <button class="fmca-button fmca-primary" type="submit" ${state.roleGeneratorBusy ? "disabled" : ""}>${state.roleGeneratorBusy ? "\u751f\u6210\u4e2d..." : "\u6839\u636e\u4e0a\u65b9\u4fe1\u606f\u751f\u6210\u8349\u7a3f"}</button>
          <button class="fmca-button" type="button" data-action="save-role-generator-selected" ${!selectedDraft || state.roleGeneratorBusy ? "disabled" : ""}>保存选中</button>
          <button class="fmca-button" type="button" data-action="save-role-generator-all" ${!drafts.length || state.roleGeneratorBusy ? "disabled" : ""}>全部保存</button>
        </div>
      </form>
      <div class="fmca-two-col fmca-role-generator-result">
        <section>
          <h3>\u5f85\u786e\u8ba4\u8349\u7a3f</h3>
          <p class="fmca-muted">\u8fd9\u91cc\u5c55\u793a AI \u751f\u6210\u6216\u4ece\u5386\u53f2\u5185\u5bb9\u63d0\u53d6\u51fa\u7684\u89d2\u8272\u8349\u7a3f\u3002\u786e\u8ba4\u65e0\u8bef\u540e\u518d\u4fdd\u5b58\u5230\u89d2\u8272\u5e93\u3002</p>
          <div class="fmca-list">${drafts.length ? drafts.map((draft, index) => roleGeneratorDraftCard(draft, index, selectedIndex)).join("") : '<div class="fmca-empty">暂无草稿。</div>'}</div>
        </section>
        <section>
          <h3>\u5ba1\u6838\u5e76\u7f16\u8f91\u8349\u7a3f</h3>
          <p class="fmca-muted">\u8fd9\u91cc\u7528\u4e8e\u4fee\u6539\u9009\u4e2d\u8349\u7a3f\u3002\u70b9\u51fb\u201c\u4fdd\u5b58\u9009\u4e2d\u201d\u6216\u201c\u5168\u90e8\u4fdd\u5b58\u201d\u540e\uff0c\u624d\u4f1a\u8fdb\u5165\u5c0f\u624b\u673a\u72ec\u7acb\u89d2\u8272\u5e93\u3002</p>
          ${roleGeneratorDraftEditor(selectedDraft, selectedIndex)}
        </section>
      </div>
      ${state.roleGeneratorSaved.length ? `<p class="fmca-muted">最近保存：${state.roleGeneratorSaved.map((item) => esc(item.display_name)).join("、")}</p>` : ""}
    `;
  }

  function renderStickers() {
    const container = byId("fmca-sticker-list");
    if (!container) return;
    if (!state.selectedPackId) {
      const editable = state.stickerPacks.find((pack) => pack.manifest_editable);
      state.selectedPackId = editable?.pack_id || state.stickerPacks[0]?.pack_id || "";
    }
    container.innerHTML = state.stickerPacks
      .map((pack) => `
        <article class="fmca-list-card${state.selectedPackId === pack.pack_id ? " is-selected" : ""}">
          <header>
            <div>
              <strong>${esc(displayPackLabel(pack))}</strong>
              <span>${esc(pack.pack_id)} ? ${esc(pack.type)} ? ${pack.count || 0} \u4e2a\u8d34\u7eb8</span>
            </div>
            <button class="fmca-button" type="button" data-action="edit-pack" data-pack-id="${esc(pack.pack_id)}">${pack.manifest_editable ? "\u7f16\u8f91 manifest" : "\u67e5\u770b\u8d34\u7eb8"}</button>
          </header>
          <p>${pack.manifest_editable ? `\u53ef\u7f16\u8f91 manifest\uff1a${pack.manifest_count || 0} \u6761 ? ${esc(pack.directory || "")}` : "\u5185\u7f6e\u53ea\u8bfb\u8d34\u7eb8\u5305\uff1a\u53ef\u67e5\u770b\u8d34\u7eb8\u9884\u89c8\uff0c\u4e0d\u4f1a\u5199 manifest\u3002"}</p>
        </article>
      `)
      .join("") || '<div class="fmca-empty">\u6682\u65e0\u8868\u60c5\u5305\u3002</div>';
    renderStickerEditor();
  }

  function renderStickerEditor() {
    const container = byId("fmca-sticker-editor");
    if (!container) return;
    const pack = selectedPack();
    if (!pack) {
      container.innerHTML = '<h3>Manifest 编辑</h3><div class="fmca-placeholder">选择一个表情包后编辑。</div>';
      return;
    }
    if (!pack.manifest_editable) {
      const rows = stickersForPack(pack.pack_id);
      container.innerHTML = `
        <div class="fmca-editor-header">
          <div>
            <h3>${esc(displayPackLabel(pack))} \u8d34\u7eb8\u9884\u89c8</h3>
            <p>\u8fd9\u662f\u5185\u7f6e\u53ea\u8bfb\u8868\u60c5\u5305\uff1b\u4e0d\u652f\u6301\u5199\u5165 manifest\uff0c\u4f46\u53ef\u4ee5\u67e5\u770b\u5f53\u524d\u53ef\u7528\u8d34\u7eb8\u3002\u5982\u9700\u7f16\u8f91\uff0c\u8bf7\u5728 stickers \u76ee\u5f55\u4e0b\u65b0\u5efa\u81ea\u5b9a\u4e49\u5305\u5e76\u7ef4\u62a4 manifest.json\u3002</p>
          </div>
        </div>
        <div class="fmca-sticker-preview-grid">
          ${rows.map((item) => `
            <article class="fmca-sticker-preview-card">
              <div class="fmca-sticker-preview-thumb">${item.url_path ? `<img class="fmca-sticker-thumb" src="./api${esc(item.url_path)}" alt="${esc(item.label || item.id)}" loading="lazy">` : `<span>${esc(item.id || item.label || "-")}</span>`}</div>
              <strong>${esc(item.label || item.id)}</strong>
              <span>ID: ${esc(item.id || "-")}</span>
              <span>Tags: ${esc((item.tags || []).join(", ") || "-")}</span>
            </article>
          `).join("") || '<div class="fmca-empty">\u6682\u65e0\u53ef\u9884\u89c8\u8d34\u7eb8\u3002</div>'}
        </div>
      `;
      return;
    }
    container.innerHTML = `
      <div class="fmca-editor-header">
        <div>
          <h3>${esc(displayPackLabel(pack))} manifest</h3>
          <p>${esc(pack.directory || "")}</p>
        </div>
        <button class="fmca-button" type="button" data-action="scan-pack" data-pack-id="${esc(pack.pack_id)}">重扫</button>
      </div>
      <form class="fmca-form-grid" data-form="manifest" data-pack-id="${esc(pack.pack_id)}">
        <div class="fmca-manifest-list">
          ${state.manifestRows.map((item, index) => `
            <div class="fmca-manifest-row">
              <div>
                <img class="fmca-sticker-thumb" src="./api${esc(item.url_path)}" alt="${esc(item.label)}" loading="lazy">
                <small>${esc(item.filename)}</small>
                <input type="hidden" name="filename_${index}" value="${esc(item.filename)}">
              </div>
              <label class="fmca-field">
                <span>Label</span>
                <input name="label_${index}" value="${esc(item.label || "")}">
              </label>
              <label class="fmca-field">
                <span>Tags</span>
                <input name="tags_${index}" value="${esc(tagsToText(item.tags || []))}" placeholder="happy, sad, cute">
              </label>
              <label class="fmca-field is-wide">
                <span>Description</span>
                <textarea name="description_${index}" maxlength="120">${esc(item.description || "")}</textarea>
              </label>
            </div>
          `).join("") || '<div class="fmca-empty">未读取到 PNG。</div>'}
        </div>
        <div class="fmca-actions">
          <button class="fmca-button fmca-primary" type="submit">保存 manifest</button>
        </div>
      </form>
    `;
  }

  function renderAutomation() {
    const container = byId("fmca-automation-editor");
    if (!container) return;
    const auto = state.automation?.auto_behavior || state.summary?.settings?.auto_behavior || {};
    const runtime = state.automation?.state || {};
    container.innerHTML = `
      <h3>自动插话设置</h3>
      <form class="fmca-form-grid" data-form="automation">
        <label class="fmca-check">
          <input type="checkbox" name="enabled" ${auto.enabled ? "checked" : ""}>
          <span>启用自动插话</span>
        </label>
        <label class="fmca-check">
          <input type="checkbox" name="active_group_only" ${auto.active_group_only !== false ? "checked" : ""}>
          <span>仅当前打开群聊触发</span>
        </label>
        <label class="fmca-field">
          <span>空闲秒数</span>
          <input name="idle_seconds" type="number" min="15" max="3600" value="${esc(auto.idle_seconds || 90)}">
        </label>
        <label class="fmca-field">
          <span>最小间隔秒数</span>
          <input name="interval_seconds" type="number" min="15" max="3600" value="${esc(auto.interval_seconds || 120)}">
        </label>
        <label class="fmca-field">
          <span>每会话最多轮数</span>
          <input name="max_rounds_per_session" type="number" min="1" max="20" value="${esc(auto.max_rounds_per_session || 3)}">
        </label>
        <label class="fmca-field">
          <span>每小时最多生成</span>
          <input name="max_generations_per_hour" type="number" min="1" max="60" value="${esc(auto.max_generations_per_hour || 6)}">
        </label>
        <div class="fmca-actions">
          <button class="fmca-button fmca-primary" type="submit">保存自动行为</button>
          <button class="fmca-button fmca-danger" type="button" data-action="pause-automation">暂停全部</button>
        </div>
      </form>
      <hr>
      <form class="fmca-form-grid" data-form="automation-test">
        <label class="fmca-field">
          <span>测试群聊</span>
          <select name="group_id">
            ${state.groups.map((group) => `<option value="${esc(group.group_id)}">${esc(group.name)}</option>`).join("")}
          </select>
        </label>
        <div class="fmca-actions">
          <button class="fmca-button" type="submit">测试续聊一次</button>
        </div>
      </form>
      <div class="fmca-placeholder">运行状态：${runtime.paused ? "已暂停" : "未暂停"}${runtime.paused_at ? ` · ${esc(runtime.paused_at)}` : ""}</div>
    `;
  }

  function currentPromptSettings() {
    return state.summary?.settings?.prompt || state.promptPreview?.settings || {};
  }

  function promptScopeLabel(scope) {
    return (promptScopes.find(([value]) => value === scope) || [scope, scope])[1];
  }

  function selectedPromptScope() {
    const settings = currentPromptSettings();
    const scope = state.promptScope || state.promptPreview?.scope || settings.last_preview_channel || "group_chat";
    return promptScopes.some(([value]) => value === scope) ? scope : "group_chat";
  }

  function promptCustomValue(scope) {
    const settings = currentPromptSettings();
    const prompts = settings.custom_prompts || {};
    return prompts[scope] || "";
  }

  function selectedPromptMode() {
    const settings = currentPromptSettings();
    if (settings.prompt_mode) return settings.prompt_mode;
    return settings.use_custom_prompt ? "override" : "default";
  }

  function stripLockedPromptContract(text) {
    let value = String(text || "").trim();
    const contract = String(state.promptPreview?.locked_contract_text || "").trim();
    if (value && contract && value.endsWith(contract)) {
      value = value.slice(0, -contract.length).trim();
    }
    return value;
  }

  function editableDefaultPrompt() {
    return stripLockedPromptContract(state.promptPreview?.editable_default_prompt || state.promptPreview?.default_prompt || "");
  }

  function promptBlockHelp(block) {
    const id = block?.block_id || "";
    const help = {
      base_contract: "基础边界：说明小手机是独立插件，不能改写主 Chat。普通用户不建议修改。",
      role_context: "角色上下文：要求模型按角色资料、状态和当前频道行动。普通用户不建议修改。",
      channel_behavior: "App 生成规则：控制动态、论坛、邮箱、直播等内容保持紧凑可信。普通用户不建议修改。",
      sticker_contract: "贴纸规则：限制群聊贴纸只能使用可用 sticker id。普通用户不建议修改。",
      json_output: "JSON 输出契约：保证模型只返回可解析 JSON。通常必须保持启用。",
    };
    return help[id] || "底层提示块：影响模型基础行为。仅建议高级用户修改。";
  }

  function renderPromptTools() {
    const blocksBox = byId("fmca-prompt-blocks");
    const previewBox = byId("fmca-prompt-preview");
    const settings = currentPromptSettings();
    const scope = selectedPromptScope();
    const customValue = stripLockedPromptContract(promptCustomValue(scope));
    const promptMode = selectedPromptMode();
    const editorValue = promptMode === "override" && !customValue.trim() ? editableDefaultPrompt() : customValue;
    if (blocksBox) {
      blocksBox.innerHTML = `
        <h3>Prompt \u7f16\u8f91</h3>
        <p>\u5148\u9009\u62e9\u5165\u53e3\u548c\u6a21\u5f0f\uff1a\u201c\u9ed8\u8ba4\u201d\u4f7f\u7528\u7cfb\u7edf Prompt\uff1b\u201c\u8ffd\u52a0\u8bf4\u660e\u201d\u628a\u4f60\u5199\u7684\u5185\u5bb9\u52a0\u5230\u9ed8\u8ba4 Prompt \u4e4b\u540e\uff1b\u201c\u7f16\u8f91\u5b8c\u6574 Prompt\u201d\u76f4\u63a5\u7f16\u8f91\u9ed8\u8ba4\u4e3b\u4f53\u3002\u9501\u5b9a\u7684 JSON \u8f93\u51fa\u5951\u7ea6\u4f1a\u5355\u72ec\u663e\u793a\u5e76\u81ea\u52a8\u8ffd\u52a0\u3002</p>
        <form class="fmca-prompt-editor" data-form="prompt-custom">
          <div class="fmca-prompt-toolbar">
            <label>
              <span>\u7f16\u8f91\u8303\u56f4</span>
              <select id="fmca-prompt-scope" name="scope">
                ${promptScopes.map(([value, label]) => `<option value="${esc(value)}" ${value === scope ? "selected" : ""}>${esc(label)}</option>`).join("")}
              </select>
            </label>
            <label>
              <span>\u7f16\u8f91\u6a21\u5f0f</span>
              <select name="prompt_mode" id="fmca-prompt-mode">
                <option value="default" ${promptMode === "default" ? "selected" : ""}>\u9ed8\u8ba4\uff1a\u4f7f\u7528\u7cfb\u7edf Prompt</option>
                <option value="additive" ${promptMode === "additive" ? "selected" : ""}>\u8ffd\u52a0\uff1a\u8865\u5145\u81ea\u7136\u8bed\u8a00\u8981\u6c42</option>
                <option value="override" ${promptMode === "override" ? "selected" : ""}>\u7f16\u8f91\u5b8c\u6574 Prompt\uff1a\u4fee\u6539\u9ed8\u8ba4\u4e3b\u4f53</option>
              </select>
            </label>
          </div>
          <label class="fmca-field is-wide fmca-prompt-textarea">
            <span>${promptMode === "override" ? "\u7f16\u8f91\u5b8c\u6574 Prompt" : "\u8ffd\u52a0\u81ea\u7136\u8bed\u8a00\u8bf4\u660e"} · ${esc(promptScopeLabel(scope))}</span>
            <textarea id="fmca-custom-prompt" name="custom_prompt" rows="15" placeholder="\u8ffd\u52a0\u6a21\u5f0f\uff1a\u53ef\u5199\u4e00\u53e5\u81ea\u7136\u8bed\u8a00\u8981\u6c42\u3002\u7f16\u8f91\u5b8c\u6574 Prompt \u6a21\u5f0f\uff1a\u6587\u672c\u6846\u4f1a\u81ea\u52a8\u8f7d\u5165\u9ed8\u8ba4\u4e3b\u4f53\uff0c\u53ef\u76f4\u63a5\u5728\u91cc\u9762\u4fee\u6539\u3002">${esc(editorValue)}</textarea>
          </label>
          <div class="fmca-prompt-note">\u9ed8\u8ba4\u6a21\u5f0f\u4e0d\u4f7f\u7528\u6587\u672c\u6846\u5185\u5bb9\uff1b\u8ffd\u52a0\u6a21\u5f0f\u4f1a\u628a\u6587\u672c\u4f5c\u4e3a\u9ad8\u4f18\u5148\u7ea7\u8865\u5145\u8bf4\u660e\uff1b\u7f16\u8f91\u5b8c\u6574 Prompt \u6a21\u5f0f\u4f1a\u7528\u6587\u672c\u6846\u5185\u5bb9\u66ff\u6362\u9ed8\u8ba4\u4e3b\u4f53\u3002JSON \u8f93\u51fa\u5951\u7ea6\u662f\u7cfb\u7edf\u9501\u5b9a\u6bb5\uff0c\u9884\u89c8\u91cc\u4f1a\u5355\u72ec\u5217\u51fa\uff0c\u4e0d\u9700\u8981\u5728\u4e3b\u4f53 Prompt \u91cc\u91cd\u590d\u5199\u3002</div>
          <div class="fmca-actions">
            <button class="fmca-button fmca-primary" type="submit">\u4fdd\u5b58 Prompt \u8bbe\u7f6e</button>
            <button class="fmca-button" type="button" data-action="load-default-prompt">\u8f7d\u5165\u9ed8\u8ba4\u4e3b\u4f53 Prompt</button>
            <button class="fmca-button" type="button" data-action="clear-current-prompt">\u6e05\u7a7a\u5f53\u524d\u8303\u56f4</button>
            <button class="fmca-button" type="button" data-action="refresh-prompt-preview">\u5237\u65b0\u9884\u89c8</button>
          </div>
        </form>
        <section class="fmca-prompt-test">
          <h4>Prompt \u6d4b\u8bd5\u5de5\u4f5c\u53f0</h4>
          <p>\u7528\u4e8e\u68c0\u67e5\u6700\u7ec8 prompt\u3001user message\u3001Provider \u7b56\u7565\u3001raw reply \u548c\u89e3\u6790\u7ed3\u679c\u3002\u771f\u5b9e\u6a21\u5f0f\u4f1a\u8c03\u7528\u6a21\u578b\uff0c\u4f46\u672c\u6d4b\u8bd5\u56fa\u5b9a save=false\u3002</p>
          <form class="fmca-form-grid" data-form="prompt-test">
            <label class="fmca-field">
              <span>\u6d4b\u8bd5\u6a21\u5f0f</span>
              <select name="mode">
                <option value="dry-run">dry-run\uff1a\u53ea\u7ec4\u88c5 Prompt</option>
                <option value="mock">mock\uff1a\u6a21\u62df\u6a21\u578b\u8fd4\u56de\u5e76\u6d4b\u8bd5\u89e3\u6790</option>
                <option value="real">real\uff1a\u8c03\u7528\u771f\u5b9e\u6a21\u578b\uff08save=false\uff09</option>
              </select>
            </label>
            <label class="fmca-field is-wide">
              <span>\u6d4b\u8bd5\u4e0a\u4e0b\u6587</span>
              <textarea name="user_input" rows="4" placeholder="\u53ef\u5199\u5165\u60f3\u9a8c\u8bc1\u7684\u573a\u666f\u3001\u5173\u952e\u8bcd\u6216\u8fb9\u754c\u6761\u4ef6\u3002"></textarea>
            </label>
            <div class="fmca-actions">
              <button class="fmca-button fmca-primary" type="submit" ${state.promptTestBusy ? "disabled" : ""}>${state.promptTestBusy ? "\u6d4b\u8bd5\u4e2d..." : "\u8fd0\u884c\u6d4b\u8bd5"}</button>
              <button class="fmca-button" type="button" data-action="clear-prompt-test">\u6e05\u7a7a\u7ed3\u679c</button>
            </div>
          </form>
          <pre class="fmca-pre fmca-prompt-test-result">${esc(readablePromptTest(state.promptTestResult))}</pre>
        </section>
        <details class="fmca-prompt-details">
          <summary>\u9ad8\u7ea7\uff1a\u5e95\u5c42 Prompt Blocks\uff08\u4e0d\u5efa\u8bae\u666e\u901a\u7528\u6237\u4fee\u6539\uff09</summary>
          <p>\u8fd9\u91cc\u662f\u7ed9\u6a21\u578b\u770b\u7684\u5e95\u5c42\u7cfb\u7edf\u5951\u7ea6\uff0c\u5185\u5bb9\u4fdd\u7559\u82f1\u6587\u662f\u4e3a\u4e86\u7a33\u5b9a JSON \u548c\u6a21\u578b\u517c\u5bb9\u6027\u3002\u666e\u901a\u7528\u6237\u8bf7\u4f18\u5148\u7f16\u8f91\u4e0a\u65b9\u201c\u81ea\u5b9a\u4e49\u63d0\u793a\u8bcd\u201d\uff1b\u9664\u975e\u77e5\u9053\u5f71\u54cd\u8303\u56f4\uff0c\u5426\u5219\u4e0d\u8981\u4fee\u6539\u8fd9\u91cc\u3002</p>
          <form class="fmca-form-grid" data-form="prompt-blocks">
            ${(state.promptBlocks || []).map((block, index) => `
              <article class="fmca-mini-card">
                <label class="fmca-check">
                  <input type="checkbox" name="enabled_${index}" ${block.enabled ? "checked" : ""} ${block.locked ? "disabled" : ""}>
                  <span><strong>${esc(block.label)}</strong> ? ${esc(block.block_id)} ? order ${esc(block.order)}</span>
                </label>
                <p class="fmca-prompt-block-help">${esc(promptBlockHelp(block))}</p>
                <label class="fmca-field is-wide">
                  <span>\u9002\u7528\u8303\u56f4 Scope</span>
                  <input name="scope_${index}" value="${esc(tagsToText(block.scope || []))}" ${block.locked ? "readonly" : ""}>
                </label>
                <label class="fmca-field is-wide">
                  <span>\u5e95\u5c42\u5185\u5bb9 Content\uff08\u7ed9\u6a21\u578b\u770b\u7684\u82f1\u6587\u5951\u7ea6\uff09</span>
                  <textarea name="content_${index}" rows="4" ${block.locked ? "readonly" : ""}>${esc(block.content || "")}</textarea>
                </label>
                <input type="hidden" name="block_id_${index}" value="${esc(block.block_id)}">
                <input type="hidden" name="label_${index}" value="${esc(block.label)}">
                <input type="hidden" name="order_${index}" value="${esc(block.order)}">
                <input type="hidden" name="locked_${index}" value="${block.locked ? "1" : "0"}">
              </article>
            `).join("") || '<div class="fmca-empty">\u6682\u65e0 prompt blocks\u3002</div>'}
            <div class="fmca-actions">
              <button class="fmca-button fmca-primary" type="submit">\u4fdd\u5b58 blocks</button>
              <button class="fmca-button fmca-danger" type="button" data-action="reset-prompt-blocks">\u91cd\u7f6e blocks</button>
            </div>
          </form>
        </details>
      `;
    }
    if (previewBox) {
      previewBox.textContent = readablePromptPreview(state.promptPreview);
    }
  }

  function renderApps() {
    const container = byId("fmca-app-list");
    if (!container) return;
    container.innerHTML = (state.apps || []).map((app, index) => `
      <article class="fmca-list-card">
        <div class="fmca-list-head">
          <div>
            <strong>${esc(app.label)}</strong>
            <span>${esc(app.app_id)} · ${esc(app.page)} · ${esc(app.stage || "-")}</span>
          </div>
          <label class="fmca-check">
            <input type="checkbox" data-app-enabled="${esc(app.app_id)}" ${app.enabled ? "checked" : ""}>
            <span>启用</span>
          </label>
        </div>
        <div class="fmca-form-grid">
          <label class="fmca-field">
            <span>排序</span>
            <input type="number" data-app-order="${esc(app.app_id)}" value="${esc(app.order ?? (index + 1) * 10)}">
          </label>
          <label class="fmca-field is-wide">
            <span>副标题</span>
            <input data-app-subtitle="${esc(app.app_id)}" value="${esc(app.subtitle || "")}">
          </label>
        </div>
      </article>
    `).join("") || '<div class="fmca-empty">暂无应用。</div>';
  }

  function renderChannels() {
    const container = byId("fmca-channel-list");
    if (!container) return;
    const counts = state.summary?.diagnostics?.channel_event_counts || {};
    container.innerHTML = (state.channels || []).map((channel) => `
      <article class="fmca-list-card">
        <div class="fmca-list-head">
          <div>
            <strong>${esc(channel.label)}</strong>
            <span>${esc(channel.channel_id)} · ${esc(channel.type)} · ${counts[channel.channel_id] || 0} 条</span>
          </div>
          <button class="fmca-button" type="button" data-action="seed-channel" data-channel-id="${esc(channel.channel_id)}">Seed</button>
        </div>
        <p>${esc(channel.description || "暂无描述。")}</p>
      </article>
    `).join("") || '<div class="fmca-empty">暂无频道。</div>';
  }

  function renderDiagnostics() {
    const box = byId("fmca-diagnostics");
    if (!box) return;
    box.textContent = JSON.stringify(state.diagnostics || state.summary?.diagnostics || {}, null, 2);
  }



  function renderGenerationControl() {
    const root = byId("fmca-generation-control");
    if (!root) return;
    const control = state.generationControl?.settings || state.summary?.settings?.generation_control || {};
    const appEnabled = control.app_enabled || {};
    const apps = [
      ["group_chat", "群聊"], ["feed", "动态"], ["forum", "论坛"], ["mail", "邮箱"],
      ["diary", "日记"], ["calendar", "日程"], ["live", "直播"], ["phone", "电话"], ["workbench", "工作台"],
    ];
    root.innerHTML = `
      <form class="fmca-form-grid" data-form="generation-control">
        <label class="fmca-row"><span>暂停生成</span><input name="paused" type="checkbox" ${control.paused ? "checked" : ""}></label>
        <label><span>每小时上限</span><input name="hourly_limit" type="number" min="1" max="240" value="${esc(control.hourly_limit ?? 24)}"></label>
        <label><span>失败重试次数</span><input name="retry_limit" type="number" min="0" max="5" value="${esc(control.retry_limit ?? 1)}"></label>
        <label class="fmca-row"><span>显示成本提醒</span><input name="cost_notice" type="checkbox" ${control.cost_notice !== false ? "checked" : ""}></label>
        <div class="fmca-wide fmca-grid">
          ${apps.map(([id, label]) => `<label class="fmca-check"><input name="app_${esc(id)}" type="checkbox" ${appEnabled[id] !== false ? "checked" : ""}><span>${esc(label)}</span></label>`).join("")}
        </div>
        <div class="fmca-actions fmca-wide">
          <button class="fmca-button fmca-primary" type="submit">保存生成控制</button>
          <button class="fmca-button fmca-danger" type="button" data-action="pause-generation-all">全部暂停</button>
          <button class="fmca-button" type="button" data-action="resume-generation-all">全部恢复</button>
        </div>
      </form>
      <pre class="fmca-pre">${esc(JSON.stringify(state.generationControl?.state || {}, null, 2))}</pre>
    `;
  }

  function renderDataTools() {
    const overview = state.dataOverview || {};
    const box = byId("fmca-data-overview");
    if (box) box.textContent = JSON.stringify(overview, null, 2);
    const channelBox = byId("fmca-data-channel-tools");
    if (channelBox) {
      const rows = Object.values(overview.channels || {});
      channelBox.innerHTML = `
        <article class="fmca-mini-card">
          <strong>全局测试数据</strong>
          <p>清理所有频道中带 fallback、workbench 或 test 标记的内容。</p>
          <button class="fmca-button fmca-danger" type="button" data-action="clear-all-channel-test-events">清理全部测试/fallback</button>
        </article>
        ${rows.map((row) => `
          <article class="fmca-mini-card">
            <strong>${esc(row.label)} / ${esc(row.channel_id)}</strong>
            <p>${esc(row.type)} · ${esc(row.count)} events · fallback ${esc(row.fallback_count)} · workbench ${esc(row.workbench_count)}</p>
            <button class="fmca-button fmca-danger" type="button" data-action="clear-channel-test-events" data-channel-id="${esc(row.channel_id)}">清理测试/fallback</button>
            ${(row.recent || []).length ? `<div class="fmca-data-mini-list">${(row.recent || []).slice(0, 4).map((event) => `
              <div>
                <span>${esc(event.title || event.event_id)}</span>
                <button class="fmca-button fmca-danger" type="button" data-action="delete-channel-event" data-channel-id="${esc(row.channel_id)}" data-event-id="${esc(event.event_id)}">删除</button>
              </div>
            `).join("")}</div>` : ""}
          </article>
        `).join("") || '<div class="fmca-empty">暂无频道数据。</div>'}
      `;
    }
    const phone = overview.phone || {};
    if (channelBox && phone.recent) {
      channelBox.insertAdjacentHTML("beforeend", `
        <article class="fmca-mini-card">
          <strong>通话记录</strong>
          <p>${esc(phone.session_count || 0)} sessions · empty ${esc(phone.empty_session_count || 0)}</p>
          <button class="fmca-button fmca-danger" type="button" data-action="prune-empty-phone">清理空通话</button>
          <button class="fmca-button fmca-danger" type="button" data-action="prune-ended-phone">清理已结束通话</button>
          ${(phone.recent || []).length ? `<div class="fmca-data-mini-list">${(phone.recent || []).slice(0, 5).map((session) => `
            <div>
              <span>${esc(session.role_name || session.session_id)} · ${esc(session.status)} · ${esc(session.line_count)} lines</span>
              <button class="fmca-button fmca-danger" type="button" data-action="delete-phone-session" data-session-id="${esc(session.session_id)}">删除</button>
            </div>
          `).join("")}</div>` : ""}
        </article>
      `);
    }
  }

  function renderWorkbench() {
    const workbench = state.workbench || {};
    const roleBox = byId("fmca-workbench-role-draft");
    if (roleBox) roleBox.textContent = state.workbenchRoleDraft ? JSON.stringify(state.workbenchRoleDraft, null, 2) : "-";
    const previewBox = byId("fmca-workbench-preview");
    if (previewBox) previewBox.textContent = readableWorkbenchPreview(state.workbenchPreview);
    const resultBox = byId("fmca-workbench-result");
    if (resultBox) resultBox.textContent = state.workbenchResult ? JSON.stringify(state.workbenchResult, null, 2) : "-";
  }


  function renderChannelTokenSettings(settings) {
    const root = byId("fmca-channel-token-settings");
    if (!root) return;
    const tokenSettings = settings.channel_token_settings || {};
    root.innerHTML = channelTokenRows.map(([key, label]) => {
      const row = tokenSettings[key] || {};
      return `
        <label><span>${esc(label)}初次 tokens</span><input data-channel-token="${esc(key)}" data-token-field="initial" type="number" min="64" max="32000" value="${esc(row.initial || "")}"></label>
        <label><span>${esc(label)}重试 tokens</span><input data-channel-token="${esc(key)}" data-token-field="retry" type="number" min="64" max="32000" value="${esc(row.retry || "")}"></label>
      `;
    }).join("");
  }

  function collectChannelTokenSettings() {
    const rows = {};
    document.querySelectorAll("[data-channel-token][data-token-field]").forEach((input) => {
      const key = input.dataset.channelToken || "default";
      const field = input.dataset.tokenField || "initial";
      const value = Number.parseInt(input.value, 10);
      rows[key] = rows[key] || {};
      if (Number.isFinite(value)) rows[key][field] = value;
    });
    return rows;
  }

  function modelRequestPayload() {
    return {
      base_url: byId("fmca-api-base-url").value.trim(),
      api_key: byId("fmca-api-key").value.trim(),
      request_timeout: Number.parseInt(byId("fmca-api-timeout").value, 10) || 120,
    };
  }

  function renderModelMenu() {
    const menu = byId("fmca-model-menu");
    if (!menu) return;
    const currentValue = byId("fmca-api-model").value.trim();
    const models = Array.from(new Set((state.fetchedModels || []).filter(Boolean)));
    menu.innerHTML = "";
    if (!models.length) {
      menu.innerHTML = '<div class="fmca-model-menu-empty">还没有模型列表，先点“拉取模型”。</div>';
      return;
    }
    const ordered = currentValue && !models.includes(currentValue) ? [currentValue, ...models] : models;
    ordered.forEach((modelName) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "fmca-model-menu-item";
      button.textContent = modelName;
      button.addEventListener("click", () => {
        byId("fmca-api-model").value = modelName;
        hideModelMenu();
      });
      menu.appendChild(button);
    });
  }

  function showModelMenu() {
    renderModelMenu();
    byId("fmca-model-menu").hidden = false;
  }

  function hideModelMenu() {
    const menu = byId("fmca-model-menu");
    if (menu) menu.hidden = true;
  }

  function applyApiPreset() {
    const preset = apiPresets[byId("fmca-api-preset").value] || apiPresets.openai;
    byId("fmca-model-source").value = "custom";
    byId("fmca-api-base-url").value = preset.base_url || "";
    if (preset.model) byId("fmca-api-model").value = preset.model;
    setToast(preset.hint || "已填入 API URL。");
  }

  async function fetchModelList() {
    const button = byId("fmca-fetch-models");
    const oldText = button.textContent;
    button.disabled = true;
    button.textContent = "拉取中...";
    setError();
    try {
      const payload = await request("/admin/models", {
        method: "POST",
        body: JSON.stringify(modelRequestPayload()),
      });
      state.fetchedModels = payload.items || [];
      if (payload.preferred_model) byId("fmca-api-model").value = payload.preferred_model;
      renderModelMenu();
      showModelMenu();
      setToast(state.fetchedModels.length ? `已拉取 ${state.fetchedModels.length} 个模型。` : "模型列表为空，可以继续手动填写。");
    } catch (error) {
      setError(`拉取模型失败：${error.message}`);
    } finally {
      button.disabled = false;
      button.textContent = oldText;
    }
  }

  function applySettingsForm(settings) {
    byId("fmca-enabled").checked = Boolean(settings.enabled);
    byId("fmca-show-fab").checked = Boolean(settings.show_floating_button);
    byId("fmca-remember-position").checked = Boolean(settings.remember_position);
    byId("fmca-reply-count").value = settings.reply_count === "1" ? "1" : "1-2";
    byId("fmca-max-tokens").value = settings.max_tokens || 500;
    byId("fmca-recent-limit").value = settings.recent_message_limit || 30;
    const apiConfig = settings.api_config || {};
    byId("fmca-model-source").value = settings.model_source === "custom" ? "custom" : "main";
    byId("fmca-api-base-url").value = apiConfig.base_url || "";
    byId("fmca-api-key").value = "";
    byId("fmca-api-model").value = apiConfig.model || "";
    byId("fmca-api-temp").value = apiConfig.temperature ?? 0.85;
    byId("fmca-api-timeout").value = apiConfig.request_timeout || 120;
    byId("fmca-api-key").placeholder = apiConfig.api_key_configured ? "已保存，留空不修改" : "未配置";
    byId("fmca-role-reply").checked = settings.allow_role_to_role_reply !== false;
    renderChannelTokenSettings(settings);
  }

  function renderSummary() {
    const summary = state.summary || {};
    const settings = summary.settings || {};
    const model = summary.model_status || {};
    setText("fmca-status", settings.enabled ? "已启用" : "未启用");
    setText("fmca-enabled-state", settings.enabled ? "已启用" : "未启用");
    setText("fmca-groups", String(summary.group_count ?? 0));
    setText("fmca-messages", String(summary.message_count ?? 0));
    setText("fmca-roles", String(summary.role_count ?? 0));
    setText("fmca-stickers", String(summary.sticker_count ?? 0));
    setText("fmca-schema", `v${settings.schema_version || 1}`);
    setText("fmca-apps", String(summary.app_count ?? 0));
    setText("fmca-channel-events", String(summary.channel_event_count ?? 0));
    setText("fmca-notifications", String(summary.notification_count ?? 0));
    setText("fmca-data-dir", summary.data_dir || "data/mobile_chat");
    const modelSourceLabel = model.model_source === "custom" ? "小手机独立" : (model.provider === "route_forwarding" ? "路由转发" : "主程序");
    setText("fmca-model-name", model.model ? `${model.model} · ${modelSourceLabel}` : `未配置 · ${modelSourceLabel}`);
    setText("fmca-model-url", model.base_url_configured ? "已配置" : "未配置");
    setText("fmca-model-key", model.api_key_configured ? "已配置（已脱敏）" : "未配置");
    setText("fmca-model-temp", String(model.temperature ?? "-"));
    const latestError = summary.latest_error;
    setText(
      "fmca-latest-error",
      latestError
        ? `${latestError.created_at} · ${latestError.group_name}: ${latestError.content}`
        : "暂无错误记录。",
    );
    renderFacts("fmca-auto-facts", [
      ["自动插话", settings.allow_auto_interject ? "已启用" : "关闭"],
      ["空闲触发", `${settings.auto_behavior?.idle_seconds || 90} 秒`],
      ["间隔", `${settings.auto_behavior?.interval_seconds || 120} 秒`],
      ["每小时上限", `${settings.auto_behavior?.max_generations_per_hour || 6} 次`],
    ]);
    renderFacts("fmca-ui-facts", [
      ["悬浮球", settings.show_floating_button ? "显示" : "隐藏"],
      ["记住位置", settings.remember_position ? "开启" : "关闭"],
      ["悬浮球位置", `right ${settings.floating_position?.right ?? 28}, bottom ${settings.floating_position?.bottom ?? 150}`],
      ["面板位置", `right ${settings.panel_position?.right ?? 28}, bottom ${settings.panel_position?.bottom ?? 92}`],
    ]);
    applySettingsForm(settings);
  }

  async function loadManifest(packId) {
    const manifest = await request(`/admin/sticker-packs/${encodeURIComponent(packId)}/manifest`);
    state.selectedPackId = packId;
    state.manifestRows = manifest.stickers || [];
    renderStickers();
  }

  async function refresh() {
    setError();
    try {
      const [summary, groups, roles, roleAppPools, stickers, automation, promptBlocks, promptPreview, apps, channels, diagnostics, workbench, dataOverview, generationControl] = await Promise.all([
        request("/admin/summary"),
        request("/groups"),
        request("/admin/roles"),
        request("/admin/role-app-pools"),
        request("/admin/sticker-packs"),
        request("/admin/automation"),
        request("/admin/prompt-blocks"),
        request("/admin/prompt-preview?scope=group_chat"),
        request("/admin/apps"),
        request("/admin/channels"),
        request("/admin/diagnostics"),
        request("/admin/workbench"),
        request("/admin/data-overview"),
        request("/admin/generation-control"),
      ]);
      state.summary = summary;
      state.groups = groups.groups || [];
      state.roles = roles.roles || [];
      state.availableRoles = roles.available || [];
      state.user = roles.user || null;
      state.roleAppPools = roleAppPools || null;
      state.stickerPacks = stickers.packs || [];
      state.stickers = stickers.stickers || [];
      state.automation = automation;
      state.promptBlocks = promptBlocks.blocks || [];
      state.promptPreview = promptPreview;
      state.promptScope = promptPreview.scope || summary.settings?.prompt?.last_preview_channel || state.promptScope;
      state.apps = apps.apps || [];
      state.channels = channels.channels || [];
      state.diagnostics = diagnostics.diagnostics || null;
      state.workbench = workbench.workbench || null;
      state.dataOverview = dataOverview.data || null;
      state.generationControl = generationControl.generation_control || null;
      renderSummary();
      renderGroups();
      renderRoles();
      renderRoleGenerator();
      renderStickers();
      renderAutomation();
      renderPromptTools();
      renderApps();
      renderChannels();
      renderDiagnostics();
      renderWorkbench();
      renderDataTools();
      renderGenerationControl();
      const pack = selectedPack();
      if (pack?.manifest_editable && !state.manifestRows.length) {
        await loadManifest(pack.pack_id);
      }
    } catch (error) {
      setText("fmca-status", "读取失败");
      setError(error.message);
    }
  }

  async function saveSettings(event) {
    event.preventDefault();
    setError();
    const payload = {
      enabled: byId("fmca-enabled").checked,
      show_floating_button: byId("fmca-show-fab").checked,
      remember_position: byId("fmca-remember-position").checked,
      reply_count: byId("fmca-reply-count").value,
      max_tokens: Number.parseInt(byId("fmca-max-tokens").value, 10),
      recent_message_limit: Number.parseInt(byId("fmca-recent-limit").value, 10),
      allow_role_to_role_reply: byId("fmca-role-reply").checked,
      channel_token_settings: collectChannelTokenSettings(),
      model_source: byId("fmca-model-source").value === "custom" ? "custom" : "main",
      api_config: {
        base_url: byId("fmca-api-base-url").value.trim(),
        model: byId("fmca-api-model").value.trim(),
        temperature: Number.parseFloat(byId("fmca-api-temp").value),
        request_timeout: Number.parseInt(byId("fmca-api-timeout").value, 10),
      },
    };
    const apiKey = byId("fmca-api-key").value.trim();
    if (apiKey) payload.api_config.api_key = apiKey;
    try {
      await request("/settings", { method: "POST", body: JSON.stringify(payload) });
      await refresh();
      setToast("设置已保存。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function saveGroup(form) {
    const group = selectedGroup();
    if (!group) return;
    const data = new FormData(form);
    const selected = new Set(data.getAll("member").map(String));
    const members = memberCandidates(group).filter((item) => selected.has(item.role_id));
    try {
      await request(`/groups/${encodeURIComponent(group.group_id)}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: data.get("name"),
          description: data.get("description"),
          members,
          reply_count: data.get("reply_count"),
          allow_role_to_role_reply: data.has("allow_role_to_role_reply"),
          allow_auto_interject: data.has("allow_auto_interject"),
        }),
      });
      await refresh();
      setToast("群聊已保存。");
    } catch (error) {
      setError(error.message);
    }
  }

  function roleAppRolesValue(role) {
    const rows = role?.app_roles && typeof role.app_roles === "object" ? role.app_roles : {};
    return Object.entries(rows).map(([appId, values]) => `${appId}: ${Array.isArray(values) ? values.join(", ") : values}`).join("\n");
  }

  function parseRoleAppRoles(text) {
    const result = {};
    String(text || "").split(/\n+/).forEach((line) => {
      const [rawApp, ...rest] = line.split(":");
      const appId = normalizeAppInput(rawApp);
      const values = rest.join(":").split(/[,\uFF0C\u3001\s]+/).map(normalizeRoleUsageInput).filter(Boolean);
      if (appId && values.length) result[appId] = values;
    });
    return result;
  }

  function appScopeValuesFromData(data, name) {
    const seen = new Set();
    return data.getAll(name)
      .flatMap((value) => appScopeToTags(value))
      .filter((item) => {
        if (!item || seen.has(item)) return false;
        seen.add(item);
        return true;
      });
  }

  function roleAppRolesFromForm(form) {
    const result = parseRoleAppRoles(new FormData(form).get("app_roles"));
    form.querySelectorAll("[data-role-app-usage]").forEach((input) => {
      const appId = normalizeAppInput(input.dataset.roleAppUsage || "");
      if (!appId) return;
      const seen = new Set();
      const values = String(input.value || "")
        .split(/[,\uFF0C\u3001\s]+/)
        .map(normalizeRoleUsageInput)
        .filter((item) => {
          if (!item || seen.has(item)) return false;
          seen.add(item);
          return true;
        })
        .slice(0, 8);
      if (values.length) result[appId] = values;
      else delete result[appId];
    });
    return result;
  }

  function handleRoleAppScopeChange(input) {
    if (!input?.checked) return;
    const form = input.closest('form[data-form="role"]');
    if (!form) return;
    const field = input.dataset.roleAppScope || "";
    const opposite = field === "suitable_apps" ? "blocked_apps" : "suitable_apps";
    [...form.querySelectorAll(`[data-role-app-scope="${opposite}"]`)].forEach((peer) => {
      if (peer.value === input.value) peer.checked = false;
    });
  }

  function rolePayloadFrom(form) {
    const data = new FormData(form);
    const blockedApps = appScopeValuesFromData(data, "blocked_apps");
    const blockedSet = new Set(blockedApps);
    const suitableApps = appScopeValuesFromData(data, "suitable_apps").filter((appId) => !blockedSet.has(appId));
    return {
      role_id: data.get("role_id") || undefined,
      display_name: data.get("display_name"),
      aliases: String(data.get("aliases") || "").split(/[,，\n]+/).map((item) => item.trim()).filter(Boolean),
      status: data.get("status"),
      summary: data.get("summary"),
      chat_style: data.get("chat_style"),
      suitable_apps: suitableApps,
      blocked_apps: blockedApps,
      app_roles: roleAppRolesFromForm(form),
      auto_speak_weight: Number.parseFloat(data.get("auto_speak_weight") || "1"),
      enabled: data.has("enabled"),
      sticker_preferences: {
        preferred_tags: textToTags(data.get("preferred_tags")),
        blocked_tags: textToTags(data.get("blocked_tags")),
      },
    };
  }

  async function saveRole(form) {
    const roleId = form.dataset.roleId || "";
    const payload = rolePayloadFrom(form);
    try {
      const result = roleId
        ? await request(`/admin/roles/${encodeURIComponent(roleId)}`, { method: "PATCH", body: JSON.stringify(payload) })
        : await request("/admin/roles", { method: "POST", body: JSON.stringify(payload) });
      state.selectedRoleId = result.role?.role_id || roleId;
      await refresh();
      setToast("角色资料已保存。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function generateRoleDrafts(form) {
    const scrollTop = pageScrollTop();
    const payload = roleGeneratorPayloadFrom(form);
    state.roleGeneratorForm = payload;
    state.roleGeneratorBusy = true;
    renderRoleGeneratorKeepingScroll(scrollTop);
    try {
      const result = await request("/admin/role-generator/draft", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      state.roleGeneratorDrafts = result.drafts || (result.draft ? [result.draft] : []);
      state.roleGeneratorSelectedIndex = 0;
      setToast(state.roleGeneratorDrafts.length ? `已生成 ${state.roleGeneratorDrafts.length} 个草稿。` : "没有生成草稿。");
    } catch (error) {
      setError(error.message);
    } finally {
      state.roleGeneratorBusy = false;
      renderRoleGeneratorKeepingScroll(scrollTop);
    }
  }

  async function extractEventRoleDrafts() {
    const scrollTop = pageScrollTop();
    state.roleGeneratorBusy = true;
    renderRoleGeneratorKeepingScroll(scrollTop);
    try {
      const result = await request("/admin/role-generator/extract-events", {
        method: "POST",
        body: JSON.stringify({ limit: 20 }),
      });
      state.roleGeneratorDrafts = result.drafts || (result.draft ? [result.draft] : []);
      state.roleGeneratorSelectedIndex = 0;
      setToast(state.roleGeneratorDrafts.length ? `已从小手机事件提取 ${state.roleGeneratorDrafts.length} 个候选。` : "没有提取到新的事件候选。");
    } catch (error) {
      setError(error.message);
    } finally {
      state.roleGeneratorBusy = false;
      renderRoleGeneratorKeepingScroll(scrollTop);
    }
  }

  async function extractChatRoleDrafts() {
    const scrollTop = pageScrollTop();
    state.roleGeneratorBusy = true;
    renderRoleGeneratorKeepingScroll(scrollTop);
    try {
      const result = await request("/admin/role-generator/extract-chat", {
        method: "POST",
        body: JSON.stringify({ limit: 20, recent_messages: 160 }),
      });
      state.roleGeneratorDrafts = result.drafts || (result.draft ? [result.draft] : []);
      state.roleGeneratorSelectedIndex = 0;
      setToast(state.roleGeneratorDrafts.length ? `已从主 Chat 提取 ${state.roleGeneratorDrafts.length} 个候选。` : "没有提取到新的主 Chat 候选。");
    } catch (error) {
      setError(error.message);
    } finally {
      state.roleGeneratorBusy = false;
      renderRoleGeneratorKeepingScroll(scrollTop);
    }
  }

  async function saveRoleGeneratorDrafts({ all = false } = {}) {
    const drafts = state.roleGeneratorDrafts || [];
    const selected = drafts[state.roleGeneratorSelectedIndex || 0];
    const roles = all ? drafts : (selected ? [selected] : []);
    if (!roles.length) return;
    const scrollTop = pageScrollTop();
    state.roleGeneratorBusy = true;
    renderRoleGeneratorKeepingScroll(scrollTop);
    try {
      const result = await request("/admin/role-generator/save", {
        method: "POST",
        body: JSON.stringify({ roles }),
      });
      state.roleGeneratorSaved = result.saved || [];
      state.roles = result.roles || state.roles;
      state.availableRoles = result.available || state.availableRoles;
      state.roleGeneratorDrafts = all ? [] : drafts.filter((_, index) => index !== (state.roleGeneratorSelectedIndex || 0));
      state.roleGeneratorSelectedIndex = 0;
      renderRoleGeneratorKeepingScroll(scrollTop);
      renderRoles();
      setToast(`${state.roleGeneratorSaved.length} 个角色已保存。`);
      await refresh();
    } catch (error) {
      setError(error.message);
    } finally {
      state.roleGeneratorBusy = false;
      renderRoleGeneratorKeepingScroll(scrollTop);
    }
  }

  function clearRoleGenerator() {
    const scrollTop = pageScrollTop();
    state.roleGeneratorForm = {};
    state.roleGeneratorDrafts = [];
    state.roleGeneratorSaved = [];
    state.roleGeneratorSelectedIndex = 0;
    state.roleGeneratorBusy = false;
    renderRoleGeneratorKeepingScroll(scrollTop);
  }

  async function saveManifest(form) {
    const packId = form.dataset.packId;
    const data = new FormData(form);
    const stickers = [];
    for (let index = 0; index < state.manifestRows.length; index += 1) {
      stickers.push({
        filename: data.get(`filename_${index}`),
        label: data.get(`label_${index}`),
        tags: textToTags(data.get(`tags_${index}`)),
        description: data.get(`description_${index}`),
      });
    }
    try {
      const result = await request(`/admin/sticker-packs/${encodeURIComponent(packId)}/manifest`, {
        method: "PUT",
        body: JSON.stringify({ stickers }),
      });
      state.manifestRows = result.stickers || [];
      await refresh();
      setToast("Manifest 已保存。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function saveAutomation(form) {
    const data = new FormData(form);
    try {
      await request("/admin/automation", {
        method: "PATCH",
        body: JSON.stringify({
          enabled: data.has("enabled"),
          active_group_only: data.has("active_group_only"),
          idle_seconds: Number.parseInt(data.get("idle_seconds"), 10),
          interval_seconds: Number.parseInt(data.get("interval_seconds"), 10),
          max_rounds_per_session: Number.parseInt(data.get("max_rounds_per_session"), 10),
          max_generations_per_hour: Number.parseInt(data.get("max_generations_per_hour"), 10),
        }),
      });
      await refresh();
      setToast("自动行为已保存。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function savePromptBlocks(form) {
    const data = new FormData(form);
    const blocks = (state.promptBlocks || []).map((block, index) => ({
      block_id: data.get(`block_id_${index}`) || block.block_id,
      label: data.get(`label_${index}`) || block.label,
      order: Number.parseInt(data.get(`order_${index}`), 10),
      locked: data.get(`locked_${index}`) === "1",
      enabled: block.locked ? block.enabled : data.has(`enabled_${index}`),
      scope: textToTags(data.get(`scope_${index}`)),
      content: data.get(`content_${index}`) || "",
    }));
    try {
      const result = await request("/admin/prompt-blocks", { method: "PUT", body: JSON.stringify({ blocks }) });
      state.promptBlocks = result.blocks || [];
      state.promptPreview = await request(`/admin/prompt-preview?scope=${encodeURIComponent(selectedPromptScope())}`);
      renderPromptTools();
      setToast("Prompt blocks 已保存。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function savePromptCustom(form) {
    const data = new FormData(form);
    const scope = promptScopes.some(([value]) => value === data.get("scope")) ? String(data.get("scope")) : "group_chat";
    state.promptScope = scope;
    const current = currentPromptSettings();
    const promptMode = String(data.get("prompt_mode") || "default");
    const customPrompt = promptMode === "override" ? stripLockedPromptContract(data.get("custom_prompt")) : String(data.get("custom_prompt") || "");
    const custom_prompts = { ...(current.custom_prompts || {}), [scope]: customPrompt };
    try {
      const result = await request("/settings", {
        method: "POST",
        body: JSON.stringify({
          prompt: {
            ...current,
            use_custom_prompt: promptMode !== "default",
            prompt_mode: promptMode,
            append_json_contract: true,
            custom_prompts,
            last_preview_channel: scope,
          },
        }),
      });
      if (state.summary) state.summary.settings = result.settings || state.summary.settings;
      state.promptPreview = await request(`/admin/prompt-preview?scope=${encodeURIComponent(scope)}`);
      renderPromptTools();
      setToast("提示词已保存。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function saveApps() {
    const apps = (state.apps || []).map((app) => ({
      ...app,
      enabled: Boolean(document.querySelector(`[data-app-enabled="${CSS.escape(app.app_id)}"]`)?.checked),
      order: Number.parseInt(document.querySelector(`[data-app-order="${CSS.escape(app.app_id)}"]`)?.value || app.order || 0, 10),
      subtitle: document.querySelector(`[data-app-subtitle="${CSS.escape(app.app_id)}"]`)?.value || app.subtitle || "",
    }));
    try {
      const result = await request("/admin/apps", { method: "PUT", body: JSON.stringify({ apps }) });
      state.apps = result.apps || [];
      renderApps();
      setToast("轻应用注册表已保存。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function refreshPromptPreview(scope = selectedPromptScope()) {
    try {
      state.promptScope = scope;
      state.promptPreview = await request(`/admin/prompt-preview?scope=${encodeURIComponent(scope)}`);
      if (state.summary?.settings?.prompt && state.promptPreview?.settings) {
        state.summary.settings.prompt = state.promptPreview.settings;
      }
      renderPromptTools();
      setToast("Prompt 预览已刷新。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function clearCurrentPrompt() {
    const textarea = byId("fmca-custom-prompt");
    if (textarea) textarea.value = "";
    const form = textarea?.closest("form");
    if (form) await savePromptCustom(form);
  }

  function loadDefaultPromptIntoEditor() {
    const textarea = byId("fmca-custom-prompt");
    const mode = byId("fmca-prompt-mode");
    if (!textarea) return;
    textarea.value = editableDefaultPrompt();
    if (mode) mode.value = "override";
    setToast("\u5df2\u8f7d\u5165\u9ed8\u8ba4\u4e3b\u4f53 Prompt\uff0cJSON \u8f93\u51fa\u5951\u7ea6\u4f1a\u5728\u9884\u89c8\u4e2d\u5355\u72ec\u663e\u793a\u5e76\u81ea\u52a8\u8ffd\u52a0\u3002");
  }

  function handlePromptModeChange(select) {
    const textarea = byId("fmca-custom-prompt");
    if (!textarea) return;
    if (select.value === "override" && !textarea.value.trim()) {
      textarea.value = editableDefaultPrompt();
      setToast("\u5df2\u81ea\u52a8\u8f7d\u5165\u9ed8\u8ba4\u4e3b\u4f53 Prompt\uff0c\u53ef\u76f4\u63a5\u5728\u6587\u672c\u6846\u5185\u4fee\u6539\u3002");
    }
  }





  async function runPromptTest(form) {
    const data = new FormData(form);
    const mode = String(data.get("mode") || "dry-run");
    const user_input = String(data.get("user_input") || "");
    state.promptTestBusy = true;
    renderPromptTools();
    try {
      const result = await request("/admin/prompt-test", {
        method: "POST",
        body: JSON.stringify({ scope: selectedPromptScope(), mode, user_input }),
      });
      state.promptTestResult = result;
      renderPromptTools();
      setToast(mode === "real" ? "真实模型 Prompt 测试完成（save=false）。" : "Prompt 测试完成。");
    } catch (error) {
      setError(error.message);
    } finally {
      state.promptTestBusy = false;
      renderPromptTools();
    }
  }

  async function saveGenerationControl(form) {
    const data = new FormData(form);
    const app_enabled = {};
    ["group_chat", "feed", "forum", "mail", "diary", "calendar", "live", "phone", "workbench"].forEach((id) => {
      app_enabled[id] = data.has(`app_${id}`);
    });
    try {
      const result = await request("/admin/generation-control", {
        method: "PUT",
        body: JSON.stringify({
          paused: data.has("paused"),
          hourly_limit: Number.parseInt(data.get("hourly_limit"), 10),
          retry_limit: Number.parseInt(data.get("retry_limit"), 10),
          cost_notice: data.has("cost_notice"),
          app_enabled,
        }),
      });
      state.generationControl = result.generation_control || null;
      renderGenerationControl();
      await refreshDiagnostics();
      setToast("生成控制已保存。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function setGenerationPaused(paused) {
    const current = state.generationControl?.settings || state.summary?.settings?.generation_control || {};
    const result = await request("/admin/generation-control", {
      method: "PUT",
      body: JSON.stringify({ ...current, paused }),
    });
    state.generationControl = result.generation_control || null;
    renderGenerationControl();
    await refreshDiagnostics();
    setToast(paused ? "已暂停全部生成。" : "已恢复全部生成。");
  }

  async function refreshDataOverview() {
    try {
      const result = await request("/admin/data-overview");
      state.dataOverview = result.data || {};
      renderDataTools();
      setToast("数据概览已刷新。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function runDataAction(action, channelId = "", eventId = "", sessionId = "") {
    const actionMap = {
      "refresh-data-overview": ["/admin/data-overview", "GET", "数据概览已刷新。"],
      "notifications-read-all": ["/admin/data/notifications/read-all", "POST", "通知已全部标记为已读。"],
      "clear-invalid-notifications": ["/admin/data/notifications/clear-invalid", "POST", "无效通知已清理。"],
      "prune-empty-phone": ["/admin/data/phone/prune-empty", "POST", "空通话记录已清理。"],
      "prune-ended-phone": ["/admin/data/phone/prune-ended", "POST", "已结束通话记录已清理。"],
      "clear-all-channel-test-events": ["/admin/data/channels/clear-test-events", "POST", "全部测试/fallback 内容已清理。"],
      "clear-channel-test-events": [`/admin/data/channels/${encodeURIComponent(channelId)}/clear-test-events`, "POST", "测试/fallback 内容已清理。"],
      "delete-channel-event": [`/admin/data/channels/${encodeURIComponent(channelId)}/events/${encodeURIComponent(eventId || "")}`, "DELETE", "频道内容已删除。"],
      "delete-phone-session": [`/admin/data/phone/sessions/${encodeURIComponent(sessionId || "")}`, "DELETE", "通话记录已删除。"],
    };
    const config = actionMap[action];
    if (!config) return;
    if (action !== "refresh-data-overview" && !window.confirm("这个操作会修改小手机运行数据，确定继续？")) return;
    const [url, method, message] = config;
    const result = await request(url, method === "GET" ? {} : { method });
    state.dataOverview = result.data || (await request("/admin/data-overview")).data || {};
    renderDataTools();
    await refreshDiagnostics();
    setToast(message);
  }

  async function previewWorkbenchScope(scope) {
    try {
      const preview = await request(`/admin/prompt-preview?scope=${encodeURIComponent(scope || "group_chat")}`);
      const schema = (state.workbench?.schemas || []).find((item) => item.type === preview.scope) || null;
      state.workbenchPreview = {
        scope: preview.scope,
        blocks: (preview.blocks || []).map((item) => item.block_id),
        schema,
        context_preview: preview.context_preview,
        assembled_prompt: preview.assembled_prompt,
      };
      renderWorkbench();
      setToast("工作台预览已刷新。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function draftWorkbenchRole(form) {
    const data = new FormData(form);
    try {
      const result = await request("/admin/workbench/role-draft", {
        method: "POST",
        body: JSON.stringify({
          role_id: data.get("role_id") || "",
          display_name: data.get("role_id") || "",
          source: "admin_workbench",
        }),
      });
      state.workbenchRoleDraft = result.draft || null;
      renderWorkbench();
      setToast("角色草稿已生成。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function generateWorkbench(form) {
    const data = new FormData(form);
    const payload = {
      scope: data.get("scope") || "feed",
      mode: data.get("mode") || "mock",
      channel_id: data.get("channel_id") || "",
      role_id: data.get("role_id") || "",
      user_input: data.get("user_input") || "",
      save: data.has("save"),
    };
    if (!window.confirm("这个操作会修改小手机运行数据，确定继续？")) return;
    try {
      const result = await request("/admin/workbench/generate", { method: "POST", body: JSON.stringify(payload) });
      state.workbenchResult = result;
      renderWorkbench();
      setToast("工作台生成测试完成。");
      if (result.saved) await refresh();
    } catch (error) {
      setError(error.message);
    }
  }

  async function refreshDiagnostics() {
    try {
      const result = await request("/admin/diagnostics");
      state.diagnostics = result.diagnostics || {};
      renderDiagnostics();
      setToast("诊断已刷新。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function seedChannel(channelId) {
    const channel = state.channels.find((item) => item.channel_id === channelId);
    if (!channel) return;
    if (!window.confirm("这个操作会修改小手机运行数据，确定继续？")) return;
    try {
      await request("/admin/seed-channel", {
        method: "POST",
        body: JSON.stringify({ channel_id: channelId, count: channel.seed_count || 5, force: true }),
      });
      await refresh();
      setToast("频道内容已生成。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function testAutomation(form) {
    const data = new FormData(form);
    const groupId = String(data.get("group_id") || "");
    if (!groupId) return;
    if (!window.confirm("这个操作会修改小手机运行数据，确定继续？")) return;
    try {
      await request("/admin/automation/test-once", {
        method: "POST",
        body: JSON.stringify({ group_id: groupId }),
      });
      await refresh();
      setToast("测试续聊已完成。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function resetPosition() {
    setError();
    try {
      await request("/settings", {
        method: "POST",
        body: JSON.stringify({
          floating_position: { right: 28, bottom: 150 },
          panel_position: { right: 28, bottom: 92 },
        }),
      });
      await refresh();
      setToast("位置已复位。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function clearGroups() {
    if (!window.confirm("这个操作会修改小手机运行数据，确定继续？")) return;
    setError();
    try {
      await request("/groups", { method: "DELETE" });
      await refresh();
      setToast("群聊记录已清空。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function onClick(event) {
    const button = event.target.closest("[data-action], #fmca-sync-current-card, #fmca-import-group-roles");
    if (!button) return;
    setError();
    try {
      if (button.id === "fmca-sync-current-card") {
        await request("/admin/roles/sync-current-card", { method: "POST" });
        await refresh();
        setToast("已同步当前角色卡。");
        return;
      }
      if (button.id === "fmca-import-group-roles") {
        await request("/admin/roles/import-from-groups", { method: "POST" });
        await refresh();
        setToast("已从群聊导入角色。");
        return;
      }
      const action = button.dataset.action;
      if (action === "edit-group") {
        state.selectedGroupId = button.dataset.groupId || "";
        renderGroups();
      }
      if (action === "delete-group") {
    if (!window.confirm("这个操作会修改小手机运行数据，确定继续？")) return;
        await request(`/groups/${encodeURIComponent(button.dataset.groupId || "")}`, { method: "DELETE" });
        state.selectedGroupId = "";
        await refresh();
        setToast("群聊已删除。");
      }
      if (action === "edit-role") {
        state.selectedRoleId = button.dataset.roleId || "";
        renderRoles();
      }
      if (action === "new-role") {
        state.selectedRoleId = "";
        renderRoles();
      }
      if (action === "disable-role") {
    if (!window.confirm("这个操作会修改小手机运行数据，确定继续？")) return;
        await request(`/admin/roles/${encodeURIComponent(button.dataset.roleId || "")}`, { method: "DELETE" });
        await refresh();
        setToast("角色已禁用。");
      }
      if (action === "restore-role") {
        await request(`/admin/roles/${encodeURIComponent(button.dataset.roleId || "")}/restore`, { method: "POST" });
        await refresh();
        setToast("角色已恢复。");
      }
      if (action === "delete-role") {
        const roleId = button.dataset.roleId || "";
        if (!window.confirm(`确定从小手机角色库永久删除“${roleId}”？这不会删除主角色卡。`)) return;
        await request(`/admin/roles/${encodeURIComponent(roleId)}/purge`, { method: "DELETE" });
        state.selectedRoleId = "";
        await refresh();
        setToast("角色已删除。");
      }
      if (action === "select-role-generator-draft") {
        const scrollTop = pageScrollTop();
        const index = Number.parseInt(button.dataset.index || "0", 10);
        state.roleGeneratorSelectedIndex = Number.isFinite(index) ? index : 0;
        renderRoleGeneratorKeepingScroll(scrollTop);
      }
      if (action === "save-role-generator-selected") {
        await saveRoleGeneratorDrafts({ all: false });
      }
      if (action === "save-role-generator-all") {
        await saveRoleGeneratorDrafts({ all: true });
      }
      if (action === "clear-role-generator") {
        clearRoleGenerator();
      }
      if (action === "extract-event-role-drafts") {
        void extractEventRoleDrafts();
      }
      if (action === "extract-chat-role-drafts") {
        void extractChatRoleDrafts();
      }
      if (action === "edit-pack") {
        state.manifestRows = [];
        const packId = button.dataset.packId || "";
        const pack = state.stickerPacks.find((item) => item.pack_id === packId);
        state.selectedPackId = packId;
        if (pack?.manifest_editable) {
          await loadManifest(packId);
        } else {
          renderStickers();
        }
      }
      if (action === "scan-pack") {
        const result = await request(`/admin/sticker-packs/${encodeURIComponent(button.dataset.packId || "")}/scan`, { method: "POST" });
        state.manifestRows = result.stickers || [];
        renderStickerEditor();
        setToast("表情包已重扫。");
      }
      if (action === "pause-automation") {
        await request("/admin/automation/pause-all", { method: "POST" });
        await refresh();
        setToast("自动行为已暂停。");
      }
      if (action === "refresh-prompt-preview") {
        await refreshPromptPreview();
      }
      if (action === "load-default-prompt") {
        loadDefaultPromptIntoEditor();
      }
      if (action === "clear-current-prompt") {
        if (!window.confirm("确定清空当前范围的自定义提示词？")) return;
        await clearCurrentPrompt();
      }
      if (action === "clear-prompt-test") {
        state.promptTestResult = null;
        renderPromptTools();
        setToast("Prompt 测试结果已清空。");
      }
      if (action === "reset-prompt-blocks") {
    if (!window.confirm("这个操作会修改小手机运行数据，确定继续？")) return;
        const result = await request("/admin/prompt-blocks/reset", { method: "POST" });
        state.promptBlocks = result.blocks || [];
        await refreshPromptPreview();
      }
      if (action === "filter-role-app") {
        state.roleAppFilter = button.dataset.appId || "";
        renderRoles();
        setToast(state.roleAppFilter ? "\u5df2\u6309 App \u89d2\u8272\u6c60\u7b5b\u9009\u89d2\u8272\u5217\u8868\u3002" : "\u5df2\u663e\u793a\u5168\u90e8\u89d2\u8272\u3002");
      }
      if (action === "save-apps") {
        await saveApps();
      }
      if (action === "reset-apps") {
    if (!window.confirm("这个操作会修改小手机运行数据，确定继续？")) return;
        const result = await request("/admin/apps/reset", { method: "POST" });
        state.apps = result.apps || [];
        renderApps();
        setToast("轻应用已重置。");
      }
      if (action === "seed-channel") {
        await seedChannel(button.dataset.channelId || "");
      }
      if (action === "refresh-diagnostics") {
        await refreshDiagnostics();
      }
      if (action === "workbench-preview") {
        await previewWorkbenchScope(button.dataset.scope || "group_chat");
      }
      if (action === "reset-generation-guard") {
        const result = await request("/admin/generation-guard/reset", { method: "POST" });
        state.diagnostics = { ...(state.diagnostics || {}), generation_state: result.state };
        await refreshDiagnostics();
      }
      if (["refresh-data-overview", "notifications-read-all", "clear-invalid-notifications", "prune-empty-phone", "prune-ended-phone", "clear-all-channel-test-events", "clear-channel-test-events", "delete-channel-event", "delete-phone-session"].includes(action)) {
        await runDataAction(action, button.dataset.channelId || "", button.dataset.eventId || "", button.dataset.sessionId || "");
      }
      if (action === "pause-generation-all") {
        await setGenerationPaused(true);
      }
      if (action === "resume-generation-all") {
        await setGenerationPaused(false);
      }
    } catch (error) {
      setError(error.message);
    }
  }

  function onSubmit(event) {
    const form = event.target.closest("form[data-form]");
    if (!form) return;
    event.preventDefault();
    setError();
    if (form.dataset.form === "group") void saveGroup(form);
    if (form.dataset.form === "role") void saveRole(form);
    if (form.dataset.form === "role-generator") void generateRoleDrafts(form);
    if (form.dataset.form === "manifest") void saveManifest(form);
    if (form.dataset.form === "automation") void saveAutomation(form);
    if (form.dataset.form === "automation-test") void testAutomation(form);
    if (form.dataset.form === "prompt-custom") void savePromptCustom(form);
    if (form.dataset.form === "prompt-blocks") void savePromptBlocks(form);
    if (form.dataset.form === "prompt-test") void runPromptTest(form);
    if (form.dataset.form === "workbench-role-draft") void draftWorkbenchRole(form);
    if (form.dataset.form === "workbench-generate") void generateWorkbench(form);
    if (form.dataset.form === "generation-control") void saveGenerationControl(form);
  }

  function onInput(event) {
    const field = event.target.closest("[data-role-generator-draft-field]");
    if (!field) return;
    const index = Number.parseInt(field.dataset.index || String(state.roleGeneratorSelectedIndex || 0), 10);
    updateRoleGeneratorDraftField(Number.isFinite(index) ? index : 0, field.dataset.roleGeneratorDraftField || "", field.value);
  }

  function onChange(event) {
    const promptScope = event.target.closest("#fmca-prompt-scope");
    if (promptScope) {
      state.promptScope = promptScope.value || "group_chat";
      void refreshPromptPreview(state.promptScope);
      return;
    }
    const promptMode = event.target.closest("#fmca-prompt-mode");
    if (promptMode) {
      handlePromptModeChange(promptMode);
      return;
    }
    const roleAppScope = event.target.closest("[data-role-app-scope]");
    if (roleAppScope) {
      handleRoleAppScopeChange(roleAppScope);
      return;
    }
    const scope = event.target.closest("[data-role-generator-draft-scope]");
    if (!scope) return;
    const index = Number.parseInt(scope.dataset.index || String(state.roleGeneratorSelectedIndex || 0), 10);
    updateRoleGeneratorDraftScope(Number.isFinite(index) ? index : 0, scope.dataset.roleGeneratorDraftScope || "");
  }

  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => setTab(button.dataset.tab));
  });
  byId("fmca-refresh").addEventListener("click", refresh);
  byId("fmca-back-chat")?.addEventListener("click", backToChat);
  byId("fmca-settings-form").addEventListener("submit", saveSettings);
  byId("fmca-api-settings-form")?.addEventListener("submit", saveSettings);
  byId("fmca-apply-api-preset")?.addEventListener("click", applyApiPreset);
  byId("fmca-fetch-models")?.addEventListener("click", () => { void fetchModelList(); });
  byId("fmca-toggle-model-menu")?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    const menu = byId("fmca-model-menu");
    if (menu.hidden) {
      showModelMenu();
    } else {
      hideModelMenu();
    }
  });
  byId("fmca-reset-form").addEventListener("click", () => {
    if (state.summary?.settings) applySettingsForm(state.summary.settings);
  });
  byId("fmca-reset-api-form")?.addEventListener("click", () => {
    if (state.summary?.settings) applySettingsForm(state.summary.settings);
  });
  byId("fmca-reset-position").addEventListener("click", resetPosition);
  byId("fmca-clear").addEventListener("click", clearGroups);
  byId("fmca-clear-data").addEventListener("click", clearGroups);
  document.addEventListener("click", (event) => { void onClick(event); });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".fmca-model-combo")) hideModelMenu();
  });
  document.addEventListener("submit", onSubmit);
  document.addEventListener("input", onInput);
  document.addEventListener("change", onChange);

  window.addEventListener("hashchange", () => setTab(window.location.hash.slice(1)));
  setTab(window.location.hash.slice(1) || "overview");
  void refresh();
})();
