(() => {
  "use strict";

  const API_BASE = "/mods/auto-saga/app/api";
  const CONFIG_URL = "/mods/auto-saga";
  const state = {
    enabled: false,
    intervalSec: 30,
    autoInteract: false,
    observerMode: false,
    showSilent: false,
    turn: 0,
    choices: [],
    sessionId: "",
    history: [],
    characters: [],
  };
  let autoTimer = null;
  let busy = false;
  let waitingForJournal = false;
  let journalFallbackTimer = null;
  const STARTER_CHOICES = [
    { label: "从日常开始", intent: "生成贴合角色生活与关系的轻事件" },
    { label: "出现意外插曲", intent: "让环境或人物需求带来新的变化" },
    { label: "主动和角色交流", intent: "以情感或关系推进作为故事起点" },
  ];

  async function request(path, options = {}) {
    const response = await fetch(API_BASE + path, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function applyServerState(payload) {
    const settings = payload?.settings || {};
    state.enabled = Boolean(settings.enabled);
    state.intervalSec = 30;
    state.autoInteract = Boolean(settings.auto_interact);
    state.observerMode = Boolean(settings.observer_mode);
    state.showSilent = Boolean(settings.show_silent);
    state.turn = Number(payload?.turn) || 0;
    state.choices = Array.isArray(payload?.choices) ? payload.choices : state.choices;
    state.sessionId = String(payload?.session_id || "");
    state.history = Array.isArray(payload?.history) ? payload.history : [];
    state.characters = Array.isArray(payload?.characters) ? payload.characters : [];
    document.body.classList.toggle("fr-auto-saga-active", state.enabled);
    ensureChoiceDock();
    updateUi();
    syncAutoTimer();
  }

  async function saveSettings(patch) {
    const payload = await request("/settings", {
      method: "POST",
      body: JSON.stringify(patch),
    });
    applyServerState(payload);
    return payload;
  }

  function messageRole(role) {
    return role === "gm" ? "system" : role === "user" ? "user" : "assistant";
  }

  function visibleMessageText(value) {
    return String(value || "")
      .replace(/<think\b[^>]*>[\s\S]*?<\/think>/gi, "")
      .replace(/<thinking\b[^>]*>[\s\S]*?<\/thinking>/gi, "")
      .replace(/<analysis\b[^>]*>[\s\S]*?<\/analysis>/gi, "")
      .trim();
  }

  function messageContent(message) {
    const rawContent = String(message?.content || message?.text || "");
    const content = visibleMessageText(rawContent) || rawContent.trim();
    return message?.name ? `**${message.name}**\n${content}` : content;
  }

  function createMessageId(prefix = "auto-saga") {
    const randomId = globalThis.crypto?.randomUUID?.()
      || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    return `${prefix}-${randomId}`;
  }

  function simpleHash(value) {
    const text = String(value || "");
    let hash = 0x811c9dc5;
    for (let index = 0; index < text.length; index += 1) {
      hash ^= text.charCodeAt(index);
      hash = Math.imul(hash, 0x01000193);
    }
    return (hash >>> 0).toString(16).padStart(8, "0");
  }

  function createTurnId(turn) {
    const session = state.sessionId.replace(/[^a-zA-Z0-9_-]+/g, "").slice(0, 12) || "session";
    return `auto_saga_${session}_${String(Math.max(1, Number(turn) || 1)).padStart(4, "0")}`;
  }

  async function persistMessage(message, metadata = {}) {
    if (!message?.id || message.role === "silent") return;
    const response = await fetch("/api/chat/history/mod-message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        role: messageRole(message.role),
        content: messageContent(message),
        created_at: message.created_at || "",
        mod_message_id: message.id,
        source: "auto-saga",
        ...metadata,
      }),
    });
    if (!response.ok) throw new Error(`history HTTP ${response.status}`);
    return response.json();
  }

  function appendMessage(message) {
    if (!message || (message.role === "silent" && !state.showSilent)) return;
    if (message.id && document.querySelector(`[data-mod-message-id="${CSS.escape(message.id)}"]`)) return;
    const bridge = window.FantarealChat;
    if (bridge && typeof bridge.addModMessage === "function") {
      return bridge.addModMessage({
        role: message.role,
        name: message.name || (message.role === "gm" ? "旁白" : ""),
        content: message.text || "",
        id: message.id || "",
        createdAt: message.created_at || "",
      });
    }
    showToast(`${message.name || "旁白"}：${message.text || ""}`);
    return null;
  }

  function dispatchStateJournalTurn({ choice, messages, entries, turn }) {
    const targetIndex = messages.findLastIndex((message) => !["gm", "silent", "user"].includes(message.role));
    if (targetIndex < 0) return;
    const targetMessage = messages[targetIndex];
    const targetEntry = entries[targetIndex];
    if (!targetEntry?.wrapper || !targetMessage?.id) return;

    const assistantText = messages
      .filter((message) => !["silent", "user"].includes(message.role))
      .map((message) => messageContent(message).trim())
      .filter(Boolean)
      .join("\n\n");
    if (!assistantText) return;

    const userText = choice ? `选择：${choice}` : "角色自行互动（玩家旁观）";
    const turnId = createTurnId(turn);
    const contentHash = simpleHash(assistantText);
    const turnIndex = Math.max(1, Number(turn) || 1);
    const wrapper = targetEntry.wrapper;
    wrapper.dataset.turnId = turnId;
    wrapper.dataset.stateJournalTurn = turnId;
    wrapper.dataset.turnIndex = String(turnIndex);
    wrapper.dataset.messageId = targetMessage.id;
    wrapper.dataset.contentHash = contentHash;

    const detail = {
      turnId,
      turn_id: turnId,
      turnIndex,
      turn_index: turnIndex,
      messageId: targetMessage.id,
      message_id: targetMessage.id,
      assistantMessageId: targetMessage.id,
      assistant_message_id: targetMessage.id,
      userText,
      user_text: userText,
      assistantText,
      assistant_text: assistantText,
      assistantCleanText: assistantText,
      assistant_clean_text: assistantText,
      contentHash,
      content_hash: contentHash,
      assistantHash: contentHash,
      assistant_hash: contentHash,
      createdAt: targetMessage.created_at || new Date().toISOString(),
      created_at: targetMessage.created_at || new Date().toISOString(),
      source: "auto-saga",
      triggerSource: "chat_hook",
      trigger_source: "chat_hook",
      recentHistory: window.FantarealChat?.getContext?.().history || [],
    };
    window.dispatchEvent(new CustomEvent("fantareal:chat-user-submit", { detail }));
    window.dispatchEvent(new CustomEvent("fantareal:assistant-finalized", { detail }));
    waitingForJournal = true;
    window.clearTimeout(journalFallbackTimer);
    journalFallbackTimer = window.setTimeout(() => {
      waitingForJournal = false;
      journalFallbackTimer = null;
      syncAutoTimer();
      updateUi();
    }, 150 * 1000);
    return detail;
  }

  async function syncCurrentCharacter() {
    const bridgeContext = window.FantarealChat?.getContext?.();
    if (state.characters.length) {
      return { ...bridgeContext, characters: state.characters };
    }
    let character = bridgeContext;
    let characters = [];
    try {
      const cardPayload = await request("/current-card-characters");
      characters = Array.isArray(cardPayload?.characters) ? cardPayload.characters : [];
    } catch (_error) {
      characters = [];
    }
    if (!characters.length && !character?.characterName) {
      const persona = await fetch("/api/persona").then((response) => response.json());
      character = {
        characterName: persona.name || "角色",
        persona: persona.system_prompt || "",
      };
    }
    if (!characters.length && character?.characterName) {
      characters = [{
        name: character.characterName,
        persona: character.persona,
        trust: 50,
        addressed: false,
      }];
    }
    const merged = await request("/characters/merge", {
      method: "POST",
      body: JSON.stringify({
        characters,
      }),
    });
    state.characters = Array.isArray(merged?.characters) ? merged.characters : state.characters;
    return { ...character, characters: state.characters };
  }

  async function advanceTurn(choice = "") {
    if (busy || !state.enabled) return;
    busy = true;
    updateUi();
    try {
      const context = await syncCurrentCharacter();
      let choiceMessageId = "";
      if (choice) {
        choiceMessageId = createMessageId();
        window.FantarealChat?.addModMessage?.({
          role: "user",
          id: choiceMessageId,
          content: `选择：${choice}`,
        });
        await persistMessage({
          id: choiceMessageId,
          role: "user",
          content: `选择：${choice}`,
          created_at: new Date().toLocaleString(),
        });
      }
      const payload = await request("/next", {
        method: "POST",
        body: JSON.stringify({
          choice,
          choice_message_id: choiceMessageId,
          recent_history: Array.isArray(context?.history) ? context.history : [],
        }),
      });
      state.turn = Number(payload.turn) || state.turn + 1;
      state.choices = Array.isArray(payload.choices) ? payload.choices : [];
      const messages = Array.isArray(payload.messages) ? payload.messages : [];
      const entries = [];
      const targetIndex = messages.findLastIndex((message) => !["gm", "silent", "user"].includes(message.role));
      const assistantText = messages
        .filter((message) => !["silent", "user"].includes(message.role))
        .map((message) => messageContent(message).trim())
        .filter(Boolean)
        .join("\n\n");
      const turnId = createTurnId(state.turn);
      const contentHash = simpleHash(assistantText);
      for (const [index, message] of messages.entries()) {
        if (!message.id) message.id = createMessageId();
        entries[index] = appendMessage(message);
        const isTarget = index === targetIndex;
        await persistMessage(message, isTarget ? {
          turn_id: turnId,
          turn_index: state.turn,
          content_hash: contentHash,
        } : {});
      }
      dispatchStateJournalTurn({ choice, messages, entries, turn: state.turn });
      if (!payload.llm) showToast("当前未配置模型密钥，正在使用本地模拟叙事。");
    } catch (error) {
      stopAuto();
      showToast(`推进失败：${error.message}`, true);
    } finally {
      busy = false;
      updateUi();
    }
  }

  function startAuto() {
    stopAuto();
    if (waitingForJournal || busy) return;
    autoTimer = window.setTimeout(() => {
      autoTimer = null;
      autoStep();
    }, 30 * 1000);
    updateUi();
  }

  function autoStep() {
    advanceTurn("");
  }

  function stopAuto() {
    if (autoTimer) window.clearTimeout(autoTimer);
    autoTimer = null;
    updateUi();
  }

  function syncAutoTimer() {
    if (state.enabled && state.autoInteract && !waitingForJournal && !busy) {
      if (!autoTimer) startAuto();
      return;
    }
    if (autoTimer) stopAuto();
  }

  function ensureUi() {
    if (document.getElementById("fr-auto-saga-trigger")) return;
    const actions = document.querySelector(".chat-page .header-actions");
    if (!actions) return;

    const trigger = document.createElement("button");
    trigger.id = "fr-auto-saga-trigger";
    trigger.type = "button";
    trigger.className = "secondary compact icon-button fr-auto-saga-trigger";
    trigger.setAttribute("aria-label", "自动叙事设置");
    trigger.setAttribute("title", "自动叙事设置");
    trigger.setAttribute("aria-expanded", "false");
    trigger.innerHTML = '<span aria-hidden="true">▶</span><i class="fr-auto-saga-dot" aria-hidden="true"></i>';
    actions.appendChild(trigger);

    const panel = document.createElement("section");
    panel.id = "fr-auto-saga-panel";
    panel.className = "fr-auto-saga-panel";
    panel.hidden = true;
    panel.innerHTML = `
      <div class="fr-auto-saga-panel-head">
        <div>
          <span class="fr-auto-saga-kicker">AUTO SAGA</span>
          <strong>自动叙事模式</strong>
        </div>
        <button type="button" class="fr-auto-saga-close" aria-label="关闭">×</button>
      </div>
      <label class="fr-auto-saga-switch-row">
        <span><strong>启用模式</strong><small>隐藏输入框，由旁白与角色自主推进</small></span>
        <input id="fr-auto-saga-enabled" type="checkbox">
      </label>
      <label class="fr-auto-saga-switch-row">
        <span><strong>角色自行互动</strong><small>开启后每 30 秒让角色自由发言，玩家选项仍可随时介入</small></span>
        <input id="fr-auto-saga-auto-interact" type="checkbox">
      </label>
      <label class="fr-auto-saga-switch-row">
        <span><strong>旁观模式</strong><small>下一轮不再返回选项；关闭后下一轮恢复选项</small></span>
        <input id="fr-auto-saga-observer" type="checkbox">
      </label>
      <div class="fr-auto-saga-status" id="fr-auto-saga-status">尚未推进</div>
      <div class="fr-auto-saga-actions">
        <button type="button" id="fr-auto-saga-next" class="fr-auto-saga-primary">立即推进一回合</button>
      </div>
      <a class="fr-auto-saga-config-link" href="${CONFIG_URL}">打开完整插件配置 <span>→</span></a>
    `;
    document.body.appendChild(panel);

    trigger.addEventListener("click", () => togglePanel(panel.hidden));
    panel.querySelector(".fr-auto-saga-close").addEventListener("click", () => togglePanel(false));
    panel.querySelector("#fr-auto-saga-enabled").addEventListener("change", async (event) => {
      await saveSettings({ enabled: event.target.checked });
      if (!state.enabled) stopAuto();
    });
    panel.querySelector("#fr-auto-saga-auto-interact").addEventListener("change", async (event) => {
      await saveSettings({ auto_interact: event.target.checked });
    });
    panel.querySelector("#fr-auto-saga-observer").addEventListener("change", async (event) => {
      await saveSettings({ observer_mode: event.target.checked });
    });
    panel.querySelector("#fr-auto-saga-next").addEventListener("click", () => advanceTurn(""));
    document.addEventListener("click", (event) => {
      if (panel.hidden || panel.contains(event.target) || trigger.contains(event.target)) return;
      togglePanel(false);
    });
    ensureChoiceDock();
  }

  function ensureChoiceDock() {
    let dock = document.getElementById("fr-auto-saga-choices");
    if (dock) return dock;
    const composer = document.getElementById("chat-form");
    if (!composer) return null;
    dock = document.createElement("section");
    dock.id = "fr-auto-saga-choices";
    dock.className = "fr-auto-saga-choices";
    dock.setAttribute("aria-label", "自动叙事行动选择");
    dock.innerHTML = `
      <div class="fr-auto-saga-choice-head">
        <span><strong>你准备怎么做？</strong><small>选择一项，旁白和角色会继续推进</small></span>
        <button type="button" id="fr-auto-saga-random-choice" title="随机选择">随机</button>
      </div>
      <div class="fr-auto-saga-choice-grid"></div>
    `;
    composer.insertAdjacentElement("afterend", dock);
    dock.querySelector("#fr-auto-saga-random-choice").addEventListener("click", () => {
      const choices = availableChoices();
      const selected = choices[Math.floor(Math.random() * choices.length)];
      if (selected) advanceTurn(selected.label);
    });
    return dock;
  }

  function renderChoices() {
    const dock = ensureChoiceDock();
    const grid = dock?.querySelector(".fr-auto-saga-choice-grid");
    if (!grid) return;
    const displayChoices = availableChoices();
    dock.hidden = displayChoices.length === 0;
    if (!displayChoices.length) {
      grid.innerHTML = "";
      return;
    }
    grid.innerHTML = "";
    displayChoices.forEach((choice, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "fr-auto-saga-choice";
      button.disabled = busy || !state.enabled;
      button.innerHTML = `
        <span class="fr-auto-saga-choice-index">0${index + 1}</span>
        <span><strong>${escapeHtml(choice.label)}</strong><small>${escapeHtml(choice.intent || "")}</small></span>
      `;
      button.addEventListener("click", () => advanceTurn(choice.label));
      grid.appendChild(button);
    });
  }

  function availableChoices() {
    if (state.choices?.length) return state.choices;
    if (state.turn === 0 && !state.observerMode) return STARTER_CHOICES;
    return [];
  }

  function escapeHtml(value) {
    return String(value || "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char]));
  }

  function togglePanel(open) {
    const panel = document.getElementById("fr-auto-saga-panel");
    const trigger = document.getElementById("fr-auto-saga-trigger");
    if (!panel || !trigger) return;
    panel.hidden = !open;
    trigger.classList.toggle("active", open);
    trigger.setAttribute("aria-expanded", String(open));
  }

  function updateUi() {
    const enabled = document.getElementById("fr-auto-saga-enabled");
    const autoInteract = document.getElementById("fr-auto-saga-auto-interact");
    const observer = document.getElementById("fr-auto-saga-observer");
    const next = document.getElementById("fr-auto-saga-next");
    const status = document.getElementById("fr-auto-saga-status");
    const trigger = document.getElementById("fr-auto-saga-trigger");
    if (enabled) enabled.checked = state.enabled;
    if (autoInteract) autoInteract.checked = state.autoInteract;
    if (observer) observer.checked = state.observerMode;
    if (next) next.disabled = !state.enabled || busy;
    if (status) {
      status.textContent = state.enabled
        ? `${busy ? "正在推进" : waitingForJournal ? "等待心笺完成" : state.autoInteract ? "角色每 30 秒自行互动" : "已启用"} · 第 ${state.turn} 回合`
        : "当前未启用";
    }
    trigger?.classList.toggle("is-enabled", state.enabled);
    renderChoices();
  }

  function showToast(message, error = false) {
    let toast = document.getElementById("fr-auto-saga-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "fr-auto-saga-toast";
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.toggle("is-error", error);
    toast.classList.add("is-visible");
    window.clearTimeout(toast._timer);
    toast._timer = window.setTimeout(() => toast.classList.remove("is-visible"), 3200);
  }

  async function init() {
    ensureUi();
    try {
      const payload = await request("/state");
      applyServerState(payload);
      for (const message of state.history) {
        if (message.role === "silent") continue;
        appendMessage(message);
        await persistMessage(message);
      }
    } catch (error) {
      showToast(`自动叙事配置读取失败：${error.message}`, true);
    }
  }

  window.addEventListener("fantareal:conversation-ended", async () => {
    stopAuto();
    waitingForJournal = false;
    window.clearTimeout(journalFallbackTimer);
    journalFallbackTimer = null;
    try {
      applyServerState(await request("/state"));
    } catch (error) {
      showToast(`自动叙事重置失败：${error.message}`, true);
    }
  });

  window.addEventListener("state_journal:updated", () => {
    if (!waitingForJournal) return;
    waitingForJournal = false;
    window.clearTimeout(journalFallbackTimer);
    journalFallbackTimer = null;
    syncAutoTimer();
    updateUi();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
