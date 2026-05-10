(() => {
  const scriptUrl = new URL(document.currentScript?.src || window.location.href);
  const apiBase = new URL("../api/", scriptUrl).toString();
  let configCache = null;
  let inFlight = false;
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
    if (document.getElementById("xinjian-chat-bubble-style")) return;
    const style = document.createElement("style");
    style.id = "xinjian-chat-bubble-style";
    style.textContent = `
      .xinjian-chat-bubble {
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
      .xinjian-chat-bubble.is-visible { opacity: 1; transform: translateX(-50%) translateY(0); pointer-events: auto; }
      .xinjian-chat-bubble.is-success { border-color: color-mix(in srgb, #6ac486 60%, var(--border, rgba(255,255,255,0.18)) 40%); }
      .xinjian-chat-bubble.is-empty { border-color: color-mix(in srgb, #8ca6c8 55%, var(--border, rgba(255,255,255,0.18)) 45%); }
      .xinjian-chat-bubble.is-error { border-color: color-mix(in srgb, #ff7878 64%, var(--border, rgba(255,255,255,0.18)) 36%); cursor: pointer; }
      .xinjian-chat-bubble-mark {
        flex: 0 0 auto; width: 2rem; height: 2rem; border-radius: 999px; display: inline-flex; align-items: center; justify-content: center;
        background: color-mix(in srgb, var(--accent, #d8b273) 18%, transparent 82%);
        border: 1px solid color-mix(in srgb, var(--accent, #d8b273) 36%, transparent 64%);
        font-weight: 800; line-height: 1;
      }
      .xinjian-chat-bubble.is-pending .xinjian-chat-bubble-mark::before { content: ""; width: 0.82rem; height: 0.82rem; border-radius: 999px; border: 2px solid color-mix(in srgb, currentColor 28%, transparent 72%); border-top-color: currentColor; animation: xinjian-spin 0.85s linear infinite; }
      .xinjian-chat-bubble.is-success .xinjian-chat-bubble-mark::before { content: "✓"; }
      .xinjian-chat-bubble.is-empty .xinjian-chat-bubble-mark::before { content: "◇"; }
      .xinjian-chat-bubble.is-error .xinjian-chat-bubble-mark::before { content: "!"; }
      .xinjian-chat-bubble-copy { min-width: 0; flex: 1 1 auto; }
      .xinjian-chat-bubble-title { font-weight: 800; font-size: 0.92rem; line-height: 1.25; letter-spacing: 0.01em; }
      .xinjian-chat-bubble-desc { margin-top: 0.26rem; color: var(--muted, rgba(245,239,229,0.74)); font-size: 0.78rem; line-height: 1.45; word-break: break-word; }
      .xinjian-chat-bubble-close {
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
      .xinjian-chat-bubble-close:hover { opacity: 1; background: color-mix(in srgb, currentColor 10%, transparent 90%); }

      .xinjian-inline-scene-card {
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
      .xinjian-inline-scene-card summary {
        list-style: none;
        cursor: pointer;
        padding: .72rem .88rem;
        display: grid;
        gap: .26rem;
      }
      .xinjian-inline-scene-card summary::-webkit-details-marker { display: none; }
      .xinjian-scene-kicker { color: var(--accent, #d8b273); font-size: .68rem; text-transform: uppercase; letter-spacing: .18em; font-weight: 850; }
      .xinjian-scene-title-line { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
      .xinjian-scene-title { font-weight: 900; letter-spacing: .04em; font-size: clamp(.96rem, 1.55vw, 1.18rem); }
      .xinjian-scene-toggle { flex: 0 0 auto; opacity: .78; font-size: .74rem; color: var(--muted, rgba(245,239,229,.72)); }
      .xinjian-inline-scene-card[open] .xinjian-scene-toggle { color: var(--accent, #d8b273); }
      .xinjian-scene-subtitle { color: var(--muted, rgba(245,239,229,.72)); font-size: .8rem; line-height: 1.5; }
      .xinjian-scene-body { padding: 0 .88rem .82rem; display: grid; gap: .58rem; }
      .xinjian-scene-meta { display: flex; flex-wrap: wrap; gap: .36rem; }
      .xinjian-scene-chip { border: 1px solid var(--border, rgba(255,255,255,.16)); border-radius: 999px; padding: .22rem .54rem; background: color-mix(in srgb, var(--input-bg, rgba(0,0,0,.18)) 70%, transparent 30%); font-size: .72rem; color: var(--muted, rgba(245,239,229,.72)); }
      .xinjian-scene-event { border-left: 3px solid color-mix(in srgb, var(--accent, #d8b273) 72%, transparent 28%); padding-left: .72rem; color: var(--text, #f5efe5); font-size: .82rem; line-height: 1.6; }

      .xinjian-turn-note {
        margin-top: .62rem;
        border: 1px solid color-mix(in srgb, var(--accent, #d8b273) 28%, var(--border, rgba(255,255,255,.16)) 72%);
        border-radius: 1rem;
        background: color-mix(in srgb, var(--panel, rgba(35,31,27,.72)) 70%, transparent 30%);
        color: var(--text, #f5efe5);
        overflow: hidden;
        box-shadow: 0 10px 24px rgba(0,0,0,.12), inset 0 1px 0 rgba(255,255,255,.06);
      }
      .xinjian-turn-note.is-mode-expanded { border-color: color-mix(in srgb, var(--accent, #d8b273) 38%, var(--border, rgba(255,255,255,.16)) 62%); }
      .xinjian-turn-note-compact {
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
      .xinjian-turn-note-compact strong { color: var(--accent, #d8b273); font-weight: 850; }
      .xinjian-turn-note-compact span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .xinjian-turn-note summary {
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
      .xinjian-turn-note summary::-webkit-details-marker { display: none; }
      .xinjian-turn-summary-main { display: flex; align-items: center; gap: .5rem; min-width: 0; }
      .xinjian-note-dot { width: .48rem; height: .48rem; border-radius: 999px; background: var(--accent, #d8b273); box-shadow: 0 0 0 4px color-mix(in srgb, var(--accent, #d8b273) 13%, transparent 87%); }
      .xinjian-turn-note[open] summary { color: var(--text, #f5efe5); }
      .xinjian-note-body { display: grid; gap: .62rem; padding: 0 .82rem .82rem; }
      .xinjian-note-toolbar { display: flex; flex-wrap: wrap; gap: .36rem; color: var(--muted, rgba(245,239,229,.72)); font-size: .74rem; }
      .xinjian-note-section { border: 1px solid var(--border, rgba(255,255,255,.13)); border-radius: .86rem; padding: .68rem; background: rgba(255,255,255,.035); }
      .xinjian-note-section h4 { margin: 0 0 .42rem; font-size: .9rem; }
      .xinjian-note-grid { display: grid; gap: .38rem; }
      .xinjian-note-field { display: grid; gap: .11rem; }
      .xinjian-note-field span { color: var(--muted, rgba(245,239,229,.68)); font-size: .7rem; }
      .xinjian-note-field strong { font-size: .8rem; line-height: 1.5; font-weight: 600; }
      .xinjian-turn-note.is-note-gufeng .xinjian-note-field strong { font-family: inherit; letter-spacing: .025em; }
      .xinjian-turn-note.is-note-sensory .xinjian-note-grid { gap: .44rem; }
      .xinjian-turn-note.is-note-sensory .xinjian-note-field {
        display: block;
        padding: .44rem .56rem;
        border-radius: .68rem;
        border: 1px solid color-mix(in srgb, var(--accent, #d8b273) 24%, var(--border, rgba(255,255,255,.14)) 76%);
        background: color-mix(in srgb, var(--input-bg, rgba(0,0,0,.16)) 78%, transparent 22%);
      }
      .xinjian-turn-note.is-note-sensory .xinjian-note-field span {
        display: inline;
        color: color-mix(in srgb, var(--accent, #d8b273) 70%, currentColor 30%);
        font-size: .72rem;
        font-weight: 800;
        letter-spacing: .04em;
      }
      .xinjian-turn-note.is-note-sensory .xinjian-note-field span::before { content: "<"; }
      .xinjian-turn-note.is-note-sensory .xinjian-note-field span::after { content: ">"; }
      .xinjian-turn-note.is-note-sensory .xinjian-note-field strong {
        display: inline;
        margin-left: .42rem;
        font-size: .8rem;
        line-height: 1.65;
        font-weight: 650;
      }
      .xinjian-relation-list { display: grid; gap: .42rem; color: var(--muted, rgba(245,239,229,.74)); font-size: .8rem; line-height: 1.55; }
      .xinjian-note-empty { color: var(--muted, rgba(245,239,229,.72)); font-size: .8rem; padding: .3rem 0; }

      .xinjian-inline-scene-card.theme-gufeng-paper,
      .xinjian-turn-note.theme-gufeng-paper,
      .xinjian-turn-note-compact.theme-gufeng-paper {
        --xj-paper-accent: var(--xj-beauty-accent, #9f5f41);
        border-color: color-mix(in srgb, var(--xj-paper-accent) 38%, rgba(86, 52, 31, .22) 62%);
        background:
          radial-gradient(circle at 16% 0%, rgba(196, 126, 70, .10), transparent 32%),
          linear-gradient(135deg, rgba(255, 248, 232, .94), rgba(238, 224, 199, .86));
        color: #2f251d;
        box-shadow: 0 12px 32px rgba(78, 50, 32, .14), inset 0 0 0 1px rgba(255,255,255,.34);
      }
      .xinjian-inline-scene-card.theme-gufeng-paper .xinjian-scene-kicker,
      .xinjian-inline-scene-card.theme-gufeng-paper .xinjian-scene-toggle,
      .xinjian-turn-note.theme-gufeng-paper .xinjian-note-toolbar,
      .xinjian-turn-note.theme-gufeng-paper .xinjian-note-field span,
      .xinjian-turn-note-compact.theme-gufeng-paper strong { color: var(--xj-paper-accent); }
      .xinjian-inline-scene-card.theme-gufeng-paper .xinjian-scene-subtitle,
      .xinjian-inline-scene-card.theme-gufeng-paper .xinjian-scene-chip,
      .xinjian-turn-note.theme-gufeng-paper summary,
      .xinjian-turn-note.theme-gufeng-paper .xinjian-relation-list,
      .xinjian-turn-note.theme-gufeng-paper .xinjian-note-empty,
      .xinjian-turn-note-compact.theme-gufeng-paper span { color: rgba(47,37,29,.72); }
      .xinjian-inline-scene-card.theme-gufeng-paper .xinjian-scene-title { font-weight: 900; letter-spacing: .08em; }
      .xinjian-inline-scene-card.theme-gufeng-paper .xinjian-scene-chip,
      .xinjian-turn-note.theme-gufeng-paper .xinjian-note-section,
      .xinjian-turn-note.theme-gufeng-paper .xinjian-note-field {
        border-color: rgba(126, 76, 45, .18);
        background: rgba(255, 253, 244, .48);
      }
      .xinjian-turn-note.theme-gufeng-paper .xinjian-note-field {
        border-radius: .55rem;
        box-shadow: inset 3px 0 0 color-mix(in srgb, var(--xj-paper-accent) 46%, transparent 54%);
      }
      .xinjian-turn-note.theme-gufeng-paper .xinjian-note-field span::before,
      .xinjian-turn-note.theme-gufeng-paper .xinjian-note-field span::after { content: ""; }
      .xinjian-turn-note.theme-gufeng-paper .xinjian-note-field strong { color: #2f251d; font-weight: 700; }
      .xinjian-turn-note.theme-gufeng-paper .xinjian-note-dot { background: var(--xj-paper-accent); box-shadow: 0 0 0 4px color-mix(in srgb, var(--xj-paper-accent) 14%, transparent 86%); }


      /* v0.7 外观模板包：现代 Time Card 结构 */
      .xinjian-inline-scene-card.theme-time-card,
      .xinjian-turn-note.theme-time-card,
      .xinjian-turn-note-compact.theme-time-card {
        --xj-time-accent: var(--xj-beauty-accent, #1f6feb);
        background: rgba(255,255,255,.92);
        color: #2e3440;
        border-color: rgba(31,111,235,.18);
        box-shadow: 0 14px 36px rgba(24, 40, 72, .14), inset 0 1px 0 rgba(255,255,255,.88);
      }
      .xinjian-inline-scene-card.theme-time-card { border-radius: 1.15rem; }
      .xinjian-inline-scene-card.theme-time-card summary { padding: .9rem 1rem .64rem; }
      .xinjian-inline-scene-card.theme-time-card .xinjian-scene-kicker { color: #697386; letter-spacing: .12em; font-size: .74rem; }
      .xinjian-inline-scene-card.theme-time-card .xinjian-scene-title { color: #101828; font-size: 1.05rem; letter-spacing: .02em; }
      .xinjian-inline-scene-card.theme-time-card .xinjian-scene-subtitle { color: #4b5565; }
      .xinjian-inline-scene-card.theme-time-card .xinjian-scene-toggle { color: #6b7280; }
      .xinjian-inline-scene-card.theme-time-card .xinjian-scene-body { padding: .15rem 1rem 1rem; gap: .65rem; }
      .xinjian-inline-scene-card.theme-time-card .xinjian-scene-meta { display: grid; gap: .45rem; }
      .xinjian-inline-scene-card.theme-time-card .xinjian-scene-chip {
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
      .xinjian-inline-scene-card.theme-time-card .xinjian-scene-chip b { color: #9b4b43; font-weight: 800; }
      .xinjian-inline-scene-card.theme-time-card .xinjian-scene-event {
        border: 0;
        border-top: 2px solid rgba(31,111,235,.14);
        padding: .7rem .25rem 0;
        color: #344054;
        line-height: 1.7;
      }
      .xinjian-turn-note.theme-time-card .xinjian-note-body { gap: .7rem; }
      .xinjian-turn-note.theme-time-card .xinjian-note-toolbar { color: #697386; }
      .xinjian-turn-note.theme-time-card summary { color: #475467; }
      .xinjian-turn-note.theme-time-card .xinjian-note-section {
        background: rgba(255,255,255,.78);
        border-color: rgba(31,111,235,.14);
        border-radius: 1rem;
      }
      .xinjian-turn-note.theme-time-card .xinjian-note-section h4 { color: #101828; letter-spacing: .02em; }
      .xinjian-turn-note.theme-time-card .xinjian-note-grid { gap: .32rem; }
      .xinjian-turn-note.theme-time-card .xinjian-note-field {
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
      .xinjian-turn-note.theme-time-card .xinjian-note-field:last-child { border-bottom: 0; }
      .xinjian-turn-note.theme-time-card .xinjian-note-field .xinjian-note-icon { font-style: normal; text-align: center; opacity: .92; }
      .xinjian-turn-note.theme-time-card .xinjian-note-field span { color: #9b4b43; font-weight: 800; font-size: .78rem; }
      .xinjian-turn-note.theme-time-card .xinjian-note-field span::before,
      .xinjian-turn-note.theme-time-card .xinjian-note-field span::after { content: ""; }
      .xinjian-turn-note.theme-time-card .xinjian-note-field strong { color: #344054; font-size: .84rem; line-height: 1.72; font-weight: 500; margin-left: 0; }
      .xinjian-turn-note.theme-time-card .xinjian-relation-list {
        background: rgba(245,249,255,.8);
        border-radius: .8rem;
        padding: .6rem .72rem;
        color: #475467;
      }
      .xinjian-turn-note-compact.theme-time-card { border-radius: 999px; background: rgba(255,255,255,.9); color: #475467; }
      .xinjian-turn-note-compact.theme-time-card strong { color: var(--xj-time-accent); }

      /* v0.7 外观模板包：古风结构强化 */
      .xinjian-inline-scene-card.theme-gufeng-paper .xinjian-scene-meta { gap: .42rem; }
      .xinjian-inline-scene-card.theme-gufeng-paper .xinjian-scene-event { color: #3f3026; }
      .xinjian-turn-note.theme-gufeng-paper .xinjian-note-section h4::before { content: "◇ "; color: var(--xj-paper-accent); }



      /* v0.7.1 美化包扩展：月白冷笺 */
      .xinjian-inline-scene-card.theme-moon-white,
      .xinjian-turn-note.theme-moon-white,
      .xinjian-turn-note-compact.theme-moon-white {
        --xj-moon-accent: var(--xj-beauty-accent, #7e9bb8);
        background:
          radial-gradient(circle at 12% 0%, rgba(174, 203, 232, .18), transparent 30%),
          linear-gradient(145deg, rgba(247,250,253,.96), rgba(227,235,244,.9));
        color: #243244;
        border-color: rgba(126,155,184,.32);
        box-shadow: 0 14px 34px rgba(50, 75, 105, .12), inset 0 1px 0 rgba(255,255,255,.65);
      }
      .xinjian-inline-scene-card.theme-moon-white .xinjian-scene-kicker,
      .xinjian-inline-scene-card.theme-moon-white .xinjian-scene-toggle,
      .xinjian-turn-note.theme-moon-white .xinjian-note-toolbar,
      .xinjian-turn-note.theme-moon-white .xinjian-note-field span,
      .xinjian-turn-note-compact.theme-moon-white strong { color: var(--xj-moon-accent); }
      .xinjian-inline-scene-card.theme-moon-white .xinjian-scene-subtitle,
      .xinjian-inline-scene-card.theme-moon-white .xinjian-scene-chip,
      .xinjian-turn-note.theme-moon-white summary,
      .xinjian-turn-note.theme-moon-white .xinjian-relation-list,
      .xinjian-turn-note-compact.theme-moon-white span { color: rgba(36,50,68,.68); }
      .xinjian-inline-scene-card.theme-moon-white .xinjian-scene-title { color: #1f2c3c; font-weight: 900; letter-spacing: .05em; }
      .xinjian-inline-scene-card.theme-moon-white .xinjian-scene-chip,
      .xinjian-turn-note.theme-moon-white .xinjian-note-section,
      .xinjian-turn-note.theme-moon-white .xinjian-note-field {
        border-color: rgba(126,155,184,.2);
        background: rgba(255,255,255,.5);
      }
      .xinjian-turn-note.theme-moon-white .xinjian-note-field { border-radius: .7rem; box-shadow: inset 2px 0 0 rgba(126,155,184,.34); }
      .xinjian-turn-note.theme-moon-white .xinjian-note-field span::before,
      .xinjian-turn-note.theme-moon-white .xinjian-note-field span::after { content: ""; }
      .xinjian-turn-note.theme-moon-white .xinjian-note-field strong { color: #243244; }

      /* v0.7.1 美化包扩展：朱砂密卷 */
      .xinjian-inline-scene-card.theme-cinnabar-dossier,
      .xinjian-turn-note.theme-cinnabar-dossier,
      .xinjian-turn-note-compact.theme-cinnabar-dossier {
        --xj-case-accent: var(--xj-beauty-accent, #b8322a);
        background:
          linear-gradient(90deg, rgba(184,50,42,.08), transparent 34%),
          linear-gradient(145deg, rgba(245,238,222,.96), rgba(222,207,183,.92));
        color: #211b17;
        border-color: rgba(94,45,30,.28);
        box-shadow: 0 16px 36px rgba(64, 34, 22, .18), inset 0 0 0 1px rgba(255,255,255,.28);
      }
      .xinjian-inline-scene-card.theme-cinnabar-dossier .xinjian-scene-kicker,
      .xinjian-turn-note.theme-cinnabar-dossier .xinjian-note-toolbar,
      .xinjian-turn-note.theme-cinnabar-dossier .xinjian-note-field span,
      .xinjian-turn-note-compact.theme-cinnabar-dossier strong { color: var(--xj-case-accent); }
      .xinjian-inline-scene-card.theme-cinnabar-dossier .xinjian-scene-title { color: #1b1410; font-weight: 950; letter-spacing: .08em; }
      .xinjian-inline-scene-card.theme-cinnabar-dossier .xinjian-scene-kicker::before { content: "卷宗 · "; }
      .xinjian-inline-scene-card.theme-cinnabar-dossier .xinjian-scene-chip,
      .xinjian-turn-note.theme-cinnabar-dossier .xinjian-note-section,
      .xinjian-turn-note.theme-cinnabar-dossier .xinjian-note-field {
        border-color: rgba(126, 51, 38, .2);
        background: rgba(255,249,237,.55);
      }
      .xinjian-turn-note.theme-cinnabar-dossier .xinjian-note-section h4::before { content: "【人物】"; color: var(--xj-case-accent); margin-right: .25rem; }
      .xinjian-turn-note.theme-cinnabar-dossier .xinjian-note-field { border-radius: .42rem; border-left: 3px solid rgba(184,50,42,.42); }
      .xinjian-turn-note.theme-cinnabar-dossier .xinjian-note-field span::before,
      .xinjian-turn-note.theme-cinnabar-dossier .xinjian-note-field span::after { content: ""; }
      .xinjian-turn-note.theme-cinnabar-dossier .xinjian-note-field strong,
      .xinjian-turn-note.theme-cinnabar-dossier summary,
      .xinjian-turn-note.theme-cinnabar-dossier .xinjian-relation-list { color: #2b201b; }

      /* v0.7.1 美化包扩展：玉简灵纹 */
      .xinjian-inline-scene-card.theme-jade-slip,
      .xinjian-turn-note.theme-jade-slip,
      .xinjian-turn-note-compact.theme-jade-slip {
        --xj-jade-accent: var(--xj-beauty-accent, #47a985);
        background:
          radial-gradient(circle at 90% 8%, rgba(91, 225, 185, .20), transparent 28%),
          linear-gradient(145deg, rgba(236,252,246,.95), rgba(210,235,226,.9));
        color: #183b32;
        border-color: rgba(71,169,133,.32);
        box-shadow: 0 14px 34px rgba(20, 97, 76, .16), 0 0 0 1px rgba(188, 255, 234, .34) inset;
      }
      .xinjian-inline-scene-card.theme-jade-slip .xinjian-scene-kicker,
      .xinjian-inline-scene-card.theme-jade-slip .xinjian-scene-toggle,
      .xinjian-turn-note.theme-jade-slip .xinjian-note-toolbar,
      .xinjian-turn-note.theme-jade-slip .xinjian-note-field span,
      .xinjian-turn-note-compact.theme-jade-slip strong { color: #237d64; }
      .xinjian-inline-scene-card.theme-jade-slip .xinjian-scene-kicker::before { content: "灵简 · "; }
      .xinjian-inline-scene-card.theme-jade-slip .xinjian-scene-title { color: #14392f; letter-spacing: .07em; text-shadow: 0 0 16px rgba(71,169,133,.18); }
      .xinjian-inline-scene-card.theme-jade-slip .xinjian-scene-chip,
      .xinjian-turn-note.theme-jade-slip .xinjian-note-section,
      .xinjian-turn-note.theme-jade-slip .xinjian-note-field {
        border-color: rgba(71,169,133,.22);
        background: rgba(244,255,251,.54);
      }
      .xinjian-turn-note.theme-jade-slip .xinjian-note-field { box-shadow: inset 0 0 0 1px rgba(188,255,234,.36); }
      .xinjian-turn-note.theme-jade-slip .xinjian-note-field span::before { content: "◇ "; }
      .xinjian-turn-note.theme-jade-slip .xinjian-note-field span::after { content: ""; }
      .xinjian-turn-note.theme-jade-slip .xinjian-note-field strong,
      .xinjian-turn-note.theme-jade-slip summary,
      .xinjian-turn-note.theme-jade-slip .xinjian-relation-list { color: #183b32; }

      /* v0.7.1 美化包扩展：暗夜档案 */
      .xinjian-inline-scene-card.theme-midnight-archive,
      .xinjian-turn-note.theme-midnight-archive,
      .xinjian-turn-note-compact.theme-midnight-archive {
        --xj-night-accent: var(--xj-beauty-accent, #62d6ff);
        background:
          linear-gradient(135deg, rgba(15,23,42,.96), rgba(3,7,18,.93));
        color: #d8f3ff;
        border-color: rgba(98,214,255,.28);
        box-shadow: 0 18px 42px rgba(0,0,0,.32), 0 0 0 1px rgba(98,214,255,.08) inset;
      }
      .xinjian-inline-scene-card.theme-midnight-archive .xinjian-scene-kicker,
      .xinjian-turn-note.theme-midnight-archive .xinjian-note-toolbar,
      .xinjian-turn-note.theme-midnight-archive .xinjian-note-field span,
      .xinjian-turn-note-compact.theme-midnight-archive strong { color: var(--xj-night-accent); }
      .xinjian-inline-scene-card.theme-midnight-archive .xinjian-scene-title { color: #f1fbff; letter-spacing: .08em; }
      .xinjian-inline-scene-card.theme-midnight-archive .xinjian-scene-kicker::before { content: "XJ-FILE // "; }
      .xinjian-inline-scene-card.theme-midnight-archive .xinjian-scene-subtitle,
      .xinjian-turn-note.theme-midnight-archive summary,
      .xinjian-turn-note.theme-midnight-archive .xinjian-relation-list,
      .xinjian-turn-note-compact.theme-midnight-archive span { color: rgba(216,243,255,.76); }
      .xinjian-inline-scene-card.theme-midnight-archive .xinjian-scene-chip,
      .xinjian-turn-note.theme-midnight-archive .xinjian-note-section,
      .xinjian-turn-note.theme-midnight-archive .xinjian-note-field {
        border-color: rgba(98,214,255,.16);
        background: rgba(15,23,42,.54);
      }
      .xinjian-turn-note.theme-midnight-archive .xinjian-note-field { grid-template-columns: 3.8rem 5rem 1fr; }
      .xinjian-turn-note.theme-midnight-archive .xinjian-note-field span::before,
      .xinjian-turn-note.theme-midnight-archive .xinjian-note-field span::after { content: ""; }
      .xinjian-turn-note.theme-midnight-archive .xinjian-note-field strong { color: #e8fbff; }

      /* v0.7.1 美化包扩展：剧本分镜 */
      .xinjian-inline-scene-card.theme-storyboard,
      .xinjian-turn-note.theme-storyboard,
      .xinjian-turn-note-compact.theme-storyboard {
        --xj-shot-accent: var(--xj-beauty-accent, #f59e0b);
        background:
          linear-gradient(90deg, rgba(0,0,0,.035) 1px, transparent 1px),
          linear-gradient(180deg, rgba(255,255,255,.96), rgba(246,241,231,.92));
        background-size: 18px 18px, auto;
        color: #25201a;
        border-color: rgba(15,23,42,.20);
        box-shadow: 0 14px 34px rgba(30, 25, 18, .14);
      }
      .xinjian-inline-scene-card.theme-storyboard .xinjian-scene-kicker,
      .xinjian-turn-note.theme-storyboard .xinjian-note-toolbar,
      .xinjian-turn-note.theme-storyboard .xinjian-note-field span,
      .xinjian-turn-note-compact.theme-storyboard strong { color: #b76b00; }
      .xinjian-inline-scene-card.theme-storyboard .xinjian-scene-kicker::before { content: "SCENE / "; }
      .xinjian-inline-scene-card.theme-storyboard .xinjian-scene-title { color: #17130f; font-weight: 950; }
      .xinjian-inline-scene-card.theme-storyboard .xinjian-scene-chip,
      .xinjian-turn-note.theme-storyboard .xinjian-note-section,
      .xinjian-turn-note.theme-storyboard .xinjian-note-field {
        border-color: rgba(15,23,42,.16);
        background: rgba(255,255,255,.68);
      }
      .xinjian-turn-note.theme-storyboard .xinjian-note-section h4::before { content: "TAKE · "; color: #b76b00; font-size: .72rem; }
      .xinjian-turn-note.theme-storyboard .xinjian-note-field span::before,
      .xinjian-turn-note.theme-storyboard .xinjian-note-field span::after { content: ""; }
      .xinjian-turn-note.theme-storyboard .xinjian-note-field strong,
      .xinjian-turn-note.theme-storyboard summary,
      .xinjian-turn-note.theme-storyboard .xinjian-relation-list { color: #25201a; }

      /* v0.7.1 美化包扩展：状态面板 Pro */
      .xinjian-inline-scene-card.theme-status-pro,
      .xinjian-turn-note.theme-status-pro,
      .xinjian-turn-note-compact.theme-status-pro {
        --xj-status-accent: var(--xj-beauty-accent, #7c3aed);
        background:
          linear-gradient(135deg, rgba(24,20,39,.94), rgba(12,10,20,.92));
        color: #efe9ff;
        border-color: rgba(124,58,237,.36);
        box-shadow: 0 18px 44px rgba(0,0,0,.34), 0 0 22px rgba(124,58,237,.12);
      }
      .xinjian-inline-scene-card.theme-status-pro .xinjian-scene-kicker,
      .xinjian-turn-note.theme-status-pro .xinjian-note-toolbar,
      .xinjian-turn-note.theme-status-pro .xinjian-note-field span,
      .xinjian-turn-note-compact.theme-status-pro strong { color: #b99cff; }
      .xinjian-inline-scene-card.theme-status-pro .xinjian-scene-kicker::before { content: "STATUS PANEL · "; }
      .xinjian-inline-scene-card.theme-status-pro .xinjian-scene-title { color: #fff; letter-spacing: .05em; }
      .xinjian-inline-scene-card.theme-status-pro .xinjian-scene-subtitle,
      .xinjian-turn-note.theme-status-pro summary,
      .xinjian-turn-note.theme-status-pro .xinjian-relation-list,
      .xinjian-turn-note-compact.theme-status-pro span { color: rgba(239,233,255,.75); }
      .xinjian-inline-scene-card.theme-status-pro .xinjian-scene-chip,
      .xinjian-turn-note.theme-status-pro .xinjian-note-section,
      .xinjian-turn-note.theme-status-pro .xinjian-note-field {
        border-color: rgba(124,58,237,.2);
        background: rgba(255,255,255,.055);
      }
      .xinjian-turn-note.theme-status-pro .xinjian-note-section h4 { color: #fff; }
      .xinjian-turn-note.theme-status-pro .xinjian-note-field { grid-template-columns: 3.4rem 5rem 1fr; }
      .xinjian-turn-note.theme-status-pro .xinjian-note-field span::before,
      .xinjian-turn-note.theme-status-pro .xinjian-note-field span::after { content: ""; }
      .xinjian-turn-note.theme-status-pro .xinjian-note-field strong { color: #f5f0ff; }


      /* v0.7.2：结构级外置美化包支持 */
      .xinjian-inline-scene-card.is-layout-paper-time,
      .xinjian-turn-note.is-theme-layout-paper_time,
      .xinjian-turn-note.is-theme-layout-paper_time_card {
        background:
          linear-gradient(90deg, rgba(126, 81, 42, .055) 1px, transparent 1px),
          linear-gradient(180deg, rgba(255,252,245,.98), rgba(248,241,229,.94));
        background-size: 24px 24px, auto;
        color: #2d261f;
        border-color: rgba(166, 115, 68, .28);
        box-shadow: 0 16px 38px rgba(86, 58, 29, .16);
      }
      .xinjian-inline-scene-card.is-layout-paper-time .xinjian-scene-kicker,
      .xinjian-turn-note.is-theme-layout-paper_time .xinjian-note-toolbar,
      .xinjian-turn-note.is-theme-layout-paper_time .xinjian-note-section h4,
      .xinjian-paper-note-row span,
      .xinjian-paper-time-row b { color: var(--xj-beauty-accent, #a75f2f); }
      .xinjian-inline-scene-card.is-layout-paper-time .xinjian-scene-title,
      .xinjian-turn-note.is-theme-layout-paper_time summary { color: #211912; }
      .xinjian-scene-paper-rows,
      .xinjian-paper-note-table { display: grid; gap: .38rem; }
      .xinjian-paper-time-row,
      .xinjian-paper-note-row {
        display: grid;
        grid-template-columns: 1.4rem 4.4rem minmax(0, 1fr);
        gap: .58rem;
        align-items: start;
        padding: .42rem .1rem;
        border-bottom: 1px dashed rgba(166,115,68,.20);
        color: #3a3028;
      }
      .xinjian-paper-time-row:last-child,
      .xinjian-paper-note-row:last-child { border-bottom: 0; }
      .xinjian-paper-note-row strong,
      .xinjian-paper-time-row span { font-weight: 600; line-height: 1.55; color: #312821; }

      .xinjian-inline-scene-card.is-layout-status-panel,
      .xinjian-turn-note.is-theme-layout-status_panel,
      .xinjian-turn-note.is-theme-layout-status_panel_pro,
      .xinjian-turn-note.is-theme-layout-hud {
        background:
          linear-gradient(90deg, rgba(79, 180, 255, .055) 1px, transparent 1px),
          linear-gradient(180deg, rgba(8,18,34,.97), rgba(3,8,18,.95));
        background-size: 18px 18px, auto;
        color: #d9f0ff;
        border-color: rgba(72, 188, 255, .35);
        box-shadow: 0 20px 48px rgba(0,0,0,.42), 0 0 24px rgba(56,189,248,.12);
      }
      .xinjian-status-scene-hud { display: grid; grid-template-columns: repeat(auto-fit, minmax(8.5rem, 1fr)); gap: .46rem; }
      .xinjian-status-scene-hud span,
      .xinjian-status-row {
        border: 1px solid rgba(72,188,255,.18);
        background: rgba(15,36,66,.50);
        border-radius: .56rem;
        padding: .48rem .56rem;
        color: rgba(217,240,255,.86);
      }
      .xinjian-status-scene-hud b,
      .xinjian-status-row span { color: #82d8ff; font-weight: 800; margin-right: .32rem; }
      .xinjian-status-timeline { display:flex; justify-content:space-between; align-items:center; color:#82d8ff; border-top:1px solid rgba(72,188,255,.18); padding-top:.52rem; letter-spacing:.08em; }
      .xinjian-status-note-table { display: grid; gap: .52rem; border: 0; border-radius: .78rem; overflow: visible; }
      .xinjian-status-row {
        display: grid;
        grid-template-columns: 1.55rem minmax(4.6rem, 5.6rem) minmax(0, 1fr) 2.1rem;
        align-items: start;
        gap: .62rem;
        border: 1px solid rgba(72,188,255,.16);
        border-radius: .68rem;
        padding: .62rem .7rem;
        background: rgba(15,36,66,.42);
      }
      .xinjian-status-row strong { color: #eefaff; line-height: 1.7; font-weight: 600; overflow-wrap: anywhere; }
      .xinjian-status-row i { color: rgba(130,216,255,.42); font-style: normal; text-align: right; font-size: .72rem; }
      @media (max-width: 720px) {
        .xinjian-status-row { grid-template-columns: 1.35rem 4.6rem minmax(0, 1fr); }
        .xinjian-status-row i { display: none; }
      }

      .xinjian-inline-scene-card.is-layout-storyboard,
      .xinjian-turn-note.is-theme-layout-storyboard,
      .xinjian-turn-note.is-theme-layout-storyboard_frame,
      .xinjian-turn-note.is-theme-layout-scene_board {
        background:
          linear-gradient(90deg, rgba(0,0,0,.045) 1px, transparent 1px),
          linear-gradient(180deg, rgba(34,31,27,.96), rgba(16,15,13,.95));
        background-size: 20px 20px, auto;
        color: #efe7d6;
        border-color: rgba(208, 137, 56, .34);
        box-shadow: 0 18px 44px rgba(0,0,0,.38);
      }
      .xinjian-storyboard-hero { grid-template-columns: minmax(0, .9fr) minmax(10rem, 1.15fr); align-items: stretch; }
      .xinjian-storyboard-meta { display:grid; gap:.18rem; padding:.58rem; border:1px solid rgba(208,137,56,.22); border-radius:.66rem; background:rgba(255,255,255,.035); }
      .xinjian-storyboard-meta p { margin: 0; line-height: 1.55; color: rgba(239,231,214,.78); }
      .xinjian-storyboard-meta b { color: #d18a38; }
      .xinjian-storyboard-frame {
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
      .xinjian-storyboard-frame.has-image { display: block; padding: 0; min-height: 9.6rem; }
      .xinjian-storyboard-frame.has-image::before {
        content: "";
        position: absolute;
        inset: 0;
        pointer-events: none;
        background: linear-gradient(180deg, rgba(0,0,0,.10), transparent 34%, rgba(0,0,0,.18));
        z-index: 1;
      }
      .xinjian-storyboard-frame.has-image::after {
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
      .xinjian-storyboard-frame img { width: 100%; height: 100%; min-height: 9.6rem; object-fit: cover; display:block; }
      .xinjian-storyboard-frame span { display:block; color:#d18a38; font-weight:900; letter-spacing:.08em; }
      .xinjian-storyboard-frame small { display:block; margin-top:.35rem; font-size:.68rem; }
      .xinjian-inline-scene-card.is-layout-storyboard .xinjian-scene-event { grid-column: 1 / -1; border-color:#d18a38; color:rgba(239,231,214,.82); }
      .xinjian-storyboard-note-table { display: grid; border: 1px solid rgba(208,137,56,.20); border-radius:.75rem; overflow:hidden; }
      .xinjian-storyboard-row { display:grid; grid-template-columns: 2rem 5rem minmax(0, 1fr); gap:.55rem; padding:.5rem .58rem; border-bottom:1px solid rgba(208,137,56,.16); align-items:start; }
      .xinjian-storyboard-row:last-child { border-bottom:0; }
      .xinjian-storyboard-row span { color:#d18a38; }
      .xinjian-storyboard-row b { color:#d18a38; font-weight:800; }
      .xinjian-storyboard-row strong { color:#f3ead9; line-height:1.55; font-weight:600; }

      /* v0.7.4：三类结构包的角色状态栏差异化 */
      .xinjian-turn-note.is-theme-layout-paper_time .xinjian-note-section {
        background: rgba(255,255,255,.58);
        border-color: rgba(166,115,68,.18);
        padding: .9rem 1rem;
      }
      .xinjian-turn-note.is-theme-layout-paper_time .xinjian-note-section h4 {
        color: #9b5a2c;
        font-size: .9rem;
        letter-spacing: .08em;
        border-bottom: 1px dashed rgba(166,115,68,.22);
        padding-bottom: .35rem;
        margin-bottom: .6rem;
      }
      .xinjian-turn-note.is-theme-layout-paper_time .xinjian-paper-note-table { display: grid; gap: .48rem; }
      .xinjian-turn-note.is-theme-layout-paper_time .xinjian-paper-note-row {
        display: grid;
        grid-template-columns: 4.8rem minmax(0,1fr);
        gap: .6rem;
        padding: .12rem 0 .42rem;
        border-bottom: 1px dotted rgba(166,115,68,.18);
      }
      .xinjian-turn-note.is-theme-layout-paper_time .xinjian-paper-note-row i { display:none; }
      .xinjian-turn-note.is-theme-layout-paper_time .xinjian-paper-note-row span { color:#a75f2f; font-weight:850; font-size:.78rem; }
      .xinjian-turn-note.is-theme-layout-paper_time .xinjian-paper-note-row strong { color:#312821; font-weight:520; line-height:1.78; }

      .xinjian-turn-note.is-theme-layout-status_panel .xinjian-note-section,
      .xinjian-turn-note.is-theme-layout-status_panel_pro .xinjian-note-section,
      .xinjian-turn-note.is-theme-layout-hud .xinjian-note-section {
        border-color: rgba(72,188,255,.22);
        background: rgba(5,16,30,.56);
        padding: .8rem;
      }
      .xinjian-turn-note.is-theme-layout-status_panel .xinjian-note-section h4,
      .xinjian-turn-note.is-theme-layout-status_panel_pro .xinjian-note-section h4,
      .xinjian-turn-note.is-theme-layout-hud .xinjian-note-section h4 {
        color:#82d8ff;
        font-size:.78rem;
        letter-spacing:.16em;
        text-transform:uppercase;
        margin-bottom:.7rem;
      }
      .xinjian-turn-note.is-theme-layout-status_panel .xinjian-status-note-table,
      .xinjian-turn-note.is-theme-layout-status_panel_pro .xinjian-status-note-table,
      .xinjian-turn-note.is-theme-layout-hud .xinjian-status-note-table { gap:.44rem; }
      .xinjian-turn-note.is-theme-layout-status_panel .xinjian-status-row,
      .xinjian-turn-note.is-theme-layout-status_panel_pro .xinjian-status-row,
      .xinjian-turn-note.is-theme-layout-hud .xinjian-status-row {
        grid-template-columns: 5.4rem minmax(0,1fr) 2rem;
        gap:.7rem;
        padding:.68rem .78rem;
        border-color: rgba(72,188,255,.14);
        background: linear-gradient(90deg, rgba(72,188,255,.10), rgba(15,36,66,.28));
      }
      .xinjian-turn-note.is-theme-layout-status_panel .xinjian-status-row em,
      .xinjian-turn-note.is-theme-layout-status_panel_pro .xinjian-status-row em,
      .xinjian-turn-note.is-theme-layout-hud .xinjian-status-row em { display:none; }
      .xinjian-turn-note.is-theme-layout-status_panel .xinjian-status-row span,
      .xinjian-turn-note.is-theme-layout-status_panel_pro .xinjian-status-row span,
      .xinjian-turn-note.is-theme-layout-hud .xinjian-status-row span { color:#82d8ff; font-size:.72rem; letter-spacing:.08em; font-weight:900; }
      .xinjian-turn-note.is-theme-layout-status_panel .xinjian-status-row strong,
      .xinjian-turn-note.is-theme-layout-status_panel_pro .xinjian-status-row strong,
      .xinjian-turn-note.is-theme-layout-hud .xinjian-status-row strong { color:#eaf8ff; font-size:.8rem; line-height:1.62; font-weight:560; }

      .xinjian-turn-note.is-theme-layout-storyboard .xinjian-note-section {
        background: rgba(0,0,0,.18);
        border-color: rgba(208,137,56,.22);
        padding: .8rem;
      }
      .xinjian-turn-note.is-theme-layout-storyboard .xinjian-note-section h4 {
        color:#d18a38;
        font-size:.84rem;
        letter-spacing:.12em;
        text-transform:uppercase;
        border-bottom: 1px solid rgba(208,137,56,.18);
        padding-bottom:.42rem;
      }
      .xinjian-turn-note.is-theme-layout-storyboard .xinjian-storyboard-row {
        grid-template-columns: 1.5rem 4.6rem minmax(0,1fr);
        padding:.62rem .65rem;
        background: rgba(255,255,255,.018);
      }
      .xinjian-turn-note.is-theme-layout-storyboard .xinjian-storyboard-row b { letter-spacing:.08em; }


      /* v0.7.6.2：外观包只改布局，不裁剪字段；三套角色状态视图差异化 */
      .xinjian-metric-strip { display:flex; flex-wrap:wrap; gap:.36rem; margin-bottom:.58rem; }
      .xinjian-metric-chip { display:inline-flex; align-items:center; gap:.34rem; border-radius:999px; padding:.28rem .52rem; font-size:.72rem; line-height:1.2; border:1px solid rgba(255,255,255,.12); background:rgba(255,255,255,.055); }
      .xinjian-metric-chip b { color:inherit; font-weight:900; }
      .xinjian-metric-chip i { font-style:normal; opacity:.82; }
      .xinjian-metric-diary { margin-top:.75rem; }
      .xinjian-metric-diary-list { display:grid; gap:.45rem; }
      .xinjian-metric-diary-row { border:1px solid rgba(201,130,99,.18); border-radius:14px; padding:.55rem .65rem; background:rgba(255,255,255,.045); }
      .xinjian-metric-diary-row strong { display:block; margin-bottom:.35rem; font-size:.85rem; }
      .xinjian-metric-diary-row p { margin:0; display:flex; flex-wrap:wrap; gap:.35rem; }
      .xinjian-metric-diary-row span { display:inline-flex; gap:.25rem; align-items:center; border-radius:999px; padding:.22rem .48rem; background:rgba(201,130,99,.08); border:1px solid rgba(201,130,99,.18); font-size:.74rem; }

      .xinjian-status-pro-shell { display:grid; gap:.72rem; }
      .xinjian-status-pro-layer { display:grid; gap:.5rem; }
      .xinjian-status-pro-card {
        border:1px solid rgba(82,196,255,.18); border-radius:.72rem; overflow:hidden;
        background:linear-gradient(135deg, rgba(82,196,255,.075), rgba(7,20,38,.34));
      }
      .xinjian-status-pro-card summary { list-style:none; cursor:pointer; display:grid; grid-template-columns:4.6rem minmax(0,1fr) 2.2rem; gap:.6rem; align-items:center; padding:.56rem .68rem; }
      .xinjian-status-pro-card summary::-webkit-details-marker { display:none; }
      .xinjian-status-pro-card summary span { color:#7bd8ff; font-size:.66rem; font-weight:950; letter-spacing:.14em; }
      .xinjian-status-pro-card summary b { color:#eaf8ff; font-size:.78rem; letter-spacing:.04em; }
      .xinjian-status-pro-card summary i { color:rgba(123,216,255,.56); font-style:normal; text-align:right; font-size:.72rem; }
      .xinjian-status-pro-grid { display:grid; gap:.44rem; padding:0 .62rem .62rem; }
      .xinjian-status-pro-row {
        display:grid; grid-template-columns: 4.8rem minmax(0,1fr) 2.2rem; gap:.72rem; align-items:start;
        padding:.56rem .68rem; border:1px solid rgba(82,196,255,.14); border-radius:.62rem;
        background: linear-gradient(90deg, rgba(82,196,255,.10), rgba(7,20,38,.34));
        box-shadow: inset 2px 0 0 rgba(82,196,255,.28);
      }
      .xinjian-status-pro-row span { color:#7bd8ff; font-size:.68rem; font-weight:950; letter-spacing:.13em; }
      .xinjian-status-pro-row strong { color:#eefaff; font-size:.82rem; line-height:1.62; font-weight:600; }
      .xinjian-status-pro-row i { color:rgba(123,216,255,.45); font-style:normal; text-align:right; font-size:.72rem; }
      .xinjian-status-pro-meters { display:grid; grid-template-columns: repeat(auto-fit, minmax(7.2rem,1fr)); gap:.5rem; }
      .xinjian-status-meter { padding:.5rem .58rem; border:1px solid rgba(82,196,255,.16); border-radius:.62rem; background:rgba(0,0,0,.20); }
      .xinjian-status-meter span { display:block; color:#7bd8ff; font-size:.64rem; font-weight:900; letter-spacing:.12em; margin-bottom:.32rem; }
      .xinjian-status-meter b { display:block; height:.38rem; border-radius:999px; overflow:hidden; background:rgba(255,255,255,.10); }
      .xinjian-status-meter b em { display:block; height:100%; border-radius:999px; background:linear-gradient(90deg,#42caff,#ffc36a); }
      .xinjian-status-meter i { display:flex; justify-content:flex-end; align-items:center; gap:.34rem; margin-top:.24rem; color:rgba(238,250,255,.78); font-style:normal; font-size:.7rem; }
      .xinjian-status-meter i small { color:#ffc36a; font-size:.68rem; }
      .xinjian-turn-note.is-theme-layout-status_panel .xinjian-status-note-table,
      .xinjian-turn-note.is-theme-layout-status_panel_pro .xinjian-status-note-table,
      .xinjian-turn-note.is-theme-layout-hud .xinjian-status-note-table { display:none; }

      .xinjian-paper-note-table.is-literary-note { display:grid; gap:.58rem; }
      .xinjian-paper-note-table.is-literary-note .xinjian-metric-strip { margin-bottom:.2rem; padding-bottom:.5rem; border-bottom:1px dashed rgba(166,115,68,.22); }
      .xinjian-paper-note-table.is-literary-note .xinjian-metric-chip { color:#8f4f27; background:rgba(255,248,232,.48); border-color:rgba(166,115,68,.22); }
      .xinjian-paper-note-table.is-literary-note .xinjian-paper-note-row {
        grid-template-columns: 4.8rem minmax(0,1fr);
        padding:.38rem 0 .68rem;
        border-bottom:1px dashed rgba(166,115,68,.20);
        background:transparent;
        border-radius:0;
      }
      .xinjian-paper-note-table.is-literary-note .xinjian-paper-note-row:last-child { border-bottom:0; }
      .xinjian-paper-note-table.is-literary-note .xinjian-paper-note-row i { display:none; }
      .xinjian-paper-note-table.is-literary-note .xinjian-paper-note-row span { color:#a45e30; font-size:.74rem; letter-spacing:.12em; }
      .xinjian-paper-note-table.is-literary-note .xinjian-paper-note-row strong { color:#2f251e; font-size:.9rem; line-height:1.9; font-weight:500; }

      .xinjian-storyboard-note-table.is-cut-sheet { border-radius:.7rem; display:grid; gap:.5rem; border:0; }
      .xinjian-storyboard-note-table.is-cut-sheet .xinjian-metric-strip { margin-bottom:.1rem; }
      .xinjian-storyboard-note-table.is-cut-sheet .xinjian-metric-chip { color:#d18a38; background:rgba(208,137,56,.08); border-color:rgba(208,137,56,.22); }
      .xinjian-storyboard-group { border:1px solid rgba(208,137,56,.18); border-radius:.72rem; overflow:hidden; background:rgba(0,0,0,.12); }
      .xinjian-storyboard-group-title { display:flex; align-items:center; gap:.46rem; padding:.42rem .66rem; border-bottom:1px solid rgba(208,137,56,.16); background:rgba(208,137,56,.08); }
      .xinjian-storyboard-group-title span { color:rgba(209,138,56,.75); font-size:.64rem; letter-spacing:.16em; font-weight:900; }
      .xinjian-storyboard-group-title b { color:#d18a38; font-size:.76rem; letter-spacing:.08em; }
      .xinjian-storyboard-note-table.is-cut-sheet .xinjian-storyboard-row {
        grid-template-columns: 1.4rem 4.8rem minmax(0,1fr);
        padding:.68rem .72rem;
        background:linear-gradient(90deg, rgba(208,137,56,.055), rgba(255,255,255,.014));
        border-bottom:1px solid rgba(208,137,56,.14);
      }
      .xinjian-storyboard-note-table.is-cut-sheet .xinjian-storyboard-row:last-child { border-bottom:0; }
      .xinjian-storyboard-note-table.is-cut-sheet .xinjian-storyboard-row em { color:#d18a38; font-style:normal; }
      .xinjian-storyboard-note-table.is-cut-sheet .xinjian-storyboard-row span { color:#d18a38; font-size:.76rem; letter-spacing:.14em; font-weight:900; }
      .xinjian-storyboard-note-table.is-cut-sheet .xinjian-storyboard-row strong { color:#f6ecd7; font-weight:520; line-height:1.72; }

      @keyframes xinjian-spin { to { transform: rotate(360deg); } }
      @media (max-width: 900px) { .xinjian-chat-bubble { left: 50%; top: 4.8rem; } }
    `;
    document.head.appendChild(style);
  }

  function ensureBubble() {
    ensureVisualStyle();
    let bubble = document.getElementById("xinjian-chat-bubble");
    if (bubble) return bubble;
    bubble = document.createElement("div");
    bubble.id = "xinjian-chat-bubble";
    bubble.className = "xinjian-chat-bubble";
    bubble.setAttribute("role", "status");
    bubble.setAttribute("aria-live", "polite");
    bubble.innerHTML = `
      <span class="xinjian-chat-bubble-mark" aria-hidden="true"></span>
      <span class="xinjian-chat-bubble-copy">
        <strong class="xinjian-chat-bubble-title"></strong>
        <span class="xinjian-chat-bubble-desc"></span>
      </span>
      <button type="button" class="xinjian-chat-bubble-close" aria-label="关闭心笺提示">×</button>
    `;
    bubble.querySelector(".xinjian-chat-bubble-close")?.addEventListener("click", (event) => {
      event.stopPropagation();
      hideBubble();
    });
    bubble.addEventListener("click", () => {
      if (bubble.classList.contains("is-error")) window.open("/mods/xinjian", "_blank");
    });
    document.body.appendChild(bubble);
    return bubble;
  }

  function hideBubble() {
    if (hideTimer) {
      clearTimeout(hideTimer);
      hideTimer = null;
    }
    const bubble = document.getElementById("xinjian-chat-bubble");
    if (bubble) bubble.classList.remove("is-visible");
  }

  function showBubble(kind, title, desc = "", timeout = 0) {
    if (configCache && configCache.notify_in_chat === false) return;
    const bubble = ensureBubble();
    if (hideTimer) {
      clearTimeout(hideTimer);
      hideTimer = null;
    }
    bubble.className = `xinjian-chat-bubble is-${kind}`;
    bubble.querySelector(".xinjian-chat-bubble-title").textContent = title;
    bubble.querySelector(".xinjian-chat-bubble-desc").textContent = desc;
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

  function bubbleWrapFor(message) {
    return message?.querySelector(".bubble-wrap") || message;
  }

  function stableTurnId(payload, fallback = "") {
    return String(payload?.turn_id || payload?.created_at || fallback || Date.now());
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
    node.dataset.xinjianTheme = pack?.id || "standard";
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

  let xinjianStaticRootCache = "";

  function xinjianStaticRoot() {
    if (xinjianStaticRootCache) return xinjianStaticRootCache;
    const scriptUrl = Array.from(document.scripts || [])
      .map((script) => script?.src || "")
      .find((src) => src.includes("/mods/xinjian/") && src.includes("xinjian-chat.js"));
    if (scriptUrl) {
      try {
        const url = new URL(scriptUrl, window.location.href);
        url.search = "";
        url.hash = "";
        url.pathname = url.pathname.replace(/[^/]*$/, "");
        xinjianStaticRootCache = url.toString();
      } catch (err) {
        xinjianStaticRootCache = "";
      }
    }
    if (!xinjianStaticRootCache) xinjianStaticRootCache = "/mods/xinjian/app/static/";
    return xinjianStaticRootCache;
  }

  function resolveThemeAssetUrl(value) {
    const raw = String(value || "").trim();
    if (!raw || ["none", "chat_background", "character_avatar", "film_placeholder"].includes(raw)) return "";
    if (/^(https?:)?\/\//i.test(raw) || raw.startsWith("data:")) return raw;
    let clean = raw.replace(/^\/+/, "");
    // Normalize them to the actual mounted static root, normally /mods/xinjian/app/static/.
    clean = clean.replace(/^mods\/xinjian\/app\/static\//, "");
    clean = clean.replace(/^mods\/xinjian\/static\//, "");
    if (clean.startsWith("static/assets/") || clean.startsWith("assets/")) {
      clean = clean.split("/").filter(Boolean).pop() || "";
    } else if (clean.startsWith("static/")) {
      clean = clean.slice("static/".length);
    }
    if (!clean) return "";
    try {
      return new URL(encodeURI(clean), xinjianStaticRoot()).toString();
    } catch (err) {
      return `${xinjianStaticRoot()}${encodeURIComponent(clean)}`;
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
    return `<div class="xinjian-metric-strip is-${escapeHtml(variant)}">${metrics.map((metric) => {
      const label = metric.name || metric.label;
      const text = variant === "paper" ? formatMetricPlain(metric, "本轮 ") : formatMetricPlain(metric);
      return `<span class="xinjian-metric-chip"><b>${escapeHtml(label)}</b><i>${escapeHtml(text)}</i></span>`;
    }).join("")}</div>`;
  }

  function renderMetricMeters(metrics = []) {
    if (!metrics.length) return "";
    return `<div class="xinjian-status-pro-meters">${metrics.map((metric) => {
      const max = Math.max(1, Number(metric.max || 100) || 100);
      const value = Math.max(0, Math.min(max, Number(metric.value) || 0));
      const width = Math.max(0, Math.min(100, (value / max) * 100));
      const delta = metricDeltaText(metric.delta, "hud");
      return `<div class="xinjian-status-meter"><span>${escapeHtml(metric.label || metric.name)}</span><b><em style="width:${width}%"></em></b><i>${escapeHtml(String(Math.round(value)))}${delta ? `<small>${escapeHtml(delta)}</small>` : ""}</i></div>`;
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

  function renderFieldRows(items = [], className = "xinjian-status-pro-row", options = {}) {
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
    card.className = "xinjian-inline-scene-card is-layout-paper-time";
    applyBeautyPack(card);
    card.dataset.xinjianScene = turnId;
    card.open = true;
    card.innerHTML = `
      <summary>
        <span class="xinjian-scene-kicker">${escapeHtml(themeLabel("scene_kicker", "SCENE / TIME"))}</span>
        <span class="xinjian-scene-title-line"><strong class="xinjian-scene-title">${seq ? `${escapeHtml(seq)} · ` : ""}《${escapeHtml(title)}》</strong><span class="xinjian-scene-toggle">收起</span></span>
        <span class="xinjian-scene-subtitle">${escapeHtml(subtitle)}</span>
      </summary>
      <div class="xinjian-scene-body">
        <div class="xinjian-scene-paper-rows"></div>
        <div class="xinjian-scene-event"></div>
      </div>
    `;
    card.addEventListener("toggle", () => {
      const toggle = card.querySelector(".xinjian-scene-toggle");
      if (toggle) toggle.textContent = card.open ? "收起" : "展开";
    });
    card.querySelector(".xinjian-scene-paper-rows").innerHTML = sceneRows(display)
      .map(([key, label, value]) => `<div class="xinjian-paper-time-row"><i>${escapeHtml(tokenForLabel(label, key))}</i><b>${escapeHtml(label)}</b><span>${escapeHtml(value)}</span></div>`)
      .join("");
    card.querySelector(".xinjian-scene-event").textContent = scene.event_summary || subtitle || "心笺已生成本轮幕题。";
    return card;
  }

  function buildStatusPanelSceneCard(display, turnId = "") {
    const scene = display?.scene || {};
    const title = display?.title || scene.title || "本轮幕笺";
    const subtitle = display?.subtitle || scene.event_summary || scene.atmosphere || "";
    const seq = display?.sequence_label || scene.sequence_label || "";
    const card = document.createElement("details");
    card.className = "xinjian-inline-scene-card is-layout-status-panel";
    applyBeautyPack(card);
    card.dataset.xinjianScene = turnId;
    card.open = true;
    card.innerHTML = `
      <summary>
        <span class="xinjian-scene-kicker">${escapeHtml(themeLabel("scene_kicker", "STATUS PANEL · TIME"))}</span>
        <span class="xinjian-scene-title-line"><strong class="xinjian-scene-title">${seq ? `${escapeHtml(seq)} · ` : ""}《${escapeHtml(title)}》</strong><span class="xinjian-scene-toggle">收起</span></span>
        <span class="xinjian-scene-subtitle">${escapeHtml(subtitle)}</span>
      </summary>
      <div class="xinjian-scene-body">
        <div class="xinjian-status-scene-hud"></div>
        <div class="xinjian-status-timeline"><b>${escapeHtml(seq || "TIME")}</b><span>SYNC</span></div>
      </div>
    `;
    card.addEventListener("toggle", () => {
      const toggle = card.querySelector(".xinjian-scene-toggle");
      if (toggle) toggle.textContent = card.open ? "收起" : "展开";
    });
    card.querySelector(".xinjian-status-scene-hud").innerHTML = sceneRows(display)
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
      ? `<div class="xinjian-storyboard-frame has-image"><img src="${escapeHtml(imageUrl)}" alt="心笺分镜图" loading="lazy" data-xj-frame-image="1"></div>`
      : `<div class="xinjian-storyboard-frame"><span>${escapeHtml(placeholder)}</span><small>NO IMAGE / SAFE PLACEHOLDER</small></div>`;
    const card = document.createElement("details");
    card.className = "xinjian-inline-scene-card is-layout-storyboard";
    applyBeautyPack(card);
    card.dataset.xinjianScene = turnId;
    card.open = true;
    card.innerHTML = `
      <summary>
        <span class="xinjian-scene-kicker">${escapeHtml(themeLabel("scene_kicker", "SCENE"))} ${escapeHtml(seq || "")}</span>
        <span class="xinjian-scene-title-line"><strong class="xinjian-scene-title">《${escapeHtml(title)}》</strong><span class="xinjian-scene-toggle">收起</span></span>
        <span class="xinjian-scene-subtitle">${escapeHtml(subtitle)}</span>
      </summary>
      <div class="xinjian-scene-body xinjian-storyboard-hero">
        <div class="xinjian-storyboard-meta"></div>
        ${frameHtml}
        <div class="xinjian-scene-event"></div>
      </div>
    `;
    card.addEventListener("toggle", () => {
      const toggle = card.querySelector(".xinjian-scene-toggle");
      if (toggle) toggle.textContent = card.open ? "收起" : "展开";
    });
    const frameImg = card.querySelector("[data-xj-frame-image]");
    if (frameImg) {
      frameImg.addEventListener("error", () => {
        const frame = frameImg.closest(".xinjian-storyboard-frame");
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
    card.querySelector(".xinjian-storyboard-meta").innerHTML = meta.map(([label, value]) => `<p><b>${escapeHtml(label)}：</b>${escapeHtml(value)}</p>`).join("");
    card.querySelector(".xinjian-scene-event").textContent = scene.event_summary || subtitle || "心笺已生成本轮幕题。";
    return card;
  }

  function buildTimeSceneCard(display, turnId = "") {
    const scene = display?.scene || {};
    const title = display?.title || scene.title || "本轮幕笺";
    const subtitle = display?.subtitle || scene.subtitle || scene.atmosphere || "";
    const seq = display?.sequence_label || scene.sequence_label || "";
    const card = document.createElement("details");
    card.className = "xinjian-inline-scene-card is-layout-time-card";
    applyBeautyPack(card);
    card.dataset.xinjianScene = turnId;
    card.open = true;
    card.innerHTML = `
      <summary>
        <span class="xinjian-scene-kicker">Time</span>
        <span class="xinjian-scene-title-line"><strong class="xinjian-scene-title">${seq ? `${escapeHtml(seq)} · ` : ""}《${escapeHtml(title)}》</strong><span class="xinjian-scene-toggle">收起</span></span>
        <span class="xinjian-scene-subtitle">${escapeHtml(subtitle)}</span>
      </summary>
      <div class="xinjian-scene-body">
        <div class="xinjian-scene-meta"></div>
        <div class="xinjian-scene-event"></div>
      </div>
    `;
    card.addEventListener("toggle", () => {
      const toggle = card.querySelector(".xinjian-scene-toggle");
      if (toggle) toggle.textContent = card.open ? "收起" : "展开";
    });
    const rows = [
      ["time", "时间", scene.time || "时间未明"],
      ["location", "地点", scene.location || "地点未明"],
      ["weather", "天气", scene.weather || ""],
      ["atmosphere", "氛围", scene.atmosphere || ""],
      ["characters", "人物", scene.characters || ""],
    ].filter((row) => row[2]);
    card.querySelector(".xinjian-scene-meta").innerHTML = rows.map(([key, label, value]) => `<span class="xinjian-scene-chip"><i>${escapeHtml(tokenForLabel(label, key))}</i><b>${escapeHtml(label)}：</b><span>${escapeHtml(value)}</span></span>`).join("");
    card.querySelector(".xinjian-scene-event").textContent = scene.event_summary || subtitle || "心笺已生成本轮幕题。";
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
    card.className = "xinjian-inline-scene-card";
    applyBeautyPack(card);
    card.dataset.xinjianScene = turnId;
    card.innerHTML = `
      <summary>
        <span class="xinjian-scene-kicker">XINJIAN · 幕题${seq ? ` · ${escapeHtml(seq)}` : ""}</span>
        <span class="xinjian-scene-title-line"><strong class="xinjian-scene-title">${seq ? `${escapeHtml(seq)} · ` : ""}《${escapeHtml(title)}》</strong><span class="xinjian-scene-toggle">展开</span></span>
        <span class="xinjian-scene-subtitle">${escapeHtml(subtitle)}</span>
      </summary>
      <div class="xinjian-scene-body">
        <div class="xinjian-scene-meta"></div>
        <div class="xinjian-scene-event"></div>
      </div>
    `;
    card.addEventListener("toggle", () => {
      const toggle = card.querySelector(".xinjian-scene-toggle");
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
    card.querySelector(".xinjian-scene-meta").innerHTML = metaItems.map((item) => `<span class="xinjian-scene-chip">${escapeHtml(item)}</span>`).join("");
    card.querySelector(".xinjian-scene-event").textContent = scene.event_summary || subtitle || "心笺已生成本轮幕题。";
    return card;
  }

  function attachSceneCard(display, targetMessage, turnId = "") {
    if (!configCache?.mujian_enabled || !configCache?.mujian_title_card || !display || !targetMessage) return;
    const wrap = bubbleWrapFor(targetMessage);
    const key = stableTurnId(display, turnId);
    const old = wrap.querySelector(`.xinjian-inline-scene-card[data-xinjian-scene="${CSS.escape(key)}"]`);
    if (old) old.remove();
    const card = buildSceneCard(display, key);
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
      <div class="xinjian-status-pro-shell">
        ${renderMetricMeters(metrics)}
        <div class="xinjian-status-pro-layer">
          ${groups.map((group, idx) => `<details class="xinjian-status-pro-card" ${idx === 0 ? "open" : ""}>
            <summary><span>${escapeHtml(group.code || group.title)}</span><b>${escapeHtml(group.title)}</b><i>${group.items.length}</i></summary>
            <div class="xinjian-status-pro-grid">${renderFieldRows(group.items, "xinjian-status-pro-row", { count: true })}</div>
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
    return `<div class="xinjian-storyboard-note-table is-cut-sheet">
      ${renderMetricText(metrics, "storyboard")}
      ${groups.map((group) => `<div class="xinjian-storyboard-group"><div class="xinjian-storyboard-group-title"><span>${escapeHtml(group.code || group.title)}</span><b>【${escapeHtml(group.title)}】</b></div>${renderFieldRows(group.items, "xinjian-storyboard-row", { icon: true })}</div>`).join("")}
    </div>`;
  }

  function renderPaperTimeFields(list) {
    const { metrics, fields } = splitMetricFields(list);
    return `<div class="xinjian-paper-note-table is-literary-note">
      ${renderMetricText(metrics, "paper")}
      ${fields.map(([label, value, key]) => `<div class="xinjian-paper-note-row"><i>${escapeHtml(tokenForLabel(label, key))}</i><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}
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
      rows.push(`<div class="xinjian-metric-diary-row"><strong>${escapeHtml(character?.name || "角色")}</strong><p>${chips}</p></div>`);
    });
    if (!rows.length) return "";
    return `<section class="xinjian-note-section xinjian-metric-diary"><h4>本轮数值变化</h4><div class="xinjian-metric-diary-list">${rows.join("")}</div></section>`;
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
    return `<div class="xinjian-note-grid">${list.map(([label, value, key]) => `<div class="xinjian-note-field">${useIcon ? `<em class="xinjian-note-icon">${escapeHtml(tokenForLabel(label, key))}</em>` : ""}<span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join("")}</div>`;
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
    note.className = `xinjian-turn-note-compact is-layout-${safeLayoutClass(activeThemeLayout().status_bar || "compact")}`;
    applyBeautyPack(note);
    note.dataset.xinjianTurn = stableTurnId(display, turnId);
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
    note.className = `xinjian-turn-note is-note-${noteStyle} is-mode-${mode} is-layout-${safeLayoutClass(layout.character_card || layoutType || "field_blocks")} is-theme-layout-${layoutType}`;
    applyBeautyPack(note);
    note.dataset.xinjianTurn = stableTurnId(display, turnId);
    if (mode === "expanded") note.open = true;
    const allCharacters = Array.isArray(display.characters) ? display.characters : [];
    const characters = filterCharacters(allCharacters);
    const relationships = Array.isArray(display.relationships) ? display.relationships : [];
    const changed = payload?.summary?.by_table?.map((item) => `${item.name || item.table} +${item.count || 0}`).join("｜") || "本轮幕笺已生成";
    const densityLabel = { compact: "简洁", standard: "标准", detailed: "详细" }[configCache?.mujian_note_density || "standard"] || "标准";
    const filterLabel = { turn: "本轮生成", heroine: "双女主", protagonist: "主角相关", custom: "自定义", all: "全部" }[configCache?.mujian_character_filter || "turn"] || "本轮生成";
    const noteStyleLabel = { classic: "经典状态", gufeng: "古风旁白", sensory: "感官标签" }[noteStyle] || "经典状态";
    note.innerHTML = `
      <summary>
        <span class="xinjian-turn-summary-main"><span class="xinjian-note-dot"></span><span>心笺有新记 · ${escapeHtml(changed)}</span></span>
        <span>${characters.length ? `${characters.length} 人物` : "展开"}</span>
      </summary>
      <div class="xinjian-note-body">
        <div class="xinjian-note-toolbar"><span>附笺：${escapeHtml(noteStyleLabel)}</span><span>显示：${escapeHtml(filterLabel)}</span><span>密度：${escapeHtml(densityLabel)}</span></div>
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
          <section class="xinjian-note-section xinjian-note-section-${safeLayoutClass(layoutType)}">
            <h4>${escapeHtml(sectionTitle)}</h4>
            ${(() => {
              const templateFields = parseTemplateRenderedFields(renderedTemplate);
              const baseFields = characterFields(character, display);
              const safeFields = mergeRenderedAndTemplateFields(templateFields, baseFields);
              const html = renderNoteFields(safeFields);
              return html || `<pre class="xinjian-note-template-output">${escapeHtml(renderedTemplate)}</pre>`;
            })()}
          </section>`;
        }).join("") : `<div class="xinjian-note-empty">当前显示范围下没有可展示角色。可以在心笺设置里切换为“全部角色”或“自定义名单”。</div>`}
        ${renderTurnMetricSummary(characters, display)}
        ${relationships.length ? `<section class="xinjian-note-section xinjian-note-section-${safeLayoutClass(layoutType)}"><h4>${escapeHtml(["storyboard", "storyboard_frame", "scene_board"].includes(layoutType) ? "导演注 / 关系推进" : ["status_panel", "status_panel_pro", "hud"].includes(layoutType) ? "RELATION LOG" : ["paper_time", "paper_time_card"].includes(layoutType) ? "情节旁注" : "关系变化")}</h4><div class="xinjian-relation-list">${relationships.map((item) => `<div><strong>${escapeHtml(item.pair || "关系")}</strong>${item.stage ? ` · ${escapeHtml(item.stage)}` : ""}<br>${escapeHtml(item.change || "")}</div>`).join("")}</div></section>` : ""}
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
    const wrap = bubbleWrapFor(msg);
    const key = stableTurnId(display, turnId);
    const old = wrap.querySelector(`.xinjian-turn-note[data-xinjian-turn="${CSS.escape(key)}"], .xinjian-turn-note-compact[data-xinjian-turn="${CSS.escape(key)}"]`);
    if (old) old.remove();
    const note = mode === "compact" ? buildCompactTurnNote(display, payload, key) : buildTurnNote(display, payload, key);
    wrap.appendChild(note);
  }

  function renderTurnDisplay(display, targetMessage, payload = {}) {
    if (!display || !targetMessage) return;
    const turnId = stableTurnId(display, payload?.turn_id || payload?.created_at || "");
    targetMessage.dataset.xinjianTurn = turnId;
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
    const userText = String(detail.userText || "").trim();
    if (!userText) return null;
    const turnId = String(detail.turnId || makeTurnId(userText));
    const source = String(detail.source || "send");
    pendingTurn = {
      turnId,
      userText,
      userHash: simpleHash(userText),
      createdAt: detail.createdAt || new Date().toISOString(),
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
      console.warn("Xinjian turn start failed:", error);
    }
    return pendingTurn;
  }

  async function invalidateTrackedTurn(detail = {}) {
    const turnId = detail.turnId || detail.fromTurnId || "";
    const reason = detail.reason || detail.type || "history_changed";
    if (reason === "reroll" || reason === "edit_user" || reason === "edit") {
      showBubble("pending", "心笺已标记本轮重算", "正在等待新回复完成……");
    } else {
      showBubble("pending", "心笺已标记记录过期", "等待后续重建或重新生成……");
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
      console.warn("Xinjian turn invalidate failed:", error);
    }
  }

  async function pingHook(event = "loaded", message = "聊天页心笺脚本已加载。", turnId = "") {
    try {
      await requestJson(new URL("hook/ping", apiBase).toString(), {
        method: "POST",
        body: JSON.stringify({ event, message, page: "chat", turn_id: turnId }),
      });
    } catch (error) {
      console.warn("Xinjian hook ping failed:", error);
    }
  }

  async function loadConfig() {
    const payload = await requestJson(new URL("config", apiBase).toString());
    configCache = payload.config || {};
    return configCache;
  }

  async function restoreRecentDisplays() {
    try {
      const payload = await requestJson(new URL("display/recent?limit=40", apiBase).toString());
      const displays = Array.isArray(payload.turns) ? payload.turns : [];
      if (!displays.length) return;
      const messages = assistantMessages();
      if (!messages.length) return;
      const unused = new Set(messages);
      let restored = 0;
      displays.forEach((display) => {
        const turnId = String(display.turn_id || "");
        const matched = turnId ? messages.find((msg) => msg.dataset.xinjianTurn === turnId) : null;
        if (matched) {
          renderTurnDisplay(display, matched, { turn_id: turnId, created_at: display.created_at });
          unused.delete(matched);
          restored += 1;
        }
      });
      const remainingDisplays = displays.filter((display) => !messages.some((msg) => msg.dataset.xinjianTurn === String(display.turn_id || "")));
      const fallbackMessages = [...unused];
      const start = Math.max(0, fallbackMessages.length - remainingDisplays.length);
      remainingDisplays.slice(-fallbackMessages.length).forEach((display, index) => {
        const msg = fallbackMessages[start + index];
        if (!msg) return;
        renderTurnDisplay(display, msg, { turn_id: display.turn_id, created_at: display.created_at });
        restored += 1;
      });
      pingHook("restore_display", `已恢复 ${restored} 条幕笺。`);
    } catch (error) {
      console.warn("Xinjian recent display restore failed:", error);
    }
  }

  function turnSignature(detail) {
    const turnId = String(detail?.turnId || "");
    const userText = String(detail?.userText || "").slice(0, 240);
    const assistantText = String(detail?.assistantText || "").slice(0, 240);
    return turnId ? `${turnId}::${simpleHash(userText)}::${simpleHash(assistantText)}` : `${userText}\n---\n${assistantText}`;
  }

  async function updateFromTurn(detail) {
    const config = await loadConfig();
    if (!config.enabled || !config.auto_update) return;
    const userText = String(detail?.userText || "").trim();
    const assistantText = String(detail?.assistantText || "").trim();
    if (!userText && !assistantText) return;
    const signature = turnSignature(detail);
    if (processedTurns.has(signature) || inFlight) return;
    processedTurns.add(signature);
    inFlight = true;
    const targetMessage = findLatestAssistantMessage();
    const matchedPending = pendingTurn && pendingTurn.userText === userText ? pendingTurn : null;
    const isRebuild = ["reroll", "edit"].includes(String(detail?.source || matchedPending?.source || ""));
    showBubble("pending", isRebuild ? "心笺正在重新填表……" : (config.mujian_enabled ? "心笺正在生成幕笺……" : "心笺正在填表……"), isRebuild ? "正在替换本轮幕笺与状态影响" : (config.mujian_enabled ? "正在整理本轮标题、场景与角色状态" : "正在整理本轮角色状态与关系"));
    pingHook(isRebuild ? "auto_rebuild_start" : "auto_update_start", isRebuild ? "心笺重算已触发。" : "自动填表与幕笺生成已触发。", detail?.turnId || "");
    try {
      const history = await fetch("/api/history").then((res) => res.json()).catch(() => []);
      const turnId = String(detail?.turnId || matchedPending?.turnId || makeTurnId(userText));
      const createdAt = String(detail?.createdAt || matchedPending?.createdAt || new Date().toISOString());
      await requestJson(new URL("turn/complete", apiBase).toString(), {
        method: "POST",
        body: JSON.stringify({ turn_id: turnId, user_text: userText, assistant_text: assistantText, created_at: createdAt }),
      }).catch((error) => console.warn("Xinjian turn complete failed:", error));
      const payload = await requestJson(new URL("worker/update", apiBase).toString(), {
        method: "POST",
        body: JSON.stringify({
          latest_turn: { user: userText, assistant: assistantText },
          history,
          turn_id: turnId,
          created_at: createdAt,
          user_hash: simpleHash(userText),
          assistant_hash: simpleHash(assistantText),
          event_type: isRebuild ? "rebuild" : "auto_update",
          source: detail?.source || matchedPending?.source || "send",
        }),
      });
      const errors = payload.result?.errors || [];
      const count = payload.summary?.total ?? payload.result?.applied?.length ?? 0;
      if (payload.display && targetMessage) {
        renderTurnDisplay(payload.display, targetMessage, { ...payload, turn_id: payload.display.turn_id || turnId, created_at: turnId });
      }
      if (payload.skipped) {
        showBubble("empty", "心笺未运行", payload.message || payload.reason || "已跳过本轮更新", 2800);
      } else if (errors.length || payload.ok === false || payload.status === "error") {
        showBubble("error", "心笺生成失败", `${payload.message || errors[0] || "辅助模型返回异常"}，点击查看日志`, 9000);
      } else if (count) {
        showBubble("success", isRebuild ? "心笺已重算" : (payload.display ? "心笺已生成幕笺" : "心笺已更新"), isRebuild ? "本轮幕笺已替换｜" + formatSummary(payload) : formatSummary(payload), 3600);
      } else {
        showBubble("empty", payload.display ? "幕笺已生成" : "心笺无变化", payload.message || "本轮没有需要写入的状态", 3000);
      }
      pingHook(payload.ok === false || payload.status === "error" ? "auto_update_error" : (isRebuild ? "auto_rebuild_done" : "auto_update_done"), payload.message || "自动填表与幕笺生成已完成。 ", turnId);
      if (pendingTurn?.turnId === turnId) pendingTurn = null;
      window.dispatchEvent(new CustomEvent("xinjian:updated", { detail: payload }));
    } catch (error) {
      showBubble("error", "心笺生成失败", `${error.message || "未知错误"}，点击查看日志`, 9000);
      pingHook("auto_update_error", error.message || "自动填表失败。 ");
      console.warn("Xinjian auto update failed:", error);
    } finally {
      inFlight = false;
    }
  }

  window.addEventListener("fantareal:chat-user-submit", (event) => startTrackedTurn(event.detail || {}));
  window.addEventListener("fantareal:chat-done", (event) => updateFromTurn(event.detail || {}));
  window.addEventListener("fantareal:chat-reroll", (event) => invalidateTrackedTurn({ ...(event.detail || {}), reason: "reroll" }));
  window.addEventListener("fantareal:chat-edit", (event) => invalidateTrackedTurn({ ...(event.detail || {}), reason: "edit_user" }));
  window.addEventListener("fantareal:chat-delete", (event) => invalidateTrackedTurn({ ...(event.detail || {}), reason: "delete_history" }));

  window.xinjianChatBridge = {
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
    .catch((error) => console.warn("Xinjian config/display load failed:", error));
})();
