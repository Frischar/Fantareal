/* =============================================================================
 * auto-saga mod — 自动叙事模式 (v0.2.0)
 *
 * 旁观式玩法：玩家不再每回合输入，全程点击 Next ▶（或自动播放）推进剧情。
 * 角色依据人设卡性格由后端自主判断是否发言（可沉默）。聊天渲染支持 KaTeX。
 *
 * v0.2.0：推进逻辑改为调用本 mod 后端 /mods/auto-saga/app/api/next，
 * 由后端逐角色 willSpeak 判定与调 LLM（Key 不暴露前端）。
 *
 * 设计原则：零侵入。仅注入一个浮动控制卡片 + 一个自己的消息流，命名空间 fr-auto-saga。
 * 关联 Issue #4。
 * ========================================================================== */
(() => {
  'use strict';

  const STORE_KEY = 'fantareal.autoSaga.v1';
  const API_BASE = '/mods/auto-saga/app/api';
  const KATEX_CSS = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css';
  const KATEX_JS = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js';
  const KATEX_AUTO = 'https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js';

  const state = loadState();
  let autoTimer = null;
  let busy = false;

  function loadState() {
    try {
      const raw = JSON.parse(localStorage.getItem(STORE_KEY) || '{}');
      return {
        active: !!raw.active,
        intervalSec: Number(raw.intervalSec) > 0 ? Number(raw.intervalSec) : 6,
        turn: Number(raw.turn) || 0,
      };
    } catch (e) {
      return { active: false, intervalSec: 6, turn: 0 };
    }
  }

  function saveState() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch (e) { /* ignore */ }
  }

  // ---- 启发式：与后端 speak_probability 保持一致（仅用于前端可选预览/测试）----
  function speakProbability(persona, opts) {
    const o = opts || {};
    let p = 0.55;
    const text = String(persona || '');
    if (/沉默|寡言|高冷|冷淡|内向/.test(text)) p -= 0.25;
    if (/健谈|热情|话痨|外向|活泼/.test(text)) p += 0.25;
    if (/多疑|谨慎|警惕/.test(text)) p -= 0.1;
    if (o.addressed) p += 0.4;
    if (typeof o.trust === 'number') p += (o.trust - 50) / 200;
    return Math.max(0.05, Math.min(0.95, p));
  }

  function willSpeak(persona, opts, rng) {
    const r = typeof rng === 'function' ? rng : Math.random;
    return r() < speakProbability(persona, opts);
  }

  // ---- KaTeX 数学渲染 -----------------------------------------------------------
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

  // ---- 轻量 Markdown → HTML（仅处理本 mod 自己的消息流，不动主聊天 DOM）------
  function esc(s) {
    return String(s == null ? '' : s)
      .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
  }

  function miniMarkdown(text) {
    let html = esc(text);
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\n/g, '<br>');
    return html;
  }

  // ---- 消息流渲染 -------------------------------------------------------------
  function ensureFeed() {
    let feed = document.getElementById('fr-auto-saga-feed');
    if (feed) return feed;
    feed = document.createElement('div');
    feed.id = 'fr-auto-saga-feed';
    document.body.appendChild(feed);
    return feed;
  }

  function renderMessage(m) {
    const feed = ensureFeed();
    const el = document.createElement('div');
    el.className = 'fr-auto-saga-msg fr-auto-saga-' + (m.role || 'gm');
    const who = m.role === 'gm' ? '' : `<span class="fr-auto-saga-who">${esc(m.name)}</span>`;
    el.innerHTML = `${who}<div class="fr-auto-saga-body">${miniMarkdown(m.text)}</div>`;
    feed.appendChild(el);
    renderMathIn(el);
    feed.scrollTop = feed.scrollHeight;
  }

  // ---- 推进一回合：调 mod 后端 ----------------------------------------------
  async function advanceTurn() {
    if (busy) return;
    busy = true;
    updateBar();
    try {
      const resp = await fetch(API_BASE + '/next', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      });
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const data = await resp.json();
      state.turn = data.turn || state.turn + 1;
      saveState();
      (data.messages || []).forEach(renderMessage);
      if (!data.llm) flashHint('后端未配置 API Key，当前为本地模拟叙事。', 2500);
    } catch (e) {
      flashHint('推进失败：' + e.message + '（请确认 auto-saga mod 后端已启用）');
      stopAuto();
    } finally {
      busy = false;
      updateBar();
    }
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
      // 同步间隔到后端（失败不阻断）
      fetch(API_BASE + '/settings', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interval_sec: state.intervalSec }),
      }).catch(() => {});
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
    const feed = document.getElementById('fr-auto-saga-feed');
    if (feed) feed.style.display = state.active ? '' : 'none';
  }

  function updateBar() {
    const bar = document.getElementById('fr-auto-saga-bar');
    if (!bar) return;
    const next = bar.querySelector('#fr-auto-saga-next');
    const auto = bar.querySelector('#fr-auto-saga-auto');
    const turn = bar.querySelector('#fr-auto-saga-turn');
    if (next) next.disabled = !state.active || !!autoTimer || busy;
    if (auto) {
      auto.disabled = !state.active || busy;
      auto.textContent = autoTimer ? '⏸ 暂停' : '▶ 自动';
    }
    if (turn) turn.textContent = state.active ? `已推进 ${state.turn} 回合${busy ? ' …' : ''}` : '未开启';
  }

  function flashHint(msg, ms) {
    let hint = document.getElementById('fr-auto-saga-hint');
    if (!hint) {
      hint = document.createElement('div');
      hint.id = 'fr-auto-saga-hint';
      hint.style.cssText = 'position:fixed;right:16px;bottom:200px;z-index:61;background:rgba(227,179,65,.12);color:#e3b341;border:1px solid rgba(227,179,65,.4);border-radius:8px;padding:8px 12px;font-size:12px;max-width:240px;';
      document.body.appendChild(hint);
    }
    hint.textContent = msg;
    clearTimeout(hint._t);
    hint._t = setTimeout(() => { hint.remove(); }, ms || 4000);
  }

  // ---- 初始化 -----------------------------------------------------------------
  function init() {
    ensureBar();
    ensureFeed();
    applyActiveClass();
    ensureKatex();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { willSpeak, speakProbability };
  }
})();
