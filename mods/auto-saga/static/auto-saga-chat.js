/* =============================================================================
 * auto-saga mod — 自动叙事模式 (v0.1.0)
 *
 * 旁观式玩法：玩家不再每回合输入，全程点击 Next ▶（或自动播放）推进剧情。
 * 角色依据人设卡性格自主判断是否发言（可沉默）。聊天渲染支持 KaTeX 数学公式。
 *
 * 设计原则：零侵入。
 *  - 仅注入一个浮动控制卡片，命名空间 fr-auto-saga。
 *  - 推进剧情复用主应用现有发送/历史接口（运行时探测，找不到则降级提示）。
 *  - 不修改 fantareal/ 核心，不改其他 mod 的状态与 DOM。
 *  - UI 与轻量进度状态存 localStorage。
 *
 * 关联 Issue #4。
 * ========================================================================== */
(() => {
  'use strict';

  const STORE_KEY = 'fantareal.autoSaga.v1';
  const KATEX_CSS = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css';
  const KATEX_JS = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js';
  const KATEX_AUTO = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js';

  const state = loadState();
  let autoTimer = null;

  function loadState() {
    try {
      const raw = JSON.parse(localStorage.getItem(STORE_KEY) || '{}');
      return {
        active: !!raw.active,
        intervalSec: Number(raw.intervalSec) > 0 ? Number(raw.intervalSec) : 6,
        turn: Number(raw.turn) || 0,
        lastSpeaker: raw.lastSpeaker || '',
      };
    } catch (e) {
      return { active: false, intervalSec: 6, turn: 0, lastSpeaker: '' };
    }
  }

  function saveState() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch (e) { /* ignore */ }
  }

  // ---- KaTeX 数学渲染：动态加载并对聊天容器做增量渲染 -------------------------
  function ensureKatex() {
    return new Promise((resolve) => {
      if (window.renderMathInElement) return resolve(true);
      if (!document.querySelector('link[data-fr-auto-saga-katex]')) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = KATEX_CSS;
        link.setAttribute('data-fr-auto-saga-katex', '1');
        document.head.appendChild(link);
      }
      loadScript(KATEX_JS)
        .then(() => loadScript(KATEX_AUTO))
        .then(() => resolve(!!window.renderMathInElement))
        .catch(() => resolve(false));
    });
  }

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = src;
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  function renderMathIn(el) {
    if (!el || !window.renderMathInElement) return;
    try {
      window.renderMathInElement(el, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '$', right: '$', display: false },
          { left: '\\(', right: '\\)', display: false },
          { left: '\\[', right: '\\]', display: true },
        ],
        throwOnError: false,
      });
    } catch (e) { /* ignore */ }
  }

  // 找到聊天消息容器（按常见选择器探测）
  function findChatContainer() {
    const sels = ['#chat-messages', '.chat-messages', '#messages', '.message-list', '[data-role="messages"]', '#chat-log', '.chat-log'];
    for (const s of sels) {
      const el = document.querySelector(s);
      if (el) return el;
    }
    return null;
  }

  // 监听聊天容器新增节点，自动渲染数学公式
  function observeChatForMath() {
    const container = findChatContainer();
    if (!container) return;
    ensureKatex().then((ok) => {
      if (!ok) return;
      renderMathIn(container);
      const mo = new MutationObserver((muts) => {
        for (const m of muts) {
          m.addedNodes && m.addedNodes.forEach((n) => {
            if (n.nodeType === 1) renderMathIn(n);
          });
        }
      });
      mo.observe(container, { childList: true, subtree: true });
    });
  }

  // ---- 角色「是否发言」判定（性格驱动 + 随机性）--------------------------------
  // 在缺少结构化角色数据时，提供一个可解释的本地启发式，供前端节奏控制与提示。
  function willSpeak(persona, opts) {
    const o = opts || {};
    let p = 0.55;
    const text = String(persona || '');
    if (/沉默|寡言|高冷|冷淡|内向/.test(text)) p -= 0.25;
    if (/健谈|热情|话痨|外向|活泼/.test(text)) p += 0.25;
    if (/多疑|谨慎|警惕/.test(text)) p -= 0.1;
    if (o.addressed) p += 0.4;       // 上一回合被点名
    if (typeof o.trust === 'number') p += (o.trust - 50) / 200;
    p = Math.max(0.05, Math.min(0.95, p));
    return Math.random() < p;
  }

  // ---- 推进一回合：复用主应用现有的发送逻辑 -----------------------------------
  // 优先调用主应用暴露的全局发送函数；否则模拟点击发送按钮。
  function advanceTurn() {
    state.turn += 1;
    saveState();
    updateBar();

    // 1) 主应用若暴露了发送 API，直接复用（不同版本命名可能不同，逐一探测）
    const fn = window.sendChatMessage || window.fantarealSend || (window.Fantareal && window.Fantareal.send);
    if (typeof fn === 'function') {
      try { fn('(继续推进剧情)'); return; } catch (e) { /* 落到下面的兜底 */ }
    }

    // 2) 兜底：填充输入框 + 触发发送按钮点击
    const input = document.querySelector('textarea, input[type="text"][data-role="chat-input"], #chat-input, .chat-input textarea');
    const sendBtn = document.querySelector('#send-btn, .send-btn, [data-action="send"], button[type="submit"]');
    if (input && sendBtn) {
      input.value = '(继续推进剧情)';
      input.dispatchEvent(new Event('input', { bubbles: true }));
      sendBtn.click();
      return;
    }

    // 3) 都找不到：提示用户（不同 chat 版本选择器差异）
    flashHint('未找到聊天发送入口，请在普通 Chat 页开启自动叙事模式。');
  }

  // ---- 自动播放 ---------------------------------------------------------------
  function startAuto() {
    stopAuto();
    autoTimer = setInterval(advanceTurn, Math.max(2, state.intervalSec) * 1000);
    updateBar();
  }

  function stopAuto() {
    if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
    updateBar();
  }

  // ---- UI 控制卡片 ------------------------------------------------------------
  function ensureBar() {
    if (document.getElementById('fr-auto-saga-bar')) return;
    const bar = document.createElement('div');
    bar.id = 'fr-auto-saga-bar';
    bar.innerHTML = `
      <div class="fr-auto-saga-card">
        <div class="fr-auto-saga-row">
          <span class="fr-auto-saga-toggle">🎬 自动叙事模式</span>
          <input type="checkbox" id="fr-auto-saga-active">
        </div>
        <div class="fr-auto-saga-row">
          <label for="fr-auto-saga-interval">自动播放间隔(秒)</label>
          <input type="number" min="2" max="60" id="fr-auto-saga-interval" class="fr-auto-saga-interval">
        </div>
        <div class="fr-auto-saga-row">
          <span id="fr-auto-saga-turn" style="color:#8b949e"></span>
        </div>
        <div class="fr-auto-saga-actions">
          <button class="fr-auto-saga-btn" id="fr-auto-saga-next">Next ▶</button>
          <button class="fr-auto-saga-btn ghost" id="fr-auto-saga-auto">▶ 自动</button>
        </div>
      </div>`;
    document.body.appendChild(bar);

    const cbActive = bar.querySelector('#fr-auto-saga-active');
    const inInterval = bar.querySelector('#fr-auto-saga-interval');
    cbActive.checked = state.active;
    inInterval.value = state.intervalSec;

    cbActive.addEventListener('change', () => {
      state.active = cbActive.checked;
      saveState();
      applyActiveClass();
      if (!state.active) stopAuto();
      updateBar();
    });
    inInterval.addEventListener('change', () => {
      state.intervalSec = Math.max(2, Math.min(60, Number(inInterval.value) || 6));
      inInterval.value = state.intervalSec;
      saveState();
      if (autoTimer) startAuto();
    });
    bar.querySelector('#fr-auto-saga-next').addEventListener('click', () => {
      if (!state.active) { flashHint('请先勾选「自动叙事模式」'); return; }
      advanceTurn();
    });
    bar.querySelector('#fr-auto-saga-auto').addEventListener('click', () => {
      if (!state.active) { flashHint('请先勾选「自动叙事模式」'); return; }
      if (autoTimer) stopAuto(); else startAuto();
    });

    updateBar();
  }

  function applyActiveClass() {
    document.body.classList.toggle('fr-auto-saga-active', !!state.active);
  }

  function updateBar() {
    const bar = document.getElementById('fr-auto-saga-bar');
    if (!bar) return;
    const next = bar.querySelector('#fr-auto-saga-next');
    const auto = bar.querySelector('#fr-auto-saga-auto');
    const turn = bar.querySelector('#fr-auto-saga-turn');
    if (next) next.disabled = !state.active || !!autoTimer;
    if (auto) {
      auto.disabled = !state.active;
      auto.textContent = autoTimer ? '⏸ 暂停' : '▶ 自动';
    }
    if (turn) turn.textContent = state.active ? `已推进 ${state.turn} 回合` : '未开启';
  }

  function flashHint(msg) {
    let hint = document.getElementById('fr-auto-saga-hint');
    if (!hint) {
      hint = document.createElement('div');
      hint.id = 'fr-auto-saga-hint';
      hint.style.cssText = 'position:fixed;right:16px;bottom:200px;z-index:61;background:rgba(227,179,65,.12);color:#e3b341;border:1px solid rgba(227,179,65,.4);border-radius:8px;padding:8px 12px;font-size:12px;max-width:240px;';
      document.body.appendChild(hint);
    }
    hint.textContent = msg;
    clearTimeout(hint._t);
    hint._t = setTimeout(() => { hint.remove(); }, 4000);
  }

  // ---- 初始化 -----------------------------------------------------------------
  function init() {
    ensureBar();
    applyActiveClass();
    observeChatForMath();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // 暴露最小测试接口（便于 node --test 复用纯函数）
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { willSpeak };
  }
})();
