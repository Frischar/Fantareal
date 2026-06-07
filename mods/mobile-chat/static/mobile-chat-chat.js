(() => {
  "use strict";

  const script = document.currentScript;
  const scriptUrl = script && script.src ? script.src : "";
  const staticIndex = scriptUrl.indexOf("/static/");
  const modBase = staticIndex >= 0 ? scriptUrl.slice(0, staticIndex) : "/mods/mobile-chat/app";
  const modHostBase = modBase.replace(/\/app\/?$/, "") || "/mods/mobile-chat";
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
    flame: '<svg viewBox="0 0 24 24"><path d="M12 22a7 7 0 0 0 7-7c0-3.8-2.8-6.2-4.4-8.6-.5 2.7-2 4.1-3.7 5.5.2-2.4-.9-4.2-2.2-5.9C7.7 9.2 5 11.4 5 15a7 7 0 0 0 7 7Z"/></svg>',
    heart: '<svg viewBox="0 0 24 24"><path d="M20.8 5.6a5.5 5.5 0 0 0-7.8 0L12 6.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 22l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8Z"/></svg>',
    image: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="m8 14 2.4-2.4a1.4 1.4 0 0 1 2 0L17 16"/><circle cx="8.5" cy="9.5" r="1.5"/></svg>',
    live: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="m10 9 5 3-5 3V9Z"/><path d="M7 2v3m10-3v3m-7 16h4"/></svg>',
    location: '<svg viewBox="0 0 24 24"><path d="M12 21s7-5.3 7-12a7 7 0 1 0-14 0c0 6.7 7 12 7 12Z"/><circle cx="12" cy="9" r="2.5"/></svg>',
    mail: '<svg viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="m4 7 8 6 8-6"/></svg>',
    message: '<svg viewBox="0 0 24 24"><path d="M5 18.5A8 8 0 1 1 8.2 21L4 22l1-3.5Z"/><path d="M8 12h.01M12 12h.01M16 12h.01"/></svg>',
    mic: '<svg viewBox="0 0 24 24"><path d="M12 3a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Z"/><path d="M5 10v1a7 7 0 0 0 14 0v-1M12 18v4m-4 0h8"/></svg>',
    more: '<svg viewBox="0 0 24 24"><path d="M6 12h.01M12 12h.01M18 12h.01"/></svg>',
    phone: '<svg viewBox="0 0 24 24"><rect x="6" y="2.5" width="12" height="19" rx="3"/><path d="M10 5h4m-2 13.5h.01"/></svg>',
    phoneOff: '<svg viewBox="0 0 24 24"><path d="M10.2 5.3 9.3 3.4A2 2 0 0 0 7.5 2H4.8A2 2 0 0 0 3 4.3c.5 3.3 2 6.4 4.4 8.8S12.9 17 16.2 17.5a2 2 0 0 0 2.3-1.8v-2.7a2 2 0 0 0-1.4-1.9l-1.9-.7a2 2 0 0 0-2 .4l-.8.8a12 12 0 0 1-4-4l.8-.8a2 2 0 0 0 .4-2Z"/><path d="M3 3l18 18"/></svg>',
    plus: '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg>',
    refresh: '<svg viewBox="0 0 24 24"><path d="M20 11a8 8 0 0 0-14.9-3M4 4v4h4m-4 5a8 8 0 0 0 14.9 3M20 20v-4h-4"/></svg>',
    settings: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.86 2.86-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6v.08h-4V20a1.7 1.7 0 0 0-1-.6 1.7 1.7 0 0 0-1.88.34l-.06.06-2.86-2.86.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-.6-1h-.08v-4H4a1.7 1.7 0 0 0 .6-1 1.7 1.7 0 0 0-.34-1.88l-.06-.06L7.06 4.2l.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-.6v-.08h4V4a1.7 1.7 0 0 0 1 .6 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.86 2.86-.06.06A1.7 1.7 0 0 0 19.4 9a1.7 1.7 0 0 0 .6 1h.08v4H20a1.7 1.7 0 0 0-.6 1Z"/></svg>',
    smile: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M8.5 10h.01m6.99 0h.01M8 14a5 5 0 0 0 8 0"/></svg>',
    spark: '<svg viewBox="0 0 24 24"><path d="M12 2l1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z"/></svg>',
    toolbox: '<svg viewBox="0 0 24 24"><path d="M9 6V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v1"/><rect x="3" y="6" width="18" height="14" rx="3"/><path d="M3 12h18M10 12v2h4v-2"/></svg>',
    trash: '<svg viewBox="0 0 24 24"><path d="M4 7h16m-10 4v6m4-6v6M9 7l1-3h4l1 3m3 0-1 14H7L6 7"/></svg>',
    users: '<svg viewBox="0 0 24 24"><path d="M16 20v-1a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v1m7-9a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm13 9v-1a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    volume: '<svg viewBox="0 0 24 24"><path d="M4 9v6h4l5 4V5L8 9H4Z"/><path d="M17 9.5a4 4 0 0 1 0 5M20 7a8 8 0 0 1 0 10"/></svg>',
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
    currentChannelEventId: "",
    channelTabs: {},
    channelAuthorFilters: {},
    mailDrafts: {},
    channelComposerOpen: {},
    channelReplyOpen: {},
    diaryRoleId: "",
    calendarSelectedDate: "",
    channelListScrollTops: {},
    notifications: [],
    phoneSessions: [],
    phoneRoles: [],
    currentPhoneRoleId: "",
    currentPhoneSessionId: "",
    phoneComposerOpen: false,
    phoneSpeakerOn: true,
    newPhoneLineIds: [],
    notificationFilter: "all",
    currentGroupId: "",
    open: false,
    page: "home",
    loading: false,
    generating: false,
    generationTask: null,
    roleGeneratorForm: {},
    roleGeneratorDrafts: [],
    roleGeneratorSaved: [],
    disabledRoles: [],
    roleGeneratorSelectedIndex: 0,
    roleGeneratorBusy: false,
    roleGeneratorNotice: "",
    liveFollows: {},
    revealedLiveThoughts: {},
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
  let activeGenerationAbort = null;
  let phoneLineAnimationTimer = 0;
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

  function groupHasUser(group) {
    return Boolean(group && Array.isArray(group.members) && group.members.some((item) => item.type === "user"));
  }

  function formatDate(value) {
    if (!value) return "";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
  }

  function currentChannel() {
    return state.channels.find((item) => item.channel_id === state.currentChannelId) || null;
  }

  function currentChannelEvents() {
    return state.channelEvents[state.currentChannelId] || [];
  }

  function currentChannelEvent() {
    return currentChannelEvents().find((item) => item.event_id === state.currentChannelEventId) || null;
  }

  function phoneStatusLabel(status, session = null) {
    if (status === "ended" && session?.ended_by === "role") return "对方已挂断";
    if (status === "ended" && session?.ended_by === "user") return "你已挂断";
    const labels = {
      active: "通话中",
      ongoing: "通话中",
      ringing: "响铃中",
      dialing: "拨号中",
      ended: "已结束",
      missed: "未接通",
    };
    return labels[status] || status || "通话中";
  }

  function phoneElapsedLabel(session) {
    if (!session?.started_at) return "00:00";
    const started = new Date(session.started_at);
    if (Number.isNaN(started.getTime())) return "00:00";
    const totalSeconds = Math.max(0, Math.floor((Date.now() - started.getTime()) / 1000));
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }

  function currentPhoneRole(roles) {
    return roles.find((item) => item.role_id === state.currentPhoneRoleId) || null;
  }

  function isPhoneSessionEnded(session) {
    return Boolean(session && ["ended", "missed"].includes(session.status));
  }

  function phoneLineKind(line) {
    if (line.source === "user" || line.speaker_id === "user") return "user";
    const content = String(line.content || "").trim();
    const mood = String(line.mood || "").toLowerCase();
    if (/^[（(]/.test(content) || mood.includes("inner") || mood.includes("thought")) return "thought";
    return "spoken";
  }

  function phoneLineLabel(line) {
    const kind = phoneLineKind(line);
    if (kind === "user") return "我";
    if (kind === "thought") return "内心";
    return "通话";
  }

  function metadataValueText(value) {
    if (value === null || value === undefined) return "";
    if (Array.isArray(value) || typeof value === "object") {
      try {
        return JSON.stringify(value);
      } catch {
        return String(value);
      }
    }
    return String(value);
  }

  function eventMetadataRows(event) {
    return Object.entries(event?.metadata || {})
      .filter(([key, value]) => key !== "replies" && metadataValueText(value))
      .map(([key, value]) => [key, metadataValueText(value)]);
  }

  function forumReplies(event) {
    const rows = event?.metadata?.replies;
    if (!Array.isArray(rows)) return [];
    return rows
      .map((reply, index) => ({
        floor: Number.parseInt(reply?.floor, 10) || index + 1,
        author_name: reply?.author_name || reply?.speaker_name || reply?.author || "System",
        author_type: reply?.author_type || reply?.source_type || "role",
        source: reply?.source || "",
        content: reply?.content || reply?.body || "",
        mood: reply?.mood || "",
        created_at: reply?.created_at || "",
      }))
      .filter((reply) => reply.content);
  }

  function authorTypeLabel(type) {
    const labels = { role: "角色", bystander: "路人", moderator: "版主", system: "System", user: "你" };
    return labels[type] || type || "角色";
  }

  function forumRepliesMarkup(event, title = "楼层回复") {
    const replies = forumReplies(event);
    if (!replies.length) return "";
    return `
      <div class="fmcp-forum-replies">
        <div class="fmcp-forum-replies-title">${esc(title)} · ${replies.length}</div>
        ${replies.map((reply) => `
          <article class="fmcp-forum-reply">
            <div class="fmcp-event-meta">#${esc(reply.floor)} · ${esc(reply.author_name)} <span class="fmcp-reply-source is-${esc(reply.author_type)}">${esc(authorTypeLabel(reply.author_type))}</span>${reply.mood ? ` · ${esc(reply.mood)}` : ""}${formatDate(reply.created_at) ? ` · ${esc(formatDate(reply.created_at))}` : ""}</div>
            <p>${esc(reply.content)}</p>
          </article>
        `).join("")}
      </div>
    `;
  }

  function channelTypeLabel(type) {
    const labels = { feed: "动态", forum: "论坛", mail: "邮箱", diary: "日记", calendar: "日程", live: "直播" };
    return labels[type] || type || "频道";
  }

  function eventTypeLabel(type) {
    const labels = { post: "动态", thread: "帖子", reply: "回复", mail: "邮件", diary: "日记", calendar: "日程", live: "直播" };
    return labels[type] || type || "内容";
  }

  function isFallbackEvent(event) {
    return Array.isArray(event?.tags) && event.tags.includes("fallback");
  }

  function eventContentText(event) {
    if (!isFallbackEvent(event)) return event?.content || "";
    return "模型本次没有返回可用的频道结构，已记录为失败占位。请稍后重试生成。";
  }

  function eventStats(event, index = 0) {
    const replies = forumReplies(event).length;
    const tagWeight = Array.isArray(event?.tags) ? event.tags.length : 0;
    const seed = Math.max(1, (event?.title || "").length + (event?.content || "").length + index * 17);
    return {
      views: seed * 37 + 820,
      comments: replies || Math.max(1, tagWeight + index),
      likes: Math.max(0, tagWeight * 2 + replies),
    };
  }

  function initials(name) {
    const text = String(name || "S").trim();
    return Array.from(text).slice(0, 2).join("");
  }

  function channelSeedCopy(channel) {
    const label = channelTypeLabel(channel?.type);
    return `正在生成${label}内容...`;
  }

  function channelSeedCount(channel) {
    const configured = Number.parseInt(channel?.seed_count, 10);
    const count = Number.isFinite(configured) && configured > 0 ? configured : 5;
    return channel?.type === "forum" ? 1 : count;
  }

  function generationOverlayMarkup() {
    if (!state.generationTask) return "";
    return `
      <div class="fmcp-generation-overlay" role="status" aria-live="polite">
        <div class="fmcp-generation-spinner" aria-hidden="true">
          <span></span><span></span><span></span><span></span><span></span><span></span>
        </div>
        <div class="fmcp-generation-text">${esc(state.generationTask.message || "正在生成内容...")}</div>
        <button class="fmcp-generation-stop" type="button" data-action="cancel-generation">
          <span aria-hidden="true"></span>
          ${esc(state.generationTask.cancelLabel || "停止生成")}
        </button>
      </div>
    `;
  }

  function eventStatsMarkup(event, index = 0) {
    const stats = eventStats(event, index);
    return `
      <span>浏览 ${stats.views}</span>
      <span>评论 ${stats.comments}</span>
      ${stats.likes ? `<span>赞 ${stats.likes}</span>` : ""}
    `;
  }

  function channelTabs(channel) {
    const type = channel?.type;
    if (type === "feed") return [
      ["home", "首页"],
      ["discover", "发现"],
      ["notice", "通知"],
      ["mine", "我的"],
    ];
    if (type === "forum") return [
      ["nearby", "附近"],
      ["discover", "发现"],
      ["hot", "热搜"],
    ];
    if (type === "live") return [
      ["recommend", "推荐"],
      ["living", "直播中"],
      ["chat", "聊天"],
      ["music", "音乐"],
    ];
    if (type === "mail") return [
      ["inbox", "收件箱"],
      ["unread", "未读"],
      ["draft", "草稿"],
    ];
    if (type === "diary") return [
      ["archive", "归档"],
      ["role", "角色"],
      ["mine", "我的"],
    ];
    if (type === "calendar") return [
      ["upcoming", "将来"],
      ["today", "今日"],
      ["all", "全部"],
    ];
    return [];
  }

  function currentChannelTab(channel) {
    const tabs = channelTabs(channel);
    const saved = state.channelTabs[channel?.channel_id || ""];
    return tabs.some(([id]) => id === saved) ? saved : tabs[0]?.[0] || "";
  }

  function channelTabsMarkup(channel) {
    const tabs = channelTabs(channel);
    if (!tabs.length) return "";
    const active = currentChannelTab(channel);
    return `
      <div class="fmcp-app-tabs">
        ${tabs.map(([id, label]) => `
          <button class="${id === active ? "is-active" : ""}" type="button" data-action="channel-tab" data-channel-id="${esc(channel.channel_id)}" data-tab-id="${esc(id)}">${esc(label)}</button>
        `).join("")}
      </div>
    `;
  }


  function eventAuthorOptions(events) {
    const seen = new Set();
    return (events || []).map((event) => event.author_name).filter((name) => {
      const key = String(name || "").trim().toLowerCase();
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    }).slice(0, 8);
  }

  function channelDepthStats(channel, events) {
    const rows = Array.isArray(events) ? events : [];
    const replies = rows.reduce((sum, event) => sum + eventReplies(event).length, 0);
    const tags = new Set(rows.flatMap((event) => Array.isArray(event.tags) ? event.tags : []));
    const authors = new Set(rows.map((event) => event.author_name).filter(Boolean));
    if (channel?.type === "feed") return [`${rows.length} 条动态`, `${authors.size} 位作者`, `${replies} 条回复`, `${tags.size} 个标签`];
    if (channel?.type === "forum") return [`${rows.length} 个帖子`, `${replies} 条回复`, `${authors.size} 位作者`, `${tags.size} 个标签`];
    if (channel?.type === "mail") return [`${rows.length} 封邮件`, `${Object.keys(state.mailDrafts).length} 封草稿`, `${authors.size} 位发件人`];
    if (channel?.type === "diary") return [`${rows.length} 篇日记`, `${authors.size} 位作者`, `${tags.size} 个标签`];
    if (channel?.type === "calendar") return [`${rows.length} 条日程`, `${tags.size} 个标签`, `${authors.size} 位参与者`];
    if (channel?.type === "live") return [`${rows.length} 个直播间`, `${authors.size} 位主播`, `${tags.size} 个标签`];
    return [`${rows.length} 条`];
  }

  function channelDepthSummaryMarkup(channel, events) {
    const stats = channelDepthStats(channel, events);
    return `<div class="fmcp-depth-summary">${stats.map((item) => `<span>${esc(item)}</span>`).join("")}</div>`;
  }

  function channelAuthorFilterMarkup(channel, events) {
    if (!channel || !["feed", "forum"].includes(channel.type)) return "";
    const active = state.channelAuthorFilters[channel.channel_id] || "";
    const authors = eventAuthorOptions(events);
    if (!authors.length) return "";
    return `
      <div class="fmcp-author-filter">
        <button class="${!active ? "is-active" : ""}" type="button" data-action="channel-author-filter" data-channel-id="${esc(channel.channel_id)}" data-author="">全部</button>
        ${authors.map((author) => `<button class="${active === author ? "is-active" : ""}" type="button" data-action="channel-author-filter" data-channel-id="${esc(channel.channel_id)}" data-author="${esc(author)}">${esc(author)}</button>`).join("")}
      </div>
    `;
  }

  function filteredChannelEvents(channel, events) {
    const tab = currentChannelTab(channel);
    let rows = Array.isArray(events) ? [...events] : [];
    const authorFilter = state.channelAuthorFilters[channel?.channel_id || ""] || "";
    if (authorFilter && ["feed", "forum"].includes(channel?.type)) {
      rows = rows.filter((event) => event.author_name === authorFilter);
    }
    if (channel?.type === "feed") {
      if (tab === "discover") {
        return rows.sort((a, b) => eventSocialScore(b) - eventSocialScore(a));
      }
      if (tab === "notice") {
        return rows.filter((event) => /通知|公告|提醒|系统|notice/i.test(eventSearchText(event)));
      }
      if (tab === "mine") {
        return rows.filter(isOwnEvent);
      }
      return rows;
    }
    if (channel?.type === "forum") {
      rows = rows.sort((a, b) => eventTimeValue(b) - eventTimeValue(a));
    }
    if (channel?.type === "forum" && tab === "nearby") {
      const nearby = rows.filter((event) => /附近|本地|街|巷|院|店|茶馆|门口|同城|nearby/i.test(eventSearchText(event)));
      return nearby.length ? nearby : rows;
    }
    if (channel?.type === "forum") return rows;
    if (channel?.type === "live") {
      if (tab === "living") return rows.filter((event) => /直播中|live|on/i.test(metadataValueText(event.metadata?.live_status) || "直播中"));
      if (tab === "chat") {
        const chatRows = rows.filter((event) => /聊天|闲聊|问答|茶话|talk|chat/i.test(eventSearchText(event)));
        return chatRows.length ? chatRows : rows;
      }
      if (tab === "music") {
        const musicRows = rows.filter((event) => /音乐|唱|歌|曲|琴|music|song/i.test(eventSearchText(event)));
        return musicRows.length ? musicRows : rows;
      }
      return rows.sort((a, b) => Number.parseInt(metadataValueText(b.metadata?.viewers), 10) - Number.parseInt(metadataValueText(a.metadata?.viewers), 10));
    }
    if (channel?.type === "mail") {
      if (tab === "unread") {
        return rows.filter((event, index) => isMailUnread(event, index, rows));
      }
      if (tab === "draft") {
        return rows.filter((event) => state.mailDrafts[event.event_id]);
      }
      return rows;
    }
    if (channel?.type === "calendar" && tab === "today") {
      const today = new Date().toISOString().slice(0, 10);
      return rows.filter((event) => String(event.created_at || "").slice(0, 10) === today || metadataValueText(event.metadata?.date).startsWith(today));
    }
    if (channel?.type === "calendar" && tab === "upcoming") {
      const today = new Date().toISOString().slice(0, 10);
      return rows.filter((event) => isoDateOnly(event.metadata?.date || event.created_at) >= today);
    }
    return rows;
  }

  function eventDateLabel(event) {
    const date = metadataValueText(event?.metadata?.date || event?.metadata?.time || event?.created_at);
    return date ? date.slice(0, 16).replace("T", " ") : "";
  }

  function eventLocationLabel(event) {
    return metadataValueText(event?.metadata?.location || event?.metadata?.place || event?.metadata?.地点);
  }

  function eventReplies(event) {
    const replies = event?.metadata?.replies;
    return Array.isArray(replies) ? replies : [];
  }

  function currentUserName() {
    return state.user?.name || state.user?.display_name || "我";
  }

  function eventSearchText(event) {
    return [
      event?.title,
      eventContentText(event),
      event?.author_name,
      event?.event_type,
      ...(Array.isArray(event?.tags) ? event.tags : []),
      ...eventMetadataRows(event).map(([, value]) => value),
    ].map((item) => String(item || "")).join(" ");
  }

  function eventSocialScore(event) {
    const stats = eventStats(event);
    return (stats.views || 0) + (stats.likes || 0) * 5 + eventReplies(event).length * 8;
  }

  function eventTimeValue(event) {
    const value = event?.created_at || event?.updated_at || event?.metadata?.date || "";
    const time = new Date(value).getTime();
    return Number.isFinite(time) ? time : 0;
  }

  function isOwnEvent(event) {
    const userNames = new Set([currentUserName(), state.user?.display_name, state.user?.name, "我"].filter(Boolean));
    return userNames.has(event?.author_name)
      || event?.source === "user"
      || metadataValueText(event?.metadata?.source) === "user"
      || metadataValueText(event?.metadata?.author_id) === "user";
  }

  function isMailUnread(event, index, rows) {
    const metadata = event?.metadata && typeof event.metadata === "object" ? event.metadata : {};
    if (event?.read !== undefined) return !event.read;
    if (metadata.read !== undefined) return !metadata.read;
    if (metadata.unread !== undefined) return Boolean(metadata.unread);
    if (metadata.status) return /未读|unread|new/i.test(metadataValueText(metadata.status));
    return index < Math.ceil((rows || []).length / 2);
  }

  function schedulePhoneLineAnimation(lineIds) {
    state.newPhoneLineIds = (lineIds || []).filter(Boolean);
    if (phoneLineAnimationTimer) window.clearTimeout(phoneLineAnimationTimer);
    if (!state.newPhoneLineIds.length) return;
    phoneLineAnimationTimer = window.setTimeout(() => {
      state.newPhoneLineIds = [];
      phoneLineAnimationTimer = 0;
      if (state.open && state.page === "phone") render();
    }, 1800);
  }

  function seedButtonMarkup(label = "生成内容") {
    return `
      <button class="fmcp-icon-btn fmcp-seed-button fmcp-seed-icon-button" type="button" data-action="seed-current-channel" ${state.generating ? "disabled" : ""} aria-label="${esc(label)}" title="${esc(label)}">
        ${icon("spark")}
      </button>
    `;
  }

  function feedBottomNavMarkup(channel) {
    const tabs = channelTabs(channel);
    const active = currentChannelTab(channel);
    const iconById = { home: "message", discover: "spark", notice: "bell", mine: "users" };
    return `
      <nav class="fmcp-feed-bottom-nav" aria-label="动态导航">
        ${tabs.slice(0, 2).map(([id, label]) => `
          <button class="${id === active ? "is-active" : ""}" type="button" data-action="channel-tab" data-channel-id="${esc(channel.channel_id)}" data-tab-id="${esc(id)}">
            ${icon(iconById[id] || "message")}<span>${esc(label)}</span>
          </button>
        `).join("")}
        <button class="fmcp-feed-compose-pivot" type="button" data-action="toggle-channel-compose" data-channel-id="${esc(channel.channel_id)}" aria-label="发布动态">${icon("plus")}</button>
        ${tabs.slice(2).map(([id, label]) => `
          <button class="${id === active ? "is-active" : ""}" type="button" data-action="channel-tab" data-channel-id="${esc(channel.channel_id)}" data-tab-id="${esc(id)}">
            ${icon(iconById[id] || "message")}<span>${esc(label)}</span>
          </button>
        `).join("")}
      </nav>
    `;
  }

  function forumTabsMarkup(channel) {
    const tabs = channelTabs(channel);
    const active = currentChannelTab(channel);
    const iconById = { nearby: "location", discover: "spark", hot: "flame" };
    return `
      <div class="fmcp-forum-tabs" aria-label="论坛分区">
        ${tabs.map(([id, label]) => `
          <button class="${id === active ? "is-active" : ""}" type="button" data-action="channel-tab" data-channel-id="${esc(channel.channel_id)}" data-tab-id="${esc(id)}">
            ${icon(iconById[id] || "forum")}<span>${esc(label)}</span>
          </button>
        `).join("")}
      </div>
    `;
  }

  function roleGeneratorAppOptions() {
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
      .filter((app) => app && app.app_id !== "assist" && app.page !== "assist")
      .map((app) => ({ app_id: String(app.app_id || ""), label: String(app.label || app.app_id || "") }))
      .filter((app) => {
        if (!app.app_id || seen.has(app.app_id)) return false;
        seen.add(app.app_id);
        return true;
      });
  }

  function roleGeneratorField(name) {
    const value = state.roleGeneratorForm && state.roleGeneratorForm[name];
    return typeof value === "string" ? value : "";
  }

  function roleGeneratorSelectedValues(name) {
    const value = state.roleGeneratorForm && state.roleGeneratorForm[name];
    return new Set(Array.isArray(value) ? value.map(String) : []);
  }

  function roleGeneratorScopeMarkup(name, label) {
    const selected = roleGeneratorSelectedValues(name);
    const options = roleGeneratorAppOptions();
    return `
      <div class="fmcp-generator-scope">
        <span>${esc(label)}</span>
        <div>
          ${options.map((app) => `
            <label>
              <input type="checkbox" name="${esc(name)}" value="${esc(app.app_id)}" ${selected.has(app.app_id) ? "checked" : ""}>
              <small>${esc(app.label)}</small>
            </label>
          `).join("")}
        </div>
      </div>
    `;
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
      source: "role_generator",
    };
  }

  function roleGeneratorChips(values) {
    const rows = Array.isArray(values) ? values : [];
    return rows.length ? rows.map((item) => `<span>${esc(item)}</span>`).join("") : "<span>未限定</span>";
  }

  function roleGeneratorDraftField(index, field, label, value, options = {}) {
    const tag = options.multiline ? "textarea" : "input";
    const extraClass = options.wide ? " is-wide" : "";
    const attrs = [
      `class="${options.multiline ? "fmcp-textarea" : "fmcp-input"}"`,
      `data-role-draft-field="${esc(field)}"`,
      `data-draft-index="${index}"`,
      options.maxlength ? `maxlength="${options.maxlength}"` : "",
      options.placeholder ? `placeholder="${esc(options.placeholder)}"` : "",
    ].filter(Boolean).join(" ");
    return `
      <label class="fmcp-field fmcp-generator-edit-field${extraClass}">
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
      <div class="fmcp-generator-scope fmcp-generator-edit-scope">
        <span>${esc(label)}</span>
        <div>
          ${roleGeneratorAppOptions().map((app) => `
            <label>
              <input type="checkbox" data-role-draft-scope="${esc(field)}" data-draft-index="${index}" value="${esc(app.app_id)}" ${selected.has(app.app_id) ? "checked" : ""}>
              <small>${esc(app.label)}</small>
            </label>
          `).join("")}
        </div>
      </div>
    `;
  }

  function roleGeneratorDraftPreview(draft, index = 0) {
    if (!draft) {
      return '<div class="fmcp-empty"><div>还没有草稿</div></div>';
    }
    return `
      <article class="fmcp-generator-preview">
        <div class="fmcp-generator-preview-head">
          ${avatarMarkup({ name: draft.display_name, avatar: draft.avatar }, "fmcp-role-avatar")}
          <div>
            <strong>编辑草稿</strong>
            <span>改完后直接保存选中或全部保存。</span>
          </div>
        </div>
        <div class="fmcp-generator-edit-grid">
          ${roleGeneratorDraftField(index, "display_name", "名字", draft.display_name, { maxlength: 80 })}
          ${roleGeneratorDraftField(index, "role_id", "角色 ID", draft.role_id, { maxlength: 120, placeholder: "留空则按名字生成" })}
          ${roleGeneratorDraftField(index, "identity", "身份", draft.identity, { maxlength: 160, wide: true })}
          ${roleGeneratorDraftField(index, "appearance", "外观", draft.appearance, { maxlength: 260, multiline: true, wide: true })}
          ${roleGeneratorDraftField(index, "summary", "摘要", draft.summary, { maxlength: 500, multiline: true, wide: true })}
          ${roleGeneratorDraftField(index, "chat_style", "说话风格", draft.chat_style, { maxlength: 500, multiline: true, wide: true })}
        </div>
        ${roleGeneratorDraftScopeEditor(draft, index, "suitable_apps", "适合出现的 App")}
        ${roleGeneratorDraftScopeEditor(draft, index, "blocked_apps", "禁止出现的 App")}
      </article>
    `;
  }

  function updateRoleGeneratorDraftField(index, field, value) {
    const drafts = state.roleGeneratorDrafts || [];
    const draft = drafts[index];
    if (!draft) return;
    draft[field] = String(value || "");
  }

  function updateRoleGeneratorDraftScope(index, field, input) {
    const drafts = state.roleGeneratorDrafts || [];
    const draft = drafts[index];
    if (!draft) return;
    const checked = [...root.querySelectorAll(`[data-role-draft-scope="${CSS.escape(field)}"][data-draft-index="${index}"]:checked`)]
      .map((item) => String(item.value || ""))
      .filter(Boolean);
    draft[field] = checked;
  }

  function roleChoices() {
    const seen = new Set();
    const rows = [];
    const add = (role) => {
      const id = role?.role_id || role?.id || role?.display_name || role?.name;
      const name = role?.display_name || role?.name || role?.role_name;
      if (!id || !name || seen.has(id)) return;
      seen.add(id);
      rows.push({ role_id: id, display_name: name, avatar: role.avatar || "" });
    };
    state.phoneRoles.forEach(add);
    state.roles.forEach(add);
    state.groups.forEach((group) => (group.members || []).forEach((member) => {
      if (member.type === "character") add({ role_id: member.role_id, display_name: member.name, avatar: member.avatar });
    }));
    return rows;
  }

  function selectedDiaryRole() {
    const roles = roleChoices();
    if (!state.diaryRoleId && roles[0]) state.diaryRoleId = roles[0].role_id;
    return roles.find((role) => role.role_id === state.diaryRoleId) || roles[0] || null;
  }

  function eventRoleKey(event) {
    return metadataValueText(event?.metadata?.role_id || event?.metadata?.role || event?.author_id || event?.author_name);
  }

  function isoDateOnly(value) {
    const text = metadataValueText(value);
    if (/^\d{4}-\d{2}-\d{2}/.test(text)) return text.slice(0, 10);
    const date = text ? new Date(text) : new Date();
    if (Number.isNaN(date.getTime())) return new Date().toISOString().slice(0, 10);
    return date.toISOString().slice(0, 10);
  }

  function selectedCalendarDate(events) {
    const dates = [...new Set((events || [])
      .map((event) => isoDateOnly(event?.metadata?.date || event?.created_at))
      .filter(Boolean))]
      .sort();
    if (state.calendarSelectedDate && dates.includes(state.calendarSelectedDate)) return state.calendarSelectedDate;
    state.calendarSelectedDate = dates[0] || state.calendarSelectedDate || isoDateOnly(new Date());
    return state.calendarSelectedDate;
  }

  function channelComposerMarkup(channel, options = {}) {
    if (!["feed", "forum"].includes(channel.type)) return "";
    const open = !!state.channelComposerOpen[channel.channel_id];
    const label = channel.type === "forum" ? "发布新帖" : "发布动态";
    if (!open) {
      if (options.hideClosed) return "";
      return `<button class="fmcp-floating-compose" type="button" data-action="toggle-channel-compose" data-channel-id="${esc(channel.channel_id)}">${icon("plus")}<span>${esc(label)}</span></button>`;
    }
    return `
      <form class="fmcp-channel-compose" data-form="channel-post" data-channel-id="${esc(channel.channel_id)}">
        <label>${esc(label)}</label>
        <input name="title" maxlength="120" placeholder="标题（动态可留空）">
        <textarea name="content" maxlength="1200" required placeholder="写点什么，发送后角色会自动互动。"></textarea>
        <div class="fmcp-compose-actions">
          <button class="fmcp-button" type="button" data-action="toggle-channel-compose" data-channel-id="${esc(channel.channel_id)}">取消</button>
          <button class="fmcp-button fmcp-button-primary" type="submit" ${state.generating ? "disabled" : ""}>发送并生成回复</button>
        </div>
      </form>
    `;
  }

  function eventReplyFormMarkup(channel, event) {
    if (!["feed", "forum"].includes(channel.type) || isFallbackEvent(event)) return "";
    const key = `${channel.channel_id}:${event.event_id}`;
    const open = !!state.channelReplyOpen[key];
    const label = channel.type === "forum" ? "回复帖子" : "评论动态";
    if (!open) {
      return `<button class="fmcp-button fmcp-button-primary" type="button" data-action="toggle-channel-reply" data-channel-id="${esc(channel.channel_id)}" data-event-id="${esc(event.event_id)}">${esc(label)}</button>`;
    }
    return `
      <form class="fmcp-channel-reply-form" data-form="channel-reply" data-channel-id="${esc(channel.channel_id)}" data-event-id="${esc(event.event_id)}">
        <label>${esc(label)}</label>
        <textarea name="content" maxlength="800" required placeholder="写下你的回复，角色会继续接话。"></textarea>
        <div class="fmcp-compose-actions">
          <button class="fmcp-button" type="button" data-action="toggle-channel-reply" data-channel-id="${esc(channel.channel_id)}" data-event-id="${esc(event.event_id)}">取消</button>
          <button class="fmcp-button fmcp-button-primary" type="submit" ${state.generating ? "disabled" : ""}>回复并生成互动</button>
        </div>
      </form>
    `;
  }

  function eventParticipantsLabel(event) {
    const raw = event?.metadata?.participants || event?.metadata?.roles || event?.metadata?.参与者;
    return metadataValueText(raw);
  }

  function textParagraphs(text) {
    const rows = String(text || "")
      .split(/\n{1,}|\s*；\s*/g)
      .map((item) => item.trim())
      .filter(Boolean);
    return rows.length ? rows : [String(text || "").trim()].filter(Boolean);
  }

  function structuredRows(value) {
    if (Array.isArray(value)) return value;
    if (typeof value === "string" && value.trim().startsWith("[")) {
      try {
        const parsed = JSON.parse(value);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    }
    return [];
  }

  function mailReplies(event) {
    return structuredRows(event?.metadata?.replies)
      .map((reply) => ({
        reply_id: reply?.reply_id || reply?.id || "",
        author_name: reply?.author_name || reply?.author || "System",
        direction: reply?.direction === "sent" ? "sent" : "received",
        content: reply?.content || reply?.body || "",
        mood: reply?.mood || "",
        created_at: reply?.created_at || "",
      }))
      .filter((reply) => reply.content);
  }

  function liveRows(value) {
    return structuredRows(value)
      .map((item) => ({
        author_name: item?.author_name || item?.name || item?.author || "观众",
        author_type: item?.author_type || "bystander",
        content: item?.content || item?.body || item?.text || item?.note || "",
        mood: item?.mood || "",
        amount: item?.amount || "",
      }))
      .filter((item) => item.content || item.amount);
  }

  function liveContributors(value) {
    return structuredRows(value)
      .map((item) => ({
        name: item?.name || item?.author_name || "观众",
        amount: item?.amount || item?.score || item?.gift || "1",
        note: item?.note || item?.content || "",
      }))
      .filter((item) => item.name);
  }

  function feedEventCardMarkup(event, index) {
    return `
      <button class="fmcp-event-card fmcp-event-card-button fmcp-feed-card is-${esc(event.channel_type)}${isFallbackEvent(event) ? " is-fallback" : ""}" type="button" data-action="open-channel-event" data-channel-id="${esc(event.channel_id)}" data-event-id="${esc(event.event_id)}">
        <span class="fmcp-feed-author">
          <span class="fmcp-feed-avatar">${esc(initials(event.author_name))}</span>
          <span>
            <strong>${esc(event.author_name || "System")}</strong>
            <small>${formatDate(event.created_at) ? esc(formatDate(event.created_at)) : eventTypeLabel(event.event_type)}</small>
          </span>
          <span class="fmcp-feed-card-more">${icon("more")}</span>
        </span>
        <span class="fmcp-feed-copy">${esc(eventContentText(event))}</span>
        ${!isFallbackEvent(event) ? `<span class="fmcp-feed-card-media">${icon("image")}</span>` : ""}
        ${(event.tags || []).length && !isFallbackEvent(event) ? `<span class="fmcp-feed-inline-tags">${event.tags.slice(0, 3).map((tag) => `<span>${esc(tag)}</span>`).join("")}</span>` : ""}
        <span class="fmcp-feed-card-actions">${eventStatsMarkup(event, index)}</span>
      </button>
    `;
  }

  function forumEventCardMarkup(event, index) {
    const tags = event.tags || [];
    const pinned = tags.some((tag) => /公告|置顶|预警|官方/.test(String(tag)));
    const created = formatDate(event.created_at);
    return `
      <button class="fmcp-event-card fmcp-event-card-button fmcp-forum-card is-${esc(event.channel_type)}${pinned ? " is-pinned" : ""}${isFallbackEvent(event) ? " is-fallback" : ""}" type="button" data-action="open-channel-event" data-channel-id="${esc(event.channel_id)}" data-event-id="${esc(event.event_id)}">
        <span class="fmcp-forum-title-row">
          ${pinned ? '<span class="fmcp-pin-badge">公告</span>' : ""}
          <strong>${esc(event.title)}</strong>
        </span>
        <span class="fmcp-event-card-copy">${esc(eventContentText(event))}</span>
        ${tags.length && !isFallbackEvent(event) ? `<span class="fmcp-forum-badges">${tags.slice(0, 2).map((tag, tagIndex) => `<span class="${pinned && tagIndex === 0 ? "is-official" : ""}">${esc(tag)}</span>`).join("")}${pinned ? '<span>置顶</span>' : ""}</span>` : ""}
        <span class="fmcp-forum-footer">
          <span class="fmcp-forum-author">${esc(event.author_name || "System")}</span>
          ${created ? `<span class="fmcp-forum-time">${esc(created)}</span>` : ""}
          <span class="fmcp-social-stats">${eventStatsMarkup(event, index)}</span>
        </span>
      </button>
    `;
  }

  function genericEventCardMarkup(event, index) {
    return `
      <button class="fmcp-event-card fmcp-event-card-button is-${esc(event.channel_type)}${isFallbackEvent(event) ? " is-fallback" : ""}" type="button" data-action="open-channel-event" data-channel-id="${esc(event.channel_id)}" data-event-id="${esc(event.event_id)}">
        <span class="fmcp-event-meta">${esc(event.author_name)} · ${esc(eventTypeLabel(event.event_type))} · ${formatDate(event.created_at) ? esc(formatDate(event.created_at)) : ""}</span>
        <strong>${esc(event.title)}</strong>
        <span class="fmcp-event-card-copy">${esc(eventContentText(event))}</span>
        ${(event.tags || []).length && !isFallbackEvent(event) ? `<span class="fmcp-tag-row">${event.tags.map((tag) => `<span>${esc(tag)}</span>`).join("")}</span>` : ""}
        <span class="fmcp-social-stats">${eventStatsMarkup(event, index)}</span>
      </button>
    `;
  }

  function eventCardMarkup(event, index) {
    if (event.channel_type === "feed") return feedEventCardMarkup(event, index);
    if (event.channel_type === "forum") return forumEventCardMarkup(event, index);
    if (event.channel_type === "live") return liveEventCardMarkup(event, index);
    if (event.channel_type === "mail") return mailEventCardMarkup(event, index);
    if (event.channel_type === "diary") return diaryEventCardMarkup(event, index);
    if (event.channel_type === "calendar") return calendarEventCardMarkup(event, index);
    return genericEventCardMarkup(event, index);
  }

  function mailEventCardMarkup(event) {
    const replyCount = mailReplies(event).length;
    return `
      <button class="fmcp-event-card fmcp-event-card-button fmcp-mail-card${isFallbackEvent(event) ? " is-fallback" : ""}" type="button" data-action="open-channel-event" data-channel-id="${esc(event.channel_id)}" data-event-id="${esc(event.event_id)}">
        <span class="fmcp-mail-row">
          <span class="fmcp-mail-avatar">${esc(initials(event.author_name))}</span>
          <span>
            <strong>${esc(event.title)}</strong>
            <small>${esc(event.author_name || "System")} · ${formatDate(event.created_at) ? esc(formatDate(event.created_at)) : "邮件"}</small>
          </span>
        </span>
        <span class="fmcp-event-card-copy">${esc(eventContentText(event))}</span>
        ${replyCount ? `<span class="fmcp-draft-badge">往来 ${replyCount}</span>` : ""}
        ${state.mailDrafts[event.event_id] ? '<span class="fmcp-draft-badge">已暂存草稿</span>' : ""}
      </button>
    `;
  }

  function liveEventCardMarkup(event) {
    const danmaku = liveRows(event.metadata?.danmaku);
    const status = metadataValueText(event.metadata?.live_status) || "直播中";
    const viewers = metadataValueText(event.metadata?.viewers) || "实时";
    return `
      <button class="fmcp-event-card fmcp-event-card-button fmcp-live-card${isFallbackEvent(event) ? " is-fallback" : ""}" type="button" data-action="open-channel-event" data-channel-id="${esc(event.channel_id)}" data-event-id="${esc(event.event_id)}">
        <span class="fmcp-live-thumb">${icon("live")}</span>
        <span class="fmcp-live-card-main">
          <strong>${esc(event.title)}</strong>
          <span>${esc(eventContentText(event))}</span>
          <small>${esc(event.author_name || "主播")} · ${esc(status)} · ${esc(viewers)} 人观看 · ${danmaku.length} 条弹幕</small>
        </span>
      </button>
    `;
  }

  function diaryEventCardMarkup(event) {
    return `
      <button class="fmcp-event-card fmcp-event-card-button fmcp-diary-card${isFallbackEvent(event) ? " is-fallback" : ""}" type="button" data-action="open-channel-event" data-channel-id="${esc(event.channel_id)}" data-event-id="${esc(event.event_id)}">
        <span class="fmcp-diary-date">${esc(eventDateLabel(event) || formatDate(event.created_at) || "今日")}</span>
        <strong>${esc(event.title)}</strong>
        <span class="fmcp-event-card-copy">${esc(eventContentText(event))}</span>
        ${(event.tags || []).length && !isFallbackEvent(event) ? `<span class="fmcp-tag-row">${event.tags.map((tag) => `<span>${esc(tag)}</span>`).join("")}</span>` : ""}
      </button>
    `;
  }

  function calendarEventCardMarkup(event) {
    const date = eventDateLabel(event) || formatDate(event.created_at) || "待定";
    const day = date.slice(8, 10) || "·";
    const month = date.slice(5, 7) || "日程";
    return `
      <button class="fmcp-event-card fmcp-event-card-button fmcp-calendar-card${isFallbackEvent(event) ? " is-fallback" : ""}" type="button" data-action="open-channel-event" data-channel-id="${esc(event.channel_id)}" data-event-id="${esc(event.event_id)}">
        <span class="fmcp-calendar-datebox"><strong>${esc(day)}</strong><small>${esc(month)}</small></span>
        <span class="fmcp-calendar-main">
          <strong>${esc(event.title)}</strong>
          <span>${esc(eventContentText(event))}</span>
          ${eventLocationLabel(event) ? `<small>${esc(eventLocationLabel(event))}</small>` : ""}
        </span>
      </button>
    `;
  }

  function eventDetailShell(channel, event, innerMarkup, options = {}) {
    return `
      <div class="fmcp-channel-app fmcp-channel-${esc(channel.type)} ${esc(options.extraClass || "")}">
        ${options.hideToolbar ? "" : `<div class="fmcp-toolbar">
          <span class="fmcp-help">${esc(channel.label)} · ${esc(eventTypeLabel(event.event_type))}</span>
          <button class="fmcp-button" type="button" data-action="show-channel-list">返回列表</button>
        </div>`}
        ${innerMarkup}
      </div>
    `;
  }

  function genericEventDetailMarkup(channel, event) {
    const metadataRows = eventMetadataRows(event);
    return eventDetailShell(channel, event, `
      <article class="fmcp-event-detail is-${esc(event.channel_type)}${isFallbackEvent(event) ? " is-fallback" : ""}">
        <div class="fmcp-event-meta">${esc(event.author_name)} · ${formatDate(event.created_at) ? esc(formatDate(event.created_at)) : ""}</div>
        <strong>${esc(event.title)}</strong>
        <p>${esc(eventContentText(event))}</p>
        ${(event.tags || []).length && !isFallbackEvent(event) ? `<div class="fmcp-tag-row">${event.tags.map((tag) => `<span>${esc(tag)}</span>`).join("")}</div>` : ""}
        ${metadataRows.length && !isFallbackEvent(event) ? `
          <dl class="fmcp-event-fields">
            ${metadataRows.map(([key, value]) => `
              <div>
                <dt>${esc(key)}</dt>
                <dd>${esc(value)}</dd>
              </div>
            `).join("")}
          </dl>
        ` : ""}
      </article>
    `);
  }

  function feedDetailMarkup(channel, event) {
    return eventDetailShell(channel, event, `
      <article class="fmcp-feed-detail${isFallbackEvent(event) ? " is-fallback" : ""}">
        <div class="fmcp-feed-author">
          <span class="fmcp-feed-avatar">${esc(initials(event.author_name))}</span>
          <span>
            <strong>${esc(event.author_name || "System")}</strong>
            <small>${formatDate(event.created_at) ? esc(formatDate(event.created_at)) : "动态"}</small>
          </span>
        </div>
        <p>${esc(eventContentText(event))}</p>
        ${!isFallbackEvent(event) ? '<div class="fmcp-feed-media-placeholder">图片 / 片段占位</div>' : ""}
        ${(event.tags || []).length && !isFallbackEvent(event) ? `<div class="fmcp-tag-row">${event.tags.map((tag) => `<span>${esc(tag)}</span>`).join("")}</div>` : ""}
        <div class="fmcp-feed-actions">${eventStatsMarkup(event)}</div>
        ${!isFallbackEvent(event) ? forumRepliesMarkup(event, "评论") : ""}
        ${eventReplyFormMarkup(channel, event)}
      </article>
    `, { hideToolbar: true, extraClass: "fmcp-feed-detail-page" });
  }

  function forumDetailMarkup(channel, event) {
    return eventDetailShell(channel, event, `
      <article class="fmcp-forum-detail${isFallbackEvent(event) ? " is-fallback" : ""}">
        <h3>${esc(event.title)}</h3>
        <div class="fmcp-forum-detail-meta">${esc(event.author_name || "System")} · ${eventStatsMarkup(event)} · ${formatDate(event.created_at) ? esc(formatDate(event.created_at)) : ""}</div>
        <p>${esc(eventContentText(event))}</p>
        ${(event.tags || []).length && !isFallbackEvent(event) ? `<div class="fmcp-tag-row">${event.tags.map((tag) => `<span>${esc(tag)}</span>`).join("")}</div>` : ""}
        ${!isFallbackEvent(event) ? forumRepliesMarkup(event) : ""}
        ${eventReplyFormMarkup(channel, event)}
      </article>
    `, { hideToolbar: true, extraClass: "fmcp-forum-detail-page" });
  }

  function mailDetailMarkup(channel, event) {
    const draft = state.mailDrafts[event.event_id] || "";
    const replies = mailReplies(event);
    return eventDetailShell(channel, event, `
      <article class="fmcp-mail-detail${isFallbackEvent(event) ? " is-fallback" : ""}">
        <div class="fmcp-mail-envelope">
          <span>From</span><strong>${esc(event.author_name || "System")}</strong>
          <span>To</span><strong>我</strong>
          <span>Date</span><strong>${formatDate(event.created_at) ? esc(formatDate(event.created_at)) : "未记录"}</strong>
        </div>
        <h3>${esc(event.title)}</h3>
        <p>${esc(eventContentText(event))}</p>
        ${replies.length ? `
          <div class="fmcp-mail-thread">
            <strong>往来回复 · ${replies.length}</strong>
            ${replies.map((reply) => `
              <article class="fmcp-mail-reply is-${esc(reply.direction)}">
                <small>${esc(reply.direction === "sent" ? "我" : reply.author_name)}${reply.mood ? ` · ${esc(reply.mood)}` : ""}${formatDate(reply.created_at) ? ` · ${esc(formatDate(reply.created_at))}` : ""}</small>
                <p>${esc(reply.content)}</p>
              </article>
            `).join("")}
          </div>
        ` : ""}
        <form class="fmcp-mail-draft" data-form="mail-reply" data-channel-id="${esc(channel.channel_id)}" data-event-id="${esc(event.event_id)}">
          <label>回复邮件</label>
          <textarea name="content" maxlength="1000" placeholder="写下回复，发送后会写入邮箱线程，并尝试生成对方回信。">${esc(draft)}</textarea>
          <div class="fmcp-compose-actions">
            <button class="fmcp-button" type="button" data-action="save-mail-draft" data-event-id="${esc(event.event_id)}">暂存</button>
            <button class="fmcp-button fmcp-button-primary" type="submit" ${state.generating ? "disabled" : ""}>发送并等待回信</button>
          </div>
          ${draft ? '<p class="fmcp-mail-draft-status">草稿已暂存在本次小手机会话中。</p>' : ""}
        </form>
      </article>
    `);
  }

  function diaryDetailMarkup(channel, event) {
    const metadata = event.metadata || {};
    const paragraphs = textParagraphs(eventContentText(event));
    return eventDetailShell(channel, event, `
      <article class="fmcp-diary-detail${isFallbackEvent(event) ? " is-fallback" : ""}">
        <div class="fmcp-diary-page-date">${esc(eventDateLabel(event) || formatDate(event.created_at) || "今日")}</div>
        <h3>${esc(event.title)}</h3>
        <div class="fmcp-diary-detail-body">
          ${paragraphs.map((paragraph) => `<p>${esc(paragraph)}</p>`).join("")}
        </div>
        <div class="fmcp-diary-facts">
          ${metadataValueText(metadata.mood) ? `<span><b>心情</b>${esc(metadataValueText(metadata.mood))}</span>` : ""}
          ${metadataValueText(metadata.related_people) ? `<span><b>相关</b>${esc(metadataValueText(metadata.related_people))}</span>` : ""}
          ${event.author_name ? `<span><b>记录</b>${esc(event.author_name)}</span>` : ""}
        </div>
        ${(event.tags || []).length && !isFallbackEvent(event) ? `<div class="fmcp-tag-row">${event.tags.map((tag) => `<span>${esc(tag)}</span>`).join("")}</div>` : ""}
      </article>
    `);
  }

  function calendarDetailMarkup(channel, event) {
    return eventDetailShell(channel, event, `
      <article class="fmcp-calendar-detail${isFallbackEvent(event) ? " is-fallback" : ""}">
        <div class="fmcp-calendar-hero-date">${esc(eventDateLabel(event) || formatDate(event.created_at) || "待定")}</div>
        <h3>${esc(event.title)}</h3>
        <p>${esc(eventContentText(event))}</p>
        <div class="fmcp-calendar-facts">
          ${eventLocationLabel(event) ? `<span><b>地点</b>${esc(eventLocationLabel(event))}</span>` : ""}
          ${eventParticipantsLabel(event) ? `<span><b>参与</b>${esc(eventParticipantsLabel(event))}</span>` : ""}
          <span><b>状态</b>${isFallbackEvent(event) ? "待重试" : "已记录"}</span>
        </div>
      </article>
    `);
  }

  function liveDetailMarkup(channel, event) {
    const metadata = event.metadata || {};
    const danmaku = liveRows(metadata.danmaku).slice(-30);
    const danmakuItems = danmaku.slice(-18);
    const highlights = liveRows(metadata.highlights).slice(0, 6);
    const contributors = liveContributors(metadata.contributors).slice(0, 8);
    const followed = !!state.liveFollows[event.event_id];
    const status = metadataValueText(metadata.live_status) || "直播中";
    const viewers = metadataValueText(metadata.viewers) || "1.2k";
    const topContributor = contributors[0];
    const innerThought = metadataValueText(metadata.inner_thought);
    const thoughtRevealed = !!state.revealedLiveThoughts[event.event_id];
    return eventDetailShell(channel, event, `
      <article class="fmcp-live-room fmcp-live-theater${isFallbackEvent(event) ? " is-fallback" : ""}">
        <div class="fmcp-live-room-head">
          <span class="fmcp-live-avatar">${esc(initials(event.author_name))}</span>
          <div>
            <strong>${esc(event.author_name || "主播")}</strong>
            <small>${metadataValueText(metadata.fans) ? `${esc(metadataValueText(metadata.fans))} 粉丝` : `${esc(viewers)} 观看`}</small>
          </div>
          <button class="fmcp-live-follow ${followed ? "is-active" : ""}" type="button" data-action="toggle-live-follow" data-event-id="${esc(event.event_id)}">${followed ? "已关注" : "+ 关注"}</button>
        </div>
        <section class="fmcp-live-player">
          <div class="fmcp-live-player-top">
            <span class="fmcp-live-badge">${icon("live")} ${esc(status)}</span>
            <span>${esc(viewers)} 观看</span>
          </div>
          <div class="fmcp-live-player-copy">
            <h3>${esc(event.title)}</h3>
            <p>${esc(eventContentText(event))}</p>
          </div>
          ${highlights[0] ? `<div class="fmcp-live-highlight-strip"><b>${esc(highlights[0].author_name)}</b>${esc(highlights[0].content)}</div>` : ""}
          <div class="fmcp-live-danmaku-stage" aria-label="滚动弹幕">
            ${danmakuItems.length ? danmakuItems.map((item, index) => `
              <p class="fmcp-live-danmaku-item" style="--lane:${index % 4};--delay:-${(index * 1.35).toFixed(2)}s;--duration:${(13.5 + (index % 5) * 0.9).toFixed(1)}s;">
                <b>${esc(item.author_name)}</b><span>${esc(item.content)}</span>
              </p>
            `).join("") : '<p class="fmcp-live-muted"><span>还没有弹幕。</span></p>'}
          </div>
          <div class="fmcp-live-player-foot">
            <span>直播内容</span><b>1/5</b>
            ${topContributor ? `<span class="fmcp-live-top-gift">#1 ${esc(topContributor.name)} ${esc(topContributor.amount)}</span>` : ""}
          </div>
        </section>
        <section class="fmcp-live-room-notes">
          ${innerThought ? `
            <label class="fmcp-live-thought-card">
              <input class="fmcp-live-thought-toggle" type="checkbox" data-change="toggle-live-thought" data-event-id="${esc(event.event_id)}" aria-label="查看内心想法"${thoughtRevealed ? " checked" : ""}>
              <span class="fmcp-live-note-head">
                <strong>${icon("heart")} 内心想法</strong>
                <span class="fmcp-live-thought-cta"><em class="is-closed">点击查看</em><em class="is-open">已清晰</em></span>
              </span>
              <span class="fmcp-live-thought-glass"><span>${esc(innerThought)}</span></span>
            </label>
          ` : ""}
          ${contributors.length ? `<div class="fmcp-live-note-card"><strong>贡献榜</strong><p>${contributors.slice(0, 3).map((item, index) => `#${index + 1} ${esc(item.name)} ${esc(item.amount)}`).join(" · ")}</p></div>` : ""}
        </section>
        <form class="fmcp-live-input" data-form="live-message" data-channel-id="${esc(channel.channel_id)}" data-event-id="${esc(event.event_id)}">
          <input name="content" maxlength="240" placeholder="发送弹幕">
          <button class="fmcp-live-like" type="button" data-action="toggle-live-follow" data-event-id="${esc(event.event_id)}" aria-label="喜欢">${icon("heart")}</button>
          <button class="fmcp-button fmcp-button-primary" type="submit">发送</button>
        </form>
      </article>
    `, { hideToolbar: true, extraClass: "fmcp-live-detail-page" });
  }

  function eventDetailMarkup(channel, event) {
    if (event.channel_type === "feed") return feedDetailMarkup(channel, event);
    if (event.channel_type === "forum") return forumDetailMarkup(channel, event);
    if (event.channel_type === "live") return liveDetailMarkup(channel, event);
    if (event.channel_type === "mail") return mailDetailMarkup(channel, event);
    if (event.channel_type === "diary") return diaryDetailMarkup(channel, event);
    if (event.channel_type === "calendar") return calendarDetailMarkup(channel, event);
    return genericEventDetailMarkup(channel, event);
  }

  function feedChannelMarkup(channel, events, visibleEvents) {
    const composer = channelComposerMarkup(channel, { hideClosed: true });
    return `
      <div class="fmcp-channel-app fmcp-channel-${esc(channel.type)} fmcp-feed-app">
        <div class="fmcp-feed-topbar">
          <span></span>
          <strong>${esc(channel.label)}</strong>
          ${seedButtonMarkup("刷新")}
        </div>
        ${composer ? `<div class="fmcp-feed-compose-panel">${composer}</div>` : ""}
        <div class="fmcp-feed-stream">
          ${visibleEvents.length ? visibleEvents.map((item, index) => eventCardMarkup(item, index)).join("") : '<div class="fmcp-empty"><div>暂无动态，可以点击底部加号发布。</div></div>'}
        </div>
        ${feedBottomNavMarkup(channel)}
      </div>
    `;
  }

  function forumChannelMarkup(channel, events, visibleEvents) {
    const composer = channelComposerMarkup(channel, { hideClosed: true });
    return `
      <div class="fmcp-channel-app fmcp-channel-${esc(channel.type)} fmcp-forum-app">
        <div class="fmcp-forum-topbar">
          <span></span>
          <strong>${esc(channel.label)}</strong>
          ${seedButtonMarkup("刷新")}
        </div>
        ${forumTabsMarkup(channel)}
        ${composer ? `<div class="fmcp-forum-compose-panel">${composer}</div>` : ""}
        <div class="fmcp-forum-board">
          ${visibleEvents.length ? visibleEvents.map((item, index) => eventCardMarkup(item, index)).join("") : '<div class="fmcp-empty"><div>暂无帖子，可以发布新帖或点击生成内容。</div></div>'}
        </div>
        ${state.channelComposerOpen[channel.channel_id] ? "" : `<button class="fmcp-forum-compose-fab" type="button" data-action="toggle-channel-compose" data-channel-id="${esc(channel.channel_id)}">${icon("plus")}<span>发布新帖</span></button>`}
      </div>
    `;
  }

  function liveChannelMarkup(channel, events, visibleEvents) {
    return `
      <div class="fmcp-channel-app fmcp-channel-${esc(channel.type)} fmcp-live-app">
        <div class="fmcp-live-hero">
          <strong>${esc(channel.label)}</strong>
          <span>${esc(channel.description || "正在直播的角色房间")}</span>
          ${seedButtonMarkup("生成直播间")}
        </div>
        ${channelTabsMarkup(channel)}
        ${channelDepthSummaryMarkup(channel, events)}
        <div class="fmcp-live-list">
          ${visibleEvents.length ? visibleEvents.map((item, index) => eventCardMarkup(item, index)).join("") : '<div class="fmcp-empty"><div>暂无直播间，可以点击生成直播。</div></div>'}
        </div>
      </div>
    `;
  }

  function mailChannelMarkup(channel, events, visibleEvents) {
    const activeTab = currentChannelTab(channel);
    const unread = events.filter((item, index) => isMailUnread(item, index, events)).length;
    const draftCount = Object.keys(state.mailDrafts).length;
    const folderButton = (id, label, count) => `
      <button class="${activeTab === id ? "is-active" : ""}" type="button" data-action="channel-tab" data-channel-id="${esc(channel.channel_id)}" data-tab-id="${esc(id)}">
        ${esc(label)} <b>${count}</b>
      </button>
    `;
    return `
      <div class="fmcp-channel-app fmcp-channel-${esc(channel.type)} fmcp-mail-client">
        <div class="fmcp-mail-topbar">
          <div><strong>${esc(channel.label)}</strong><span>${esc(channel.description || "角色邮箱")}</span></div>
          ${seedButtonMarkup("收取邮件")}
        </div>
        ${channelDepthSummaryMarkup(channel, events)}
        <div class="fmcp-mail-search">搜索邮件、角色或关键词</div>
        <div class="fmcp-mail-folders">
          ${folderButton("inbox", "收件箱", events.length)}
          ${folderButton("unread", "未读", unread)}
          ${folderButton("draft", "草稿", draftCount)}
        </div>
        <div class="fmcp-mail-list">
          ${visibleEvents.length ? visibleEvents.map((item, index) => eventCardMarkup(item, index)).join("") : '<div class="fmcp-empty"><div>暂无邮件，可以点击右上角收取。</div></div>'}
        </div>
      </div>
    `;
  }

  function diaryChannelMarkup(channel, events, visibleEvents) {
    const roles = roleChoices();
    const selected = selectedDiaryRole();
    const selectedKey = selected ? metadataValueText(selected.role_id || selected.display_name) : "";
    const roleEvents = selectedKey
      ? visibleEvents.filter((event) => {
          const key = eventRoleKey(event);
          return !key || key === selectedKey || key === selected.display_name || event.author_name === selected.display_name;
        })
      : visibleEvents;
    return `
      <div class="fmcp-channel-app fmcp-channel-${esc(channel.type)} fmcp-diary-app">
        <div class="fmcp-home-intro fmcp-diary-hero">
          <strong>${esc(channel.label)}</strong>
          <span>${esc(selected ? `${selected.display_name} 的日记` : channel.description || "角色日记")}</span>
        </div>
        ${channelDepthSummaryMarkup(channel, events)}
        <div class="fmcp-diary-roles">
          ${roles.length ? roles.map((role) => `
            <button class="fmcp-diary-role ${role.role_id === selected?.role_id ? "is-active" : ""}" type="button" data-action="select-diary-role" data-role-id="${esc(role.role_id)}">
              ${avatarMarkup({ name: role.display_name, avatar: role.avatar }, "fmcp-role-avatar")}
              <span>${esc(role.display_name)}</span>
            </button>
          `).join("") : '<div class="fmcp-empty"><div>暂无角色资料，先在群聊或后台导入角色。</div></div>'}
        </div>
        <div class="fmcp-toolbar">
          <span class="fmcp-help">${roleEvents.length} 篇日记</span>
          ${seedButtonMarkup("生成日记")}
        </div>
        <div class="fmcp-diary-list">
          ${roleEvents.length ? roleEvents.map((item, index) => eventCardMarkup(item, index)).join("") : '<div class="fmcp-empty"><div>这个角色暂时没有日记。</div></div>'}
        </div>
      </div>
    `;
  }

  function calendarChannelMarkup(channel, events, visibleEvents) {
    const calendarEvents = visibleEvents.length ? visibleEvents : events;
    const selectedDate = selectedCalendarDate(calendarEvents);
    const monthStart = new Date(`${selectedDate.slice(0, 7)}-01T00:00:00`);
    const year = monthStart.getFullYear();
    const month = monthStart.getMonth();
    const firstDay = monthStart.getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const byDate = new Map();
    calendarEvents.forEach((item) => {
      const key = isoDateOnly(item.metadata?.date || item.created_at);
      byDate.set(key, [...(byDate.get(key) || []), item]);
    });
    const cells = [];
    for (let i = 0; i < firstDay; i += 1) cells.push('<span class="fmcp-calendar-cell is-empty"></span>');
    for (let day = 1; day <= daysInMonth; day += 1) {
      const date = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
      const count = (byDate.get(date) || []).length;
      cells.push(`<button class="fmcp-calendar-cell ${date === selectedDate ? "is-active" : ""} ${count ? "has-events" : ""}" type="button" data-action="select-calendar-date" data-date="${esc(date)}" title="${count ? "有安排" : "暂无安排"}"><strong>${day}</strong>${count ? '<small class="fmcp-calendar-dot" aria-hidden="true"></small>' : ""}</button>`);
    }
    const dayEvents = byDate.get(selectedDate) || [];
    return `
      <div class="fmcp-channel-app fmcp-channel-${esc(channel.type)} fmcp-calendar-app">
        <div class="fmcp-calendar-month-head">
          <div><strong>${year} 年 ${month + 1} 月</strong><span>${esc(channel.description || "日历")}</span></div>
          ${seedButtonMarkup("生成日程")}
        </div>
        ${channelTabsMarkup(channel)}
        ${channelDepthSummaryMarkup(channel, events)}
        <div class="fmcp-calendar-weekdays"><span>日</span><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span></div>
        <div class="fmcp-calendar-grid">${cells.join("")}</div>
        <div class="fmcp-calendar-day-panel">
          <strong>${esc(selectedDate)} 当日安排</strong>
          <div class="fmcp-calendar-day-list">
            ${dayEvents.length ? dayEvents.map((item, index) => eventCardMarkup(item, index)).join("") : '<div class="fmcp-empty"><div>这一天暂无日程。</div></div>'}
          </div>
        </div>
      </div>
    `;
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
      const error = new Error(formatApiError(payload, response.status));
      error.payload = payload;
      error.status = response.status;
      throw error;
    }
    return payload;
  }

  function formatApiError(payload = {}, status = 0) {
    const raw = String(payload.error || payload.detail || `请求失败 (${status})`).trim();
    const lower = raw.toLowerCase();
    const lines = [];
    const suggestions = [];
    const context = payload.model_context || {};
    const structuredSuggestions = Array.isArray(payload.suggestions) ? payload.suggestions.filter(Boolean) : [];
    let title = raw || `请求失败 (${status})`;
    if (/模型服务返回\s*http\s*\d+/i.test(raw) || lower.includes("upstream=")) {
      const matched = raw.match(/模型服务返回\s*(HTTP\s*\d+)/i);
      title = matched ? `模型上游拒绝：${matched[1].toUpperCase()}` : "模型上游拒绝请求";
      suggestions.push("检查 API Key、Base URL 和模型名是否匹配当前供应商。", "尝试拉取模型列表或切换到已确认可用的模型。", "如果是 422/400，可尝试降低 max_tokens、temperature，或关闭/更换不兼容参数。", "如果是流式失败，可改用非流式或换供应商兼容网关。");
    } else if (lower.includes("超时") || lower.includes("timeout")) {
      title = "模型请求超时";
      suggestions.push("稍后重试，或调大 Timeout。", "降低输出 token，减少本次生成内容。", "检查供应商状态和本地网络。");
    } else if (lower.includes("无法连接") || lower.includes("network") || lower.includes("connect")) {
      title = "无法连接模型服务";
      suggestions.push("检查 Base URL 是否完整且以 /v1 等兼容路径结尾。", "检查网络、代理或供应商服务状态。", "确认小手机独立 API 设置是否覆盖了主程序配置。");
    } else if (lower.includes("无法解析") || lower.includes("不是合法 json") || lower.includes("格式不兼容") || lower.includes("parser")) {
      title = "模型返回格式无法解析";
      suggestions.push("重试一次，或切换更稳定的模型。", "降低 temperature，让模型更严格输出 JSON。", "在后台 Prompt 中保留 JSON contract，避免删除结构要求。");
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
    if (payload.job_id) lines.push(`任务：${payload.job_id}`);
    return lines.join("\n");
  }

  function pageTitle() {
    if (state.page === "home") return ["小手机", "应用桌面"];
    if (state.page === "create") return ["创建群聊", "从当前角色卡选择成员"];
    if (state.page === "settings") return ["详细设置", "小手机偏好"];
    if (state.page === "stickers") return ["贴纸包", "默认表情资源"];
    if (state.page === "assist") return ["辅助功能", "人物生成"];
    if (state.page === "notifications") return ["通知", `${state.notifications.filter((item) => !item.read).length} 条未读`];
    if (state.page === "phone") return ["电话", "模拟通话 RP"];
    if (state.page.startsWith("channel-")) {
      const channel = currentChannel();
      const event = currentChannelEvent();
      if (event) return [event.title || channel?.label || "详情", `${channel?.label || "频道"} · ${event.author_name || "System"}`];
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
    return state.error ? `<div class="fmcp-error">${esc(state.error).replace(/\\n/g, "<br>")}</div>` : "";
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
    const roles = state.roles;
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
        <button class="fmcp-import-card" type="button" data-action="import-current-card-roles" ${state.loading ? "disabled" : ""}>
          ${icon("import")}
          <span>从当前角色卡导入</span>
          ${icon("chevron")}
        </button>
        <div class="fmcp-field">
          <span>可选角色 <em>(${roles.length})</em></span>
          ${state.loading ? '<div class="fmcp-loading">正在读取当前角色卡...</div>' : ""}
          ${!state.loading && !state.roles.length ? '<div class="fmcp-help">点击上方导入按钮，从当前角色卡刷新候选角色。</div>' : ""}
          <div class="fmcp-role-list">
            ${roles.map((role) => `
              <label class="fmcp-role-row">
                ${avatarMarkup(role, "fmcp-role-avatar")}
                <span class="fmcp-role-copy">
                  <strong>${esc(role.name)}</strong>
                  <span class="fmcp-help">角色</span>
                </span>
                <input type="checkbox" name="member" value="${esc(role.role_id)}">
              </label>
            `).join("")}
          </div>
        </div>
        <div class="fmcp-create-options">
          <label class="fmcp-settings-row">
            <span class="fmcp-settings-copy"><strong>我也加入群聊</strong><small>关闭后只观察角色之间的对话</small></span>
            <span class="fmcp-switch"><input type="checkbox" name="include_user"><i></i></span>
          </label>
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
    const emptyText = groupHasUser(group) ? "群聊刚刚建立，发一句话试试。" : "观察位已开启，点续聊让角色自然展开对话。";
    return `
      <div class="fmcp-chat-body" data-role="messages">
        ${state.messages.length ? state.messages.map(messageMarkup).join("") : `<div class="fmcp-empty"><div>${esc(emptyText)}</div></div>`}
        ${state.generating ? '<div class="fmcp-loading">角色正在回复...</div>' : ""}
      </div>
    `;
  }

  function composerMarkup() {
    if (state.page !== "chat") return "";
    const group = currentGroup();
    const observerOnly = group && !groupHasUser(group);
    if (observerOnly) {
      return `
        <div class="fmcp-composer">
          ${state.showExtensions ? `
            <div class="fmcp-extension-panel">
              <button class="fmcp-extension-item" type="button" data-action="continue-chat">
                ${icon("refresh")}
                <span><strong>角色续聊一轮</strong><small>观察位不会替用户发言</small></span>
              </button>
              <button class="fmcp-extension-item" type="button" data-action="clear-messages">
                ${icon("trash")}
                <span><strong>清空当前群聊</strong><small>仅清除这个小手机群聊的消息</small></span>
              </button>
            </div>
          ` : ""}
          <div class="fmcp-composer-row">
            <button class="fmcp-composer-icon" type="button" data-action="toggle-extensions" aria-label="打开更多功能">${icon("plus")}</button>
            <div class="fmcp-composer-input">
              <input value="观察位：你不在这个群聊中" disabled>
            </div>
            <button class="fmcp-composer-icon fmcp-continue-button" type="button" data-action="continue-chat" aria-label="让角色继续聊天" ${state.generating ? "disabled" : ""}>${icon("refresh")}</button>
          </div>
        </div>
      `;
    }
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
    const apiConfig = settings.api_config || {};
    const modelSourceLabel = settings.model_source === "custom" ? "小手机独立配置" : "跟随主程序";
    const modelStatus = settings.model_source === "custom"
      ? `${apiConfig.model || "未填写模型"} · ${apiConfig.base_url ? "URL 已配置" : "URL 未配置"} · ${apiConfig.api_key_configured ? "Key 已配置" : "Key 未配置"}`
      : "使用主程序聊天模型";
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
              <span class="fmcp-settings-copy"><strong>最大输出 tokens</strong><small>范围 64-32000</small></span>
              <input class="fmcp-number-input" name="max_tokens" type="number" min="64" max="32000" value="${esc(settings.max_tokens || 500)}">
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
            <div class="fmcp-settings-row"><span class="fmcp-settings-copy"><strong>模型来源</strong><small>${esc(modelStatus)}</small></span><span class="fmcp-setting-value">${esc(modelSourceLabel)} ${icon("chevron")}</span></div>
          </div>
        </div>
        <div class="fmcp-settings-section">
          <div class="fmcp-section-title">高级</div>
          <div class="fmcp-settings-card">
            <a class="fmcp-settings-row fmcp-settings-action" href="${modHostBase}">${icon("settings")}<span class="fmcp-settings-copy"><strong>打开后台管理</strong><small>在主程序插件页内嵌打开后台</small></span>${icon("chevron")}</a>
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
          <span>已读取 ${stickers.length} 个贴纸；mod 目录 static/stickers 下的表情包会自动加入。</span>
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
    const channel = currentChannel();
    const events = currentChannelEvents();
    const event = currentChannelEvent();
    if (state.loading) return '<div class="fmcp-loading">正在读取频道...</div>';
    if (!channel) return '<div class="fmcp-empty"><div>频道不存在。</div></div>';
    if (event) {
      return eventDetailMarkup(channel, event);
    }
    const visibleEvents = filteredChannelEvents(channel, events);
    if (channel.type === "feed") return feedChannelMarkup(channel, events, visibleEvents);
    if (channel.type === "forum") return forumChannelMarkup(channel, events, visibleEvents);
    if (channel.type === "live") return liveChannelMarkup(channel, events, visibleEvents);
    if (channel.type === "mail") return mailChannelMarkup(channel, events, visibleEvents);
    if (channel.type === "diary") return diaryChannelMarkup(channel, events, visibleEvents);
    if (channel.type === "calendar") return calendarChannelMarkup(channel, events, visibleEvents);
    return `
      <div class="fmcp-channel-app fmcp-channel-${esc(channel.type)}">
        <div class="fmcp-home-intro">
          <strong>${esc(channel.label)}</strong>
          <span>${esc(channel.description || "小手机独立频道")}</span>
        </div>
        ${channelTabsMarkup(channel)}
        <div class="fmcp-toolbar">
          <span class="fmcp-help">${visibleEvents.length} / ${events.length} 条内容</span>
          ${seedButtonMarkup("生成内容")}
        </div>
        <div class="fmcp-event-list">
          ${visibleEvents.length ? visibleEvents.map((item, index) => eventCardMarkup(item, index)).join("") : '<div class="fmcp-empty"><div>暂无内容，可以点击生成内容。</div></div>'}
        </div>
      </div>
    `;
  }

  function notificationsMarkup() {
    if (state.loading) return '<div class="fmcp-loading">正在读取...</div>';
    const unread = state.notifications.filter((item) => !item.read).length;
    const filteredNotifications = state.notificationFilter === "unread" ? state.notifications.filter((item) => !item.read) : state.notifications;
    return `
      <div class="fmcp-notification-app">
        <div class="fmcp-notification-summary">
          <strong>${unread}</strong>
          <span>未读通知</span>
        </div>
        <div class="fmcp-toolbar">
          <span class="fmcp-help">${filteredNotifications.length} / ${state.notifications.length} 条通知</span>
          <button class="fmcp-button ${state.notificationFilter !== "unread" ? "is-active" : ""}" type="button" data-action="notification-filter" data-filter="all">全部</button>
          <button class="fmcp-button ${state.notificationFilter === "unread" ? "is-active" : ""}" type="button" data-action="notification-filter" data-filter="unread">未读</button>
          <button class="fmcp-button" type="button" data-action="read-all-notifications">全部已读</button>
        </div>
        <div class="fmcp-notification-list">
          ${filteredNotifications.length ? filteredNotifications.map((item) => `
            <article class="fmcp-notice-row ${item.read ? "is-read" : "is-unread"}">
              <span class="fmcp-notice-dot"></span>
              <div class="fmcp-notice-main">
                <strong>${esc(item.title)}</strong>
                <p>${esc(item.content)}</p>
                <small>${item.read ? "已读" : "未读"} · ${esc(item.source || "system")} · ${formatDate(item.created_at) ? esc(formatDate(item.created_at)) : ""}</small>
              </div>
              <div class="fmcp-notification-actions">
                ${item.channel_id && item.event_id ? `<button class="fmcp-button fmcp-button-primary" type="button" data-action="open-notification-target" data-notification-id="${esc(item.notification_id)}">查看来源</button>` : ""}
                ${item.read ? "" : `<button class="fmcp-button" type="button" data-action="read-notification" data-notification-id="${esc(item.notification_id)}">标为已读</button>`}
              </div>
            </article>
          `).join("") : '<div class="fmcp-empty"><div>暂无通知</div></div>'}
        </div>
      </div>
    `;
  }

  function phoneMarkup() {
    const roles = state.phoneRoles.length ? state.phoneRoles : state.roles;
    const session = state.phoneSessions.find((item) => item.session_id === state.currentPhoneSessionId) || null;
    const role = currentPhoneRole(roles);
    const callName = session?.role_name || role?.display_name || role?.name || "选择联系人";
    const callLines = session?.lines || [];
    const visibleCallLines = callLines.slice(-18);
    const callEnded = isPhoneSessionEnded(session);
    const canTalk = Boolean(state.currentPhoneRoleId && !state.generating && !callEnded);
    const roleSessions = state.currentPhoneRoleId
      ? state.phoneSessions.filter((item) => item.role_id === state.currentPhoneRoleId)
      : state.phoneSessions.slice(0, 8);
    return `
      <div class="fmcp-phone-app">
        <div class="fmcp-phone-stage">
          <div class="fmcp-phone-stage-top">
            ${avatarMarkup({ name: callName, avatar: role?.avatar }, "fmcp-phone-avatar")}
            <strong>${esc(callName)}</strong>
            <span>${session ? phoneStatusLabel(session.status, session) : "等待拨号"}</span>
            <em>${session ? phoneElapsedLabel(session) : "00:00"}</em>
          </div>
          <div class="fmcp-call-screen">
            ${visibleCallLines.length ? visibleCallLines.map((line, index) => {
              const kind = phoneLineKind(line);
              const isNewLine = kind !== "user" && state.newPhoneLineIds.includes(line.line_id);
              return `
                <article class="fmcp-call-line is-${kind}${isNewLine ? " is-new" : ""}" style="--fmcp-line-index:${index}">
                  <small>${esc(phoneLineLabel(line))}${line.mood ? ` · ${esc(line.mood)}` : ""}</small>
                  <span>${esc(line.content)}</span>
                </article>
              `;
            }).join("") : `
              <div class="fmcp-phone-idle">
                <strong>${state.currentPhoneRoleId ? "可以开始通话" : "先选择联系人"}</strong>
                <span>${state.currentPhoneRoleId ? "点麦克风输入你想说的话，或直接开始一次空白拨号。" : "从下方联系人里选择一个角色。"}</span>
              </div>
            `}
            ${callEnded ? `<div class="fmcp-phone-ended">${esc(phoneStatusLabel(session.status, session))}，可以重新拨号。</div>` : ""}
            ${state.generating ? '<div class="fmcp-phone-thinking">正在等待对方回应...</div>' : ""}
          </div>
          ${state.phoneComposerOpen ? `
            <form class="fmcp-phone-say-popover" data-form="phone-call">
              <label>你在电话里说</label>
              <textarea name="user_line" maxlength="500" autocomplete="off" autofocus placeholder="输入一句话，留空也可以直接接通。"></textarea>
              <div class="fmcp-phone-say-actions">
                <button class="fmcp-button" type="button" data-action="close-phone-compose">取消</button>
                <button class="fmcp-button fmcp-button-primary" type="submit" ${!canTalk ? "disabled" : ""}>${session?.lines?.length ? "继续通话" : "开始通话"}</button>
              </div>
            </form>
          ` : ""}
          <div class="fmcp-phone-controls" aria-label="电话控制">
            <button class="fmcp-phone-control" type="button" data-action="${callEnded ? "redial-phone" : "toggle-phone-compose"}" ${state.generating || !state.currentPhoneRoleId ? "disabled" : ""} aria-label="${callEnded ? "重新拨号" : "说话"}">
              ${icon("mic")}
              <span>${callEnded ? "重拨" : "说话"}</span>
            </button>
            <button class="fmcp-phone-control is-end" type="button" data-action="end-phone-call" ${!session || callEnded ? "disabled" : ""} aria-label="挂断">
              ${icon("phoneOff")}
              <span>挂断</span>
            </button>
            <button class="fmcp-phone-control ${state.phoneSpeakerOn ? "is-active" : ""}" type="button" data-action="toggle-phone-speaker" aria-label="扬声器">
              ${icon("volume")}
              <span>${state.phoneSpeakerOn ? "扬声" : "听筒"}</span>
            </button>
          </div>
        </div>
        <div class="fmcp-phone-section-title">联系人</div>
        <div class="fmcp-depth-summary"><span>${roles.length} &#20301;&#32852;&#31995;&#20154;</span><span>${state.phoneSessions.length} &#27425;&#36890;&#35805;</span><span>${state.phoneSessions.filter((item) => item.status !== "ended").length} &#20010;&#36827;&#34892;&#20013;</span></div>
        <div class="fmcp-phone-roles fmcp-contact-list">
          ${roles.length ? roles.map((role) => `
            <button class="fmcp-role-chip ${state.currentPhoneRoleId === role.role_id ? "is-active" : ""}" type="button" data-action="select-phone-role" data-role-id="${esc(role.role_id)}">
              ${avatarMarkup({ name: role.display_name || role.name, avatar: role.avatar }, "fmcp-role-avatar")}
              <span><strong>${esc(role.display_name || role.name)}</strong><small>可拨号</small></span>
            </button>
          `).join("") : '<div class="fmcp-empty"><div>暂无可通话角色，请先在后台或群聊创建角色。</div></div>'}
        </div>
        ${roleSessions.length ? `
          <div class="fmcp-phone-section-title">最近通话</div>
          <div class="fmcp-call-history">
            ${roleSessions.slice(0, 6).map((item) => `
              <button class="fmcp-call-session ${item.session_id === session?.session_id ? "is-active" : ""}" type="button" data-action="select-phone-session" data-session-id="${esc(item.session_id)}">
                <strong>${esc(item.role_name || item.role_id)}</strong>
                <span>${phoneStatusLabel(item.status, item)} · ${(item.lines || []).length} 句 · ${formatDate(item.updated_at) ? esc(formatDate(item.updated_at)) : ""}</span>
              </button>
            `).join("")}
          </div>
        ` : ""}
        <div class="fmcp-call-status">
          <span>${session ? phoneStatusLabel(session.status, session) : "尚未拨号"}</span>
          <span>${callLines.length ? `${callLines.length} 句通话记录` : "点麦克风输入或接通"}</span>
        </div>
      </div>
    `;
  }


  function disabledRoleRestoreMarkup() {
    const roles = state.disabledRoles || [];
    if (!roles.length) {
      return `
        <section class="fmcp-generator-result fmcp-disabled-role-restore">
          <div class="fmcp-phone-section-title">\u7981\u7528\u89d2\u8272\u6062\u590d</div>
          <div class="fmcp-empty">\u6682\u65e0\u88ab\u7981\u7528\u7684\u5c0f\u624b\u673a\u89d2\u8272\u3002</div>
        </section>
      `;
    }
    return `
      <section class="fmcp-generator-result fmcp-disabled-role-restore">
        <div class="fmcp-phone-section-title">\u7981\u7528\u89d2\u8272\u6062\u590d</div>
        <p class="fmcp-generator-copy">\u8fd9\u91cc\u53ea\u6062\u590d\u5c0f\u624b\u673a\u72ec\u7acb\u89d2\u8272\u5e93\uff0c\u4e0d\u4f1a\u4fee\u6539\u4e3b\u89d2\u8272\u5361\u3002</p>
        <div class="fmcp-generator-draft-tabs">
          ${roles.map((role) => `
            <button class="fmcp-generator-draft-chip" type="button" data-action="restore-disabled-role" data-role-id="${esc(role.role_id)}" ${state.roleGeneratorBusy ? "disabled" : ""} title="\u6062\u590d ${esc(role.display_name)}">
              ${esc(role.display_name || role.role_id)}
            </button>
          `).join("")}
        </div>
      </section>
    `;
  }

  function assistMarkup() {
    const drafts = state.roleGeneratorDrafts || [];
    const selectedIndex = Math.max(0, Math.min(state.roleGeneratorSelectedIndex || 0, Math.max(0, drafts.length - 1)));
    const selectedDraft = drafts[selectedIndex] || null;
    const countValue = String(state.roleGeneratorForm?.count || 1);
    return `
      <div class="fmcp-generator-app">
        <form class="fmcp-form fmcp-generator-form" data-form="role-generator">
          <div class="fmcp-phone-hero fmcp-generator-hero">
            <strong>人物生成</strong>
            <span>生成的角色只进入小手机独立角色库。</span>
          </div>
          <label class="fmcp-field">
            <span>已知信息</span>
            <textarea class="fmcp-textarea" name="known_info" maxlength="1000" placeholder="例如：她是邮箱里反复出现的旧友，语气克制但关心。">${esc(roleGeneratorField("known_info"))}</textarea>
          </label>
          <label class="fmcp-field">
            <span>整体要求</span>
            <textarea class="fmcp-textarea" name="overall_request" maxlength="1000" placeholder="想让这个人物承担什么功能或气质。">${esc(roleGeneratorField("overall_request"))}</textarea>
          </label>
          <div class="fmcp-generator-grid">
            <label class="fmcp-field">
              <span>真实姓名</span>
              <input class="fmcp-input" name="real_name" maxlength="80" value="${esc(roleGeneratorField("real_name"))}">
            </label>
            <label class="fmcp-field">
              <span>网名 / 昵称</span>
              <input class="fmcp-input" name="nickname" maxlength="80" value="${esc(roleGeneratorField("nickname"))}">
            </label>
            <label class="fmcp-field">
              <span>身份</span>
              <input class="fmcp-input" name="identity" maxlength="160" value="${esc(roleGeneratorField("identity"))}">
            </label>
            <label class="fmcp-field">
              <span>生成数量</span>
              <select class="fmcp-input" name="count">
                ${[1, 3, 5, 10].map((count) => `<option value="${count}" ${countValue === String(count) ? "selected" : ""}>${count}</option>`).join("")}
              </select>
            </label>
            <label class="fmcp-field">
              <span>发色</span>
              <input class="fmcp-input" name="hair_color" maxlength="80" value="${esc(roleGeneratorField("hair_color"))}">
            </label>
            <label class="fmcp-field">
              <span>发型</span>
              <input class="fmcp-input" name="hairstyle" maxlength="120" value="${esc(roleGeneratorField("hairstyle"))}">
            </label>
          </div>
          <label class="fmcp-field">
            <span>整体印象</span>
            <textarea class="fmcp-textarea" name="impression" maxlength="300">${esc(roleGeneratorField("impression"))}</textarea>
          </label>
          <label class="fmcp-field">
            <span>说话风格</span>
            <textarea class="fmcp-textarea" name="speech_style" maxlength="240">${esc(roleGeneratorField("speech_style"))}</textarea>
          </label>
          ${roleGeneratorScopeMarkup("suitable_apps", "适合出现的 App")}
          ${roleGeneratorScopeMarkup("blocked_apps", "禁止出现的 App")}
          <div class="fmcp-form-actions fmcp-generator-actions">
            <button class="fmcp-button" type="button" data-action="clear-role-generator" ${state.roleGeneratorBusy ? "disabled" : ""}>清空</button>
            <button class="fmcp-button" type="button" data-action="extract-event-role-drafts" ${state.roleGeneratorBusy ? "disabled" : ""}>从事件提取候选</button>
            <button class="fmcp-button" type="button" data-action="extract-chat-role-drafts" ${state.roleGeneratorBusy ? "disabled" : ""}>从主 Chat 提取候选</button>
            <button class="fmcp-button fmcp-button-primary" type="submit" ${state.roleGeneratorBusy ? "disabled" : ""}>${state.roleGeneratorBusy ? "生成中..." : "生成草稿"}</button>
          </div>
        </form>
        ${state.roleGeneratorNotice ? `<div class="fmcp-generator-notice">${esc(state.roleGeneratorNotice)}</div>` : ""}
        ${disabledRoleRestoreMarkup()}
        <section class="fmcp-generator-result">
          <div class="fmcp-phone-section-title">草稿预览</div>
          ${drafts.length > 1 ? `
            <div class="fmcp-generator-draft-tabs">
              ${drafts.map((draft, index) => `
                <button class="fmcp-generator-draft-chip ${index === selectedIndex ? "is-active" : ""}" type="button" data-action="select-role-draft" data-index="${index}" aria-pressed="${index === selectedIndex ? "true" : "false"}" title="${esc(draft.display_name || `草稿 ${index + 1}`)}">
                  ${esc(draft.display_name || `草稿 ${index + 1}`)}
                </button>
              `).join("")}
            </div>
          ` : ""}
          ${roleGeneratorDraftPreview(selectedDraft, selectedIndex)}
          <div class="fmcp-form-actions fmcp-generator-actions">
            <button class="fmcp-button" type="button" data-action="save-role-draft" ${!selectedDraft || state.roleGeneratorBusy ? "disabled" : ""}>保存选中</button>
            <button class="fmcp-button fmcp-button-primary" type="button" data-action="save-all-role-drafts" ${!drafts.length || state.roleGeneratorBusy ? "disabled" : ""}>全部保存</button>
          </div>
        </section>
      </div>
    `;
  }

  function bodyMarkup() {
    if (state.page === "home") return homeMarkup();
    if (state.page === "create") return createMarkup();
    if (state.page === "chat") return chatMarkup();
    if (state.page === "settings") return settingsMarkup();
    if (state.page === "stickers") return stickersMarkup();
    if (state.page === "assist") return assistMarkup();
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
            <div class="fmcp-shell${state.generationTask ? " is-generating" : ""}">
              ${headerMarkup()}
              <main class="fmcp-body fmcp-body-${esc(state.page)}">
                ${errorMarkup()}
                ${bodyMarkup()}
              </main>
              ${composerMarkup()}
              ${generationOverlayMarkup()}
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
      if (state.page === "phone") {
        const screen = root.querySelector(".fmcp-call-screen");
        if (screen) screen.scrollTop = screen.scrollHeight;
      }
      if (state.page.startsWith("channel-live") && state.currentChannelEventId) {
        const comments = root.querySelector(".fmcp-live-comment-list");
        if (comments) comments.scrollTop = comments.scrollHeight;
      }
    });
  }

  function restoreBodyScrollAfterRender(scrollTop) {
    if (!Number.isFinite(scrollTop)) return;
    const apply = () => {
      const body = root.querySelector(".fmcp-body");
      if (body) body.scrollTop = scrollTop;
    };
    apply();
    requestAnimationFrame(apply);
    window.setTimeout(apply, 80);
  }

  function currentBodyScrollTop() {
    const body = root.querySelector(".fmcp-body");
    return body ? body.scrollTop : NaN;
  }

  function renderKeepingBodyScroll(scrollTop = currentBodyScrollTop()) {
    render();
    restoreBodyScrollAfterRender(scrollTop);
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
      const selected = state.phoneSessions.find((item) => item.session_id === state.currentPhoneSessionId);
      const keepSelected = selected && selected.role_id === state.currentPhoneRoleId && !isPhoneSessionEnded(selected);
      const session = keepSelected
        ? selected
        : state.phoneSessions.find((item) => item.role_id === state.currentPhoneRoleId && !isPhoneSessionEnded(item));
      state.currentPhoneSessionId = session?.session_id || "";
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
    state.error = "";
    state.roles = [];
    state.user = null;
    render();
  }

  async function importCurrentCardRoles() {
    if (state.loading) return;
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
    if (target === "assist") {
      state.page = "assist";
      state.currentChannelEventId = "";
      await loadDisabledRoles();
      return;
    }
    if (target === "notifications") {
      state.page = "notifications";
      state.currentChannelEventId = "";
      await loadNotifications();
      return;
    }
    if (target === "phone") {
      state.page = "phone";
      state.currentChannelEventId = "";
      await loadPhone();
      return;
    }
    if (target.startsWith("channel-")) {
      const channelId = target.slice("channel-".length);
      state.page = target;
      state.currentChannelId = channelId;
      state.currentChannelEventId = "";
      await loadChannelEvents(channelId);
      return;
    }
    state.page = "home";
    render();
  }


  async function loadDisabledRoles() {
    try {
      const payload = await request("/roles/disabled");
      state.disabledRoles = payload.roles || [];
    } catch (error) {
      state.disabledRoles = [];
      state.error = error.message;
    }
    render();
  }

  async function restoreDisabledRole(roleId) {
    const safeRoleId = String(roleId || "");
    if (!safeRoleId || state.roleGeneratorBusy) return;
    const scrollTop = currentBodyScrollTop();
    state.roleGeneratorBusy = true;
    state.roleGeneratorNotice = "";
    state.error = "";
    renderKeepingBodyScroll(scrollTop);
    try {
      const result = await request(`/roles/${encodeURIComponent(safeRoleId)}/restore`, { method: "POST" });
      state.disabledRoles = result.roles || [];
      state.roles = result.available || state.roles;
      const restoredName = result.role?.display_name || safeRoleId;
      state.roleGeneratorNotice = `\u5df2\u6062\u590d ${restoredName}\uff0c\u4ec5\u5f71\u54cd\u5c0f\u624b\u673a\u89d2\u8272\u5e93\u3002`;
    } catch (error) {
      state.error = error.message;
    } finally {
      state.roleGeneratorBusy = false;
      renderKeepingBodyScroll(scrollTop);
    }
  }

  async function generateRoleDrafts(form) {
    const scrollTop = currentBodyScrollTop();
    const payload = roleGeneratorPayloadFrom(form);
    state.roleGeneratorForm = payload;
    state.roleGeneratorBusy = true;
    state.roleGeneratorNotice = "";
    state.error = "";
    renderKeepingBodyScroll(scrollTop);
    try {
      const result = await request("/role-generator/draft", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      state.roleGeneratorDrafts = result.drafts || (result.draft ? [result.draft] : []);
      state.roleGeneratorSelectedIndex = 0;
      state.roleGeneratorNotice = state.roleGeneratorDrafts.length ? `已生成 ${state.roleGeneratorDrafts.length} 个草稿。` : "没有生成可预览的草稿。";
    } catch (error) {
      state.error = error.message;
    } finally {
      state.roleGeneratorBusy = false;
      renderKeepingBodyScroll(scrollTop);
    }
  }

  async function extractEventRoleDrafts() {
    const scrollTop = currentBodyScrollTop();
    state.roleGeneratorBusy = true;
    state.roleGeneratorNotice = "";
    state.error = "";
    renderKeepingBodyScroll(scrollTop);
    try {
      const result = await request("/role-generator/extract-events", {
        method: "POST",
        body: JSON.stringify({ limit: 12 }),
      });
      state.roleGeneratorDrafts = result.drafts || (result.draft ? [result.draft] : []);
      state.roleGeneratorSelectedIndex = 0;
      state.roleGeneratorNotice = state.roleGeneratorDrafts.length
        ? `已从小手机事件提取 ${state.roleGeneratorDrafts.length} 个候选草稿。`
        : "没有从现有事件中提取到新的候选。";
    } catch (error) {
      state.error = error.message;
    } finally {
      state.roleGeneratorBusy = false;
      renderKeepingBodyScroll(scrollTop);
    }
  }

  async function extractChatRoleDrafts() {
    const scrollTop = currentBodyScrollTop();
    state.roleGeneratorBusy = true;
    state.roleGeneratorNotice = "";
    state.error = "";
    renderKeepingBodyScroll(scrollTop);
    try {
      const result = await request("/role-generator/extract-chat", {
        method: "POST",
        body: JSON.stringify({ limit: 12, recent_messages: 120 }),
      });
      state.roleGeneratorDrafts = result.drafts || (result.draft ? [result.draft] : []);
      state.roleGeneratorSelectedIndex = 0;
      state.roleGeneratorNotice = state.roleGeneratorDrafts.length
        ? `已从主 Chat 正文提取 ${state.roleGeneratorDrafts.length} 个候选草稿。`
        : "没有从主 Chat 正文中提取到新的候选。";
    } catch (error) {
      state.error = error.message;
    } finally {
      state.roleGeneratorBusy = false;
      renderKeepingBodyScroll(scrollTop);
    }
  }

  async function saveRoleDrafts({ all = false } = {}) {
    const drafts = state.roleGeneratorDrafts || [];
    const selected = drafts[state.roleGeneratorSelectedIndex || 0];
    const roles = all ? drafts : (selected ? [selected] : []);
    if (!roles.length) return;
    const scrollTop = currentBodyScrollTop();
    state.roleGeneratorBusy = true;
    state.roleGeneratorNotice = "";
    state.error = "";
    renderKeepingBodyScroll(scrollTop);
    try {
      const result = await request("/role-generator/save", {
        method: "POST",
        body: JSON.stringify({ roles }),
      });
      state.roleGeneratorSaved = result.saved || [];
      state.roles = result.available || state.roles;
      state.roleGeneratorDrafts = all
        ? []
        : drafts.filter((_, index) => index !== (state.roleGeneratorSelectedIndex || 0));
      state.roleGeneratorSelectedIndex = 0;
      state.roleGeneratorNotice = `${state.roleGeneratorSaved.length} 个角色已保存到小手机角色库。`;
    } catch (error) {
      state.error = error.message;
    } finally {
      state.roleGeneratorBusy = false;
      renderKeepingBodyScroll(scrollTop);
    }
  }

  function clearRoleGenerator() {
    const scrollTop = currentBodyScrollTop();
    state.roleGeneratorForm = {};
    state.roleGeneratorDrafts = [];
    state.roleGeneratorSaved = [];
    state.roleGeneratorSelectedIndex = 0;
    state.roleGeneratorNotice = "";
    state.error = "";
    renderKeepingBodyScroll(scrollTop);
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
    const members = state.roles.filter((item) => selectedIds.has(item.role_id));
    if (data.has("include_user") && state.user) members.push(state.user);
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

  async function createChannelPost(form) {
    if (!state.currentChannelId || state.generating) return;
    const data = new FormData(form);
    const content = String(data.get("content") || "").trim();
    const title = String(data.get("title") || "").trim();
    if (!content) {
      state.error = "内容不能为空。";
      render();
      return;
    }
    state.generating = true;
    state.generationTask = {
      type: "channel-interaction",
      targetId: state.currentChannelId,
      message: "正在发布并等待角色互动...",
      cancelLabel: "停止等待",
    };
    state.error = "";
    const controller = new AbortController();
    activeGenerationAbort = controller;
    render();
    try {
      const payload = await request(`/channels/${encodeURIComponent(state.currentChannelId)}/interactions`, {
        method: "POST",
        body: JSON.stringify({ title, content }),
        signal: controller.signal,
      });
      state.channelEvents[state.currentChannelId] = payload.events || [];
      state.channelComposerOpen = { ...state.channelComposerOpen, [state.currentChannelId]: false };
      state.currentChannelEventId = payload.event?.event_id || "";
      await loadNotifications().catch(() => {});
    } catch (error) {
      state.error = error.name === "AbortError" ? "已停止等待互动生成；内容可能已经发布。" : error.message;
    } finally {
      if (activeGenerationAbort === controller) activeGenerationAbort = null;
      state.generating = false;
      state.generationTask = null;
      await loadChannelEvents(state.currentChannelId).catch((error) => { state.error = error.message; });
      render();
    }
  }

  async function replyChannelEvent(form) {
    const channelId = form.dataset.channelId || state.currentChannelId;
    const eventId = form.dataset.eventId || state.currentChannelEventId;
    if (!channelId || !eventId || state.generating) return;
    const data = new FormData(form);
    const content = String(data.get("content") || "").trim();
    if (!content) {
      state.error = "回复不能为空。";
      render();
      return;
    }
    state.generating = true;
    state.generationTask = {
      type: "channel-reply",
      targetId: eventId,
      message: "正在发送回复并等待角色接话...",
      cancelLabel: "停止等待",
    };
    state.error = "";
    const controller = new AbortController();
    activeGenerationAbort = controller;
    render();
    try {
      const payload = await request(`/channels/${encodeURIComponent(channelId)}/events/${encodeURIComponent(eventId)}/replies`, {
        method: "POST",
        body: JSON.stringify({ content }),
        signal: controller.signal,
      });
      state.channelEvents[channelId] = payload.events || [];
      state.channelReplyOpen = { ...state.channelReplyOpen, [`${channelId}:${eventId}`]: false };
      state.currentChannelEventId = payload.event?.event_id || eventId;
      await loadNotifications().catch(() => {});
    } catch (error) {
      state.error = error.name === "AbortError" ? "已停止等待互动生成；回复可能已经写入。" : error.message;
    } finally {
      if (activeGenerationAbort === controller) activeGenerationAbort = null;
      state.generating = false;
      state.generationTask = null;
      await loadChannelEvents(channelId).catch((error) => { state.error = error.message; });
      render();
    }
  }

  async function replyMailEvent(form) {
    const channelId = form.dataset.channelId || state.currentChannelId;
    const eventId = form.dataset.eventId || state.currentChannelEventId;
    if (!channelId || !eventId || state.generating) return;
    const data = new FormData(form);
    const content = String(data.get("content") || "").trim();
    if (!content) {
      state.error = "回复不能为空。";
      render();
      return;
    }
    state.generating = true;
    state.generationTask = {
      type: "mail-reply",
      targetId: eventId,
      message: "正在发送邮件并等待对方回信...",
      cancelLabel: "停止等待",
    };
    state.error = "";
    const controller = new AbortController();
    activeGenerationAbort = controller;
    render();
    try {
      const payload = await request(`/channels/${encodeURIComponent(channelId)}/events/${encodeURIComponent(eventId)}/mail-replies`, {
        method: "POST",
        body: JSON.stringify({ content, generate_reply: true }),
        signal: controller.signal,
      });
      state.channelEvents[channelId] = payload.events || [];
      state.mailDrafts = { ...state.mailDrafts };
      delete state.mailDrafts[eventId];
      state.currentChannelEventId = payload.event?.event_id || eventId;
      await loadNotifications().catch(() => {});
    } catch (error) {
      state.error = error.name === "AbortError" ? "已停止等待邮件回信；你的回复可能已经写入。" : error.message;
    } finally {
      if (activeGenerationAbort === controller) activeGenerationAbort = null;
      state.generating = false;
      state.generationTask = null;
      await loadChannelEvents(channelId).catch((error) => { state.error = error.message; });
      render();
    }
  }

  async function sendLiveMessage(form) {
    const channelId = form.dataset.channelId || state.currentChannelId;
    const eventId = form.dataset.eventId || state.currentChannelEventId;
    if (!channelId || !eventId) return;
    const data = new FormData(form);
    const content = String(data.get("content") || "").trim();
    if (!content) {
      state.error = "弹幕不能为空。";
      render();
      return;
    }
    state.error = "";
    try {
      const payload = await request(`/channels/${encodeURIComponent(channelId)}/events/${encodeURIComponent(eventId)}/live-messages`, {
        method: "POST",
        body: JSON.stringify({ content }),
      });
      state.channelEvents[channelId] = payload.events || [];
      state.currentChannelEventId = payload.event?.event_id || eventId;
    } catch (error) {
      state.error = error.message;
    }
    render();
  }

  async function seedCurrentChannel() {
    if (!state.currentChannelId || state.generating) return;
    const channel = currentChannel();
    state.generating = true;
    state.generationTask = {
      type: "channel-seed",
      targetId: state.currentChannelId,
      message: channelSeedCopy(channel),
      cancelLabel: "终止生成",
    };
    state.error = "";
    const controller = new AbortController();
    activeGenerationAbort = controller;
    render();
    try {
      const payload = await request(`/channels/${encodeURIComponent(state.currentChannelId)}/seed`, {
        method: "POST",
        body: JSON.stringify({ count: channelSeedCount(channel) }),
        signal: controller.signal,
      });
      state.channelEvents[state.currentChannelId] = payload.events || [];
      await loadNotifications().catch(() => {});
    } catch (error) {
      state.error = error.name === "AbortError"
        ? "已停止等待生成结果；如果模型请求已在后台完成，稍后刷新列表可能会看到新内容。"
        : error.message;
    } finally {
      if (activeGenerationAbort === controller) activeGenerationAbort = null;
      state.generating = false;
      state.generationTask = null;
      await loadChannelEvents(state.currentChannelId).catch((error) => { state.error = error.message; });
      render();
    }
  }

  function cancelGeneration(message = "已停止等待生成结果；如果服务端已经开始调用模型，结果可能稍后写入频道。") {
    if (activeGenerationAbort) activeGenerationAbort.abort();
    state.generating = false;
    state.generationTask = null;
    state.phoneComposerOpen = false;
    state.error = message;
    render();
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

  async function openNotificationTarget(notificationId) {
    const item = state.notifications.find((row) => row.notification_id === notificationId);
    if (!item || !item.channel_id || !item.event_id) {
      state.error = "这条通知没有可跳转的来源内容。";
      render();
      return;
    }
    state.error = "";
    try {
      if (!item.read) {
        const payload = await request(`/notifications/${encodeURIComponent(notificationId)}`, {
          method: "PATCH",
          body: JSON.stringify({ read: true }),
        });
        state.notifications = payload.notifications || [];
      }
      if (!state.channels.length) await loadChannels();
      state.page = `channel-${item.channel_id}`;
      state.currentChannelId = item.channel_id;
      state.currentChannelEventId = item.event_id;
      await loadChannelEvents(item.channel_id);
      if (!currentChannelEvent()) state.error = "来源内容已不存在或尚未加载。";
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
    const userLine = data.get("user_line") || "";
    state.generating = true;
    state.phoneComposerOpen = false;
    state.error = "";
    const controller = new AbortController();
    activeGenerationAbort = controller;
    render();
    try {
      const payload = await request("/phone/call", {
        method: "POST",
        body: JSON.stringify({
          role_id: state.currentPhoneRoleId,
          session_id: state.currentPhoneSessionId,
          user_line: userLine,
        }),
        signal: controller.signal,
      });
      const session = payload.session;
      if (session) {
        state.currentPhoneSessionId = session.session_id;
        state.phoneSessions = [session, ...state.phoneSessions.filter((item) => item.session_id !== session.session_id)];
      }
      schedulePhoneLineAnimation((payload.lines || []).map((line) => line.line_id));
    } catch (error) {
      state.error = error.name === "AbortError" ? "已停止等待电话回应。" : error.message;
    } finally {
      if (activeGenerationAbort === controller) activeGenerationAbort = null;
      state.generating = false;
      render();
    }
  }

  async function endPhoneCall() {
    const sessionId = state.currentPhoneSessionId;
    if (!sessionId) return;
    if (state.generating && activeGenerationAbort) cancelGeneration("已挂断并停止等待电话回应。");
    state.phoneComposerOpen = false;
    state.newPhoneLineIds = [];
    state.error = "";
    try {
      const payload = await request(`/phone/sessions/${encodeURIComponent(sessionId)}/hangup`, { method: "POST" });
      const session = payload.session;
      if (session) {
        state.phoneSessions = [session, ...state.phoneSessions.filter((item) => item.session_id !== session.session_id)];
      }
      state.currentPhoneSessionId = "";
    } catch (error) {
      state.error = error.message;
    }
    render();
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
      if (state.generating && activeGenerationAbort) cancelGeneration("");
      state.open = false;
      state.showStickers = false;
      state.showExtensions = false;
      state.phoneComposerOpen = false;
      render();
    }
    if (action === "back") {
      if (state.page.startsWith("channel-") && state.currentChannelEventId) {
        const scrollTop = state.channelListScrollTops[state.currentChannelId];
        state.currentChannelEventId = "";
        state.error = "";
        renderKeepingBodyScroll(scrollTop);
        return;
      }
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
    if (action === "import-current-card-roles") void importCurrentCardRoles();
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
    if (action === "cancel-generation") cancelGeneration();
    if (action === "channel-tab") {
      const channelId = button.dataset.channelId || state.currentChannelId;
      state.channelTabs = { ...state.channelTabs, [channelId]: button.dataset.tabId || "" };
      state.error = "";
      render();
    }
    if (action === "channel-author-filter") {
      const channelId = button.dataset.channelId || state.currentChannelId;
      state.channelAuthorFilters = { ...state.channelAuthorFilters, [channelId]: button.dataset.author || "" };
      state.currentChannelEventId = "";
      state.error = "";
      render();
    }
    if (action === "toggle-channel-compose") {
      const channelId = button.dataset.channelId || state.currentChannelId;
      state.channelComposerOpen = { ...state.channelComposerOpen, [channelId]: !state.channelComposerOpen[channelId] };
      state.error = "";
      render();
    }
    if (action === "toggle-channel-reply") {
      const channelId = button.dataset.channelId || state.currentChannelId;
      const eventId = button.dataset.eventId || state.currentChannelEventId;
      const key = `${channelId}:${eventId}`;
      state.channelReplyOpen = { ...state.channelReplyOpen, [key]: !state.channelReplyOpen[key] };
      state.error = "";
      render();
    }
    if (action === "select-diary-role") {
      state.diaryRoleId = button.dataset.roleId || "";
      state.currentChannelEventId = "";
      state.error = "";
      render();
    }
    if (action === "select-calendar-date") {
      state.calendarSelectedDate = button.dataset.date || "";
      state.currentChannelEventId = "";
      state.error = "";
      render();
    }    if (action === "open-channel-event") {
      state.currentChannelId = button.dataset.channelId || state.currentChannelId;
      state.channelListScrollTops = { ...state.channelListScrollTops, [state.currentChannelId]: currentBodyScrollTop() };
      state.currentChannelEventId = button.dataset.eventId || "";
      state.error = "";
      render();
    }
    if (action === "show-channel-list") {
      const scrollTop = state.channelListScrollTops[state.currentChannelId];
      state.currentChannelEventId = "";
      state.error = "";
      renderKeepingBodyScroll(scrollTop);
    }
    if (action === "read-notification") void readNotification(button.dataset.notificationId || "");
    if (action === "notification-filter") {
      state.notificationFilter = button.dataset.filter === "unread" ? "unread" : "all";
      state.error = "";
      render();
    }
    if (action === "open-notification-target") void openNotificationTarget(button.dataset.notificationId || "");
    if (action === "read-all-notifications") void readAllNotifications();
    if (action === "toggle-phone-compose") {
      state.phoneComposerOpen = !state.phoneComposerOpen;
      state.error = "";
      render();
    }
    if (action === "close-phone-compose") {
      if (state.generating && activeGenerationAbort) cancelGeneration("已停止等待电话回应。");
      state.phoneComposerOpen = false;
      state.error = "";
      render();
    }
    if (action === "toggle-phone-speaker") {
      state.phoneSpeakerOn = !state.phoneSpeakerOn;
      state.error = "";
      render();
    }
    if (action === "end-phone-call") {
      void endPhoneCall();
    }
    if (action === "redial-phone") {
      state.currentPhoneSessionId = "";
      state.phoneComposerOpen = true;
      state.newPhoneLineIds = [];
      state.error = "";
      render();
    }
    if (action === "select-phone-role") {
      state.currentPhoneRoleId = button.dataset.roleId || "";
      state.currentPhoneSessionId = "";
      state.phoneComposerOpen = false;
      state.newPhoneLineIds = [];
      render();
    }
    if (action === "select-phone-session") {
      const session = state.phoneSessions.find((item) => item.session_id === button.dataset.sessionId);
      if (session) {
        state.currentPhoneSessionId = session.session_id;
        state.currentPhoneRoleId = session.role_id;
        state.phoneComposerOpen = false;
        state.newPhoneLineIds = [];
        render();
      }
    }
    if (action === "clear-messages") void clearMessages();
    if (action === "reset-position") void resetPosition();
    if (action === "select-role-draft") {
      const scrollTop = currentBodyScrollTop();
      const index = Number.parseInt(button.dataset.index || "0", 10);
      state.roleGeneratorSelectedIndex = Number.isFinite(index) ? index : 0;
      state.roleGeneratorNotice = "";
      renderKeepingBodyScroll(scrollTop);
    }
    if (action === "save-role-draft") void saveRoleDrafts({ all: false });
    if (action === "save-all-role-drafts") void saveRoleDrafts({ all: true });
    if (action === "clear-role-generator") clearRoleGenerator();
    if (action === "extract-event-role-drafts") void extractEventRoleDrafts();
    if (action === "extract-chat-role-drafts") void extractChatRoleDrafts();
    if (action === "restore-disabled-role") void restoreDisabledRole(button.dataset.roleId || "");
    if (action === "save-mail-draft") {
      const eventId = button.dataset.eventId || state.currentChannelEventId;
      const form = button.closest("form");
      const data = form ? new FormData(form) : null;
      state.mailDrafts = { ...state.mailDrafts, [eventId]: data?.get("content") || "" };
      state.error = "";
      render();
    }
    if (action === "toggle-live-follow") {
      const eventId = button.dataset.eventId || state.currentChannelEventId;
      state.liveFollows = { ...state.liveFollows, [eventId]: !state.liveFollows[eventId] };
      state.error = "";
      render();
    }
  }

  function onSubmit(event) {
    const form = event.target.closest("form[data-form]");
    if (!form) return;
    event.preventDefault();
    touchActivity();
    if (form.dataset.form === "create-group") void createGroup(form);
    if (form.dataset.form === "send-message") void sendMessage(form);
    if (form.dataset.form === "settings") void saveSettings(form);
    if (form.dataset.form === "role-generator") void generateRoleDrafts(form);
    if (form.dataset.form === "phone-call") void phoneCall(form);
    if (form.dataset.form === "channel-post") void createChannelPost(form);
    if (form.dataset.form === "channel-reply") void replyChannelEvent(form);
    if (form.dataset.form === "mail-reply") void replyMailEvent(form);
    if (form.dataset.form === "live-message") void sendLiveMessage(form);
    if (form.dataset.form === "mail-draft") {
      const eventId = form.dataset.eventId || state.currentChannelEventId;
      const data = new FormData(form);
      state.mailDrafts = { ...state.mailDrafts, [eventId]: data.get("draft") || "" };
      state.error = "";
      render();
    }
  }

  function onInput(event) {
    const field = event.target.closest("[data-role-draft-field]");
    if (!field) return;
    const index = Number.parseInt(field.dataset.draftIndex || String(state.roleGeneratorSelectedIndex || 0), 10);
    updateRoleGeneratorDraftField(Number.isFinite(index) ? index : 0, field.dataset.roleDraftField || "", field.value);
  }

  function onChange(event) {
    const scope = event.target.closest("[data-role-draft-scope]");
    if (scope) {
      const index = Number.parseInt(scope.dataset.draftIndex || String(state.roleGeneratorSelectedIndex || 0), 10);
      updateRoleGeneratorDraftScope(Number.isFinite(index) ? index : 0, scope.dataset.roleDraftScope || "", scope);
      return;
    }
    const target = event.target.closest("[data-change]");
    if (!target) return;
    if (target.dataset.change === "toggle-live-thought") {
      const eventId = target.dataset.eventId || state.currentChannelEventId;
      state.revealedLiveThoughts = { ...state.revealedLiveThoughts, [eventId]: !!target.checked };
      state.error = "";
    }
  }

  function init() {
    if (document.getElementById("fantareal-mobile-chat-root")) return;
    root = document.createElement("div");
    root.id = "fantareal-mobile-chat-root";
    root.addEventListener("click", onClick);
    root.addEventListener("submit", onSubmit);
    root.addEventListener("input", onInput);
    root.addEventListener("change", onChange);
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
