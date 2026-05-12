(() => {
  const scriptUrl = new URL(document.currentScript?.src || window.location.href);
  const apiBase = new URL("../api/", scriptUrl).toString();
  let configCache = null;
  const inFlightTurns = new Map();
  const fallbackTimers = new Map();
  const invalidatedTurns = new Set();
  let hideTimer = null;
  const processedTurns = new Set();
  let pendingTurn = null;

  function simpleHash(value) {
    const text = String(value || "");
    let hash = 0x811c9dc5;
    for (let i = 0; i < text.length; i += 1) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 0x01000193);
    }
    return (hash >>> 0).toString(16).padStart(8, "0");
  }

  function makeTurnId(seed = "") {
    return `turn_${Date.now()}_${simpleHash(seed).slice(0, 8)}`;
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    }[ch]));
  }

  function compactText(value, limit = 120) {
    const text = String(value ?? "").replace(/\s+/g, " ").trim();
    if (!text) return "";
    return text.length > limit ? `${text.slice(0, limit).trim()}…` : text;
  }

  function ensureVisualStyle() {
    if (document.getElementById("state-journal-chat-bubble-style")) return;
    const style = document.createElement("style");
    style.id = "state-journal-chat-bubble-style";
    style.textContent = `
      .state-journal-chat-bubble {
        position: fixed;
        top: clamp(4.6rem, 7.5vh, 6.2rem);
        left: min(67vw, calc(100vw - 16rem));
        transform: translateX(-50%) translateY(-0.35rem);
        z-index: 1200;
        display: flex;
        align-items: flex-start;
        gap: 0.72rem;
        min-width: 15.5rem;
        max-width: min(24rem, calc(100vw - 2rem));
        padding: 0.82rem 2.35rem 0.82rem 0.95rem;
        border-radius: 1rem;
        border: 1px solid color-mix(in srgb, var(--accent, #d8b273) 48%, rgba(255,255,255,0.18));
        background: color-mix(in srgb, var(--panel-strong, #1d1a16) 72%, rgba(20, 18, 14, 0.58));
        color: var(--text, #f5efe5);
        box-shadow: 0 18px 42px rgba(0,0,0,0.26), inset 0 1px 0 rgba(255,255,255,0.08);
        backdrop-filter: blur(18px) saturate(1.1);
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.18s ease, transform 0.18s ease, border-color 0.18s ease;
      }
      .state-journal-chat-bubble.is-visible { opacity: 1; transform: translateX(-50%) translateY(0); pointer-events: auto; }
      .state-journal-chat-bubble.is-success { border-color: color-mix(in srgb, #6ac486 60%, var(--border, rgba(255,255,255,0.18)) 40%); }
      .state-journal-chat-bubble.is-empty { border-color: color-mix(in srgb, #8ca6c8 55%, var(--border, rgba(255,255,255,0.18)) 45%); }
      .state-journal-chat-bubble.is-error { border-color: color-mix(in srgb, #ff7878 64%, var(--border, rgba(255,255,255,0.18)) 36%); cursor: pointer; }
      .state-journal-chat-bubble-mark {
        flex: 0 0 auto; width: 2rem; height: 2rem; border-radius: 999px; display: inline-flex; align-items: center; justify-content: center;
        background: color-mix(in srgb, var(--accent, #d8b273) 18%, transparent 82%);
        border: 1px solid color-mix(in srgb, var(--accent, #d8b273) 36%, transparent 64%);
        font-weight: 800; line-height: 1;
      }
      .state-journal-chat-bubble.is-pending .state-journal-chat-bubble-mark::before { content: ""; width: 0.82rem; height: 0.82rem; border-radius: 999px; border: 2px solid color-mix(in srgb, currentColor 28%, transparent 72%); border-top-color: currentColor; animation: state-journal-spin 0.85s linear infinite; }
      .state-journal-chat-bubble.is-success .state-journal-chat-bubble-mark::before { content: "✓"; }
      .state-journal-chat-bubble.is-empty .state-journal-chat-bubble-mark::before { content: "◇"; }
      .state-journal-chat-bubble.is-error .state-journal-chat-bubble-mark::before { content: "!"; }
      .state-journal-chat-bubble-copy { min-width: 0; flex: 1 1 auto; }
      .state-journal-chat-bubble-title { font-weight: 800; font-size: 0.92rem; line-height: 1.25; letter-spacing: 0.01em; }
      .state-journal-chat-bubble-desc { margin-top: 0.26rem; color: var(--muted, rgba(245,239,229,0.74)); font-size: 0.78rem; line-height: 1.45; word-break: break-word; }
      .state-journal-chat-bubble-close {
        position: absolute;
        top: .55rem;
        right: .58rem;
        width: 1.45rem;
        height: 1.45rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 999px;
        border: 0;
        background: transparent;
        color: inherit;
        cursor: pointer;
        opacity: .58;
        line-height: 1;
        padding: 0;
      }
      .state-journal-chat-bubble-close:hover { opacity: 1; background: color-mix(in srgb, currentColor 10%, transparent 90%); }

      .state-journal-turn-status {
        margin-top: .58rem;
        display: flex;
        align-items: center;
        gap: .5rem;
        width: fit-content;
        max-width: min(100%, 32rem);
        padding: .46rem .64rem;
        border-radius: .86rem;
        border: 1px solid color-mix(in srgb, var(--accent, #d8b273) 26%, var(--border, rgba(255,255,255,.14)) 74%);
        background: color-mix(in srgb, var(--panel, rgba(35,31,27,.72)) 70%, transparent 30%);
        color: var(--muted, rgba(245,239,229,.78));
        font-size: .76rem;
        line-height: 1.45;
        box-shadow: 0 8px 18px rgba(0,0,0,.10), inset 0 1px 0 rgba(255,255,255,.05);
      }
      .state-journal-turn-status::before {
        content: "";
        width: .78rem;
        height: .78rem;
        flex: 0 0 auto;
        border-radius: 999px;
        border: 2px solid color-mix(in srgb, currentColor 26%, transparent 74%);
        border-top-color: currentColor;
        animation: state-journal-spin .85s linear infinite;
      }
      .state-journal-turn-status.is-error { border-color: color-mix(in srgb, #ff7878 58%, var(--border, rgba(255,255,255,.16)) 42%); color: #ffd5d5; }
      .state-journal-turn-status.is-error::before { content: "!"; display: inline-flex; align-items: center; justify-content: center; border: 0; animation: none; font-weight: 900; }

      .state-journal-inline-scene-card {
        width: 100%;
        margin: 0 0 .75rem;
        border: 1px solid color-mix(in srgb, var(--accent, #d8b273) 34%, var(--border, rgba(255,255,255,.18)) 66%);
        border-radius: 1.05rem;
        background: color-mix(in srgb, var(--panel-strong, rgba(35,31,27,.88)) 68%, transparent 32%);
        box-shadow: 0 14px 34px rgba(0,0,0,.16), inset 0 1px 0 rgba(255,255,255,.08);
        backdrop-filter: blur(14px) saturate(1.08);
        color: var(--text, #f5efe5);
        overflow: hidden;
      }
      .state-journal-inline-scene-card summary {
        list-style: none;
        cursor: pointer;
        padding: .72rem .88rem;
        display: grid;
        gap: .26rem;
      }
      .state-journal-inline-scene-card summary::-webkit-details-marker { display: none; }
      .state-journal-scene-kicker { color: var(--accent, #d8b273); font-size: .68rem; text-transform: uppercase; letter-spacing: .18em; font-weight: 850; }
      .state-journal-scene-title-line { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
      .state-journal-scene-title { font-weight: 900; letter-spacing: .04em; font-size: clamp(.96rem, 1.55vw, 1.18rem); }
      .state-journal-scene-toggle { flex: 0 0 auto; opacity: .78; font-size: .74rem; color: var(--muted, rgba(245,239,229,.72)); }
      .state-journal-inline-scene-card[open] .state-journal-scene-toggle { color: var(--accent, #d8b273); }
      .state-journal-scene-subtitle { color: var(--muted, rgba(245,239,229,.72)); font-size: .8rem; line-height: 1.5; }
      .state-journal-scene-body { padding: 0 .88rem .82rem; display: grid; gap: .58rem; }
      .state-journal-scene-meta { display: flex; flex-wrap: wrap; gap: .36rem; }
      .state-journal-scene-chip { border: 1px solid var(--border, rgba(255,255,255,.16)); border-radius: 999px; padding: .22rem .54rem; background: color-mix(in srgb, var(--input-bg, rgba(0,0,0,.18)) 70%, transparent 30%); font-size: .72rem; color: var(--muted, rgba(245,239,229,.72)); }
      .state-journal-scene-event { border-left: 3px solid color-mix(in srgb, var(--accent, #d8b273) 72%, transparent 28%); padding-left: .72rem; color: var(--text, #f5efe5); font-size: .82rem; line-height: 1.6; }

      .state-journal-turn-note {
        margin-top: .62rem;
        border: 1px solid color-mix(in srgb, var(--accent, #d8b273) 28%, var(--border, rgba(255,255,255,.16)) 72%);
        border-radius: 1rem;
        background: color-mix(in srgb, var(--panel, rgba(35,31,27,.72)) 70%, transparent 30%);
        color: var(--text, #f5efe5);
        overflow: hidden;
        box-shadow: 0 10px 24px rgba(0,0,0,.12), inset 0 1px 0 rgba(255,255,255,.06);
      }
      .state-journal-turn-note.is-mode-expanded { border-color: color-mix(in srgb, var(--accent, #d8b273) 38%, var(--border, rgba(255,255,255,.16)) 62%); }
      .state-journal-turn-note-compact {
        margin-top: .52rem;
        display: flex;
        align-items: center;
        gap: .48rem;
        padding: .5rem .68rem;
        border-radius: .86rem;
        border: 1px solid color-mix(in srgb, var(--accent, #d8b273) 22%, var(--border, rgba(255,255,255,.14)) 78%);
        background: color-mix(in srgb, var(--panel, rgba(35,31,27,.66)) 72%, transparent 28%);
        color: var(--muted, rgba(245,239,229,.78));
        font-size: .78rem;
        line-height: 1.45;
        box-shadow: 0 8px 18px rgba(0,0,0,.10), inset 0 1px 0 rgba(255,255,255,.05);
      }
      .state-journal-turn-note-compact strong { color: var(--accent, #d8b273); font-weight: 850; }
      .state-journal-turn-note-compact span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .state-journal-turn-note summary {
        list-style: none;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: .75rem;
        padding: .68rem .82rem;
        color: var(--muted, rgba(245,239,229,.75));
        font-size: .82rem;
      }
      .state-journal-turn-note summary::-webkit-details-marker { display: none; }
      .state-journal-turn-summary-main { display: flex; align-items: center; gap: .5rem; min-width: 0; }
      .state-journal-note-dot { width: .48rem; height: .48rem; border-radius: 999px; background: var(--accent, #d8b273); box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent, #d8b273) 13%, transparent 87%); }
      .state-journal-turn-note[open] summary { color: var(--text, #f5efe5); }
      .state-journal-note-body { display: grid; gap: .62rem; padding: 0 .82rem .82rem; }
      .state-journal-note-toolbar { display: flex; flex-wrap: wrap; gap: .36rem; color: var(--muted, rgba(245,239,229,.72)); font-size: .74rem; }
      .state-journal-note-section { border: 1px solid var(--border, rgba(255,255,255,.13)); border-radius: .86rem; padding: .68rem; background: rgba(255,255,255,.035); }
      .state-journal-note-section h4 { margin: 0 0 .42rem; font-size: .9rem; }
      .state-journal-note-grid { display: grid; gap: .38rem; }
      .state-journal-note-field { display: grid; gap: .11rem; }
      .state-journal-note-field span { color: var(--muted, rgba(245,239,229,.68)); font-size: .7rem; }
      .state-journal-note-field strong { font-size: .8rem; line-height: 1.5; font-weight: 600; }
      .state-journal-turn-note.is-note-gufeng .state-journal-note-field strong { font-family: inherit; letter-spacing: .025em; }
      .state-journal-turn-note.is-note-sensory .state-journal-note-grid { gap: .44rem; }
      .state-journal-turn-note.is-note-sensory .state-journal-note-field {
        display: block;
        padding: .44rem .56rem;
        border-radius: .68rem;
        border: 1px solid color-mix(in srgb, var(--accent, #d8b273) 24%, var(--border, rgba(255,255,255,.14)) 76%);
        background: color-mix(in srgb, var(--input-bg, rgba(0,0,0,.16)) 78%, transparent 22%);
      }
      .state-journal-turn-note.is-note-sensory .state-journal-note-field span {
        display: inline;
        color: color-mix(in srgb, var(--accent, #d8b273) 70%, currentColor 30%);
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .04em;
      }
      .state-journal-turn-note.is-note-sensory .state-journal-note-field span::before { content: "<"; }
      .state-journal-turn-note.is-note-sensory .state-journal-note-field span::after { content: ">"; }
      .state-journal-turn-note.is-note-sensory .state-journal-note-field strong {
        display: inline;
        margin-left: .42rem;
        font-size: .8rem;
        line-height: 1.65;
        font-weight: 650;
      }
      .state-journal-relation-list { display: grid; gap: .42rem; color: var(--muted, rgba(245,239,229,.74)); font-size: .8rem; line-height: 1.55; }
      .state-journal-note-empty { color: var(--muted, rgba(245,239,229,.72)); font-size: .8rem; padding: .3rem 0; }

      .state-journal-inline-scene-card.theme-gufeng-paper,
      .state-journal-turn-note.theme-gufeng-paper,
      .state-journal-turn-note-compact.theme-gufeng-paper {
        --xj-paper-accent: var(--xj-beauty-accent, #9f5f41);
        border-color: color-mix(in srgb, var(--xj-paper-accent) 38%, rgba(86, 52, 31, .22) 62%);
        background:
          radial-gradient(circle at 16% 0%, rgba(196, 126, 70, .10), transparent 32%),
          linear-gradient(135deg, rgba(255, 248, 232, .94), rgba(238, 224, 199, .86));
        color: #2f251d;
        box-shadow: 0 12px 32px rgba(78, 50, 32, .14), inset 0 0 0 1px rgba(255,255,255,.34);
      }
      .state-journal-inline-scene-card.theme-gufeng-paper .state-journal-scene-kicker,
      .state-journal-inline-scene-card.theme-gufeng-paper .state-journal-scene-toggle,
      .state-journal-turn-note.theme-gufeng-paper .state-journal-note-toolbar,
      .state-journal-turn-note.theme-gufeng-paper .state-journal-note-field span,
      .state-journal-turn-note-compact.theme-gufeng-paper strong { color: var(--xj-paper-accent); }
      .state-journal-inline-scene-card.theme-gufeng-paper .state-journal-scene-subtitle,
      .state-journal-inline-scene-card.theme-gufeng-paper .state-journal-scene-chip,
      .state-journal-turn-note.theme-gufeng-paper summary,
      .state-journal-turn-note.theme-gufeng-paper .state-journal-relation-list,
      .state-journal-turn-note.theme-gufeng-paper .state-journal-note-empty,
      .state-journal-turn-note-compact.theme-gufeng-paper span { color: rgba(47,37,29,.72); }
      .state-journal-inline-scene-card.theme-gufeng-paper .state-journal-scene-title { font-weight: 900; letter-spacing: .08em; }
      .state-journal-inline-scene-card.theme-gufeng-paper .state-journal-scene-chip,
      .state-journal-turn-note.theme-gufeng-paper .state-journal-note-section,
      .state-journal-turn-note.theme-gufeng-paper .state-journal-note-field {
        border-color: rgba(126, 76, 45, .18);
        background: rgba(255, 253, 244, .48);
      }
      .state-journal-turn-note.theme-gufeng-paper .state-journal-note-field {
        border-radius: .55rem;
        box-shadow: inset 3px 0 0 color-mix(in srgb, var(--xj-paper-accent) 46%, transparent 54%);
      }
      .state-journal-turn-note.theme-gufeng-paper .state-journal-note-field span::before,
      .state-journal-turn-note.theme-gufeng-paper .state-journal-note-field span::after { content: ""; }
      .state-journal-turn-note.theme-gufeng-paper .state-journal-note-field strong { color: #2f251d; font-weight: 700; }
      .state-journal-turn-note.theme-gufeng-paper .state-journal-note-dot { background: var(--xj-paper-accent); box-shadow: 0 0 0 4px color-mix(in srgb, var(--xj-paper-accent) 14%, transparent 86%); }


      /* v0.7 外观模板包：现代 Time Card 结构 */
      .state-journal-inline-scene-card.theme-time-card,
      .state-journal-turn-note.theme-time-card,
      .state-journal-turn-note-compact.theme-time-card {
        --xj-time-accent: var(--xj-beauty-accent, #1f6feb);
        background: rgba(255,255,255,.92);
        color: #2e3440;
        border-color: rgba(31,111,235,.18);
        box-shadow: 0 14px 36px rgba(24, 40, 72, .14), inset 0 1px 0 rgba(255,255,255,.88);
      }
      .state-journal-inline-scene-card.theme-time-card { border-radius: 1.15rem; }
      .state-journal-inline-scene-card.theme-time-card summary { padding: .9rem 1rem .64rem; }
      .state-journal-inline-scene-card.theme-time-card .state-journal-scene-kicker { color: #697386; letter-spacing: .12em; font-size: .74rem; }
      .state-journal-inline-scene-card.theme-time-card .state-journal-scene-title { color: #101828; font-size: 1.05rem; letter-spacing: .02em; }
      .state-journal-inline-scene-card.theme-time-card .state-journal-scene-subtitle { color: #4b5565; }
      .state-journal-inline-scene-card.theme-time-card .state-journal-scene-toggle { color: #6b7280; }
      .state-journal-inline-scene-card.theme-time-card .state-journal-scene-body { padding: .15rem 1rem 1rem; gap: .65rem; }
      .state-journal-inline-scene-card.theme-time-card .state-journal-scene-meta { display: grid; gap: .45rem; }
      .state-journal-inline-scene-card.theme-time-card .state-journal-scene-chip {
        display: grid;
        grid-template-columns: 1.35rem auto 1fr;
        align-items: start;
        gap: .45rem;
        border: 0;
        border-radius: .72rem;
        padding: .46rem .64rem;
        background: rgba(248,250,252,.88);
        color: #475467;
        font-size: .8rem;
      }
      .state-journal-inline-scene-card.theme-time-card .state-journal-scene-chip b { color: #9b4b43; font-weight: 800; }
      .state-journal-inline-scene-card.theme-time-card .state-journal-scene-event {
        border: 0;
        border-top: 2px solid rgba(31,111,235,.14);
        padding: .7rem .25rem 0;
        color: #344054;
        line-height: 1.7;
      }
      .state-journal-turn-note.theme-time-card .state-journal-note-body { gap: .7rem; }
      .state-journal-turn-note.theme-time-card .state-journal-note-toolbar { color: #697386; }
      .state-journal-turn-note.theme-time-card summary { color: #475467; }
      .state-journal-turn-note.theme-time-card .state-journal-note-section {
        background: rgba(255,255,255,.78);
        border-color: rgba(31,111,235,.14);
        border-radius: 1rem;
      }
      .state-journal-turn-note.theme-time-card .state-journal-note-section h4 { color: #101828; letter-spacing: .02em; }
      .state-journal-turn-note.theme-time-card .state-journal-note-grid { gap: .32rem; }
      .state-journal-turn-note.theme-time-card .state-journal-note-field {
        display: grid;
        grid-template-columns: 1.35rem 5.4rem 1fr;
        align-items: start;
        gap: .48rem;
        padding: .42rem .25rem;
        border: 0;
        border-bottom: 1px solid rgba(102,112,133,.14);
        background: transparent;
        border-radius: 0;
      }
      .state-journal-turn-note.theme-time-card .state-journal-note-field:last-child { border-bottom: 0; }
      .state-journal-turn-note.theme-time-card .state-journal-note-field .state-journal-note-icon { font-style: normal; text-align: center; opacity: .92; }
      .state-journal-turn-note.theme-time-card .state-journal-note-field span { color: #9b4b43; font-weight: 800; font-size: .78rem; }
      .state-journal-turn-note.theme-time-card .state-journal-note-field span::before,
      .state-journal-turn-note.theme-time-card .state-journal-note-field span::after { content: ""; }
      .state-journal-turn-note.theme-time-card .state-journal-note-field strong { color: #344054; font-size: .84rem; line-height: 1.72; font-weight: 500; margin-left: 0; }
      .state-journal-turn-note.theme-time-card .state-journal-relation-list {
        background: rgba(245,249,255,.8);
        border-radius: .8rem;
        padding: .6rem .72rem;
        color: #475467;
      }
      .state-journal-turn-note-compact.theme-time-card { border-radius: 999px; background: rgba(255,255,255,.9); color: #475467; }
      .state-journal-turn-note-compact.theme-time-card strong { color: var(--xj-time-accent); }

      /* v0.7 外观模板包：古风结构强化 */
      .state-journal-inline-scene-card.theme-gufeng-paper .state-journal-scene-meta { gap: .42rem; }
      .state-journal-inline-scene-card.theme-gufeng-paper .state-journal-scene-event { color: #3f3026; }
      .state-journal-turn-note.theme-gufeng-paper .state-journal-note-section h4::before { content: "◇ "; color: var(--xj-paper-accent); }



      /* v0.7.1 美化包扩展：月白冷笺 */
      .state-journal-inline-scene-card.theme-moon-white,
      .state-journal-turn-note.theme-moon-white,
      .state-journal-turn-note-compact.theme-moon-white {
        --xj-moon-accent: var(--xj-beauty-accent, #7e9bb8);
        background:
          radial-gradient(circle at 12% 0%, rgba(174, 203, 232, .18), transparent 30%),
          linear-gradient(145deg, rgba(247,250,253,.96), rgba(227,235,244,.9));
        color: #243244;
        border-color: rgba(126,155,184,.32);
        box-shadow: 0 14px 34px rgba(50, 75, 105, .12), inset 0 1px 0 rgba(255,255,255,.65);
      }
      .state-journal-inline-scene-card.theme-moon-white .state-journal-scene-kicker,
      .state-journal-inline-scene-card.theme-moon-white .state-journal-scene-toggle,
      .state-journal-turn-note.theme-moon-white .state-journal-note-toolbar,
      .state-journal-turn-note.theme-moon-white .state-journal-note-field span,
      .state-journal-turn-note-compact.theme-moon-white strong { color: var(--xj-moon-accent); }
      .state-journal-inline-scene-card.theme-moon-white .state-journal-scene-subtitle,
      .state-journal-inline-scene-card.theme-moon-white .state-journal-scene-chip,
      .state-journal-turn-note.theme-moon-white summary,
      .state-journal-turn-note.theme-moon-white .state-journal-relation-list,
      .state-journal-turn-note-compact.theme-moon-white span { color: rgba(36,50,68,.68); }
      .state-journal-inline-scene-card.theme-moon-white .state-journal-scene-title { color: #1f2c3c; font-weight: 900; letter-spacing: .05em; }
      .state-journal-inline-scene-card.theme-moon-white .state-journal-scene-chip,
      .state-journal-turn-note.theme-moon-white .state-journal-note-section,
      .state-journal-turn-note.theme-moon-white .state-journal-note-field {
        border-color: rgba(126,155,184,.2);
        background: rgba(255,255,255,.5);
      }
      .state-journal-turn-note.theme-moon-white .state-journal-note-field { border-radius: .7rem; box-shadow: inset 2px 0 0 rgba(126,155,184,.34); }
      .state-journal-turn-note.theme-moon-white .state-journal-note-field span::before,
      .state-journal-turn-note.theme-moon-white .state-journal-note-field span::after { content: ""; }
      .state-journal-turn-note.theme-moon-white .state-journal-note-field strong { color: #243244; }

      /* v0.7.1 美化包扩展：朱砂密卷 */
      .state-journal-inline-scene-card.theme-cinnabar-dossier,
      .state-journal-turn-note.theme-cinnabar-dossier,
      .state-journal-turn-note-compact.theme-cinnabar-dossier {
        --xj-case-accent: var(--xj-beauty-accent, #b8322a);
        background:
          linear-gradient(90deg, rgba(184,50,42,.08), transparent 34%),
          linear-gradient(145deg, rgba(245,238,222,.96), rgba(222,207,183,.92));
        color: #211b17;
        border-color: rgba(94,45,30,.28);
        box-shadow: 0 16px 36px rgba(64, 34, 22, .18), inset 0 0 0 1px rgba(255,255,255,.28);
      }
      .state-journal-inline-scene-card.theme-cinnabar-dossier .state-journal-scene-kicker,
      .state-journal-turn-note.theme-cinnabar-dossier .state-journal-note-toolbar,
      .state-journal-turn-note.theme-cinnabar-dossier .state-journal-note-field span,
      .state-journal-turn-note-compact.theme-cinnabar-dossier strong { color: var(--xj-case-accent); }
      .state-journal-inline-scene-card.theme-cinnabar-dossier .state-journal-scene-title { color: #1b1410; font-weight: 950; letter-spacing: .08em; }
      .state-journal-inline-scene-card.theme-cinnabar-dossier .state-journal-scene-kicker::before { content: "卷宗 · "; }
      .state-journal-inline-scene-card.theme-cinnabar-dossier .state-journal-scene-chip,
      .state-journal-turn-note.theme-cinnabar-dossier .state-journal-note-section,
      .state-journal-turn-note.theme-cinnabar-dossier .state-journal-note-field {
        border-color: rgba(126, 51, 38, .2);
        background: rgba(255,249,237,.55);
      }
      .state-journal-turn-note.theme-cinnabar-dossier .state-journal-note-section h4::before { content: "【人物】"; color: var(--xj-case-accent); margin-right: .25rem; }
      .state-journal-turn-note.theme-cinnabar-dossier .state-journal-note-field { border-radius: .42rem; border-left: 3px solid rgba(184,50,42,.42); }
      .state-journal-turn-note.theme-cinnabar-dossier .state-journal-note-field span::before,
      .state-journal-turn-note.theme-cinnabar-dossier .state-journal-note-field span::after { content: ""; }
      .state-journal-turn-note.theme-cinnabar-dossier .state-journal-note-field strong,
      .state-journal-turn-note.theme-cinnabar-dossier summary,
      .state-journal-turn-note.theme-cinnabar-dossier .state-journal-relation-list { color: #2b201b; }

      /* v0.7.1 美化包扩展：玉简灵纹 */
      .state-journal-inline-scene-card.theme-jade-slip,
      .state-journal-turn-note.theme-jade-slip,
      .state-journal-turn-note-compact.theme-jade-slip {
        --xj-jade-accent: var(--xj-beauty-accent, #47a985);
        background:
          radial-gradient(circle at 90% 8%, rgba(91, 225, 185, .20), transparent 28%),
          linear-gradient(145deg, rgba(236,252,246,.95), rgba(210,235,226,.9));
        color: #183b32;
        border-color: rgba(71,169,133,.32);
        box-shadow: 0 14px 34px rgba(20, 97, 76, .16), 0 0 0 1px rgba(188, 255, 234, .34) inset;
      }
      .state-journal-inline-scene-card.theme-jade-slip .state-journal-scene-kicker,
      .state-journal-inline-scene-card.theme-jade-slip .state-journal-scene-toggle,
      .state-journal-turn-note.theme-jade-slip .state-journal-note-toolbar,
      .state-journal-turn-note.theme-jade-slip .state-journal-note-field span,
      .state-journal-turn-note-compact.theme-jade-slip strong { color: #237d64; }
      .state-journal-inline-scene-card.theme-jade-slip .state-journal-scene-kicker::before { content: "灵简 · "; }
      .state-journal-inline-scene-card.theme-jade-slip .state-journal-scene-title { color: #14392f; letter-spacing: .07em; text-shadow: 0 0 16px rgba(71,169,133,.18); }
      .state-journal-inline-scene-card.theme-jade-slip .state-journal-scene-chip,
      .state-journal-turn-note.theme-jade-slip .state-journal-note-section,
      .state-journal-turn-note.theme-jade-slip .state-journal-note-field {
        border-color: rgba(71,169,133,.22);
        background: rgba(244,255,251,.54);
      }
      .state-journal-turn-note.theme-jade-slip .state-journal-note-field { box-shadow: inset 0 0 0 1px rgba(188,255,234,.36); }
      .state-journal-turn-note.theme-jade-slip .state-journal-note-field span::before { content: "◇ "; }
      .state-journal-turn-note.theme-jade-slip .state-journal-note-field span::after { content: ""; }
      .state-journal-turn-note.theme-jade-slip .state-journal-note-field strong,
      .state-journal-turn-note.theme-jade-slip summary,
      .state-journal-turn-note.theme-jade-slip .state-journal-relation-list { color: #183b32; }

      /* v0.7.1 美化包扩展：暗夜档案 */
      .state-journal-inline-scene-card.theme-midnight-archive,
      .state-journal-turn-note.theme-midnight-archive,
      .state-journal-turn-note-compact.theme-midnight-archive {
        --xj-night-accent: var(--xj-beauty-accent, #62d6ff);
        background:
          linear-gradient(135deg, rgba(15,23,42,.96), rgba(3,7,18,.93));
        color: #d8f3ff;
        border-color: rgba(98,214,255,.28);
        box-shadow: 0 18px 42px rgba(0,0,0,.32), 0 0 0 1px rgba(98,214,255,.08) inset;
      }
      .state-journal-inline-scene-card.theme-midnight-archive .state-journal-scene-kicker,
      .state-journal-turn-note.theme-midnight-archive .state-journal-note-toolbar,
      .state-journal-turn-note.theme-midnight-archive .state-journal-note-field span,
      .state-journal-turn-note-compact.theme-midnight-archive strong { color: var(--xj-night-accent); }
      .state-journal-inline-scene-card.theme-midnight-archive .state-journal-scene-title { color: #f1fbff; letter-spacing: .08em; }
      .state-journal-inline-scene-card.theme-midnight-archive .state-journal-scene-kicker::before { content: "XJ-FILE // "; }
      .state-journal-inline-scene-card.theme-midnight-archive .state-journal-scene-subtitle,
      .state-journal-turn-note.theme-midnight-archive summary,
      .state-journal-turn-note.theme-midnight-archive .state-journal-relation-list,
      .state-journal-turn-note-compact.theme-midnight-archive span { color: rgba(216,243,255,.76); }
      .state-journal-inline-scene-card.theme-midnight-archive .state-journal-scene-chip,
      .state-journal-turn-note.theme-midnight-archive .state-journal-note-section,
      .state-journal-turn-note.theme-midnight-archive .state-journal-note-field {
        border-color: rgba(98,214,255,.16);
        background: rgba(15,23,42,.54);
      }
      .state-journal-turn-note.theme-midnight-archive .state-journal-note-field { grid-template-columns: 3.8rem 5rem 1fr; }
      .state-journal-turn-note.theme-midnight-archive .state-journal-note-field span::before,
      .state-journal-turn-note.theme-midnight-archive .state-journal-note-field span::after { content: ""; }
      .state-journal-turn-note.theme-midnight-archive .state-journal-note-field strong { color: #e8fbff; }

      /* v0.7.1 美化包扩展：剧本分镜 */
      .state-journal-inline-scene-card.theme-storyboard,
      .state-journal-turn-note.theme-storyboard,
      .state-journal-turn-note-compact.theme-storyboard {
        --xj-shot-accent: var(--xj-beauty-accent, #f59e0b);
        background:
          linear-gradient(90deg, rgba(0,0,0,.035) 1px, transparent 1px),
          linear-gradient(180deg, rgba(255,255,255,.96), rgba(246,241,231,.92));
        background-size: 18px 18px, auto;
        color: #25201a;
        border-color: rgba(15,23,42,.20);
        box-shadow: 0 14px 34px rgba(30, 25, 18, .14);
      }
      .state-journal-inline-scene-card.theme-storyboard .state-journal-scene-kicker,
      .state-journal-turn-note.theme-storyboard .state-journal-note-toolbar,
      .state-journal-turn-note.theme-storyboard .state-journal-note-field span,
      .state-journal-turn-note-compact.theme-storyboard strong { color: #b76b00; }
      .state-journal-inline-scene-card.theme-storyboard .state-journal-scene-kicker::before { content: "SCENE / "; }
      .state-journal-inline-scene-card.theme-storyboard .state-journal-scene-title { color: #17130f; font-weight: 950; }
      .state-journal-inline-scene-card.theme-storyboard .state-journal-scene-chip,
      .state-journal-turn-note.theme-storyboard .state-journal-note-section,
      .state-journal-turn-note.theme-storyboard .state-journal-note-field {
        border-color: rgba(15,23,42,.16);
        background: rgba(255,255,255,.68);
      }
      .state-journal-turn-note.theme-storyboard .state-journal-note-section h4::before { content: "TAKE · "; color: #b76b00; font-size: .72rem; }
      .state-journal-turn-note.theme-storyboard .state-journal-note-field span::before,
      .state-journal-turn-note.theme-storyboard .state-journal-note-field span::after { content: ""; }
      .state-journal-turn-note.theme-storyboard .state-journal-note-field strong,
      .state-journal-turn-note.theme-storyboard summary,
      .state-journal-turn-note.theme-storyboard .state-journal-relation-list { color: #25201a; }

      /* v0.7.1 美化包扩展：状态面板 Pro */
      .state-journal-inline-scene-card.theme-status-pro,
      .state-journal-turn-note.theme-status-pro,
      .state-journal-turn-note-compact.theme-status-pro {
        --xj-status-accent: var(--xj-beauty-accent, #7c3aed);
        background:
          linear-gradient(135deg, rgba(24,20,39,.94), rgba(12,10,20,.92));
        color: #efe9ff;
        border-color: rgba(124,58,237,.36);
        box-shadow: 0 18px 44px rgba(0,0,0,.34), 0 0 22px rgba(124,58,237,.12);
      }
      .state-journal-inline-scene-card.theme-status-pro .state-journal-scene-kicker,
      .state-journal-turn-note.theme-status-pro .state-journal-note-toolbar,
      .state-journal-turn-note.theme-status-pro .state-journal-note-field span,
      .state-journal-turn-note-compact.theme-status-pro strong { color: #b99cff; }
      .state-journal-inline-scene-card.theme-status-pro .state-journal-scene-kicker::before { content: "STATUS PANEL · "; }
      .state-journal-inline-scene-card.theme-status-pro .state-journal-scene-title { color: #fff; letter-spacing: .05em; }
      .state-journal-inline-scene-card.theme-status-pro .state-journal-scene-subtitle,
      .state-journal-turn-note.theme-status-pro summary,
      .state-journal-turn-note.theme-status-pro .state-journal-relation-list,
      .state-journal-turn-note-compact.theme-status-pro span { color: rgba(239,233,255,.75); }
      .state-journal-inline-scene-card.theme-status-pro .state-journal-scene-chip,
      .state-journal-turn-note.theme-status-pro .state-journal-note-section,
      .state-journal-turn-note.theme-status-pro .state-journal-note-field {
        border-color: rgba(124,58,237,.2);
        background: rgba(255,255,255,.055);
      }
      .state-journal-turn-note.theme-status-pro .state-journal-note-section h4 { color: #fff; }
      .state-journal-turn-note.theme-status-pro .state-journal-note-field { grid-template-columns: 3.4rem 5rem 1fr; }
      .state-journal-turn-note.theme-status-pro .state-journal-note-field span::before,
      .state-journal-turn-note.theme-status-pro .state-journal-note-field span::after { content: ""; }
      .state-journal-turn-note.theme-status-pro .state-journal-note-field strong { color: #f5f0ff; }


      /* v0.7.2：结构级外置美化包支持 */
      .state-journal-inline-scene-card.is-layout-paper-time,
      .state-journal-turn-note.is-theme-layout-paper_time,
      .state-journal-turn-note.is-theme-layout-paper_time_card {
        background:
          linear-gradient(90deg, rgba(126, 81, 42, .055) 1px, transparent 1px),
          linear-gradient(180deg, rgba(255,252,245,.98), rgba(248,241,229,.94));
        background-size: 24px 24px, auto;
        color: #2d261f;
        border-color: rgba(166, 115, 68, .28);
        box-shadow: 0 16px 38px rgba(86, 58, 29, .16);
      }
      .state-journal-inline-scene-card.is-layout-paper-time .state-journal-scene-kicker,
      .state-journal-turn-note.is-theme-layout-paper_time .state-journal-note-toolbar,
      .state-journal-turn-note.is-theme-layout-paper_time .state-journal-note-section h4,
      .state-journal-paper-note-row span,
      .state-journal-paper-time-row b { color: var(--xj-beauty-accent, #a75f2f); }
      .state-journal-inline-scene-card.is-layout-paper-time .state-journal-scene-title,
      .state-journal-turn-note.is-theme-layout-paper_time summary { color: #211912; }
      .state-journal-scene-paper-rows,
      .state-journal-paper-note-table { display: grid; gap: .38rem; }
      .state-journal-paper-time-row,
      .state-journal-paper-note-row {
        display: grid;
        grid-template-columns: 1.4rem 4.4rem minmax(0, 1fr);
        gap: .58rem;
        align-items: start;
        padding: .42rem .1rem;
        border-bottom: 1px dashed rgba(166,115,68,.20);
        color: #3a3028;
      }
      .state-journal-paper-time-row:last-child,
      .state-journal-paper-note-row:last-child { border-bottom: 0; }
      .state-journal-paper-note-row strong,
      .state-journal-paper-time-row span { font-weight: 600; line-height: 1.55; color: #312821; }

      .state-journal-inline-scene-card.is-layout-status-panel,
      .state-journal-turn-note.is-theme-layout-status_panel,
      .state-journal-turn-note.is-theme-layout-status_panel_pro,
      .state-journal-turn-note.is-theme-layout-hud {
        background:
          linear-gradient(90deg, rgba(79, 180, 255, .055) 1px, transparent 1px),
          linear-gradient(180deg, rgba(8,18,34,.97), rgba(3,8,18,.95));
        background-size: 18px 18px, auto;
        color: #d9f0ff;
        border-color: rgba(72, 188, 255, .35);
        box-shadow: 0 20px 48px rgba(0,0,0,.42), 0 0 24px rgba(56,189,248,.12);
      }
      .state-journal-status-scene-hud { display: grid; grid-template-columns: repeat(auto-fit, minmax(8.5rem, 1fr)); gap: .46rem; }
      .state-journal-status-scene-hud span,
      .state-journal-status-row {
        border: 1px solid rgba(72,188,255,.18);
        background: rgba(15,36,66,.50);
        border-radius: .56rem;
        padding: .48rem .56rem;
        color: rgba(217,240,255,.86);
      }
      .state-journal-status-scene-hud b,
      .state-journal-status-row span { color: #82d8ff; font-weight: 800; margin-right: .32rem; }
      .state-journal-status-timeline { display:flex; justify-content:space-between; align-items:center; color:#82d8ff; border-top:1px solid rgba(72,188,255,.18); padding-top:.52rem; letter-spacing:.08em; }
      .state-journal-status-note-table { display: grid; gap: .52rem; border: 0; border-radius: .78rem; overflow: visible; }
      .state-journal-status-row {
        display: grid;
        grid-template-columns: 1.55rem minmax(4.6rem, 5.6rem) minmax(0, 1fr) 2.1rem;
        align-items: start;
        gap: .62rem;
        border: 1px solid rgba(72,188,255,.16);
        border-radius: .68rem;
        padding: .62rem .7rem;
        background: rgba(15,36,66,.42);
      }
      .state-journal-status-row strong { color: #eefaff; line-height: 1.7; font-weight: 600; overflow-wrap: anywhere; }
      .state-journal-status-row i { color: rgba(130,216,255,.42); font-style: normal; text-align: right; font-size: .72rem; }
      @media (max-width: 720px) {
        .state-journal-status-row { grid-template-columns: 1.35rem 4.6rem minmax(0, 1fr); }
        .state-journal-status-row i { display: none; }
      }

      .state-journal-inline-scene-card.is-layout-storyboard,
      .state-journal-turn-note.is-theme-layout-storyboard,
      .state-journal-turn-note.is-theme-layout-storyboard_frame,
      .state-journal-turn-note.is-theme-layout-scene_board {
        background:
          linear-gradient(90deg, rgba(0,0,0,.045) 1px, transparent 1px),
          linear-gradient(180deg, rgba(34,31,27,.96), rgba(16,15,13,.95));
        background-size: 20px 20px, auto;
        color: #efe7d6;
        border-color: rgba(208, 137, 56, .34);
        box-shadow: 0 18px 44px rgba(0,0,0,.38);
      }
      .state-journal-storyboard-hero { grid-template-columns: minmax(0, .9fr) minmax(10rem, 1.15fr); align-items: stretch; }
      .state-journal-storyboard-meta { display:grid; gap:.18rem; padding:.58rem; border:1px solid rgba(208,137,56,.22); border-radius:.66rem; background:rgba(255,255,255,.035); }
      .state-journal-storyboard-meta p { margin: 0; line-height: 1.55; color: rgba(239,231,214,.78); }
      .state-journal-storyboard-meta b { color: #d18a38; }
      .state-journal-storyboard-frame {
        min-height: 8.6rem;
        border: 1px solid rgba(208,137,56,.30);
        border-radius: .66rem;
        display:grid;
        place-content:center;
        text-align:center;
        background: linear-gradient(135deg, rgba(255,255,255,.055), rgba(0,0,0,.12));
        color: rgba(239,231,214,.58);
        overflow: hidden;
        position: relative;
      }
      .state-journal-storyboard-frame.has-image { display: block; padding: 0; min-height: 9.6rem; }
      .state-journal-storyboard-frame.has-image::before {
        content: "";
        position: absolute;
        inset: 0;
        pointer-events: none;
        background: linear-gradient(180deg, rgba(0,0,0,.10), transparent 34%, rgba(0,0,0,.18));
        z-index: 1;
      }
      .state-journal-storyboard-frame.has-image::after {
        content: "STORYBOARD  ·  FRAME";
        position: absolute;
        left: .58rem;
        right: .58rem;
        bottom: .38rem;
        z-index: 2;
        color: rgba(255,245,225,.76);
        font-size: .58rem;
        letter-spacing: .22em;
        text-align: right;
        text-shadow: 0 1px 4px rgba(0,0,0,.55);
      }
      .state-journal-storyboard-frame img { width: 100%; height: 100%; min-height: 9.6rem; object-fit: cover; display:block; }
      .state-journal-storyboard-frame span { display:block; color:#d18a38; font-weight:900; letter-spacing:.08em; }
      .state-journal-storyboard-frame small { display:block; margin-top:.35rem; font-size:.68rem; }
      .state-journal-inline-scene-card.is-layout-storyboard .state-journal-scene-event { grid-column: 1 / -1; border-color:#d18a38; color:rgba(239,231,214,.82); }
      .state-journal-storyboard-note-table { display: grid; border: 1px solid rgba(208,137,56,.20); border-radius:.75rem; overflow:hidden; }
      .state-journal-storyboard-row { display:grid; grid-template-columns: 2rem 5rem minmax(0, 1fr); gap:.55rem; padding:.5rem .58rem; border-bottom:1px solid rgba(208,137,56,.16); align-items:start; }
      .state-journal-storyboard-row:last-child { border-bottom:0; }
      .state-journal-storyboard-row span { color:#d18a38; }
      .state-journal-storyboard-row b { color:#d18a38; font-weight:800; }
      .state-journal-storyboard-row strong { color:#f3ead9; line-height:1.55; font-weight:600; }

      /* v0.7.4：三类结构包的角色状态栏差异化 */
      .state-journal-turn-note.is-theme-layout-paper_time .state-journal-note-section {
        background: rgba(255,255,255,.58);
        border-color: rgba(166,115,68,.18);
        padding: .9rem 1rem;
      }
      .state-journal-turn-note.is-theme-layout-paper_time .state-journal-note-section h4 {
        color: #9b5a2c;
        font-size: .9rem;
        letter-spacing: .08em;
        border-bottom: 1px dashed rgba(166,115,68,.22);
        padding-bottom: .35rem;
        margin-bottom: .6rem;
      }
      .state-journal-turn-note.is-theme-layout-paper_time .state-journal-paper-note-table { display: grid; gap: .48rem; }
      .state-journal-turn-note.is-theme-layout-paper_time .state-journal-paper-note-row {
        display: grid;
        grid-template-columns: 4.8rem minmax(0,1fr);
        gap: .6rem;
        padding: .12rem 0 .42rem;
        border-bottom: 1px dotted rgba(166,115,68,.18);
      }
      .state-journal-turn-note.is-theme-layout-paper_time .state-journal-paper-note-row i { display:none; }
      .state-journal-turn-note.is-theme-layout-paper_time .state-journal-paper-note-row span { color:#a75f2f; font-weight:850; font-size:.78rem; }
      .state-journal-turn-note.is-theme-layout-paper_time .state-journal-paper-note-row strong { color:#312821; font-weight:520; line-height:1.78; }

      .state-journal-turn-note.is-theme-layout-status_panel .state-journal-note-section,
      .state-journal-turn-note.is-theme-layout-status_panel_pro .state-journal-note-section,
      .state-journal-turn-note.is-theme-layout-hud .state-journal-note-section {
        border-color: rgba(72,188,255,.22);
        background: rgba(5,16,30,.56);
        padding: .8rem;
      }
      .state-journal-turn-note.is-theme-layout-status_panel .state-journal-note-section h4,
      .state-journal-turn-note.is-theme-layout-status_panel_pro .state-journal-note-section h4,
      .state-journal-turn-note.is-theme-layout-hud .state-journal-note-section h4 {
        color:#82d8ff;
        font-size:.78rem;
        letter-spacing:.16em;
        text-transform:uppercase;
        margin-bottom:.7rem;
      }
      .state-journal-turn-note.is-theme-layout-status_panel .state-journal-status-note-table,
      .state-journal-turn-note.is-theme-layout-status_panel_pro .state-journal-status-note-table,
      .state-journal-turn-note.is-theme-layout-hud .state-journal-status-note-table { gap:.44rem; }
      .state-journal-turn-note.is-theme-layout-status_panel .state-journal-status-row,
      .state-journal-turn-note.is-theme-layout-status_panel_pro .state-journal-status-row,
      .state-journal-turn-note.is-theme-layout-hud .state-journal-status-row {
        grid-template-columns: 5.4rem minmax(0,1fr) 2rem;
        gap:.7rem;
        padding:.68rem .78rem;
        border-color: rgba(72,188,255,.14);
        background: linear-gradient(90deg, rgba(72,188,255,.10), rgba(15,36,66,.28));
      }
      .state-journal-turn-note.is-theme-layout-status_panel .state-journal-status-row em,
      .state-journal-turn-note.is-theme-layout-status_panel_pro .state-journal-status-row em,
      .state-journal-turn-note.is-theme-layout-hud .state-journal-status-row em { display:none; }
      .state-journal-turn-note.is-theme-layout-status_panel .state-journal-status-row span,
      .state-journal-turn-note.is-theme-layout-status_panel_pro .state-journal-status-row span,
      .state-journal-turn-note.is-theme-layout-hud .state-journal-status-row span { color:#82d8ff; font-size:.72rem; letter-spacing:.08em; font-weight:900; }
      .state-journal-turn-note.is-theme-layout-status_panel .state-journal-status-row strong,
      .state-journal-turn-note.is-theme-layout-status_panel_pro .state-journal-status-row strong,
      .state-journal-turn-note.is-theme-layout-hud .state-journal-status-row strong { color:#eaf8ff; font-size:.8rem; line-height:1.62; font-weight:560; }

      .state-journal-turn-note.is-theme-layout-storyboard .state-journal-note-section {
        background: rgba(0,0,0,.18);
        border-color: rgba(208,137,56,.22);
        padding: .8rem;
      }
      .state-journal-turn-note.is-theme-layout-storyboard .state-journal-note-section h4 {
        color:#d18a38;
        font-size:.84rem;
        letter-spacing:.12em;
        text-transform:uppercase;
        border-bottom: 1px solid rgba(208,137,56,.18);
        padding-bottom:.42rem;
      }
      .state-journal-turn-note.is-theme-layout-storyboard .state-journal-storyboard-row {
        grid-template-columns: 1.5rem 4.6rem minmax(0,1fr);
        padding:.62rem .65rem;
        background: rgba(255,255,255,.018);
      }
      .state-journal-turn-note.is-theme-layout-storyboard .state-journal-storyboard-row b { letter-spacing:.08em; }


      /* v0.7.6.2：外观包只改布局，不裁剪字段；三套角色状态视图差异化 */
      .state-journal-metric-strip { display:flex; flex-wrap:wrap; gap:.36rem; margin-bottom:.58rem; }
      .state-journal-metric-chip { display:inline-flex; align-items:center; gap:.34rem; border-radius:999px; padding:.28rem .52rem; font-size:.72rem; line-height:1.2; border:1px solid rgba(255,255,255,.12); background:rgba(255,255,255,.055); }
      .state-journal-metric-chip b { color:inherit; font-weight:900; }
      .state-journal-metric-chip i { font-style:normal; opacity:.82; }
      .state-journal-metric-diary { margin-top:.75rem; }
      .state-journal-metric-diary-list { display:grid; gap:.45rem; }
      .state-journal-metric-diary-row { border:1px solid rgba(201,130,99,.18); border-radius:14px; padding:.55rem .65rem; background:rgba(255,255,255,.045); }
      .state-journal-metric-diary-row strong { display:block; margin-bottom:.35rem; font-size:.85rem; }
      .state-journal-metric-diary-row p { margin:0; display:flex; flex-wrap:wrap; gap:.35rem; }
      .state-journal-metric-diary-row span { display:inline-flex; gap:.25rem; align-items:center; border-radius:999px; padding:.22rem .48rem; background:rgba(201,130,99,.08); border:1px solid rgba(201,130,99,.18); font-size:.74rem; }

      .state-journal-status-pro-shell { display:grid; gap:.72rem; }
      .state-journal-status-pro-layer { display:grid; gap:.5rem; }
      .state-journal-status-pro-card {
        border:1px solid rgba(82,196,255,.18); border-radius:.72rem; overflow:hidden;
        background:linear-gradient(135deg, rgba(82,196,255,.075), rgba(7,20,38,.34));
      }
      .state-journal-status-pro-card summary { list-style:none; cursor:pointer; display:grid; grid-template-columns:4.6rem minmax(0,1fr) 2.2rem; gap:.6rem; align-items:center; padding:.56rem .68rem; }
      .state-journal-status-pro-card summary::-webkit-details-marker { display:none; }
      .state-journal-status-pro-card summary span { color:#7bd8ff; font-size:.66rem; font-weight:950; letter-spacing:.14em; }
      .state-journal-status-pro-card summary b { color:#eaf8ff; font-size:.78rem; letter-spacing:.04em; }
      .state-journal-status-pro-card summary i { color:rgba(123,216,255,.56); font-style:normal; text-align:right; font-size:.72rem; }
      .state-journal-status-pro-grid { display:grid; gap:.44rem; padding:0 .62rem .62rem; }
      .state-journal-status-pro-row {
        display:grid; grid-template-columns: 4.8rem minmax(0,1fr) 2.2rem; gap:.72rem; align-items:start;
        padding:.56rem .68rem; border:1px solid rgba(82,196,255,.14); border-radius:.62rem;
        background: linear-gradient(90deg, rgba(82,196,255,.10), rgba(7,20,38,.34));
        box-shadow: inset 2px 0 0 rgba(82,196,255,.28);
      }
      .state-journal-status-pro-row span { color:#7bd8ff; font-size:.68rem; font-weight:950; letter-spacing:.13em; }
      .state-journal-status-pro-row strong { color:#eefaff; font-size:.82rem; line-height:1.62; font-weight:600; }
      .state-journal-status-pro-row i { color:rgba(123,216,255,.45); font-style:normal; text-align:right; font-size:.72rem; }
      .state-journal-status-pro-meters { display:grid; grid-template-columns: repeat(auto-fit, minmax(7.2rem,1fr)); gap:.5rem; }
      .state-journal-status-meter { padding:.5rem .58rem; border:1px solid rgba(82,196,255,.16); border-radius:.62rem; background:rgba(0,0,0,.20); }
      .state-journal-status-meter span { display:block; color:#7bd8ff; font-size:.64rem; font-weight:900; letter-spacing:.12em; margin-bottom:.32rem; }
      .state-journal-status-meter b { display:block; height:.38rem; border-radius:999px; overflow:hidden; background:rgba(255,255,255,.10); }
      .state-journal-status-meter b em { display:block; height:100%; border-radius:999px; background:linear-gradient(90deg,#42caff,#ffc36a); }
      .state-journal-status-meter i { display:flex; justify-content:flex-end; align-items:center; gap:.34rem; margin-top:.24rem; color:rgba(238,250,255,.78); font-style:normal; font-size:.7rem; }
      .state-journal-status-meter i small { color:#ffc36a; font-size:.68rem; }
      .state-journal-turn-note.is-theme-layout-status_panel .state-journal-status-note-table,
      .state-journal-turn-note.is-theme-layout-status_panel_pro .state-journal-status-note-table,
      .state-journal-turn-note.is-theme-layout-hud .state-journal-status-note-table { display:none; }

      .state-journal-paper-note-table.is-literary-note { display:grid; gap:.58rem; }
      .state-journal-paper-note-table.is-literary-note .state-journal-metric-strip { margin-bottom:.2rem; padding-bottom:.5rem; border-bottom:1px dashed rgba(166,115,68,.22); }
      .state-journal-paper-note-table.is-literary-note .state-journal-metric-chip { color:#8f4f27; background:rgba(255,248,232,.48); border-color:rgba(166,115,68,.22); }
      .state-journal-paper-note-table.is-literary-note .state-journal-paper-note-row {
        grid-template-columns: 4.8rem minmax(0,1fr);
        padding:.38rem 0 .68rem;
        border-bottom:1px dashed rgba(166,115,68,.20);
        background:transparent;
        border-radius:0;
      }
      .state-journal-paper-note-table.is-literary-note .state-journal-paper-note-row:last-child { border-bottom:0; }
      .state-journal-paper-note-table.is-literary-note .state-journal-paper-note-row i { display:none; }
      .state-journal-paper-note-table.is-literary-note .state-journal-paper-note-row span { color:#a45e30; font-size:.74rem; letter-spacing:.12em; }
      .state-journal-paper-note-table.is-literary-note .state-journal-paper-note-row strong { color:#2f251e; font-size:.9rem; line-height:1.9; font-weight:500; }

      .state-journal-storyboard-note-table.is-cut-sheet { border-radius:.7rem; display:grid; gap:.5rem; border:0; }
      .state-journal-storyboard-note-table.is-cut-sheet .state-journal-metric-strip { margin-bottom:.1rem; }
      .state-journal-storyboard-note-table.is-cut-sheet .state-journal-metric-chip { color:#d18a38; background:rgba(208,137,56,.08); border-color:rgba(208,137,56,.22); }
      .state-journal-storyboard-group { border:1px solid rgba(208,137,56,.18); border-radius:.72rem; overflow:hidden; background:rgba(0,0,0,.12); }
      .state-journal-storyboard-group-title { display:flex; align-items:center; gap:.46rem; padding:.42rem .66rem; border-bottom:1px solid rgba(208,137,56,.16); background:rgba(208,137,56,.08); }
      .state-journal-storyboard-group-title span { color:rgba(209,138,56,.75); font-size:.64rem; letter-spacing:.16em; font-weight:900; }
      .state-journal-storyboard-group-title b { color:#d18a38; font-size:.76rem; letter-spacing:.08em; }
      .state-journal-storyboard-note-table.is-cut-sheet .state-journal-storyboard-row {
        grid-template-columns: 1.4rem 4.8rem minmax(0,1fr);
        padding:.68rem .72rem;
        background:linear-gradient(90deg, rgba(208,137,56,.055), rgba(255,255,255,.014));
        border-bottom:1px solid rgba(208,137,56,.14);
      }
      .state-journal-storyboard-note-table.is-cut-sheet .state-journal-storyboard-row:last-child { border-bottom:0; }
      .state-journal-storyboard-note-table.is-cut-sheet .state-journal-storyboard-row em { color:#d18a38; font-style:normal; }
      .state-journal-storyboard-note-table.is-cut-sheet .state-journal-storyboard-row span { color:#d18a38; font-size:.76rem; letter-spacing:.14em; font-weight:900; }
      .state-journal-storyboard-note-table.is-cut-sheet .state-journal-storyboard-row strong { color:#f6ecd7; font-weight:520; line-height:1.72; }

      @keyframes state-journal-spin { to { transform: rotate(360deg); } }
      @media (max-width: 900px) { .state-journal-chat-bubble { left: 50%; top: 4.8rem; } }
    `;
    document.head.appendChild(style);
  }

  function ensureBubble() {
    ensureVisualStyle();
    let bubble = document.getElementById("state-journal-chat-bubble");
    if (bubble) return bubble;
    bubble = document.createElement("div");
    bubble.id = "state-journal-chat-bubble";
    bubble.className = "state-journal-chat-bubble";
    bubble.setAttribute("role", "status");
    bubble.setAttribute("aria-live", "polite");
    bubble.innerHTML = `
      <span class="state-journal-chat-bubble-mark" aria-hidden="true"></span>
      <span class="state-journal-chat-bubble-copy">
        <strong class="state-journal-chat-bubble-title"></strong>
        <span class="state-journal-chat-bubble-desc"></span>
      </span>
      <button type="button" class="state-journal-chat-bubble-close" aria-label="关闭心笺提示">×</button>
    `;
    bubble.querySelector(".state-journal-chat-bubble-close")?.addEventListener("click", (event) => {
      event.stopPropagation();
      hideBubble();
    });
    bubble.addEventListener("click", () => {
      if (bubble.classList.contains("is-error")) window.open("/mods/state-journal", "_blank");
    });
    document.body.appendChild(bubble);
    return bubble;
  }

  function hideBubble() {
    if (hideTimer) {
      clearTimeout(hideTimer);
      hideTimer = null;
    }
    const bubble = document.getElementById("state-journal-chat-bubble");
    if (bubble) bubble.classList.remove("is-visible");
  }

  function showBubble(kind, title, desc = "", timeout = 0) {
    if (configCache && configCache.notify_in_chat === false) return;
    const bubble = ensureBubble();
    if (hideTimer) {
      clearTimeout(hideTimer);
      hideTimer = null;
    }
    bubble.className = `state-journal-chat-bubble is-${kind}`;
    bubble.querySelector(".state-journal-chat-bubble-title").textContent = title;
    bubble.querySelector(".state-journal-chat-bubble-desc").textContent = desc;
    requestAnimationFrame(() => bubble.classList.add("is-visible"));
    if (timeout > 0) hideTimer = window.setTimeout(hideBubble, timeout);
  }

  function assistantMessages() {
    return [...document.querySelectorAll("#messages .message.assistant:not(.opening-message)")];
  }

  function findLatestAssistantMessage() {
    const messages = assistantMessages();
    return messages[messages.length - 1] || null;
  }

  function findAssistantMessageForDetail(detail = {}) {
    const messages = assistantMessages();
    const messageId = String(detail.assistantMessageId || detail.assistant_message_id || detail.messageId || detail.message_id || "").trim();
    if (messageId) {
      const byMessage = messages.find((msg) => msg.dataset.messageId === messageId);
      if (byMessage) return byMessage;
    }
    const turnId = String(detail.turnId || detail.turn_id || "").trim();
    if (turnId) {
      const byTurn = messages.filter((msg) => msg.dataset.stateJournalTurn === turnId || msg.dataset.turnId === turnId);
      if (byTurn.length) return byTurn[byTurn.length - 1];
    }
    return null;
  }

  function clearAllDomFallbacks() {
    fallbackTimers.forEach((timer) => window.clearInterval(timer));
    fallbackTimers.clear();
  }

  function forgetTurnRuntime(turnId = "") {
    const key = String(turnId || "").trim();
    if (!key) return;
    clearDomFallback(key);
    inFlightTurns.delete(key);
    invalidatedTurns.add(key);
    processedTurns.delete(`fallback:${key}`);
    for (const sig of Array.from(processedTurns)) {
      if (String(sig).includes(`:${key}:`) || String(sig).startsWith(`${key}:`)) processedTurns.delete(sig);
    }
    if (pendingTurn?.turnId === key) pendingTurn = null;
  }

  function invalidateMessageDisplaysFromIndex(index = -1) {
    const minIndex = Number(index);
    assistantMessages().forEach((msg) => {
      const historyIndex = Number(msg.dataset.historyIndex ?? -1);
      if (Number.isFinite(minIndex) && minIndex >= 0 && historyIndex >= 0 && historyIndex < minIndex) return;
      const turnId = msg.dataset.stateJournalTurn || msg.dataset.turnId || "";
      if (turnId) {
        invalidatedTurns.add(turnId);
        clearDomFallback(turnId);
        inFlightTurns.delete(turnId);
      }
      clearExistingTurnDisplay(msg);
    });
  }

  function readMessageText(message) {
    if (!message) return "";
    const stored = message.dataset.messageContent;
    if (typeof stored === "string" && stored.trim()) return stored.trim();
    const body = message.querySelector?.(".bubble-body");
    const bubble = message.querySelector?.(".bubble");
    return String((body || bubble || message).textContent || "").trim();
  }

  function normalizeHookDetail(detail = {}, triggerSource = "chat_hook") {
    const assistantText = String(
      detail.assistantCleanText
      || detail.assistant_clean_text
      || detail.assistantText
      || detail.assistant_text
      || ""
    ).trim();
    const rawAssistantText = String(detail.assistantText || detail.assistant_text || assistantText || "").trim();
    const userText = String(detail.userText || detail.user_text || pendingTurn?.userText || "").trim();
    const turnId = String(detail.turnId || detail.turn_id || pendingTurn?.turnId || makeTurnId(userText || assistantText)).trim();
    const targetMessage = findAssistantMessageForDetail({ ...detail, turnId }) || findLatestAssistantMessage();
    const messageId = String(detail.assistantMessageId || detail.assistant_message_id || detail.messageId || detail.message_id || targetMessage?.dataset?.messageId || "").trim();
    const turnIndex = detail.turnIndex || detail.turn_index || targetMessage?.dataset?.turnIndex || 0;
    const contentHash = String(detail.contentHash || detail.content_hash || detail.assistantHash || detail.assistant_hash || targetMessage?.dataset?.contentHash || simpleHash(assistantText || rawAssistantText)).trim();
    return {
      ...detail,
      triggerSource,
      trigger_source: triggerSource,
      source: detail.source || triggerSource,
      userText,
      user_text: userText,
      assistantText: rawAssistantText || assistantText,
      assistant_text: rawAssistantText || assistantText,
      assistantCleanText: assistantText || rawAssistantText,
      assistant_clean_text: assistantText || rawAssistantText,
      turnId,
      turn_id: turnId,
      messageId,
      message_id: messageId,
      assistantMessageId: messageId,
      assistant_message_id: messageId,
      turnIndex,
      turn_index: turnIndex,
      contentHash,
      content_hash: contentHash,
      assistantHash: contentHash,
      assistant_hash: contentHash,
      recentHistory: Array.isArray(detail.recentHistory) ? detail.recentHistory : (Array.isArray(detail.recent_history) ? detail.recent_history : []),
      recent_history: Array.isArray(detail.recent_history) ? detail.recent_history : (Array.isArray(detail.recentHistory) ? detail.recentHistory : []),
      targetMessage,
    };
  }

  function buildDomFallbackDetail(turn = pendingTurn) {
    if (!turn) return null;
    let target = findAssistantMessageForDetail({ turnId: turn.turnId });
    if (!target) target = findLatestAssistantMessage();
    if (!target || target.classList.contains("streaming")) return null;
    const assistantText = readMessageText(target);
    if (!assistantText) return null;
    const messageId = target.dataset.messageId || `msg_${turn.turnId}_assistant`;
    if (!target.dataset.messageId) target.dataset.messageId = messageId;
    if (!target.dataset.turnId) target.dataset.turnId = turn.turnId;
    if (!target.dataset.stateJournalTurn) target.dataset.stateJournalTurn = turn.turnId;
    const turnIndex = target.dataset.turnIndex || turn.turnIndex || 0;
    const contentHash = target.dataset.contentHash || simpleHash(assistantText);
    target.dataset.contentHash = contentHash;
    return normalizeHookDetail({
      turnId: turn.turnId,
      turn_id: turn.turnId,
      messageId,
      message_id: messageId,
      assistantMessageId: messageId,
      assistant_message_id: messageId,
      turnIndex,
      turn_index: turnIndex,
      userText: turn.userText || "",
      user_text: turn.userText || "",
      assistantText,
      assistant_text: assistantText,
      assistantCleanText: assistantText,
      assistant_clean_text: assistantText,
      contentHash,
      content_hash: contentHash,
      createdAt: turn.createdAt || new Date().toISOString(),
      created_at: turn.createdAt || new Date().toISOString(),
      source: "dom_fallback",
    }, "dom_fallback");
  }

  function clearDomFallback(turnId = "") {
    const key = String(turnId || pendingTurn?.turnId || "").trim();
    if (!key) return;
    const timer = fallbackTimers.get(key);
    if (timer) window.clearInterval(timer);
    fallbackTimers.delete(key);
  }

  function scheduleDomFallback(turn) {
    if (!turn?.turnId) return;
    clearDomFallback(turn.turnId);
    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      if (!pendingTurn || pendingTurn.turnId !== turn.turnId || processedTurns.has(`fallback:${turn.turnId}`)) {
        clearDomFallback(turn.turnId);
        return;
      }
      const detail = buildDomFallbackDetail(turn);
      if (detail && detail.assistantCleanText && detail.messageId) {
        processedTurns.add(`fallback:${turn.turnId}`);
        clearDomFallback(turn.turnId);
        updateFromTurn(detail, "dom_fallback");
        return;
      }
      if (Date.now() - startedAt > 30000) {
        clearDomFallback(turn.turnId);
        const target = findAssistantMessageForDetail({ turnId: turn.turnId }) || findLatestAssistantMessage();
        if (target) attachInlineTurnStatus(target, turn.turnId, "心笺未检测到新回复完成，可刷新或稍后重试。", "error");
        showBubble("error", "心笺等待超时", "未检测到可绑定的新回复，已停止等待。", 8000);
      }
    }, 1000);
    fallbackTimers.set(turn.turnId, timer);
  }

  function isSameMessageTarget(message, detail = {}) {
    if (!message) return false;
    const messageId = String(detail.assistantMessageId || detail.assistant_message_id || detail.messageId || detail.message_id || "").trim();
    if (messageId && message.dataset.messageId !== messageId) return false;
    const turnId = String(detail.turnId || detail.turn_id || "").trim();
    if (turnId && message.dataset.stateJournalTurn !== turnId && message.dataset.turnId !== turnId) return false;
    const contentHash = String(detail.contentHash || detail.content_hash || detail.assistantHash || detail.assistant_hash || "").trim();
    if (contentHash && message.dataset.contentHash && message.dataset.contentHash !== contentHash) return false;
    return true;
  }

  function bubbleWrapFor(message) {
    return message?.querySelector(".bubble-wrap") || message;
  }

  function stableTurnId(payload, fallback = "") {
    return String(payload?.turn_id || payload?.created_at || fallback || Date.now());
  }

  function turnIndexFromMessage(targetMessage, display = null) {
    const value = Number(targetMessage?.dataset?.turnIndex || display?.turn_index || display?.turnIndex || 0);
    return Number.isFinite(value) && value > 0 ? Math.floor(value) : 0;
  }

  function displayForMessage(display, targetMessage) {
    if (!display || typeof display !== "object") return display;
    const turnIndex = turnIndexFromMessage(targetMessage, display);
    if (!turnIndex) return display;
    const sequenceLabel = `第 ${turnIndex} 笺`;
    return {
      ...display,
      sequence: turnIndex,
      turn_index: turnIndex,
      sequence_label: sequenceLabel,
      scene: {
        ...(display.scene || {}),
        sequence: turnIndex,
        sequence_label: sequenceLabel,
      },
    };
  }

  function activeThemePack() {
    const packs = Array.isArray(configCache?.mujian_theme_packs) ? configCache.mujian_theme_packs : [];
    const id = String(configCache?.mujian_theme_id || "standard");
    return packs.find((item) => item && item.id === id) || packs[0] || { id: "standard", style: { class_name: "theme-standard" } };
  }

  function activeThemeClass() {
    const pack = activeThemePack();
    const cls = String(pack?.style?.class_name || `theme-${pack?.id || "standard"}`).replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "");
    return cls || "theme-standard";
  }

  function applyBeautyPack(node) {
    if (!node) return node;
    const pack = activeThemePack();
    node.classList.add(activeThemeClass());
    const accent = String(pack?.style?.accent || "").trim();
    if (accent) node.style.setProperty("--xj-beauty-accent", accent);
    node.dataset.stateJournalTheme = pack?.id || "standard";
    return node;
  }

  function safeLayoutClass(value, fallback = "standard") {
    return String(value || fallback).replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "") || fallback;
  }

  function activeThemeLayout() {
    const style = activeThemePack()?.style || {};
    return (style.layout && typeof style.layout === "object") ? style.layout : {};
  }

  function activeThemeMedia() {
    const pack = activeThemePack() || {};
    const style = pack.style || {};
    const media = style.media || pack.media || {};
    return (media && typeof media === "object") ? media : {};
  }

  let stateJournalStaticRootCache = "";

  function stateJournalStaticRoot() {
    if (stateJournalStaticRootCache) return stateJournalStaticRootCache;
    const scriptUrl = Array.from(document.scripts || [])
      .map((script) => script?.src || "")
      .find((src) => src.includes("/mods/state-journal/") && src.includes("state-journal-chat.js"));
    if (scriptUrl) {
      try {
        const url = new URL(scriptUrl, window.location.href);
        url.search = "";
        url.hash = "";
        url.pathname = url.pathname.replace(/[^/]*$/, "");
        stateJournalStaticRootCache = url.toString();
      } catch (err) {
        stateJournalStaticRootCache = "";
      }
    }
    if (!stateJournalStaticRootCache) stateJournalStaticRootCache = "/mods/state-journal/app/static/";
    return stateJournalStaticRootCache;
  }

  function resolveThemeAssetUrl(value) {
    const raw = String(value || "").trim();
    if (!raw || ["none", "chat_background", "character_avatar", "film_placeholder"].includes(raw)) return "";
    if (/^(https?:)?\/\//i.test(raw) || raw.startsWith("data:")) return raw;
    let clean = raw.replace(/^\/+/, "");
    // Normalize them to the actual mounted static root, normally /mods/state-journal/app/static/.
    clean = clean.replace(/^mods\/state_journal\/app\/static\//, "");
    clean = clean.replace(/^mods\/state_journal\/static\//, "");
    if (clean.startsWith("static/assets/") || clean.startsWith("assets/")) {
      clean = clean.split("/").filter(Boolean).pop() || "";
    } else if (clean.startsWith("static/")) {
      clean = clean.slice("static/".length);
    }
    if (!clean) return "";
    try {
      return new URL(encodeURI(clean), stateJournalStaticRoot()).toString();
    } catch (err) {
      return `${stateJournalStaticRoot()}${encodeURIComponent(clean)}`;
    }
  }

  function activeLayoutType() {
    const layout = activeThemeLayout();
    return safeLayoutClass(layout.layout_type || layout.type || layout.profile || layout.title_card || layout.character_card || "standard");
  }

  function themeLabel(name, fallback = "") {
    const pack = activeThemePack() || {};
    const labels = pack.labels || pack.style?.labels || {};
    return String(labels?.[name] || fallback || name);
  }

  function activeThemeTokens() {
    const style = activeThemePack()?.style || {};
    return (style.tokens && typeof style.tokens === "object") ? style.tokens : {};
  }

  function tokenForLabel(label = "", key = "") {
    const tokens = activeThemeTokens();
    if (key && tokens[key]) return String(tokens[key]);
    const map = {
      "时间": "📅", "地点": "🧭", "天气": "🌦️", "氛围": "📝", "人物": "👥",
      "情绪": "💗", "衣着": "👘", "角色神态": "🧍", "神态": "🧍", "场景": "🌄",
      "感官场域": "🌫️", "感官区域": "🌫️", "躯体温差": "🌡️", "驱体温差": "🌡️", "肢体动态": "〰️", "微生理反应": "💫",
      "视觉焦点": "👁️", "视线焦点": "👁️", "角色互动": "🤝", "互动": "🤝", "摘要": "📌", "附笺": "✦",
      "好感": "♡", "信任": "✓", "戒备": "◇", "心绪": "≈", "牵系": "∞", "亲密": "✦", "紧张": "!", "疲惫": "…", "伤势": "+"
    };
    return tokens[label] || map[label] || "•";
  }

  function normalizeFieldName(value = "") {
    return String(value || "")
      .toLowerCase()
      .replace(/[\s_\-:：/／|｜（）()\[\]【】<>《》"'“”‘’]+/g, "")
      .trim();
  }

  function fieldMatchesAny(item, aliases = []) {
    const label = normalizeFieldName(item?.[0]);
    const key = normalizeFieldName(item?.[2]);
    return aliases.some((alias) => {
      const target = normalizeFieldName(alias);
      return target && (label === target || key === target || label.includes(target) || key.includes(target));
    });
  }

  const DEFAULT_METRIC_DEFS = [
    { key: "favor_level", label: "FAVOR", name: "好感", scope: "relationship", aliases: ["favor_level", "favor", "好感", "好感值"] },
    { key: "trust_level", label: "TRUST", name: "信任", scope: "relationship", aliases: ["trust_level", "trust", "信任", "信任值"] },
    { key: "bond_level", label: "BOND", name: "牵系", scope: "relationship", aliases: ["bond_level", "bond", "牵系", "依赖", "羁绊"] },
    { key: "guard_level", label: "GUARD", name: "戒备", scope: "relationship", aliases: ["guard_level", "guard", "戒备", "防备"] },
    { key: "intimacy_level", label: "INTIMACY", name: "亲密", scope: "relationship", aliases: ["intimacy_level", "intimacy", "亲密", "亲密度"] },
    { key: "tension_level", label: "TENSION", name: "紧张", scope: "relationship", aliases: ["tension_level", "tension", "紧张", "张力"] },
    { key: "pulse_level", label: "PULSE", name: "心绪", scope: "character", aliases: ["pulse_level", "pulse", "心绪", "心绪波动", "情绪波动"] },
    { key: "fatigue_level", label: "FATIGUE", name: "疲惫", scope: "character", aliases: ["fatigue_level", "fatigue", "疲惫", "疲劳"] },
    { key: "injury_level", label: "INJURY", name: "伤势", scope: "character", aliases: ["injury_level", "injury", "伤势", "受伤"] },
    { key: "stress_level", label: "STRESS", name: "压力", scope: "character", aliases: ["stress_level", "stress", "压力", "压迫"] },
  ];

  function defaultMetricDefs() {
    return DEFAULT_METRIC_DEFS.map((item) => ({ ...item, aliases: [...(item.aliases || [])] }));
  }

  function activeMetricDefs() {
    const pack = activeThemePack() || {};
    const style = pack.style || {};
    const raw = Array.isArray(style.progress_bars) ? style.progress_bars : (Array.isArray(pack.progress_bars) ? pack.progress_bars : []);
    const merged = raw.length ? raw : defaultMetricDefs();
    return merged.map((item) => {
      const key = String(item?.key || item?.id || "").trim();
      const name = String(item?.name || item?.display_name || item?.fallback_label || item?.label_cn || item?.label || key || "数值").trim();
      const label = String(item?.label || item?.code || key || name).trim();
      const aliases = Array.isArray(item?.aliases) ? item.aliases : [];
      return {
        key,
        label,
        name,
        aliases: [key, label, name, ...(aliases || [])].filter(Boolean),
        max: Math.max(1, Number(item?.max || 100) || 100),
      };
    }).filter((item) => item.key || item.aliases.length);
  }

  function metricDefForField(item) {
    return activeMetricDefs().find((def) => fieldMatchesAny(item, def.aliases));
  }

  function parseMetricValue(rawValue, max = 100) {
    const raw = String(rawValue || "").trim();
    if (!raw) return null;
    const normalized = raw.replace(/＋/g, "+").replace(/－/g, "-");
    const valueMatch = normalized.match(/(?:^|[^+\-\d])(\d{1,3}(?:\.\d+)?)(?=\s*(?:\/|／|分|$|[（(]|[^\d]))/) || normalized.match(/^(\d{1,3}(?:\.\d+)?)/);
    if (!valueMatch) return null;
    const numeric = Math.max(0, Math.min(max, Number(valueMatch[1])));
    if (!Number.isFinite(numeric)) return null;
    const deltaMatch = normalized.match(/([+\-]\s*\d{1,3}(?:\.\d+)?)/);
    const zeroDeltaMatch = normalized.match(/[（(]\s*0(?:\.0+)?\s*[）)]/);
    const delta = deltaMatch ? Number(deltaMatch[1].replace(/\s+/g, "")) : (zeroDeltaMatch ? 0 : 0);
    return { value: numeric, delta: Number.isFinite(delta) ? delta : 0, raw };
  }

  function splitMetricFields(list = []) {
    const metrics = [];
    const fields = [];
    const seenMetricKeys = new Set();
    for (const item of list) {
      const def = metricDefForField(item);
      const parsed = def ? parseMetricValue(item?.[1], def.max) : null;
      if (def && parsed) {
        const metricKey = def.key || normalizeFieldName(item?.[0]);
        if (!seenMetricKeys.has(metricKey)) {
          metrics.push({ ...def, ...parsed, source: item, displayName: def.name || item?.[0] || def.label });
          seenMetricKeys.add(metricKey);
        }
      } else {
        fields.push(item);
      }
    }
    return { metrics, fields };
  }

  function formatMetricDelta(delta) {
    if (delta === null || delta === undefined || !Number.isFinite(Number(delta))) return "+0";
    const value = Number(delta);
    const rounded = Number.isInteger(value) ? value : Number(value.toFixed(2));
    return rounded >= 0 ? `+${rounded}` : `${rounded}`;
  }

  function formatMetricPlain(metric, prefix = "") {
    const max = Math.max(1, Number(metric?.max || 100) || 100);
    const value = Math.max(0, Math.min(max, Number(metric?.value) || 0));
    return `${Math.round(value)}/${max}（${prefix}${formatMetricDelta(metric?.delta)}）`;
  }

  function metricDeltaText(delta, variant = "plain") {
    const plain = formatMetricDelta(delta);
    const value = Number(delta);
    if (variant === "hud") {
      if (value > 0) return `↑ ${plain}`;
      if (value < 0) return `↓ ${plain}`;
      return plain;
    }
    return plain;
  }

  function renderMetricText(metrics = [], variant = "plain") {
    if (!metrics.length) return "";
    return `<div class="state-journal-metric-strip is-${escapeHtml(variant)}">${metrics.map((metric) => {
      const label = metric.name || metric.label;
      const text = variant === "paper" ? formatMetricPlain(metric, "本轮 ") : formatMetricPlain(metric);
      return `<span class="state-journal-metric-chip"><b>${escapeHtml(label)}</b><i>${escapeHtml(text)}</i></span>`;
    }).join("")}</div>`;
  }

  function renderMetricMeters(metrics = []) {
    if (!metrics.length) return "";
    return `<div class="state-journal-status-pro-meters">${metrics.map((metric) => {
      const max = Math.max(1, Number(metric.max || 100) || 100);
      const value = Math.max(0, Math.min(max, Number(metric.value) || 0));
      const width = Math.max(0, Math.min(100, (value / max) * 100));
      const delta = metricDeltaText(metric.delta, "hud");
      return `<div class="state-journal-status-meter"><span>${escapeHtml(metric.label || metric.name)}</span><b><em style="width:${width}%"></em></b><i>${escapeHtml(String(Math.round(value)))}${delta ? `<small>${escapeHtml(delta)}</small>` : ""}</i></div>`;
    }).join("")}</div>`;
  }

  function groupedFields(list = [], groups = []) {
    const used = new Set();
    const output = groups.map((group) => ({ ...group, items: [] }));
    list.forEach((item, index) => {
      const group = output.find((candidate) => fieldMatchesAny(item, candidate.aliases || []));
      if (group) {
        group.items.push(item);
        used.add(index);
      }
    });
    const extra = list.filter((_, index) => !used.has(index));
    if (extra.length) output.push({ id: "extra", title: "扩展字段", code: "EXTRA", items: extra });
    return output.filter((group) => group.items.length);
  }

  function renderFieldRows(items = [], className = "state-journal-status-pro-row", options = {}) {
    return items.map(([label, value, key], idx) => {
      const token = options.icon ? `<em>${escapeHtml(tokenForLabel(label, key))}</em>` : "";
      const count = options.count ? `<i>${String(idx + 1).padStart(2, "0")}</i>` : "";
      return `<div class="${escapeHtml(className)}">${token}<span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong>${count}</div>`;
    }).join("");
  }

  function sceneRows(display) {
    const scene = display?.scene || {};
    return [
      ["time", "时间", scene.time || "时间未明"],
      ["location", "地点", scene.location || "地点未明"],
      ["weather", "天气", scene.weather || ""],
      ["atmosphere", "氛围", scene.atmosphere || ""],
      ["characters", "人物", scene.characters || ""],
    ].filter((row) => row[2]);
  }

  function buildPaperTimeSceneCard(display, turnId = "") {
    const scene = display?.scene || {};
    const title = display?.title || scene.title || "本轮幕笺";
    const subtitle = display?.subtitle || scene.subtitle || scene.atmosphere || "";
    const seq = display?.sequence_label || scene.sequence_label || "";
    const card = document.createElement("details");
    card.className = "state-journal-inline-scene-card is-layout-paper-time";
    applyBeautyPack(card);
    card.dataset.stateJournalScene = turnId;
    card.open = true;
    card.innerHTML = `
      <summary>
        <span class="state-journal-scene-kicker">${escapeHtml(themeLabel("scene_kicker", "SCENE / TIME"))}</span>
        <span class="state-journal-scene-title-line"><strong class="state-journal-scene-title">${seq ? `${escapeHtml(seq)} · ` : ""}《${escapeHtml(title)}》</strong><span class="state-journal-scene-toggle">收起</span></span>
        <span class="state-journal-scene-subtitle">${escapeHtml(subtitle)}</span>
      </summary>
      <div class="state-journal-scene-body">
        <div class="state-journal-scene-paper-rows"></div>
        <div class="state-journal-scene-event"></div>
      </div>
    `;
    card.addEventListener("toggle", () => {
      const toggle = card.querySelector(".state-journal-scene-toggle");
      if (toggle) toggle.textContent = card.open ? "收起" : "展开";
    });
    card.querySelector(".state-journal-scene-paper-rows").innerHTML = sceneRows(display)
      .map(([key, label, value]) => `<div class="state-journal-paper-time-row"><i>${escapeHtml(tokenForLabel(label, key))}</i><b>${escapeHtml(label)}</b><span>${escapeHtml(value)}</span></div>`)
      .join("");
    card.querySelector(".state-journal-scene-event").textContent = scene.event_summary || subtitle || "心笺已生成本轮幕题。";
    return card;
  }

  function buildStatusPanelSceneCard(display, turnId = "") {
    const scene = display?.scene || {};
    const title = display?.title || scene.title || "本轮幕笺";
    const subtitle = display?.subtitle || scene.event_summary || scene.atmosphere || "";
    const seq = display?.sequence_label || scene.sequence_label || "";
    const card = document.createElement("details");
    card.className = "state-journal-inline-scene-card is-layout-status-panel";
    applyBeautyPack(card);
    card.dataset.stateJournalScene = turnId;
    card.open = true;
    card.innerHTML = `
      <summary>
        <span class="state-journal-scene-kicker">${escapeHtml(themeLabel("scene_kicker", "STATUS PANEL · TIME"))}</span>
        <span class="state-journal-scene-title-line"><strong class="state-journal-scene-title">${seq ? `${escapeHtml(seq)} · ` : ""}《${escapeHtml(title)}》</strong><span class="state-journal-scene-toggle">收起</span></span>
        <span class="state-journal-scene-subtitle">${escapeHtml(subtitle)}</span>
      </summary>
      <div class="state-journal-scene-body">
        <div class="state-journal-status-scene-hud"></div>
        <div class="state-journal-status-timeline"><b>${escapeHtml(seq || "TIME")}</b><span>SYNC</span></div>
      </div>
    `;
    card.addEventListener("toggle", () => {
      const toggle = card.querySelector(".state-journal-scene-toggle");
      if (toggle) toggle.textContent = card.open ? "收起" : "展开";
    });
    card.querySelector(".state-journal-status-scene-hud").innerHTML = sceneRows(display)
      .map(([key, label, value]) => `<span><i>${escapeHtml(tokenForLabel(label, key))}</i><b>${escapeHtml(label)}</b>${escapeHtml(value)}</span>`)
      .join("");
    return card;
  }

  function buildStoryboardSceneCard(display, turnId = "") {
    const scene = display?.scene || {};
    const title = display?.title || scene.title || "本轮幕笺";
    const subtitle = display?.subtitle || scene.atmosphere || "";
    const seq = display?.sequence_label || scene.sequence_label || "";
    const media = activeThemeMedia();
    const imageUrl = resolveThemeAssetUrl(media?.scene_image_data || media?.scene_image_url || media?.scene_image || media?.hero_image || media?.image);
    const placeholder = media?.scene_image === "chat_background" ? "背景裁切 / 胶片占位" : "SCENE FRAME";
    const frameHtml = imageUrl
      ? `<div class="state-journal-storyboard-frame has-image"><img src="${escapeHtml(imageUrl)}" alt="心笺分镜图" loading="lazy" data-xj-frame-image="1"></div>`
      : `<div class="state-journal-storyboard-frame"><span>${escapeHtml(placeholder)}</span><small>NO IMAGE / SAFE PLACEHOLDER</small></div>`;
    const card = document.createElement("details");
    card.className = "state-journal-inline-scene-card is-layout-storyboard";
    applyBeautyPack(card);
    card.dataset.stateJournalScene = turnId;
    card.open = true;
    card.innerHTML = `
      <summary>
        <span class="state-journal-scene-kicker">${escapeHtml(themeLabel("scene_kicker", "SCENE"))} ${escapeHtml(seq || "")}</span>
        <span class="state-journal-scene-title-line"><strong class="state-journal-scene-title">《${escapeHtml(title)}》</strong><span class="state-journal-scene-toggle">收起</span></span>
        <span class="state-journal-scene-subtitle">${escapeHtml(subtitle)}</span>
      </summary>
      <div class="state-journal-scene-body state-journal-storyboard-hero">
        <div class="state-journal-storyboard-meta"></div>
        ${frameHtml}
        <div class="state-journal-scene-event"></div>
      </div>
    `;
    card.addEventListener("toggle", () => {
      const toggle = card.querySelector(".state-journal-scene-toggle");
      if (toggle) toggle.textContent = card.open ? "收起" : "展开";
    });
    const frameImg = card.querySelector("[data-xj-frame-image]");
    if (frameImg) {
      frameImg.addEventListener("error", () => {
        const frame = frameImg.closest(".state-journal-storyboard-frame");
        if (!frame) return;
        frame.classList.remove("has-image");
        frame.classList.add("is-image-missing");
        frame.innerHTML = `<span>SCENE FRAME</span><small>IMAGE LOAD FAILED</small>`;
      }, { once: true });
    }
    const meta = [
      ["镜头", scene.time || "中景 · 固定机位"],
      ["地点", scene.location || "地点未明"],
      ["焦点", scene.characters || "人物未明"],
      ["气氛", scene.atmosphere || scene.weather || "氛围未明"],
    ];
    card.querySelector(".state-journal-storyboard-meta").innerHTML = meta.map(([label, value]) => `<p><b>${escapeHtml(label)}：</b>${escapeHtml(value)}</p>`).join("");
    card.querySelector(".state-journal-scene-event").textContent = scene.event_summary || subtitle || "心笺已生成本轮幕题。";
    return card;
  }

  function buildTimeSceneCard(display, turnId = "") {
    const scene = display?.scene || {};
    const title = display?.title || scene.title || "本轮幕笺";
    const subtitle = display?.subtitle || scene.subtitle || scene.atmosphere || "";
    const seq = display?.sequence_label || scene.sequence_label || "";
    const card = document.createElement("details");
    card.className = "state-journal-inline-scene-card is-layout-time-card";
    applyBeautyPack(card);
    card.dataset.stateJournalScene = turnId;
    card.open = true;
    card.innerHTML = `
      <summary>
        <span class="state-journal-scene-kicker">Time</span>
        <span class="state-journal-scene-title-line"><strong class="state-journal-scene-title">${seq ? `${escapeHtml(seq)} · ` : ""}《${escapeHtml(title)}》</strong><span class="state-journal-scene-toggle">收起</span></span>
        <span class="state-journal-scene-subtitle">${escapeHtml(subtitle)}</span>
      </summary>
      <div class="state-journal-scene-body">
        <div class="state-journal-scene-meta"></div>
        <div class="state-journal-scene-event"></div>
      </div>
    `;
    card.addEventListener("toggle", () => {
      const toggle = card.querySelector(".state-journal-scene-toggle");
      if (toggle) toggle.textContent = card.open ? "收起" : "展开";
    });
    const rows = [
      ["time", "时间", scene.time || "时间未明"],
      ["location", "地点", scene.location || "地点未明"],
      ["weather", "天气", scene.weather || ""],
      ["atmosphere", "氛围", scene.atmosphere || ""],
      ["characters", "人物", scene.characters || ""],
    ].filter((row) => row[2]);
    card.querySelector(".state-journal-scene-meta").innerHTML = rows.map(([key, label, value]) => `<span class="state-journal-scene-chip"><i>${escapeHtml(tokenForLabel(label, key))}</i><b>${escapeHtml(label)}：</b><span>${escapeHtml(value)}</span></span>`).join("");
    card.querySelector(".state-journal-scene-event").textContent = scene.event_summary || subtitle || "心笺已生成本轮幕题。";
    return card;
  }

  function buildSceneCard(display, turnId = "") {
    ensureVisualStyle();
    const layout = activeThemeLayout();
    const sceneLayout = String(layout.layout_type || layout.title_card || layout.scene_card || "");
    if (["paper_time", "paper_time_card"].includes(sceneLayout)) return buildPaperTimeSceneCard(display, turnId);
    if (["status_panel", "status_panel_pro", "hud"].includes(sceneLayout)) return buildStatusPanelSceneCard(display, turnId);
    if (["storyboard", "storyboard_frame", "scene_board"].includes(sceneLayout)) return buildStoryboardSceneCard(display, turnId);
    if (["time_card", "time_panel"].includes(sceneLayout)) return buildTimeSceneCard(display, turnId);
    const scene = display?.scene || {};
    const title = display?.title || scene.title || "本轮幕笺";
    const subtitle = display?.subtitle || scene.subtitle || scene.atmosphere || "";
    const seq = display?.sequence_label || scene.sequence_label || "";
    const card = document.createElement("details");
    card.className = "state-journal-inline-scene-card";
    applyBeautyPack(card);
    card.dataset.stateJournalScene = turnId;
    card.innerHTML = `
      <summary>
        <span class="state-journal-scene-kicker">XINJIAN · 幕题${seq ? ` · ${escapeHtml(seq)}` : ""}</span>
        <span class="state-journal-scene-title-line"><strong class="state-journal-scene-title">${seq ? `${escapeHtml(seq)} · ` : ""}《${escapeHtml(title)}》</strong><span class="state-journal-scene-toggle">展开</span></span>
        <span class="state-journal-scene-subtitle">${escapeHtml(subtitle)}</span>
      </summary>
      <div class="state-journal-scene-body">
        <div class="state-journal-scene-meta"></div>
        <div class="state-journal-scene-event"></div>
      </div>
    `;
    card.addEventListener("toggle", () => {
      const toggle = card.querySelector(".state-journal-scene-toggle");
      if (toggle) toggle.textContent = card.open ? "收起" : "展开";
    });
    const time = scene.time || "时间未明";
    const metaItems = [
      time ? `时间：${time}` : "时间：时间未明",
      scene.location ? `地点：${scene.location}` : "",
      scene.weather ? `天气：${scene.weather}` : "",
      scene.atmosphere ? `氛围：${scene.atmosphere}` : "",
      scene.characters ? `人物：${scene.characters}` : "",
    ].filter(Boolean);
    card.querySelector(".state-journal-scene-meta").innerHTML = metaItems.map((item) => `<span class="state-journal-scene-chip">${escapeHtml(item)}</span>`).join("");
    card.querySelector(".state-journal-scene-event").textContent = scene.event_summary || subtitle || "心笺已生成本轮幕题。";
    return card;
  }

  function clearInlineTurnStatus(targetMessage, turnId = "") {
    if (!targetMessage) return;
    const wrap = bubbleWrapFor(targetMessage);
    const selector = turnId
      ? `.state-journal-turn-status[data-state-journal-turn="${CSS.escape(turnId)}"]`
      : ".state-journal-turn-status";
    wrap.querySelectorAll(selector).forEach((node) => node.remove());
  }

  function clearExistingTurnDisplay(targetMessage) {
    if (!targetMessage) return;
    const wrap = bubbleWrapFor(targetMessage);
    wrap.querySelectorAll(".state-journal-inline-scene-card, .state-journal-turn-note, .state-journal-turn-note-compact, .state-journal-turn-status").forEach((node) => node.remove());
  }

  function attachInlineTurnStatus(targetMessage, turnId, text, kind = "pending") {
    if (!targetMessage || !turnId) return;
    const wrap = bubbleWrapFor(targetMessage);
    clearInlineTurnStatus(targetMessage, turnId);
    const status = document.createElement("div");
    status.className = `state-journal-turn-status is-${kind}`;
    status.dataset.stateJournalTurn = turnId;
    status.textContent = text || (kind === "error" ? "心笺生成失败，可稍后重试。" : "心笺正在生成幕笺……");
    wrap.appendChild(status);
  }

  function attachSceneCard(display, targetMessage, turnId = "") {
    if (!configCache?.mujian_enabled || !configCache?.mujian_title_card || !display || !targetMessage) return;
    const wrap = bubbleWrapFor(targetMessage);
    const normalizedDisplay = displayForMessage(display, targetMessage);
    const key = stableTurnId(normalizedDisplay, turnId);
    const old = wrap.querySelector(`.state-journal-inline-scene-card[data-state-journal-scene="${CSS.escape(key)}"]`);
    if (old) old.remove();
    const card = buildSceneCard(normalizedDisplay, key);
    const bubble = wrap.querySelector(".bubble");
    if (bubble) wrap.insertBefore(card, bubble);
    else wrap.prepend(card);
  }

  function nameMatchesAny(name, names) {
    const text = String(name || "").trim();
    if (!text) return false;
    return names.some((item) => text === item || text.includes(item) || item.includes(text));
  }

  function configuredCharacterNames() {
    return String(configCache?.mujian_character_names || "")
      .split(/[，,、\n]/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function filterCharacters(characters) {
    const list = Array.isArray(characters) ? characters : [];
    const mode = configCache?.mujian_character_filter || "turn";
    if (mode === "all" || mode === "turn") return list;
    const names = configuredCharacterNames();
    if (!names.length) return list;
    if (["custom", "heroine", "protagonist"].includes(mode)) {
      return list.filter((item) => nameMatchesAny(item?.name, names));
    }
    return list;
  }

  function currentNoteStyle(display = null) {
    return configCache?.mujian_note_style || display?.note_style || display?.style || "classic";
  }


  function displayTemplateFields(display = null) {
    const fields = Array.isArray(display?.template_fields) ? display.template_fields : [];
    return fields
      .filter((field) => field && field.key && field.key !== "name")
      .map((field) => ({ key: String(field.key), label: String(field.label || field.key) }));
  }

  function renderOutputTemplate(template, character) {
    const text = String(template || "").trim();
    if (!text) return "";
    return text.replace(/\{([a-zA-Z0-9_]+)\}/g, (_, key) => compactText(character?.[key] ?? "", 520));
  }

  function parseTemplateRenderedFields(renderedText) {
    const text = String(renderedText || "").trim();
    if (!text) return [];
    const fields = [];
    const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    let pending = null;

    function pushPending() {
      if (pending && String(pending[1] || "").trim()) fields.push(pending);
      pending = null;
    }

    for (const line of lines) {
      const tagMatch = line.match(/^<\s*([^<>()[\]{}]+?)\s*[（(]([\s\S]*)[）)]\s*>$/);
      if (tagMatch) {
        pushPending();
        const label = tagMatch[1].trim();
        const value = tagMatch[2].trim();
        if (label && value) fields.push([label, value]);
        continue;
      }

      const colonMatch = line.match(/^([^：:]{1,24})[：:]\s*([\s\S]+)$/);
      if (colonMatch && !/^【.*】$/.test(line)) {
        pushPending();
        const label = colonMatch[1].replace(/[<>]/g, "").trim();
        const value = colonMatch[2].trim();
        if (label && value) fields.push([label, value]);
        continue;
      }

      if (/^【.*】$/.test(line) || /^#+\s+/.test(line)) {
        pushPending();
        continue;
      }

      if (pending) pending[1] = `${pending[1]}\n${line}`;
      else pending = ["附笺", line];
    }
    pushPending();
    return fields;
  }


  function renderStatusPanelFields(list) {
    const { metrics, fields } = splitMetricFields(list);
    const groups = groupedFields(fields, [
      { id: "core", title: "核心状态", code: "CORE", aliases: ["情绪", "emotion", "角色神态", "posture", "场景", "scene", "摘要", "summary"] },
      { id: "body", title: "身体状态", code: "BODY", aliases: ["衣着", "clothing", "躯体温差", "驱体温差", "body_temperature", "肢体动态", "body_motion", "微生理反应", "micro_reaction"] },
      { id: "sense", title: "感官与视线", code: "SENSE", aliases: ["感官场域", "感官区域", "sensory_field", "视觉焦点", "视线焦点", "visual_focus"] },
      { id: "link", title: "互动关系", code: "LINK", aliases: ["角色互动", "interaction", "互动"] },
    ]);
    return `
      <div class="state-journal-status-pro-shell">
        ${renderMetricMeters(metrics)}
        <div class="state-journal-status-pro-layer">
          ${groups.map((group, idx) => `<details class="state-journal-status-pro-card" ${idx === 0 ? "open" : ""}>
            <summary><span>${escapeHtml(group.code || group.title)}</span><b>${escapeHtml(group.title)}</b><i>${group.items.length}</i></summary>
            <div class="state-journal-status-pro-grid">${renderFieldRows(group.items, "state-journal-status-pro-row", { count: true })}</div>
          </details>`).join("")}
        </div>
      </div>`;
  }

  function renderStoryboardFields(list) {
    const { metrics, fields } = splitMetricFields(list);
    const groups = groupedFields(fields, [
      { id: "camera", title: "镜头", code: "CAMERA", aliases: ["场景", "scene", "视觉焦点", "视线焦点", "visual_focus", "感官场域", "感官区域", "sensory_field"] },
      { id: "acting", title: "表演", code: "ACT", aliases: ["情绪", "emotion", "角色神态", "posture", "肢体动态", "body_motion", "角色互动", "interaction"] },
      { id: "detail", title: "细节", code: "DETAIL", aliases: ["衣着", "clothing", "躯体温差", "驱体温差", "body_temperature", "微生理反应", "micro_reaction", "摘要", "summary"] },
    ]);
    return `<div class="state-journal-storyboard-note-table is-cut-sheet">
      ${renderMetricText(metrics, "storyboard")}
      ${groups.map((group) => `<div class="state-journal-storyboard-group"><div class="state-journal-storyboard-group-title"><span>${escapeHtml(group.code || group.title)}</span><b>【${escapeHtml(group.title)}】</b></div>${renderFieldRows(group.items, "state-journal-storyboard-row", { icon: true })}</div>`).join("")}
    </div>`;
  }

  function renderPaperTimeFields(list) {
    const { metrics, fields } = splitMetricFields(list);
    return `<div class="state-journal-paper-note-table is-literary-note">
      ${renderMetricText(metrics, "paper")}
      ${fields.map(([label, value, key]) => `<div class="state-journal-paper-note-row"><i>${escapeHtml(tokenForLabel(label, key))}</i><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}
    </div>`;
  }

  function collectCharacterMetrics(character, display = null) {
    const fields = characterFields(character, display);
    return splitMetricFields(fields).metrics;
  }

  function renderTurnMetricSummary(characters = [], display = null) {
    const rows = [];
    (characters || []).forEach((character) => {
      const metrics = collectCharacterMetrics(character, display);
      if (!metrics.length) return;
      const chips = metrics.map((metric) => {
        return `<span><b>${escapeHtml(metric.name || metric.label)}</b>${escapeHtml(formatMetricPlain(metric))}</span>`;
      }).join("");
      rows.push(`<div class="state-journal-metric-diary-row"><strong>${escapeHtml(character?.name || "角色")}</strong><p>${chips}</p></div>`);
    });
    if (!rows.length) return "";
    return `<section class="state-journal-note-section state-journal-metric-diary"><h4>本轮数值变化</h4><div class="state-journal-metric-diary-list">${rows.join("")}</div></section>`;
  }

  function renderNoteFields(fields) {
    const list = Array.isArray(fields) ? fields.filter(([label, value]) => String(label || "").trim() && String(value || "").trim()) : [];
    if (!list.length) return "";
    const layout = activeThemeLayout();
    const layoutType = activeLayoutType();
    const charLayout = safeLayoutClass(layout.character_card || layoutType || "field_blocks");

    if (["status_panel", "status_panel_pro", "hud_rows", "hud"].includes(layoutType) || ["status_panel", "status_rows", "hud_rows", "status_panel_pro"].includes(charLayout)) {
      return renderStatusPanelFields(list);
    }

    if (["storyboard", "storyboard_frame", "scene_board"].includes(layoutType) || ["storyboard", "cut_rows"].includes(charLayout)) {
      return renderStoryboardFields(list);
    }

    if (["paper_time", "paper_time_card"].includes(layoutType) || ["paper_rows", "note_rows"].includes(charLayout)) {
      return renderPaperTimeFields(list);
    }

    const useIcon = ["info_rows", "time_card", "icon_rows"].includes(String(layout.character_card || ""));
    return `<div class="state-journal-note-grid">${list.map(([label, value, key]) => `<div class="state-journal-note-field">${useIcon ? `<em class="state-journal-note-icon">${escapeHtml(tokenForLabel(label, key))}</em>` : ""}<span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}</div>`;
  }

  function characterFields(character, display = null) {
    const templateFields = displayTemplateFields(display);
    const allPairs = templateFields.length
      ? templateFields.map((field) => [field.label, character?.[field.key], field.key])
      : [
        ["情绪", character.emotion, "emotion"],
        ["衣着", character.clothing, "clothing"],
        ["角色神态", character.posture, "posture"],
        ["场景", character.scene, "scene"],
        ["感官场域", character.sensory_field, "sensory_field"],
        ["躯体温差", character.body_temperature, "body_temperature"],
        ["肢体动态", character.body_motion, "body_motion"],
        ["微生理反应", character.micro_reaction, "micro_reaction"],
        ["视觉焦点", character.visual_focus, "visual_focus"],
        ["角色互动", character.interaction, "interaction"],
        ["摘要", character.summary, "summary"],
      ];
    return allPairs.filter(([label, value]) => String(label || "").trim() && String(value || "").trim());
  }

  function mergeRenderedAndTemplateFields(renderedFields, baseFields) {
    const rendered = Array.isArray(renderedFields) ? renderedFields.filter(([label, value]) => String(label || "").trim() && String(value || "").trim()) : [];
    const base = Array.isArray(baseFields) ? baseFields.filter(([label, value]) => String(label || "").trim() && String(value || "").trim()) : [];
    if (!rendered.length) return base;
    const merged = [...rendered];
    const hasEquivalent = (candidate) => merged.some((item) => {
      const sameLabel = normalizeFieldName(item?.[0]) && normalizeFieldName(item?.[0]) === normalizeFieldName(candidate?.[0]);
      const sameKey = normalizeFieldName(item?.[2]) && normalizeFieldName(item?.[2]) === normalizeFieldName(candidate?.[2]);
      const sameValue = String(item?.[1] || "").trim() && String(item?.[1] || "").trim() === String(candidate?.[1] || "").trim();
      return sameLabel || sameKey || sameValue;
    });
    base.forEach((field) => {
      if (!hasEquivalent(field)) merged.push(field);
    });
    return merged;
  }

  function chatDisplayMode() {
    const explicit = configCache?.mujian_chat_display_mode;
    if (["collapsed", "expanded", "compact", "hidden"].includes(explicit)) return explicit;
    return configCache?.mujian_default_collapsed === false ? "expanded" : "collapsed";
  }

  function compactCharacterLine(character) {
    const name = character?.name || "角色";
    const status = character?.emotion || character?.summary || character?.interaction || "状态已更新";
    return `${name} · ${compactText(status, 28)}`;
  }

  function buildCompactTurnNote(display, payload = {}, turnId = "") {
    ensureVisualStyle();
    const note = document.createElement("div");
    note.className = `state-journal-turn-note-compact is-layout-${safeLayoutClass(activeThemeLayout().status_bar || "compact")}`;
    applyBeautyPack(note);
    note.dataset.stateJournalTurn = stableTurnId(display, turnId);
    const characters = filterCharacters(Array.isArray(display.characters) ? display.characters : []);
    const scene = display?.scene || {};
    const line = characters.length
      ? characters.slice(0, 3).map(compactCharacterLine).join("｜")
      : (scene.event_summary || display?.subtitle || "本轮幕笺已生成");
    const location = scene.location ? `｜场景：${compactText(scene.location, 18)}` : "";
    note.innerHTML = `<strong>心笺</strong><span>${escapeHtml(line)}${escapeHtml(location)}</span>`;
    return note;
  }

  function buildTurnNote(display, payload = {}, turnId = "") {
    ensureVisualStyle();
    const note = document.createElement("details");
    const noteStyle = currentNoteStyle(display);
    const mode = chatDisplayMode();
    const layout = activeThemeLayout();
    const layoutType = activeLayoutType();
    note.className = `state-journal-turn-note is-note-${noteStyle} is-mode-${mode} is-layout-${safeLayoutClass(layout.character_card || layoutType || "field_blocks")} is-theme-layout-${layoutType}`;
    applyBeautyPack(note);
    note.dataset.stateJournalTurn = stableTurnId(display, turnId);
    if (mode === "expanded") note.open = true;
    const allCharacters = Array.isArray(display.characters) ? display.characters : [];
    const characters = filterCharacters(allCharacters);
    const relationships = Array.isArray(display.relationships) ? display.relationships : [];
    const changed = payload?.summary?.by_table?.map((item) => `${item.name || item.table} +${item.count || 0}`).join("｜") || "本轮幕笺已生成";
    const densityLabel = { compact: "简洁", standard: "标准", detailed: "详细" }[configCache?.mujian_note_density || "standard"] || "标准";
    const filterLabel = { turn: "本轮生成", heroine: "双女主", protagonist: "主角相关", custom: "自定义", all: "全部" }[configCache?.mujian_character_filter || "turn"] || "本轮生成";
    const noteStyleLabel = { classic: "经典状态", gufeng: "古风旁白", sensory: "感官标签" }[noteStyle] || "经典状态";
    const source = String(payload?.trigger_source || payload?.triggerSource || display?.trigger_source || display?.triggerSource || "");
    const sourceLabel = configCache?.debug_enabled && source
      ? `<span class="state-journal-source-badge is-${source === "dom_fallback" ? "dom" : source === "chat_hook" ? "hook" : "other"}">来源：${escapeHtml(source === "chat_hook" ? "Hook" : source === "dom_fallback" ? "DOM兜底" : source)}</span>`
      : "";
    note.innerHTML = `
      <summary>
        <span class="state-journal-turn-summary-main"><span class="state-journal-note-dot"></span><span>心笺有新记 · ${escapeHtml(changed)}</span></span>
        <span>${characters.length ? `${characters.length} 人物` : "展开"}</span>
      </summary>
      <div class="state-journal-note-body">
        <div class="state-journal-note-toolbar"><span>附笺：${escapeHtml(noteStyleLabel)}</span><span>显示：${escapeHtml(filterLabel)}</span><span>密度：${escapeHtml(densityLabel)}</span>${sourceLabel}</div>
        ${characters.length ? characters.map((character, index) => {
          const renderedTemplate = renderOutputTemplate(display?.output_template, character);
          const characterName = character.name || "角色";
          const sectionTitle = ["storyboard", "storyboard_frame", "scene_board"].includes(layoutType)
            ? `CUT ${String(index + 1).padStart(2, "0")} · ${characterName}`
            : ["status_panel", "status_panel_pro", "hud"].includes(layoutType)
              ? `STATUS · ${characterName}`
              : ["paper_time", "paper_time_card"].includes(layoutType)
                ? `旁注 · ${characterName}`
                : characterName;
          return `
          <section class="state-journal-note-section state-journal-note-section-${safeLayoutClass(layoutType)}">
            <h4>${escapeHtml(sectionTitle)}</h4>
            ${(() => {
              const templateFields = parseTemplateRenderedFields(renderedTemplate);
              const baseFields = characterFields(character, display);
              const safeFields = mergeRenderedAndTemplateFields(templateFields, baseFields);
              const html = renderNoteFields(safeFields);
              return html || `<pre class="state-journal-note-template-output">${escapeHtml(renderedTemplate)}</pre>`;
            })()}
          </section>`;
        }).join("") : `<div class="state-journal-note-empty">当前显示范围下没有可展示角色。可以在心笺设置里切换为“全部角色”或“自定义名单”。</div>`}
        ${renderTurnMetricSummary(characters, display)}
        ${relationships.length ? `<section class="state-journal-note-section state-journal-note-section-${safeLayoutClass(layoutType)}"><h4>${escapeHtml(["storyboard", "storyboard_frame", "scene_board"].includes(layoutType) ? "导演注 / 关系推进" : ["status_panel", "status_panel_pro", "hud"].includes(layoutType) ? "RELATION LOG" : ["paper_time", "paper_time_card"].includes(layoutType) ? "情节旁注" : "关系变化")}</h4><div class="state-journal-relation-list">${relationships.map((item) => `<div><strong>${escapeHtml(item.pair || "关系")}</strong>${item.stage ? ` · ${escapeHtml(item.stage)}` : ""}<br>${escapeHtml(item.change || "")}</div>`).join("")}</div></section>` : ""}
      </div>
    `;
    return note;
  }

  function attachTurnNote(display, payload = {}, targetMessage = null, turnId = "") {
    if (!configCache?.mujian_enabled || !configCache?.mujian_turn_note || !display) return;
    const mode = chatDisplayMode();
    if (mode === "hidden") return;
    const msg = targetMessage || findLatestAssistantMessage();
    if (!msg) return;
    const normalizedDisplay = displayForMessage(display, msg);
    const wrap = bubbleWrapFor(msg);
    const key = stableTurnId(normalizedDisplay, turnId);
    const old = wrap.querySelector(`.state-journal-turn-note[data-state-journal-turn="${CSS.escape(key)}"], .state-journal-turn-note-compact[data-state-journal-turn="${CSS.escape(key)}"]`);
    if (old) old.remove();
    const note = mode === "compact" ? buildCompactTurnNote(normalizedDisplay, payload, key) : buildTurnNote(normalizedDisplay, payload, key);
    wrap.appendChild(note);
  }

  function renderTurnDisplay(display, targetMessage, payload = {}) {
    if (!display || !targetMessage) return;
    const turnId = stableTurnId(display, payload?.turn_id || payload?.created_at || "");
    targetMessage.dataset.stateJournalTurn = turnId;
    if (payload?.message_id && targetMessage.dataset.messageId !== String(payload.message_id)) {
      console.warn("State Journal display message_id mismatch, skip render", payload.message_id, targetMessage.dataset.messageId);
      return;
    }
    clearExistingTurnDisplay(targetMessage);
    attachSceneCard(display, targetMessage, turnId);
    attachTurnNote(display, payload, targetMessage, turnId);
  }

  function formatSummary(payload) {
    const summary = payload?.summary || {};
    if (Array.isArray(summary.by_table) && summary.by_table.length) {
      return summary.by_table.map((item) => `${item.name || item.table} +${item.count || 0}`).join("｜");
    }
    const count = payload?.result?.applied?.length || 0;
    if (count) return `已应用 ${count} 条更新`;
    return payload?.message || "本轮没有需要写入的状态";
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

  async function startTrackedTurn(detail = {}) {
    const userText = String(detail.userText || detail.user_text || "").trim();
    if (!userText) return null;
    const source = String(detail.source || "send");
    const isLifecycleRebuild = source === "reroll" || source === "edit" || source === "edit_user" || source === "manual" || source === "manual_rebuild" || source === "rebuild";
    const config = await loadConfig().catch(() => configCache || {});
    if (!config?.enabled) return null;
    if (!config?.auto_update && !isLifecycleRebuild) {
      pingHook("turn_auto_update_skipped", "聊天后自动填表已关闭，本轮普通聊天不自动生成心笺。", detail.turnId || detail.turn_id || "");
      return null;
    }
    if (pendingTurn?.turnId) clearDomFallback(pendingTurn.turnId);
    const turnId = String(detail.turnId || detail.turn_id || makeTurnId(userText));
    if (isLifecycleRebuild) {
      forgetTurnRuntime(turnId);
      processedTurns.clear();
      invalidateMessageDisplaysFromIndex(detail.trimmedFrom ?? detail.messageIndex ?? detail.index ?? -1);
    }
    invalidatedTurns.delete(turnId);
    pendingTurn = {
      turnId,
      turnIndex: detail.turnIndex || detail.turn_index || 0,
      userText,
      userHash: simpleHash(userText),
      createdAt: detail.createdAt || detail.created_at || new Date().toISOString(),
      source,
    };
    if (source === "reroll" || source === "edit") {
      showBubble("pending", "心笺已标记本轮重算", "正在等待新回复完成……");
    } else {
      showBubble("pending", "心笺已接管本轮", "正在记录用户输入，等待正文完成……");
    }
    try {
      await requestJson(new URL("turn/start", apiBase).toString(), {
        method: "POST",
        body: JSON.stringify({ turn_id: turnId, user_text: userText, created_at: pendingTurn.createdAt, source }),
      });
      pingHook("turn_start", `已记录用户输入：${turnId}`, turnId);
    } catch (error) {
      console.warn("State Journal turn start failed:", error);
    }
    scheduleDomFallback(pendingTurn);
    return pendingTurn;
  }

  async function invalidateTrackedTurn(detail = {}) {
    const turnId = String(detail.turnId || detail.turn_id || detail.fromTurnId || detail.from_turn_id || "").trim();
    const reason = detail.reason || detail.type || "history_changed";
    if (turnId) forgetTurnRuntime(turnId);
    else clearAllDomFallbacks();
    processedTurns.clear();
    invalidateMessageDisplaysFromIndex(detail.trimmedFrom ?? detail.messageIndex ?? detail.index ?? -1);
    if (reason === "reroll" || reason === "edit_user" || reason === "edit") {
      showBubble("pending", "心笺已标记本轮重算", "旧幕笺已失效，正在等待新回复完成……");
    } else {
      showBubble("pending", "心笺已标记记录过期", "旧幕笺已失效，等待后续重建或重新生成……");
    }
    try {
      await requestJson(new URL("turn/invalidate", apiBase).toString(), {
        method: "POST",
        body: JSON.stringify({
          turn_id: turnId,
          reason,
          message_index: detail.messageIndex ?? detail.index ?? null,
        }),
      });
      processedTurns.clear();
      pingHook("turn_invalidated", turnId ? `已标记心笺轮次过期：${turnId}` : "已标记心笺记录过期。", turnId);
    } catch (error) {
      console.warn("State Journal turn invalidate failed:", error);
    }
  }

  async function pingHook(event = "loaded", message = "聊天页心笺脚本已加载。", turnId = "") {
    try {
      await requestJson(new URL("hook/ping", apiBase).toString(), {
        method: "POST",
        body: JSON.stringify({ event, message, page: "chat", turn_id: turnId }),
      });
    } catch (error) {
      console.warn("State Journal hook ping failed:", error);
    }
  }

  async function loadConfig() {
    const payload = await requestJson(new URL("config", apiBase).toString());
    configCache = payload.config || {};
    return configCache;
  }

  async function restoreRecentDisplays() {
    try {
      const payload = await requestJson(new URL("display/recent?limit=80", apiBase).toString());
      const displays = Array.isArray(payload.turns) ? payload.turns : [];
      if (!displays.length) return;
      const messages = assistantMessages();
      if (!messages.length) return;
      const byMessageId = new Map();
      const byTurnId = new Map();
      const byIndexHash = new Map();
      const byHash = new Map();
      messages.forEach((msg) => {
        const messageId = String(msg.dataset.messageId || "").trim();
        const turnId = String(msg.dataset.stateJournalTurn || msg.dataset.turnId || "").trim();
        const turnIndex = String(msg.dataset.turnIndex || "").trim();
        const contentHash = String(msg.dataset.contentHash || "").trim();
        if (messageId) byMessageId.set(messageId, msg);
        if (turnId) byTurnId.set(turnId, msg);
        if (turnIndex && contentHash) byIndexHash.set(`${turnIndex}:${contentHash}`, msg);
        if (contentHash) {
          const bucket = byHash.get(contentHash) || [];
          bucket.push(msg);
          byHash.set(contentHash, bucket);
        }
      });
      let restored = 0;
      let fallbackRestored = 0;
      const restoredMessages = new Set();
      displays.forEach((display) => {
        const turnId = String(display.turn_id || "").trim();
        const messageId = String(display.message_id || "").trim();
        const contentHash = String(display.content_hash || "").trim();
        const turnIndex = String(display.turn_index || "").trim();
        let matched = messageId ? byMessageId.get(messageId) : null;
        if (!matched && turnId) matched = byTurnId.get(turnId) || null;
        if (!matched && turnIndex && contentHash) {
          matched = byIndexHash.get(`${turnIndex}:${contentHash}`) || null;
          if (matched) fallbackRestored += 1;
        }
        if (!matched && contentHash) {
          const bucket = byHash.get(contentHash) || [];
          if (bucket.length === 1) {
            matched = bucket[0];
            fallbackRestored += 1;
          }
        }
        const restoreKey = matched ? (matched.dataset.messageId || matched.dataset.turnId || `${matched.dataset.turnIndex}:${matched.dataset.contentHash}`) : "";
        if (!matched || restoredMessages.has(restoreKey)) return;
        if (contentHash && matched.dataset.contentHash && matched.dataset.contentHash !== contentHash) return;
        renderTurnDisplay(display, matched, {
          turn_id: turnId || matched.dataset.turnId || "",
          created_at: display.created_at,
          message_id: messageId || matched.dataset.messageId || "",
          content_hash: contentHash || matched.dataset.contentHash || "",
          trigger_source: display.trigger_source || "restore_cache",
        });
        restoredMessages.add(restoreKey);
        restored += 1;
      });
      const suffix = fallbackRestored ? `（含兜底 ${fallbackRestored} 条）` : "";
      pingHook("restore_display", `已恢复 ${restored} 条幕笺${suffix}。`);
    } catch (error) {
      console.warn("State Journal recent display restore failed:", error);
    }
  }

  function turnSignature(detail) {
    const turnId = String(detail?.turnId || "");
    const userText = String(detail?.userText || "").slice(0, 240);
    const assistantText = String(detail?.assistantText || "").slice(0, 240);
    return turnId ? `${turnId}::${simpleHash(userText)}::${simpleHash(assistantText)}` : `${userText}\n---\n${assistantText}`;
  }

  async function updateFromTurn(detail, triggerSource = "chat_hook") {
    const normalized = normalizeHookDetail(detail || {}, triggerSource);
    const config = await loadConfig();
    if (!config.enabled) return;
    const sourceToken = String(normalized.source || triggerSource || "");
    const forceGenerate = ["reroll", "edit", "edit_user", "manual", "manual_backend", "manual_rebuild", "rebuild", "dom_fallback"].includes(sourceToken);
    if (!config.auto_update && !forceGenerate) return;

    const userText = String(normalized.userText || "").trim();
    const assistantText = String(normalized.assistantCleanText || normalized.assistantText || "").trim();
    const rawAssistantText = String(normalized.assistantText || assistantText || "").trim();
    const turnId = String(normalized.turnId || makeTurnId(userText || assistantText)).trim();
    const targetMessage = normalized.targetMessage || findAssistantMessageForDetail(normalized);
    let messageId = String(normalized.messageId || targetMessage?.dataset?.messageId || "").trim();
    const turnIndex = normalized.turnIndex || targetMessage?.dataset?.turnIndex || 0;
    const contentHash = String(normalized.contentHash || normalized.assistantHash || targetMessage?.dataset?.contentHash || simpleHash(assistantText || rawAssistantText)).trim();

    if (targetMessage) {
      targetMessage.dataset.stateJournalTurn = turnId;
      targetMessage.dataset.turnId = turnId;
      if (turnIndex) targetMessage.dataset.turnIndex = String(turnIndex);
      if (contentHash) targetMessage.dataset.contentHash = contentHash;
      if (!messageId) {
        messageId = targetMessage.dataset.messageId || `msg_${turnId}_assistant`;
        targetMessage.dataset.messageId = messageId;
      }
    }

    if (!assistantText) {
      if (targetMessage) attachInlineTurnStatus(targetMessage, turnId, "心笺未检测到可绑定的 assistant 正文，本轮未生成幕笺。", "error");
      showBubble("error", "心笺未生成", "没有拿到本轮 assistant 正文。", 7000);
      return;
    }
    if (!messageId) {
      if (targetMessage) attachInlineTurnStatus(targetMessage, turnId, "心笺未获取到消息编号，本轮未生成幕笺。", "error");
      showBubble("error", "心笺未生成", "没有拿到本轮消息编号。", 7000);
      return;
    }

    if (invalidatedTurns.has(turnId) && String(normalized.source || triggerSource || "") !== "dom_fallback") {
      invalidatedTurns.delete(turnId);
    }

    const signature = `${triggerSource}:${turnId}:${messageId}:${contentHash}`;
    const messageSignature = `${turnId}:${messageId}:${contentHash}`;
    if (processedTurns.has(signature) || processedTurns.has(messageSignature) || inFlightTurns.has(turnId)) return;
    processedTurns.add(signature);
    processedTurns.add(messageSignature);
    inFlightTurns.set(turnId, messageSignature);
    clearDomFallback(turnId);

    const isRebuild = ["reroll", "edit", "dom_fallback"].includes(String(normalized.source || triggerSource || ""));
    showBubble(
      "pending",
      isRebuild ? "心笺正在重新填表……" : (config.mujian_enabled ? "心笺正在生成幕笺……" : "心笺正在填表……"),
      triggerSource === "dom_fallback" ? "Hook 未触发，已启用 DOM 兜底扫描。" : (config.mujian_enabled ? "已通过 Chat hook 接收本轮正文。" : "已通过 Chat hook 接收本轮正文。")
    );
    pingHook(triggerSource === "dom_fallback" ? "dom_fallback_start" : "chat_hook_start", triggerSource === "dom_fallback" ? "DOM 兜底触发心笺生成。" : "Chat hook 触发心笺生成。", turnId);

    try {
      const history = Array.isArray(normalized.recentHistory) && normalized.recentHistory.length
        ? normalized.recentHistory
        : await fetch("/api/history").then((res) => res.json()).catch(() => []);
      const createdAt = String(normalized.createdAt || normalized.created_at || pendingTurn?.createdAt || new Date().toISOString());
      if (targetMessage) {
        attachInlineTurnStatus(targetMessage, turnId, config.mujian_enabled ? "心笺正在生成本轮幕笺……" : "心笺正在整理本轮状态……");
      }

      await requestJson(new URL("turn/complete", apiBase).toString(), {
        method: "POST",
        body: JSON.stringify({
          turn_id: turnId,
          user_text: userText,
          assistant_text: assistantText,
          created_at: createdAt,
          message_id: messageId,
          assistant_message_id: messageId,
          turn_index: turnIndex,
          trigger_source: triggerSource,
        }),
      }).catch((error) => console.warn("State Journal turn complete failed:", error));

      const payload = await requestJson(new URL("worker/update", apiBase).toString(), {
        method: "POST",
        body: JSON.stringify({
          trigger_source: triggerSource,
          latest_turn: { user: userText, assistant: assistantText },
          user_text: userText,
          assistant_text: rawAssistantText || assistantText,
          assistant_clean_text: assistantText,
          recent_history: history,
          history,
          turn_id: turnId,
          created_at: createdAt,
          message_id: messageId,
          assistant_message_id: messageId,
          turn_index: turnIndex,
          user_hash: simpleHash(userText),
          assistant_hash: contentHash || simpleHash(assistantText),
          content_hash: contentHash || simpleHash(assistantText),
          event_type: isRebuild ? "rebuild" : "auto_update",
          source: normalized.source || triggerSource || "chat_hook",
        }),
      });

      const errors = payload.result?.errors || [];
      const count = payload.summary?.total ?? payload.result?.applied?.length ?? 0;
      const failedPayload = errors.length || payload.ok === false || payload.status === "error";
      if (!failedPayload && payload.display && targetMessage && isSameMessageTarget(targetMessage, { turnId, messageId, contentHash })) {
        renderTurnDisplay(payload.display, targetMessage, { ...payload, turn_id: payload.display.turn_id || turnId, created_at: createdAt, message_id: messageId, content_hash: contentHash, trigger_source: triggerSource });
      } else if (!failedPayload && payload.display && !targetMessage) {
        console.warn("State Journal display generated but target message not found", turnId, messageId);
      }

      if (payload.skipped) {
        showBubble("empty", "心笺未运行", payload.message || payload.reason || "已跳过本轮更新", 2800);
      } else if (failedPayload) {
        if (targetMessage) attachInlineTurnStatus(targetMessage, turnId, payload.message || errors[0] || "心笺生成失败，本轮未写入新数据。", "error");
        showBubble("error", "心笺生成失败", `${payload.message || errors[0] || "辅助模型返回异常"}，点击查看日志`, 9000);
      } else if (count) {
        showBubble("success", isRebuild ? "心笺已重算" : (payload.display ? "心笺已生成幕笺" : "心笺已更新"), `${triggerSource === "dom_fallback" ? "DOM兜底｜" : "Hook｜"}${isRebuild ? "本轮幕笺已替换｜" : ""}${formatSummary(payload)}`, 3600);
      } else {
        showBubble("empty", payload.display ? "幕笺已生成" : "心笺无变化", `${triggerSource === "dom_fallback" ? "DOM兜底｜" : "Hook｜"}${payload.message || "本轮没有需要写入的状态"}`, 3000);
      }
      pingHook(payload.ok === false || payload.status === "error" ? "auto_update_error" : (isRebuild ? "auto_rebuild_done" : "auto_update_done"), payload.message || "自动填表与幕笺生成已完成。", turnId);
      if (pendingTurn?.turnId === turnId) pendingTurn = null;
      window.dispatchEvent(new CustomEvent("state_journal:updated", { detail: { ...payload, trigger_source: triggerSource } }));
    } catch (error) {
      if (targetMessage) attachInlineTurnStatus(targetMessage, turnId, error.message || "心笺生成失败，本轮未写入新数据。", "error");
      showBubble("error", "心笺生成失败", `${error.message || "未知错误"}，点击查看日志`, 9000);
      pingHook("auto_update_error", error.message || "自动填表失败。", turnId);
      console.warn("State Journal auto update failed:", error);
    } finally {
      if (targetMessage && !targetMessage.querySelector(`.state-journal-turn-status.is-error[data-state-journal-turn="${CSS.escape(turnId)}"]`)) {
        clearInlineTurnStatus(targetMessage, turnId);
      }
      if (inFlightTurns.get(turnId) === messageSignature) inFlightTurns.delete(turnId);
    }
  }

  window.addEventListener("fantareal:chat-user-submit", (event) => startTrackedTurn(event.detail || {}));
  window.addEventListener("fantareal:assistant-finalized", (event) => updateFromTurn(event.detail || {}, "chat_hook"));
  window.addEventListener("fantareal:chat-reroll", (event) => invalidateTrackedTurn({ ...(event.detail || {}), reason: "reroll" }));
  window.addEventListener("fantareal:chat-edit", (event) => invalidateTrackedTurn({ ...(event.detail || {}), reason: "edit_user" }));
  window.addEventListener("fantareal:message-invalidated", (event) => invalidateTrackedTurn(event.detail || {}));
  window.addEventListener("fantareal:chat-delete", (event) => invalidateTrackedTurn({ ...(event.detail || {}), reason: "delete_history" }));

  window.stateJournalChatBridge = {
    reloadConfig: loadConfig,
    showBubble,
    hideBubble,
    getConfig: () => configCache,
    renderTurnDisplay,
    attachTurnNote,
    restoreRecentDisplays,
    startTrackedTurn,
    invalidateTrackedTurn,
  };

  pingHook("loaded", "聊天页心笺脚本已加载。 ");
  loadConfig()
    .then(restoreRecentDisplays)
    .catch((error) => console.warn("State Journal config/display load failed:", error));
})();
