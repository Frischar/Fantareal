(() => {
  "use strict";

  const script = document.currentScript;
  const scriptUrl = script && script.src ? script.src : "";
  const staticIndex = scriptUrl.indexOf("/static/");
  const modBase = staticIndex >= 0 ? scriptUrl.slice(0, staticIndex) : "/mods/mobile-chat/app";
  const apiBase = `${modBase}/api`;
  const unreadKey = "fantareal-mobile-chat-unread";
  const automationLockKey = "fantareal-mobile-chat-automation-lock";
  const automationHistoryKey = "fantareal-mobile-chat-automation-history";
  const automationOwner = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
  const fallbackStickerIds = ["happy", "sweat", "stare", "shy", "heart", "cry"];
  const fallbackStickers = fallbackStickerIds.map((id) => ({
    id,
    type: "builtin",
    pack_id: "default",
    pack_label: "默认",
    label: id,
  }));
  const icons = {
    back: '<svg viewBox="0 0 24 24"><path d="m15 18-6-6 6-6"/></svg>',
    chevron: '<svg viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg>',
    close: '<svg viewBox="0 0 24 24"><path d="M18 6 6 18M6 6l12 12"/></svg>',
    download: '<svg viewBox="0 0 24 24"><path d="M12 3v12m0 0 4-4m-4 4-4-4M5 19h14"/></svg>',
    import: '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M7 9h10M7 13h6m3 3 2 2 3-3"/></svg>',
    bell: '<svg viewBox="0 0 24 24"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 7-3 7h18s-3 0-3-7"/><path d="M10 19a2 2 0 0 0 4 0"/></svg>',
    calendar: '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="3"/><path d="M8 2v6m8-6v6M3 10h18"/></svg>',
    diary: '<svg viewBox="0 0 24 24"><path d="M6 3h11a2 2 0 0 1 2 2v16H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"/><path d="M8 7h8M8 11h6"/></svg>',
    forum: '<svg viewBox="0 0 24 24"><path d="M4 5h16v10H7l-3 3V5Z"/><path d="M8 9h8m-8 3h5"/></svg>',
    mail: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="m4 7 8 6 8-6"/></svg>',
    message: '<svg viewBox="0 0 24 24"><path d="M5 18.5A8 8 0 1 1 8.2 21L4 22l1-3.5Z"/><path d="M8 12h.01M12 12h.01M16 12h.01"/></svg>',
    more: '<svg viewBox="0 0 24 24"><path d="M6 12h.01M12 12h.01M18 12h.01"/></svg>',
    phone: '<svg viewBox="0 0 24 24"><rect x="6" y="2.5" width="12" height="19" rx="3"/><path d="M10 5h4m-2 13.5h.01"/></svg>',
    plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>',
    refresh: '<svg viewBox="0 0 24 24"><path d="M20 11a8 8 0 0 0-14.9-3M4 4v4h4m-4 5a8 8 0 0 0 14.9 3M20 20v-4h-4"/></svg>',
    settings: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.86 2.86-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6v.08h-4V20a1.7 1.7 0 0 0-1-.6 1.7 1.7 0 0 0-1.88.34l-.06.06-2.86-2.86.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-.6-1h-.08v-4H4a1.7 1.7 0 0 0 .6-1 1.7 1.7 0 0 0-.34-1.88l-.06-.06L7.06 4.2l.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-.6v-.08h4V4a1.7 1.7 0 0 0 1 .6 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.86 2.86-.06.06A1.7 1.7 0 0 0 19.4 9a1.7 1.7 0 0 0 .6 1h.08v4H20a1.7 1.7 0 0 0-.6 1Z"/></svg>',
    smile: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M8.5 10h.01m6.99 0h.01M8 14a5 5 0 0 0 8 0"/></svg>',
    spark: '<svg viewBox="0 0 24 24"><path d="M12 2l1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z"/></svg>',
    trash: '<svg viewBox="0 0 24 24"><path d="M4 7h16m-10 4v6m4-6v6M9 7l1-3h4l1 3m3 0-1 14H7L6 7"/></svg>',
    users: '<svg viewBox="0 0 24 24"><path d="M16 20v-1a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v1m7-9a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm13 9v-1a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
  };
  const defaults = {
    enabled: true,
    show_floating_button: true,
    remember_position: true,
    floating_position: { right: 28, bottom: 150 },
    panel_position: { right: 28, bottom: 92 },
  };
  const state = {
    settings: defaults,
    groups: [],
    messages: [],
    roles: [],
    user: null,
    apps: [],
    channels: [],
    channelEvents: {},
    currentChannelId: "",
    notifications: [],
    phoneSessions: [],
    phoneRoles: [],
    currentPhoneRoleId: "",
    currentPhoneSessionId: "",
    currentGroupId: "",
    open: false,
    page: "home",
    loading: false,
    generating: false,
    stickers: fallbackStickers,
    stickerPacks: [],
    showStickers: false,
    showExtensions: false,
    error: "",
    unread: Number.parseInt(localStorage.getItem(unreadKey) || "0", 10) || 0,
    lastActivityAt: Date.now(),
    lastAutomationAt: 0,
    automationRounds: 0,
  };
  let root = null;
  let fabDrag = null;
  let panelDrag = null;
  let suppressFabClickUntil = 0;
  let automationTimer = 0;
  let sidebarSafeLeftCache = { value: 8, width: 0, height: 0, time: 0 };

  function esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function safeNumber(value, fallback) {
    const parsed = Number.parseInt(value, 10);
    const viewportLimit = Math.max(3200, (window.innerWidth || 0) + (window.innerHeight || 0));
    return Number.isFinite(parsed) ? Math.max(0, Math.min(viewportLimit, parsed)) : fallback;
  }

  function icon(name) {
    return `<span class="fmcp-glyph" aria-hidden="true">${icons[name] || ""}</span>`;
  }

  function availableStickers() {
    return Array.isArray(state.stickers) && state.stickers.length ? state.stickers : fallbackStickers;
  }

  function stickerById(stickerId) {
    return availableStickers().find((item) => item.id === stickerId) || {
      id: stickerId,
      type: "builtin",
      pack_id: "unknown",
      pack_label: "贴纸",
      label: stickerId,
    };
  }

  function stickerUrl(sticker) {
    if (!sticker || sticker.type !== "image") return "";
    if (sticker.url) return sticker.url;
    if (sticker.url_path) return `${apiBase}${sticker.url_path}`;
    if (sticker.pack_id && sticker.filename) {
      return `${apiBase}/stickers/${encodeURIComponent(sticker.pack_id)}/${encodeURIComponent(sticker.filename)}`;
    }
    return "";
  }

  function stickerVisualMarkup(sticker) {
    const imageUrl = stickerUrl(sticker);
    if (imageUrl) {
      return `<img class="fmcp-sticker-image" src="${esc(imageUrl)}" alt="${esc(sticker.label || sticker.id)}" loading="lazy">`;
    }
    return `<span class="fmcp-sticker-art">${icon("smile")}</span>`;
  }

  function stickerButtonMarkup(sticker) {
    const imageClass = sticker.type === "image" ? " is-image" : "";
    const title = [sticker.pack_label || "贴纸", sticker.label || sticker.id, (sticker.tags || []).join(", ")]
      .filter(Boolean)
      .join(" · ");
    return `
      <button class="fmcp-sticker-option${imageClass}" type="button" data-action="send-sticker" data-sticker-id="${esc(sticker.id)}" title="${esc(title)}">
        ${stickerVisualMarkup(sticker)}
        <span>${esc(sticker.label || sticker.id)}</span>
      </button>
    `;
  }

  function avatarMarkup(member, extraClass = "") {
    const avatar = String(member && member.avatar ? member.avatar : "");
    const name = String(member && member.name ? member.name : "?").trim();
    const fallback = esc(name.slice(0, 1) || "?");
    return `
      <span class="fmcp-avatar ${extraClass}" aria-hidden="true">
        ${avatar.startsWith("/") ? `<img src="${esc(avatar)}" alt="">` : `<span>${fallback}</span>`}
      </span>
    `;
  }

  function groupAvatarMarkup(group, extraClass = "") {
    const member = group && Array.isArray(group.members)
      ? group.members.find((item) => item.type === "character")
      : null;
    return avatarMarkup(member || { name: group && group.name ? group.name : "群" }, extraClass);
  }

  function currentGroup() {
    return state.groups.find((item) => item.group_id === state.currentGroupId) || null;
  }

  function setUnread(value) {
    state.unread = Math.max(0, Number.parseInt(value, 10) || 0);
    localStorage.setItem(unreadKey, String(state.unread));
  }

  function touchActivity() {
    state.lastActivityAt = Date.now();
  }

  function autoBehavior() {
    const settings = state.settings || defaults;
    return settings.auto_behavior || {};
  }

  function automationHistory() {
    try {
      const rows = JSON.parse(localStorage.getItem(automationHistoryKey) || "[]");
      return Array.isArray(rows) ? rows.filter((item) => Number.isFinite(item)) : [];
    } catch {
      return [];
    }
  }

  function recordAutomationGeneration() {
    const now = Date.now();
    const oneHourAgo = now - 60 * 60 * 1000;
    const rows = automationHistory().filter((item) => item > oneHourAgo);
    rows.push(now);
    localStorage.setItem(automationHistoryKey, JSON.stringify(rows.slice(-80)));
  }

  function hourlyAutomationCount() {
    const oneHourAgo = Date.now() - 60 * 60 * 1000;
    return automationHistory().filter((item) => item > oneHourAgo).length;
  }

  function currentGroupAllowsAutomation() {
    const group = currentGroup();
    return Boolean(group && group.allow_auto_interject);
  }

  function automationCanRun() {
    const behavior = autoBehavior();
    const settings = state.settings || defaults;
    if (!settings.enabled || !settings.allow_auto_interject || behavior.enabled !== true || behavior.paused) return false;
    if (!state.open || state.page !== "chat" || !state.currentGroupId || state.generating) return false;
    if (!currentGroupAllowsAutomation()) return false;
    if (behavior.active_group_only !== false && document.visibilityState === "hidden") return false;
    const now = Date.now();
    const idleMs = Math.max(15, Number(behavior.idle_seconds || 90)) * 1000;
    const intervalMs = Math.max(15, Number(behavior.interval_seconds || 120)) * 1000;
    if (now - state.lastActivityAt < idleMs) return false;
    if (now - state.lastAutomationAt < intervalMs) return false;
    if (state.automationRounds >= Math.max(1, Number(behavior.max_rounds_per_session || 3))) return false;
    if (hourlyAutomationCount() >= Math.max(1, Number(behavior.max_generations_per_hour || 6))) return false;
    return true;
  }

  function acquireAutomationLock(groupId) {
    const now = Date.now();
    try {
      const current = JSON.parse(localStorage.getItem(automationLockKey) || "null");
      if (current && current.expires_at > now && current.group_id === groupId && current.owner !== automationOwner) {
        return false;
      }
      localStorage.setItem(automationLockKey, JSON.stringify({
        owner: automationOwner,
        group_id: groupId,
        expires_at: now + 90 * 1000,
      }));
      return true;
    } catch {
      return true;
    }
  }

  function releaseAutomationLock(groupId) {
    try {
      const current = JSON.parse(localStorage.getItem(automationLockKey) || "null");
      if (current && current.owner === automationOwner && current.group_id === groupId) {
        localStorage.removeItem(automationLockKey);
      }
    } catch {
      localStorage.removeItem(automationLockKey);
    }
  }

  async function runAutomationTick() {
    if (!automationCanRun()) return;
    const groupId = state.currentGroupId;
    if (!acquireAutomationLock(groupId)) return;
    state.lastAutomationAt = Date.now();
    state.automationRounds += 1;
    recordAutomationGeneration();
    try {
      await continueChat({ automated: true });
    } finally {
      releaseAutomationLock(groupId);
    }
  }

  function restartAutomationTimer() {
    if (automationTimer) window.clearInterval(automationTimer);
    automationTimer = window.setInterval(() => {
      void runAutomationTick();
    }, 5000);
  }

  async function request(path, options = {}) {
    const response = await fetch(`${apiBase}${path}`, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(payload.error || payload.detail || `请求失败 (${response.status})`);
      error.payload = payload;
      throw error;
    }
    return payload;
  }

  function pageTitle() {
    if (state.page === "home") return ["小手机", "应用桌面"];
    if (state.page === "create") return ["创建群聊", "从当前角色卡选择成员"];
    if (state.page === "settings") return ["详细设置", "小手机偏好"];
    if (state.page === "stickers") return ["贴纸包", "默认表情资源"];
    if (state.page === "notifications") return ["通知", `${state.notifications.filter((item) => !item.read).length} 条未读`];
    if (state.page === "phone") return ["电话", "模拟通话 RP"];
    if (state.page.startsWith("channel-")) {
      const channel = state.channels.find((item) => item.channel_id === state.currentChannelId);
      return [channel ? channel.label : "轻应用", channel ? channel.description || channel.type : "频道内容"];
    }
    if (state.page === "chat") {
      const group = currentGroup();
      return [group ? group.name : "群聊", group ? `${group.members.length} 人在线` : "读取中"];
    }
    return ["口袋群聊", "小手机"];
  }

  function panelStyle() {
    const settings = state.settings || defaults;
    const floating = effectiveFloatingPosition(settings.floating_position);
    const panel = effectivePanelPosition(settings.panel_position);
    return [
      `--fmcp-fab-right:${safeNumber(floating.right, 28)}px`,
      `--fmcp-fab-bottom:${safeNumber(floating.bottom, 150)}px`,
      `--fmcp-panel-right:${safeNumber(panel.right, 28)}px`,
      `--fmcp-panel-bottom:${safeNumber(panel.bottom, 92)}px`,
    ].join(";");
  }

  function errorMarkup() {
    return state.error ? `<div class="fmcp-error">${esc(state.error)}</div>` : "";
  }

  function headerMarkup() {
    const [title, subtitle] = pageTitle();
    const showBack = state.page !== "home";
    const group = currentGroup();
    const isChat = state.page === "chat";
    return `
      <header class="fmcp-header">
        ${showBack
          ? `<button class="fmcp-icon-btn fmcp-header-action" type="button" data-action="back" aria-label="返回">${icon("back")}</button>`
          : `<span class="fmcp-device-mark">${icon("phone")}</span>`}
        ${isChat ? groupAvatarMarkup(group, "fmcp-header-avatar") : ""}
        <div class="fmcp-heading">
          <div class="fmcp-title">${esc(title)}</div>
          <div class="fmcp-subtitle">${isChat ? '<span class="fmcp-online-dot"></span>' : ""}${esc(subtitle)}</div>
        </div>
        ${state.page === "groups" ? `<button class="fmcp-icon-btn fmcp-header-action" type="button" data-action="settings" aria-label="设置">${icon("settings")}</button>` : ""}
        <button class="fmcp-icon-btn fmcp-header-action" type="button" data-action="close" aria-label="关闭">${icon("close")}</button>
      </header>
    `;
  }

  function homeMarkup() {
    const fallbackApps = [
      { app_id: "group_chat", label: "口袋群聊", subtitle: "角色卡群聊", icon: "message", page: "groups" },
      { app_id: "settings", label: "详细设置", subtitle: "偏好与模型", icon: "settings", page: "settings" },
      { app_id: "stickers", label: "贴纸包", subtitle: "内置资源", icon: "smile", page: "stickers" },
    ];
    const apps = Array.isArray(state.apps) && state.apps.length ? state.apps : fallbackApps;
    return `
      <div class="fmcp-home">
        <div class="fmcp-home-intro">
          <strong>我的小手机</strong>
          <span>选择一个应用进入。后续可以继续扩展新的小应用。</span>
        </div>
        <div class="fmcp-app-grid">
          ${apps.map((app) => `
            <button class="fmcp-app-card" type="button" data-action="open-app" data-page="${esc(app.page)}">
              <span class="fmcp-app-icon is-${esc(app.icon || "message")}">${icon(app.icon || "message")}</span>
              <strong>${esc(app.label)}</strong>
              <small>${esc(app.subtitle || app.stage || "")}</small>
            </button>
          `).join("")}
        </div>
      </div>
    `;
  }

  function groupsMarkup() {
    if (state.loading) return '<div class="fmcp-loading">正在读取群聊...</div>';
    if (!state.groups.length) {
      return `
      <div class="fmcp-empty">
          <div class="fmcp-empty-mark">${icon("message")}</div>
          <div>还没有群聊</div>
          <button class="fmcp-button fmcp-button-primary" type="button" data-action="create">创建群聊</button>
        </div>
      `;
    }
    return `
      <div class="fmcp-toolbar">
        <span class="fmcp-help">${state.groups.length} 个群聊</span>
        <button class="fmcp-button fmcp-button-primary" type="button" data-action="create">新建群聊</button>
      </div>
      <div class="fmcp-group-list">
        ${state.groups.map((group) => `
          <article class="fmcp-group-card">
            ${groupAvatarMarkup(group, "fmcp-group-avatar")}
            <button class="fmcp-group-main" type="button" data-action="open-group" data-group-id="${esc(group.group_id)}">
              <div class="fmcp-group-name">${esc(group.name)}</div>
              <div class="fmcp-group-meta">${esc(group.description || "未填写群聊简介")} · ${group.members.length} 位成员</div>
            </button>
            <button class="fmcp-icon-btn fmcp-group-delete" type="button" data-action="delete-group" data-group-id="${esc(group.group_id)}" aria-label="删除群聊">${icon("trash")}</button>
            <span class="fmcp-group-chevron">${icon("chevron")}</span>
          </article>
        `).join("")}
      </div>
    `;
  }

  function createMarkup() {
    const roles = [...state.roles, ...(state.user ? [state.user] : [])];
    return `
      <form class="fmcp-form" data-form="create-group">
        <label class="fmcp-field">
          <span>群聊名称</span>
          <input class="fmcp-input" name="name" maxlength="80" placeholder="例如：小院夜话" required>
        </label>
        <label class="fmcp-field">
          <span>群聊简介</span>
          <textarea class="fmcp-textarea" name="description" maxlength="500" placeholder="可选：这群人通常聊些什么"></textarea>
        </label>
        <div class="fmcp-import-card">
          ${icon("import")}
          <span>从当前角色卡导入</span>
          ${icon("chevron")}
        </div>
        <div class="fmcp-field">
          <span>已选择角色 <em>(${roles.length})</em></span>
          ${state.loading ? '<div class="fmcp-loading">正在读取当前角色卡...</div>' : ""}
          ${!state.loading && !state.roles.length ? '<div class="fmcp-help">当前角色卡暂未提取到角色，请先在主程序载入角色卡。</div>' : ""}
          <div class="fmcp-role-list">
            ${roles.map((role) => `
              <label class="fmcp-role-row">
                ${avatarMarkup(role, "fmcp-role-avatar")}
                <span class="fmcp-role-copy">
                  <strong>${esc(role.name)}</strong>
                  <span class="fmcp-help">${role.type === "user" ? "当前用户" : "角色"}</span>
                </span>
                <input type="checkbox" name="member" value="${esc(role.role_id)}" ${role.type === "user" || state.roles.length ? "checked" : ""}>
              </label>
            `).join("")}
          </div>
        </div>
        <div class="fmcp-create-options">
          <label class="fmcp-settings-row">
            <span class="fmcp-settings-copy"><strong>角色互相回复</strong><small>角色之间可以自然接话</small></span>
            <span class="fmcp-switch"><input type="checkbox" name="allow_role_to_role_reply" ${(state.settings || defaults).allow_role_to_role_reply !== false ? "checked" : ""}><i></i></span>
          </label>
          <div class="fmcp-settings-row">
            <span class="fmcp-settings-copy"><strong>默认回复人数</strong><small>每条消息默认由几个角色回复</small></span>
            <span class="fmcp-setting-value">1-2 人 ${icon("chevron")}</span>
          </div>
        </div>
        <div class="fmcp-form-actions">
          <button class="fmcp-button" type="button" data-action="back">取消</button>
          <button class="fmcp-button fmcp-button-primary" type="submit" ${state.loading || !state.roles.length ? "disabled" : ""}>创建群聊</button>
        </div>
      </form>
    `;
  }

  function messageMarkup(message) {
    const isUser = message.source === "user";
    const userClass = isUser ? " is-user" : "";
    const errorClass = message.type === "error" ? " is-error" : "";
    const group = currentGroup();
    const member = group && Array.isArray(group.members)
      ? group.members.find((item) => item.role_id === message.speaker_id || item.name === message.speaker_name)
      : null;
    const sticker = message.type === "sticker" ? stickerById(message.content) : null;
    const content = sticker
      ? `<div class="fmcp-sticker${sticker.type === "image" ? " is-image" : ""}">${stickerVisualMarkup(sticker)}<span>${esc(sticker.pack_label || "贴纸")} · ${esc(sticker.label || message.content)}</span></div>`
      : esc(message.content);
    const time = message.created_at ? new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
    return `
      <article class="fmcp-message${userClass}${errorClass}">
        ${isUser ? "" : avatarMarkup(member || { name: message.speaker_name }, "fmcp-message-avatar")}
        <div class="fmcp-message-stack">
          <div class="fmcp-message-meta"><span>${esc(message.speaker_name)}</span>${time ? `<time>${esc(time)}</time>` : ""}</div>
          <div class="fmcp-message-bubble">${content}</div>
          ${isUser ? `<div class="fmcp-message-foot"><span class="fmcp-message-receipt">✓✓</span>${time ? `<time>${esc(time)}</time>` : ""}</div>` : ""}
        </div>
        ${isUser ? avatarMarkup(member || { name: message.speaker_name }, "fmcp-message-avatar") : ""}
      </article>
    `;
  }

  function chatMarkup() {
    const group = currentGroup();
    if (!group) return '<div class="fmcp-loading">群聊不存在或正在读取...</div>';
    return `
      <div class="fmcp-chat-body" data-role="messages">
        ${state.messages.length ? state.messages.map(messageMarkup).join("") : '<div class="fmcp-empty"><div>群聊刚刚建立，发一句话试试。</div></div>'}
        ${state.generating ? '<div class="fmcp-loading">角色正在回复...</div>' : ""}
      </div>
    `;
  }

  function composerMarkup() {
    if (state.page !== "chat") return "";
    return `
      <form class="fmcp-composer" data-form="send-message">
        ${state.showExtensions ? `
          <div class="fmcp-extension-panel">
            <button class="fmcp-extension-item" type="button" data-action="continue-chat">
              ${icon("refresh")}
              <span><strong>角色续聊一轮</strong><small>不需要用户发言，让角色自然接话</small></span>
            </button>
            <button class="fmcp-extension-item" type="button" data-action="clear-messages">
              ${icon("trash")}
              <span><strong>清空当前群聊</strong><small>仅清除这个小手机群聊的消息</small></span>
            </button>
          </div>
        ` : ""}
        ${state.showStickers ? `
          <div class="fmcp-sticker-panel">
            ${availableStickers().map(stickerButtonMarkup).join("")}
          </div>
        ` : ""}
        <div class="fmcp-composer-row">
          <button class="fmcp-composer-icon" type="button" data-action="toggle-extensions" aria-label="打开更多功能">${icon("plus")}</button>
          <div class="fmcp-composer-input">
            <input name="message" maxlength="500" autocomplete="off" placeholder="输入消息..." ${state.generating ? "disabled" : ""}>
            <button type="button" data-action="toggle-stickers" aria-label="选择贴纸">${icon("smile")}</button>
          </div>
          <button class="fmcp-composer-icon fmcp-continue-button" type="button" data-action="continue-chat" aria-label="让角色继续聊天" ${state.generating ? "disabled" : ""}>${icon("refresh")}</button>
          <button class="fmcp-button fmcp-button-primary" type="submit" ${state.generating ? "disabled" : ""}>发送</button>
        </div>
      </form>
    `;
  }

  function settingsMarkup() {
    const settings = state.settings || defaults;
    return `
      <form class="fmcp-form" data-form="settings">
        <div class="fmcp-settings-section">
          <div class="fmcp-section-title">基础设置</div>
          <div class="fmcp-settings-card">
            <label class="fmcp-settings-row">
              <span class="fmcp-settings-copy"><strong>启用小手机</strong></span>
              <span class="fmcp-switch"><input type="checkbox" name="enabled" ${settings.enabled ? "checked" : ""}><i></i></span>
            </label>
            <label class="fmcp-settings-row">
              <span class="fmcp-settings-copy"><strong>显示悬浮球</strong></span>
              <span class="fmcp-switch"><input type="checkbox" name="show_floating_button" ${settings.show_floating_button ? "checked" : ""}><i></i></span>
            </label>
            <label class="fmcp-settings-row">
              <span class="fmcp-settings-copy"><strong>记住位置</strong></span>
              <span class="fmcp-switch"><input type="checkbox" name="remember_position" ${settings.remember_position ? "checked" : ""}><i></i></span>
            </label>
          </div>
        </div>
        <div class="fmcp-settings-section">
          <div class="fmcp-section-title">聊天设置</div>
          <div class="fmcp-settings-card">
            <label class="fmcp-settings-row">
              <span class="fmcp-settings-copy"><strong>每轮回复角色数</strong><small>控制单次生成的短句气泡数量</small></span>
              <select class="fmcp-select" name="reply_count">
                <option value="1" ${settings.reply_count === "1" ? "selected" : ""}>1 人</option>
                <option value="1-2" ${settings.reply_count !== "1" ? "selected" : ""}>1-2 人</option>
              </select>
            </label>
            <label class="fmcp-settings-row">
              <span class="fmcp-settings-copy"><strong>最大输出 tokens</strong><small>范围 64-1200</small></span>
              <input class="fmcp-number-input" name="max_tokens" type="number" min="64" max="1200" value="${esc(settings.max_tokens || 500)}">
            </label>
            <label class="fmcp-settings-row">
              <span class="fmcp-settings-copy"><strong>保留最近消息</strong><small>范围 1-80 条</small></span>
              <input class="fmcp-number-input" name="recent_message_limit" type="number" min="1" max="80" value="${esc(settings.recent_message_limit || 30)}">
            </label>
            <label class="fmcp-settings-row">
              <span class="fmcp-settings-copy"><strong>角色互相回复</strong><small>允许角色自然接话</small></span>
              <span class="fmcp-switch"><input type="checkbox" name="allow_role_to_role_reply" ${settings.allow_role_to_role_reply !== false ? "checked" : ""}><i></i></span>
            </label>
            <label class="fmcp-settings-row">
              <span class="fmcp-settings-copy"><strong>自动插话</strong><small>默认关闭；详细频率请到后台管理调整</small></span>
              <span class="fmcp-switch"><input type="checkbox" name="allow_auto_interject" ${settings.allow_auto_interject ? "checked" : ""}><i></i></span>
            </label>
          </div>
        </div>
        <div class="fmcp-settings-section">
          <div class="fmcp-section-title">模型设置</div>
          <div class="fmcp-settings-card">
            <div class="fmcp-settings-row"><span class="fmcp-settings-copy"><strong>模型来源</strong><small>API Key 只在后端读取</small></span><span class="fmcp-setting-value">跟随主程序 ${icon("chevron")}</span></div>
          </div>
        </div>
        <div class="fmcp-settings-section">
          <div class="fmcp-section-title">高级</div>
          <div class="fmcp-settings-card">
            <a class="fmcp-settings-row fmcp-settings-action" href="${modBase}/" target="_blank" rel="noreferrer">${icon("settings")}<span class="fmcp-settings-copy"><strong>打开后台管理</strong><small>复杂配置将在 v1.0 后台中维护</small></span>${icon("chevron")}</a>
            <button class="fmcp-settings-row fmcp-settings-action" type="button" data-action="reset-position">${icon("refresh")}<span class="fmcp-settings-copy"><strong>复位小手机</strong></span>${icon("chevron")}</button>
            <a class="fmcp-settings-row fmcp-settings-action" href="${apiBase}/export" download>${icon("download")}<span class="fmcp-settings-copy"><strong>导出群聊记录</strong></span>${icon("chevron")}</a>
          </div>
        </div>
        <div class="fmcp-help">消息独立保存在 data/mobile_chat，不会写入主 Chat。</div>
        <button class="fmcp-button fmcp-button-primary fmcp-settings-save" type="submit">保存设置</button>
      </form>
    `;
  }

  function stickersMarkup() {
    const stickers = availableStickers();
    return `
      <div class="fmcp-sticker-app">
        <div class="fmcp-home-intro">
          <strong>贴纸包</strong>
          <span>已读取 ${stickers.length} 个贴纸；卡提希娅文件夹里的 PNG 会自动加入。</span>
        </div>
        <div class="fmcp-sticker-library">
          ${stickers.map((sticker) => `
            <div class="fmcp-sticker-library-card">
              ${stickerVisualMarkup(sticker)}
              <strong>${esc(sticker.label || sticker.id)}</strong>
              <small>${esc((sticker.tags || []).length ? `${sticker.pack_label || "贴纸"} · ${(sticker.tags || []).join(", ")}` : (sticker.pack_label || "贴纸"))}</small>
            </div>
          `).join("")}
        </div>
      </div>
    `;
  }

  function channelMarkup() {
    const channel = state.channels.find((item) => item.channel_id === state.currentChannelId);
    const events = state.channelEvents[state.currentChannelId] || [];
    if (state.loading) return '<div class="fmcp-loading">正在读取频道...</div>';
    if (!channel) return '<div class="fmcp-empty"><div>频道不存在。</div></div>';
    return `
      <div class="fmcp-channel-app">
        <div class="fmcp-home-intro">
          <strong>${esc(channel.label)}</strong>
          <span>${esc(channel.description || "小手机独立频道")}</span>
        </div>
        <div class="fmcp-toolbar">
          <span class="fmcp-help">${events.length} 条内容</span>
          <button class="fmcp-button fmcp-button-primary" type="button" data-action="seed-current-channel">生成内容</button>
        </div>
        <div class="fmcp-event-list">
          ${events.length ? events.map((event) => `
            <article class="fmcp-event-card is-${esc(event.channel_type)}">
              <div class="fmcp-event-meta">${esc(event.author_name)} · ${esc(event.event_type)} · ${event.created_at ? esc(new Date(event.created_at).toLocaleString()) : ""}</div>
              <strong>${esc(event.title)}</strong>
              <p>${esc(event.content)}</p>
              ${(event.tags || []).length ? `<div class="fmcp-tag-row">${event.tags.map((tag) => `<span>${esc(tag)}</span>`).join("")}</div>` : ""}
            </article>
          `).join("") : '<div class="fmcp-empty"><div>暂无内容，可以点击生成内容。</div></div>'}
        </div>
      </div>
    `;
  }

  function notificationsMarkup() {
    if (state.loading) return '<div class="fmcp-loading">正在读取通知...</div>';
    return `
      <div class="fmcp-notification-app">
        <div class="fmcp-toolbar">
          <span class="fmcp-help">${state.notifications.length} 条通知</span>
          <button class="fmcp-button" type="button" data-action="read-all-notifications">全部已读</button>
        </div>
        <div class="fmcp-event-list">
          ${state.notifications.length ? state.notifications.map((item) => `
            <article class="fmcp-event-card ${item.read ? "is-read" : "is-unread"}">
              <div class="fmcp-event-meta">${item.read ? "已读" : "未读"} · ${esc(item.source || "system")} · ${item.created_at ? esc(new Date(item.created_at).toLocaleString()) : ""}</div>
              <strong>${esc(item.title)}</strong>
              <p>${esc(item.content)}</p>
              ${item.read ? "" : `<button class="fmcp-button" type="button" data-action="read-notification" data-notification-id="${esc(item.notification_id)}">标为已读</button>`}
            </article>
          `).join("") : '<div class="fmcp-empty"><div>暂无通知。</div></div>'}
        </div>
      </div>
    `;
  }

  function phoneMarkup() {
    const roles = state.phoneRoles.length ? state.phoneRoles : state.roles;
    const session = state.phoneSessions.find((item) => item.session_id === state.currentPhoneSessionId)
      || state.phoneSessions.find((item) => item.role_id === state.currentPhoneRoleId)
      || null;
    return `
      <div class="fmcp-phone-app">
        <div class="fmcp-home-intro">
          <strong>电话</strong>
          <span>模拟通话内容只保存在小手机，不进入正文。</span>
        </div>
        <div class="fmcp-phone-roles">
          ${roles.length ? roles.map((role) => `
            <button class="fmcp-role-chip ${state.currentPhoneRoleId === role.role_id ? "is-active" : ""}" type="button" data-action="select-phone-role" data-role-id="${esc(role.role_id)}">
              ${avatarMarkup({ name: role.display_name || role.name, avatar: role.avatar }, "fmcp-role-avatar")}
              <span>${esc(role.display_name || role.name)}</span>
            </button>
          `).join("") : '<div class="fmcp-empty"><div>暂无可通话角色，请先在后台或群聊创建角色。</div></div>'}
        </div>
        <div class="fmcp-call-screen">
          ${session?.lines?.length ? session.lines.map((line) => `
            <article class="fmcp-call-line ${line.source === "user" ? "is-user" : "is-role"}">
              <small>${esc(line.speaker)}${line.mood ? ` · ${esc(line.mood)}` : ""}</small>
              <span>${esc(line.content)}</span>
            </article>
          `).join("") : '<div class="fmcp-empty"><div>选择角色后，可以拨号或输入一句话。</div></div>'}
          ${state.generating ? '<div class="fmcp-loading">通话中...</div>' : ""}
        </div>
        <form class="fmcp-composer fmcp-phone-composer" data-form="phone-call">
          <div class="fmcp-composer-row">
            <div class="fmcp-composer-input">
              <input name="user_line" maxlength="500" autocomplete="off" placeholder="输入你在电话里说的话..." ${state.generating ? "disabled" : ""}>
            </div>
            <button class="fmcp-button fmcp-button-primary" type="submit" ${state.generating || !state.currentPhoneRoleId ? "disabled" : ""}>通话</button>
          </div>
        </form>
      </div>
    `;
  }

  function bodyMarkup() {
    if (state.page === "home") return homeMarkup();
    if (state.page === "create") return createMarkup();
    if (state.page === "chat") return chatMarkup();
    if (state.page === "settings") return settingsMarkup();
    if (state.page === "stickers") return stickersMarkup();
    if (state.page === "notifications") return notificationsMarkup();
    if (state.page === "phone") return phoneMarkup();
    if (state.page.startsWith("channel-")) return channelMarkup();
    return groupsMarkup();
  }

  function render() {
    if (!root) return;
    const settings = state.settings || defaults;
    const showFab = settings.enabled && settings.show_floating_button;
    if (!showFab && !state.open) {
      root.innerHTML = "";
      return;
    }
    root.innerHTML = `
      <div style="${panelStyle()}">
        ${showFab ? `
          <button class="fmcp-fab" type="button" data-action="toggle" aria-label="打开小手机">
            <span class="fmcp-fab-icon">${icon("message")}</span>
            ${state.unread ? `<span class="fmcp-fab-badge">${Math.min(state.unread, 99)}</span>` : ""}
          </button>
        ` : ""}
        ${state.open ? `
          <section class="fmcp-panel${state.page === "chat" ? " is-chat-room" : ""}" aria-label="Fantareal 小手机">
            <div class="fmcp-shell">
              ${headerMarkup()}
              <main class="fmcp-body fmcp-body-${esc(state.page)}">
                ${errorMarkup()}
                ${bodyMarkup()}
              </main>
              ${composerMarkup()}
            </div>
          </section>
        ` : ""}
      </div>
    `;
    requestAnimationFrame(() => {
      applyResponsivePositions();
      if (state.page === "chat") {
        const body = root.querySelector(".fmcp-body");
        if (body) body.scrollTop = body.scrollHeight;
      }
    });
  }

  async function loadSettings() {
    try {
      const payload = await request("/settings");
      state.settings = payload.settings || defaults;
      restartAutomationTimer();
    } catch (error) {
      state.error = error.message;
    }
    render();
  }

  async function loadStickers() {
    try {
      const payload = await request("/stickers");
      const stickers = Array.isArray(payload.stickers) ? payload.stickers : [];
      state.stickers = stickers.length ? stickers : fallbackStickers;
      state.stickerPacks = Array.isArray(payload.packs) ? payload.packs : [];
    } catch (error) {
      state.stickers = fallbackStickers;
    }
    render();
  }

  async function loadApps() {
    try {
      const payload = await request("/apps");
      state.apps = payload.apps || [];
    } catch (error) {
      state.apps = [];
    }
    render();
  }

  async function loadChannels() {
    try {
      const payload = await request("/channels");
      state.channels = payload.channels || [];
    } catch (error) {
      state.error = error.message;
    }
    render();
  }

  async function loadChannelEvents(channelId) {
    state.loading = true;
    state.error = "";
    render();
    try {
      const payload = await request(`/channels/${encodeURIComponent(channelId)}/events`);
      state.currentChannelId = payload.channel?.channel_id || channelId;
      state.channelEvents[state.currentChannelId] = payload.events || [];
    } catch (error) {
      state.error = error.message;
    } finally {
      state.loading = false;
      render();
    }
  }

  async function loadNotifications() {
    state.loading = true;
    state.error = "";
    render();
    try {
      const payload = await request("/notifications");
      state.notifications = payload.notifications || [];
    } catch (error) {
      state.error = error.message;
    } finally {
      state.loading = false;
      render();
    }
  }

  async function loadPhone() {
    state.loading = true;
    state.error = "";
    render();
    try {
      const payload = await request("/phone/sessions");
      state.phoneSessions = payload.sessions || [];
      state.phoneRoles = payload.roles || [];
      if (!state.currentPhoneRoleId && state.phoneRoles[0]) {
        state.currentPhoneRoleId = state.phoneRoles[0].role_id;
      }
      const session = state.phoneSessions.find((item) => item.role_id === state.currentPhoneRoleId);
      state.currentPhoneSessionId = session?.session_id || state.currentPhoneSessionId;
    } catch (error) {
      state.error = error.message;
    } finally {
      state.loading = false;
      render();
    }
  }

  async function loadGroups() {
    state.loading = true;
    state.error = "";
    render();
    try {
      const payload = await request("/groups");
      state.groups = payload.groups || [];
    } catch (error) {
      state.error = error.message;
    } finally {
      state.loading = false;
      render();
    }
  }

  async function openCreate() {
    state.page = "create";
    state.loading = true;
    state.error = "";
    render();
    try {
      const payload = await request("/roles");
      state.roles = payload.roles || [];
      state.user = payload.user || null;
    } catch (error) {
      state.error = error.message;
    } finally {
      state.loading = false;
      render();
    }
  }

  async function openGroup(groupId) {
    state.currentGroupId = groupId;
    state.page = "chat";
    state.automationRounds = 0;
    state.lastAutomationAt = 0;
    touchActivity();
    state.showStickers = false;
    state.showExtensions = false;
    state.loading = true;
    state.error = "";
    render();
    try {
      const payload = await request(`/groups/${encodeURIComponent(groupId)}/messages`);
      state.messages = payload.messages || [];
    } catch (error) {
      state.error = error.message;
    } finally {
      state.loading = false;
      render();
    }
  }

  async function openAppPage(page) {
    const target = String(page || "home");
    state.error = "";
    state.showStickers = false;
    state.showExtensions = false;
    if (target === "groups") {
      state.page = "groups";
      await loadGroups();
      return;
    }
    if (target === "settings") {
      state.page = "settings";
      render();
      return;
    }
    if (target === "stickers") {
      state.page = "stickers";
      await loadStickers();
      return;
    }
    if (target === "notifications") {
      state.page = "notifications";
      await loadNotifications();
      return;
    }
    if (target === "phone") {
      state.page = "phone";
      await loadPhone();
      return;
    }
    if (target.startsWith("channel-")) {
      const channelId = target.slice("channel-".length);
      state.page = target;
      state.currentChannelId = channelId;
      await loadChannelEvents(channelId);
      return;
    }
    state.page = "home";
    render();
  }

  async function togglePanel() {
    state.open = !state.open;
    state.error = "";
    if (state.open) {
      setUnread(0);
      state.page = "home";
      await loadApps();
      await loadChannels();
      await loadGroups();
    } else {
      render();
    }
  }

  async function saveSettings(form) {
    const formData = new FormData(form);
    state.error = "";
    try {
      const payload = await request("/settings", {
        method: "POST",
        body: JSON.stringify({
          enabled: formData.has("enabled"),
          show_floating_button: formData.has("show_floating_button"),
          remember_position: formData.has("remember_position"),
          reply_count: formData.get("reply_count"),
          max_tokens: formData.get("max_tokens"),
          recent_message_limit: formData.get("recent_message_limit"),
          allow_role_to_role_reply: formData.has("allow_role_to_role_reply"),
          allow_auto_interject: formData.has("allow_auto_interject"),
        }),
      });
      state.settings = payload.settings;
      restartAutomationTimer();
      state.page = "home";
      render();
    } catch (error) {
      state.error = error.message;
      render();
    }
  }

  async function createGroup(form) {
    const data = new FormData(form);
    const selectedIds = new Set(data.getAll("member").map(String));
    const members = [...state.roles, ...(state.user ? [state.user] : [])].filter((item) => selectedIds.has(item.role_id));
    state.loading = true;
    state.error = "";
    render();
    try {
      const payload = await request("/groups", {
        method: "POST",
        body: JSON.stringify({
          name: data.get("name"),
          description: data.get("description"),
          members,
          allow_role_to_role_reply: data.has("allow_role_to_role_reply"),
        }),
      });
      state.groups = [payload.group, ...state.groups.filter((item) => item.group_id !== payload.group.group_id)];
      await openGroup(payload.group.group_id);
    } catch (error) {
      state.error = error.message;
      state.page = "create";
      state.loading = false;
      render();
    }
  }

  async function reloadMessages() {
    if (!state.currentGroupId) return;
    const payload = await request(`/groups/${encodeURIComponent(state.currentGroupId)}/messages`);
    state.messages = payload.messages || [];
  }

  async function sendMessage(form) {
    const data = new FormData(form);
    const message = String(data.get("message") || "").trim();
    if (!message || state.generating) return;
    touchActivity();
    state.generating = true;
    state.error = "";
    render();
    try {
      const payload = await request("/generate", {
        method: "POST",
        body: JSON.stringify({ group_id: state.currentGroupId, user_message: message }),
      });
      if (!state.open) setUnread(state.unread + (payload.messages || []).length);
    } catch (error) {
      state.error = error.message;
    } finally {
      await reloadMessages().catch((error) => { state.error = error.message; });
      state.generating = false;
      render();
    }
  }

  async function sendSticker(stickerId) {
    if (!state.currentGroupId || state.generating) return;
    touchActivity();
    state.error = "";
    try {
      await request(`/groups/${encodeURIComponent(state.currentGroupId)}/messages`, {
        method: "POST",
        body: JSON.stringify({ type: "sticker", content: stickerId }),
      });
      state.showStickers = false;
      await reloadMessages();
    } catch (error) {
      state.error = error.message;
    }
    render();
  }

  async function continueChat(options = {}) {
    if (!state.currentGroupId || state.generating) return;
    state.generating = true;
    if (!options.automated) touchActivity();
    if (!options.automated) state.showExtensions = false;
    state.error = "";
    render();
    try {
      const payload = await request("/continue", {
        method: "POST",
        body: JSON.stringify({ group_id: state.currentGroupId }),
      });
      if (!state.open) setUnread(state.unread + (payload.messages || []).length);
    } catch (error) {
      state.error = error.message;
    } finally {
      await reloadMessages().catch((error) => { state.error = error.message; });
      state.generating = false;
      if (options.automated) state.lastAutomationAt = Date.now();
      render();
    }
  }

  async function seedCurrentChannel() {
    if (!state.currentChannelId || state.generating) return;
    if (!window.confirm("生成频道内容会真实调用模型，继续？")) return;
    state.generating = true;
    state.error = "";
    render();
    try {
      const payload = await request(`/channels/${encodeURIComponent(state.currentChannelId)}/seed`, {
        method: "POST",
        body: JSON.stringify({ count: 5 }),
      });
      state.channelEvents[state.currentChannelId] = payload.events || [];
      await loadNotifications().catch(() => {});
    } catch (error) {
      state.error = error.message;
    } finally {
      state.generating = false;
      await loadChannelEvents(state.currentChannelId).catch((error) => { state.error = error.message; });
      render();
    }
  }

  async function readNotification(notificationId) {
    state.error = "";
    try {
      const payload = await request(`/notifications/${encodeURIComponent(notificationId)}`, {
        method: "PATCH",
        body: JSON.stringify({ read: true }),
      });
      state.notifications = payload.notifications || [];
    } catch (error) {
      state.error = error.message;
    }
    render();
  }

  async function readAllNotifications() {
    state.error = "";
    try {
      const payload = await request("/notifications/read-all", { method: "POST" });
      state.notifications = payload.notifications || [];
    } catch (error) {
      state.error = error.message;
    }
    render();
  }

  async function phoneCall(form) {
    if (!state.currentPhoneRoleId || state.generating) return;
    const data = new FormData(form);
    state.generating = true;
    state.error = "";
    render();
    try {
      const payload = await request("/phone/call", {
        method: "POST",
        body: JSON.stringify({
          role_id: state.currentPhoneRoleId,
          session_id: state.currentPhoneSessionId,
          user_line: data.get("user_line") || "",
        }),
      });
      const session = payload.session;
      if (session) {
        state.currentPhoneSessionId = session.session_id;
        state.phoneSessions = [session, ...state.phoneSessions.filter((item) => item.session_id !== session.session_id)];
      }
    } catch (error) {
      state.error = error.message;
    } finally {
      state.generating = false;
      render();
    }
  }

  async function clearMessages() {
    if (!state.currentGroupId || state.generating) return;
    if (!window.confirm("清空当前小手机群聊的全部消息？")) return;
    state.error = "";
    state.showExtensions = false;
    try {
      await request(`/groups/${encodeURIComponent(state.currentGroupId)}/messages`, { method: "DELETE" });
      state.messages = [];
    } catch (error) {
      state.error = error.message;
    }
    render();
  }

  async function deleteGroup(groupId) {
    const group = state.groups.find((item) => item.group_id === groupId);
    if (!window.confirm(`删除群聊“${group ? group.name : groupId}”？`)) return;
    state.error = "";
    try {
      await request(`/groups/${encodeURIComponent(groupId)}`, { method: "DELETE" });
      state.groups = state.groups.filter((item) => item.group_id !== groupId);
    } catch (error) {
      state.error = error.message;
    }
    render();
  }

  async function resetPosition() {
    state.error = "";
    try {
      const payload = await request("/settings", {
        method: "POST",
        body: JSON.stringify({
          floating_position: defaults.floating_position,
          panel_position: defaults.panel_position,
        }),
      });
      state.settings = payload.settings;
    } catch (error) {
      state.error = error.message;
    }
    render();
  }

  function getSidebarSafeLeft() {
    const margin = 8;
    const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
    const now = Date.now();
    if (
      sidebarSafeLeftCache.width === viewportWidth
      && sidebarSafeLeftCache.height === viewportHeight
      && now - sidebarSafeLeftCache.time < 260
    ) {
      return sidebarSafeLeftCache.value;
    }
    if (viewportWidth < 760) return margin;

    const selectors = [
      ".topbar.topbar-chat",
      ".topbar-stack > .topbar",
      ".app-sidebar",
      ".global-sidebar",
      ".left-sidebar",
      ".sidebar",
      "#app-sidebar",
      "#global-sidebar",
      "#sidebar",
      "[data-sidebar]",
    ];
    let railRight = 0;
    selectors.forEach((selector) => {
      document.querySelectorAll(selector).forEach((node) => {
        if (!(node instanceof HTMLElement) || node.closest("#fantareal-mobile-chat-root")) return;
        const style = window.getComputedStyle(node);
        if (style.display === "none" || style.visibility === "hidden") return;
        const rect = node.getBoundingClientRect();
        const maxRailWidth = Math.min(360, viewportWidth * 0.32);
        const minRailHeight = Math.min(220, Math.max(96, viewportHeight * 0.32));
        if (
          rect.left <= 6
          && rect.right > 96
          && rect.width >= 96
          && rect.width <= maxRailWidth
          && rect.height >= minRailHeight
        ) {
          railRight = Math.max(railRight, rect.right);
        }
      });
    });
    if (!railRight && document.body.classList.contains("chat-page")) {
      railRight = Math.min(260, Math.max(196, Math.round(viewportWidth * 0.12)));
    }
    const safeLeft = railRight ? Math.ceil(railRight + 10) : margin;
    sidebarSafeLeftCache = { value: Math.max(margin, safeLeft), width: viewportWidth, height: viewportHeight, time: now };
    return sidebarSafeLeftCache.value;
  }

  function isDefaultPosition(position, fallback) {
    return safeNumber(position && position.right, fallback.right) === fallback.right
      && safeNumber(position && position.bottom, fallback.bottom) === fallback.bottom;
  }

  function effectiveFloatingPosition(position) {
    const next = position || defaults.floating_position;
    const hasStatusPanel = Boolean(document.getElementById("xuqi-status-panel-mod"));
    return {
      right: safeNumber(next.right, defaults.floating_position.right),
      bottom: isDefaultPosition(next, defaults.floating_position) && hasStatusPanel
        ? Math.max(defaults.floating_position.bottom, 158)
        : safeNumber(next.bottom, defaults.floating_position.bottom),
    };
  }

  function effectivePanelPosition(position) {
    const next = position || defaults.panel_position;
    const hasStatusPanel = Boolean(document.getElementById("xuqi-status-panel-mod"));
    return {
      right: isDefaultPosition(next, defaults.panel_position) && hasStatusPanel
        ? Math.max(defaults.panel_position.right, 92)
        : safeNumber(next.right, defaults.panel_position.right),
      bottom: safeNumber(next.bottom, defaults.panel_position.bottom),
    };
  }

  function clampElementPosition(left, top, element, respectSidebar = true) {
    const margin = 8;
    const rect = element.getBoundingClientRect();
    const width = rect.width || 54;
    const height = rect.height || 54;
    const minLeft = respectSidebar ? Math.max(margin, getSidebarSafeLeft()) : margin;
    const maxLeft = Math.max(minLeft, window.innerWidth - width - margin);
    const maxTop = Math.max(margin, window.innerHeight - height - margin);
    return {
      left: Math.max(minLeft, Math.min(left, maxLeft)),
      top: Math.max(margin, Math.min(top, maxTop)),
    };
  }

  function bottomRightPositionFrom(left, top, element) {
    const rect = element.getBoundingClientRect();
    return {
      right: Math.max(0, Math.round(window.innerWidth - left - rect.width)),
      bottom: Math.max(0, Math.round(window.innerHeight - top - rect.height)),
    };
  }

  function applyStoredElementPosition(element, position, respectSidebar = true) {
    if (!element) return;
    const rect = element.getBoundingClientRect();
    const left = window.innerWidth - rect.width - safeNumber(position.right, 0);
    const top = window.innerHeight - rect.height - safeNumber(position.bottom, 0);
    const next = clampElementPosition(left, top, element, respectSidebar);
    element.style.left = `${next.left}px`;
    element.style.top = `${next.top}px`;
    element.style.right = "auto";
    element.style.bottom = "auto";
  }

  function applyResponsivePositions() {
    if (!root) return;
    const settings = state.settings || defaults;
    applyStoredElementPosition(root.querySelector(".fmcp-fab"), effectiveFloatingPosition(settings.floating_position));
    applyStoredElementPosition(root.querySelector(".fmcp-panel"), effectivePanelPosition(settings.panel_position));
  }

  function clampFabPosition(left, top, fab) {
    return clampElementPosition(left, top, fab);
  }

  function floatingPositionFrom(left, top, fab) {
    return bottomRightPositionFrom(left, top, fab);
  }

  async function persistFloatingPosition(position) {
    const rememberPosition = (state.settings || defaults).remember_position !== false;
    state.settings = { ...(state.settings || defaults), floating_position: position };
    if (!rememberPosition) {
      render();
      return;
    }
    try {
      const payload = await request("/settings", {
        method: "POST",
        body: JSON.stringify({ floating_position: position }),
      });
      state.settings = payload.settings;
    } catch (error) {
      state.error = error.message;
    }
    render();
  }

  async function persistPanelPosition(position) {
    const rememberPosition = (state.settings || defaults).remember_position !== false;
    state.settings = { ...(state.settings || defaults), panel_position: position };
    if (!rememberPosition) {
      render();
      return;
    }
    try {
      const payload = await request("/settings", {
        method: "POST",
        body: JSON.stringify({ panel_position: position }),
      });
      state.settings = payload.settings;
    } catch (error) {
      state.error = error.message;
    }
    render();
  }

  function beginFabDrag(fab, event, pointerId) {
    const rect = fab.getBoundingClientRect();
    fabDrag = {
      pointerId,
      fab,
      startX: event.clientX,
      startY: event.clientY,
      startLeft: rect.left,
      startTop: rect.top,
      moved: false,
    };
  }

  function beginPanelDrag(panel, event, pointerId) {
    const rect = panel.getBoundingClientRect();
    panelDrag = {
      pointerId,
      panel,
      startX: event.clientX,
      startY: event.clientY,
      startLeft: rect.left,
      startTop: rect.top,
      moved: false,
    };
  }

  function panelFromDragHandle(event) {
    if (event.target.closest("button, a, input, select, textarea, label")) return null;
    return event.target.closest(".fmcp-header")?.closest(".fmcp-panel") || null;
  }

  function onPointerDown(event) {
    if (event.button !== 0) return;
    const fab = event.target.closest(".fmcp-fab");
    if (fab) {
      beginFabDrag(fab, event, event.pointerId);
      fab.setPointerCapture?.(event.pointerId);
      return;
    }
    const panel = panelFromDragHandle(event);
    if (!panel) return;
    beginPanelDrag(panel, event, event.pointerId);
    panel.setPointerCapture?.(event.pointerId);
  }

  function moveFabDrag(event) {
    const dx = event.clientX - fabDrag.startX;
    const dy = event.clientY - fabDrag.startY;
    if (!fabDrag.moved && Math.hypot(dx, dy) < 5) return;
    fabDrag.moved = true;
    fabDrag.fab.classList.add("is-dragging");
    const next = clampFabPosition(fabDrag.startLeft + dx, fabDrag.startTop + dy, fabDrag.fab);
    fabDrag.fab.style.left = `${next.left}px`;
    fabDrag.fab.style.top = `${next.top}px`;
    fabDrag.fab.style.right = "auto";
    fabDrag.fab.style.bottom = "auto";
    event.preventDefault();
  }

  function completeFabDrag() {
    fabDrag.fab.classList.remove("is-dragging");
    if (fabDrag.moved) {
      const rect = fabDrag.fab.getBoundingClientRect();
      suppressFabClickUntil = Date.now() + 240;
      void persistFloatingPosition(floatingPositionFrom(rect.left, rect.top, fabDrag.fab));
    }
    fabDrag = null;
  }

  function movePanelDrag(event) {
    const dx = event.clientX - panelDrag.startX;
    const dy = event.clientY - panelDrag.startY;
    if (!panelDrag.moved && Math.hypot(dx, dy) < 5) return;
    panelDrag.moved = true;
    panelDrag.panel.classList.add("is-dragging");
    const next = clampElementPosition(panelDrag.startLeft + dx, panelDrag.startTop + dy, panelDrag.panel);
    panelDrag.panel.style.left = `${next.left}px`;
    panelDrag.panel.style.top = `${next.top}px`;
    panelDrag.panel.style.right = "auto";
    panelDrag.panel.style.bottom = "auto";
    event.preventDefault();
  }

  function completePanelDrag() {
    panelDrag.panel.classList.remove("is-dragging");
    if (panelDrag.moved) {
      const rect = panelDrag.panel.getBoundingClientRect();
      void persistPanelPosition(bottomRightPositionFrom(rect.left, rect.top, panelDrag.panel));
    }
    panelDrag = null;
  }

  function onPointerMove(event) {
    if (fabDrag && fabDrag.pointerId === event.pointerId) moveFabDrag(event);
    if (panelDrag && panelDrag.pointerId === event.pointerId) movePanelDrag(event);
  }

  function finishFabDrag(event) {
    if (fabDrag && fabDrag.pointerId === event.pointerId) {
      fabDrag.fab.releasePointerCapture?.(event.pointerId);
      completeFabDrag();
    }
    if (panelDrag && panelDrag.pointerId === event.pointerId) {
      panelDrag.panel.releasePointerCapture?.(event.pointerId);
      completePanelDrag();
    }
  }

  function onMouseDown(event) {
    if (fabDrag || panelDrag || event.button !== 0) return;
    const fab = event.target.closest(".fmcp-fab");
    if (fab) {
      beginFabDrag(fab, event, "mouse");
      return;
    }
    const panel = panelFromDragHandle(event);
    if (panel) beginPanelDrag(panel, event, "mouse");
  }

  function onMouseMove(event) {
    if (fabDrag && fabDrag.pointerId === "mouse") moveFabDrag(event);
    if (panelDrag && panelDrag.pointerId === "mouse") movePanelDrag(event);
  }

  function finishMouseDrag() {
    if (fabDrag && fabDrag.pointerId === "mouse") completeFabDrag();
    if (panelDrag && panelDrag.pointerId === "mouse") completePanelDrag();
  }

  function onClick(event) {
    const button = event.target.closest("[data-action]");
    if (!button) return;
    touchActivity();
    const action = button.dataset.action;
    if (action === "toggle") {
      if (Date.now() < suppressFabClickUntil) return;
      void togglePanel();
    }
    if (action === "close") {
      state.open = false;
      state.showStickers = false;
      state.showExtensions = false;
      render();
    }
    if (action === "back") {
      state.page = state.page === "chat" || state.page === "create" ? "groups" : "home";
      state.showStickers = false;
      state.showExtensions = false;
      state.error = "";
      render();
    }
    if (action === "settings") {
      state.page = "settings";
      state.error = "";
      render();
    }
    if (action === "open-chat-app") {
      state.page = "groups";
      state.error = "";
      void loadGroups();
    }
    if (action === "open-settings-app") {
      state.page = "settings";
      state.error = "";
      render();
    }
    if (action === "open-stickers-app") {
      state.page = "stickers";
      state.error = "";
      void loadStickers();
      render();
    }
    if (action === "open-app") void openAppPage(button.dataset.page || "home");
    if (action === "create") void openCreate();
    if (action === "open-group") void openGroup(button.dataset.groupId || "");
    if (action === "delete-group") void deleteGroup(button.dataset.groupId || "");
    if (action === "toggle-stickers") {
      state.showStickers = !state.showStickers;
      state.showExtensions = false;
      if (state.showStickers) void loadStickers();
      render();
    }
    if (action === "toggle-extensions") {
      state.showExtensions = !state.showExtensions;
      state.showStickers = false;
      render();
    }
    if (action === "send-sticker") void sendSticker(button.dataset.stickerId || "");
    if (action === "continue-chat") void continueChat();
    if (action === "seed-current-channel") void seedCurrentChannel();
    if (action === "read-notification") void readNotification(button.dataset.notificationId || "");
    if (action === "read-all-notifications") void readAllNotifications();
    if (action === "select-phone-role") {
      state.currentPhoneRoleId = button.dataset.roleId || "";
      const session = state.phoneSessions.find((item) => item.role_id === state.currentPhoneRoleId);
      state.currentPhoneSessionId = session?.session_id || "";
      render();
    }
    if (action === "clear-messages") void clearMessages();
    if (action === "reset-position") void resetPosition();
  }

  function onSubmit(event) {
    const form = event.target.closest("form[data-form]");
    if (!form) return;
    event.preventDefault();
    touchActivity();
    if (form.dataset.form === "create-group") void createGroup(form);
    if (form.dataset.form === "send-message") void sendMessage(form);
    if (form.dataset.form === "settings") void saveSettings(form);
    if (form.dataset.form === "phone-call") void phoneCall(form);
  }

  function init() {
    if (document.getElementById("fantareal-mobile-chat-root")) return;
    root = document.createElement("div");
    root.id = "fantareal-mobile-chat-root";
    root.addEventListener("click", onClick);
    root.addEventListener("submit", onSubmit);
    root.addEventListener("pointerdown", onPointerDown);
    root.addEventListener("mousedown", onMouseDown);
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", finishFabDrag);
    window.addEventListener("pointercancel", finishFabDrag);
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", finishMouseDrag);
    window.addEventListener("resize", () => requestAnimationFrame(applyResponsivePositions));
    document.body.appendChild(root);
    render();
    void loadSettings();
    void loadStickers();
    void loadApps();
    void loadChannels();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
