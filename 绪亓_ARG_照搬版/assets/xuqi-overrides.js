(function () {
  const path = decodeURIComponent(location.pathname).toLowerCase();
  const title = document.title || "绪亓的浅蓝日记";

  const route = (() => {
    if (/eye|ear|ftcy|fxgx|dztx|20152|20153|20154/.test(path)) {
      return {
        stage: "C",
        mood: "污染层",
        className: "xuqi-stage-flesh",
        status: "旁观",
        contam: 86
      };
    }
    if (/hospital|login|history/.test(path)) {
      return {
        stage: "B",
        mood: "档案层",
        className: "xuqi-stage-gray",
        status: "查询",
        contam: 42
      };
    }
    if (/404|ota/.test(path)) {
      return {
        stage: "D",
        mood: "断链层",
        className: "xuqi-stage-terminal",
        status: "回声",
        contam: 72
      };
    }
    return {
      stage: "A",
      mood: "浅蓝层",
      className: "xuqi-stage-blue",
      status: "记忆",
      contam: 18
    };
  })();

  document.body.classList.add(route.className);
  document.body.classList.add("xuqi-fantareal");
  document.documentElement.style.setProperty("--xuqi-contam", route.contam + "%");

  const runtimeStyle = document.createElement("style");
  runtimeStyle.id = "xuqi-fantareal-runtime";
  runtimeStyle.textContent = `
    body.xuqi-fantareal {
      --fr-bg: #f3efe7;
      --fr-panel: rgba(255, 250, 244, .82);
      --fr-panel-strong: rgba(255, 250, 244, .94);
      --fr-line: rgba(99, 73, 56, .16);
      --fr-text: #2d1f18;
      --fr-muted: #8a7361;
      --fr-accent: #c8673b;
      --fr-accent-dark: #a84f28;
      width: auto !important;
      min-width: 0 !important;
      max-width: none !important;
      margin: 0 !important;
      padding: clamp(14px, 2vw, 28px) !important;
      color: var(--fr-text) !important;
      background:
        radial-gradient(circle at 9% 8%, rgba(208, 125, 90, .22), transparent 26rem),
        radial-gradient(circle at 92% 82%, rgba(233, 184, 110, .18), transparent 28rem),
        linear-gradient(135deg, var(--fr-bg), #fbf7ef 48%, #efe8dc) !important;
      font-family: "Microsoft YaHei", "PingFang SC", system-ui, sans-serif !important;
    }

    body.xuqi-fantareal::after,
    body.xuqi-fantareal .xuqi-rail,
    body.xuqi-fantareal .xuqi-waterline,
    body.xuqi-fantareal .xuqi-drift,
    body.xuqi-fantareal .xuqi-meter,
    body.xuqi-fantareal .xuqi-mark,
    body.xuqi-fantareal .sticker,
    body.xuqi-fantareal a[href*="glitter-graphics"],
    body.xuqi-fantareal img[src*="glitter-graphics"] {
      display: none !important;
    }

    body.xuqi-fantareal > .container,
    body.xuqi-fantareal > .main-container,
    body.xuqi-fantareal .main-content,
    body.xuqi-fantareal .page-header-content,
    body.xuqi-fantareal .header-content,
    body.xuqi-fantareal .navbar-content {
      width: min(1120px, calc(100vw - 28px)) !important;
      max-width: 1120px !important;
      margin-left: auto !important;
      margin-right: auto !important;
    }

    body.xuqi-fantareal > .container,
    body.xuqi-fantareal > .main-container,
    body.xuqi-fantareal .content,
    body.xuqi-fantareal .main-content {
      background: transparent !important;
      border: 0 !important;
      box-shadow: none !important;
    }

    body.xuqi-fantareal header,
    body.xuqi-fantareal .header,
    body.xuqi-fantareal .navbar,
    body.xuqi-fantareal .wayback-nav,
    body.xuqi-fantareal .nav,
    body.xuqi-fantareal .page-header {
      color: var(--fr-text) !important;
      background:
        radial-gradient(circle at 18% 22%, rgba(255,255,255,.52), transparent 42%),
        linear-gradient(135deg, rgba(255,250,244,.88), rgba(247,234,217,.72)) !important;
      border: 1px solid rgba(190, 152, 121, .25) !important;
      border-radius: 22px !important;
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,.55),
        0 20px 58px rgba(89,58,37,.12) !important;
      backdrop-filter: blur(18px) saturate(1.06);
    }

    body.xuqi-fantareal header,
    body.xuqi-fantareal .navbar {
      margin: 0 auto 18px !important;
      width: min(1120px, calc(100vw - 28px)) !important;
    }

    body.xuqi-fantareal .page-header {
      margin: 0 auto 22px !important;
      width: min(1120px, calc(100vw - 28px)) !important;
      padding: clamp(22px, 4vw, 46px) !important;
    }

    body.xuqi-fantareal .hero {
      width: min(1120px, calc(100vw - 28px)) !important;
      margin: 0 auto 22px !important;
      padding: clamp(34px, 6vw, 76px) clamp(18px, 4vw, 48px) !important;
      color: var(--fr-text) !important;
      background:
        radial-gradient(circle at 16% 18%, rgba(255,255,255,.36), transparent 34%),
        linear-gradient(135deg, rgba(255,250,244,.86), rgba(247,234,217,.72)) !important;
      border: 1px solid rgba(190,152,121,.25) !important;
      border-radius: 26px !important;
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,.55),
        0 24px 64px rgba(89,58,37,.12) !important;
      backdrop-filter: blur(18px) saturate(1.06);
    }

    body.xuqi-fantareal .hero h1,
    body.xuqi-fantareal .hero p {
      color: var(--fr-text) !important;
      opacity: 1 !important;
    }

    body.xuqi-fantareal .search-container,
    body.xuqi-fantareal .info-section {
      background:
        radial-gradient(circle at 18% 16%, rgba(255,255,255,.45), transparent 40%),
        rgba(255,250,244,.82) !important;
      border: 1px solid rgba(99,73,56,.16) !important;
      border-radius: 20px !important;
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,.56),
        0 20px 56px rgba(89,58,37,.12) !important;
      backdrop-filter: blur(16px) saturate(1.05);
    }

    body.xuqi-fantareal .blog-title,
    body.xuqi-fantareal .logo,
    body.xuqi-fantareal .hospital-name,
    body.xuqi-fantareal h1,
    body.xuqi-fantareal h2,
    body.xuqi-fantareal h3,
    body.xuqi-fantareal .post-title,
    body.xuqi-fantareal .question-title {
      color: var(--fr-text) !important;
      text-shadow: none !important;
      letter-spacing: 0 !important;
      font-family: "Microsoft YaHei", "PingFang SC", system-ui, sans-serif !important;
    }

    body.xuqi-fantareal .nav a,
    body.xuqi-fantareal nav a,
    body.xuqi-fantareal .nav-links a,
    body.xuqi-fantareal .wayback-years a,
    body.xuqi-fantareal .footer a {
      min-height: 32px;
      padding: 7px 12px !important;
      border-radius: 14px !important;
      color: var(--fr-muted) !important;
      background: rgba(255,250,244,.58) !important;
      border: 1px solid rgba(99,73,56,.12) !important;
      box-shadow: none !important;
      text-shadow: none !important;
      text-decoration: none !important;
    }

    body.xuqi-fantareal .nav a:hover,
    body.xuqi-fantareal nav a:hover,
    body.xuqi-fantareal .nav-links a:hover,
    body.xuqi-fantareal .wayback-years a:hover,
    body.xuqi-fantareal .wayback-years a.active,
    body.xuqi-fantareal .footer a:hover {
      color: var(--fr-accent-dark) !important;
      background: rgba(255,250,244,.9) !important;
      border-color: rgba(200,103,59,.24) !important;
    }

    body.xuqi-fantareal .xuqi-frag,
    body.xuqi-fantareal .post,
    body.xuqi-fantareal .reply,
    body.xuqi-fantareal .question,
    body.xuqi-fantareal .answer,
    body.xuqi-fantareal .record-item,
    body.xuqi-fantareal .record-detail,
    body.xuqi-fantareal .archive-info,
    body.xuqi-fantareal .timeline-container,
    body.xuqi-fantareal .sidebar,
    body.xuqi-fantareal .sidebar-widget,
    body.xuqi-fantareal .reply-box,
    body.xuqi-fantareal .campus-option,
    body.xuqi-fantareal .stat-card,
    body.xuqi-fantareal .login-box,
    body.xuqi-fantareal .guestbook,
    body.xuqi-fantareal .comment-form,
    body.xuqi-fantareal .letters-section,
    body.xuqi-fantareal .diary-section {
      background:
        radial-gradient(circle at 18% 16%, rgba(255,255,255,.45), transparent 40%),
        rgba(255,250,244,.82) !important;
      color: var(--fr-text) !important;
      border: 1px solid rgba(99,73,56,.16) !important;
      border-radius: 20px !important;
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,.56),
        0 20px 56px rgba(89,58,37,.12) !important;
      backdrop-filter: blur(16px) saturate(1.05);
    }

    body.xuqi-fantareal.xuqi-fragment-board .xuqi-frag {
      position: relative;
      width: min(760px, 94%) !important;
      margin-top: 18px !important;
      margin-bottom: 22px !important;
      padding: clamp(15px, 2vw, 24px) !important;
    }

    body.xuqi-fantareal.xuqi-fragment-board .xuqi-f1 { margin-left: clamp(0px, 3vw, 42px) !important; margin-right: auto !important; transform: rotate(-.25deg); }
    body.xuqi-fantareal.xuqi-fragment-board .xuqi-f2 { margin-left: auto !important; margin-right: clamp(0px, 5vw, 72px) !important; transform: rotate(.18deg); }
    body.xuqi-fantareal.xuqi-fragment-board .xuqi-f3 { width: min(620px, 88%) !important; margin-left: clamp(34px, 11vw, 150px) !important; margin-right: auto !important; }
    body.xuqi-fantareal.xuqi-fragment-board .xuqi-f4 { width: min(820px, 96%) !important; margin-left: auto !important; margin-right: clamp(22px, 8vw, 120px) !important; }
    body.xuqi-fantareal.xuqi-fragment-board .xuqi-f5 { width: min(540px, 84%) !important; margin-left: clamp(0px, 17vw, 230px) !important; margin-right: auto !important; transform: rotate(-.12deg); }

    body.xuqi-fantareal .post::before,
    body.xuqi-fantareal .reply::before,
    body.xuqi-fantareal .question::before,
    body.xuqi-fantareal .answer::before,
    body.xuqi-fantareal .record-item::before {
      color: var(--fr-accent-dark) !important;
      opacity: .72;
    }

    body.xuqi-fantareal button,
    body.xuqi-fantareal .btn,
    body.xuqi-fantareal .submit-btn,
    body.xuqi-fantareal #searchBtn,
    body.xuqi-fantareal .wayback-next,
    body.xuqi-fantareal input[type="button"],
    body.xuqi-fantareal input[type="submit"] {
      min-height: 38px;
      padding: 8px 14px !important;
      border-radius: 14px !important;
      border: 1px solid rgba(99,73,56,.16) !important;
      background: rgba(255,250,244,.86) !important;
      color: var(--fr-text) !important;
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,.56),
        0 12px 26px rgba(89,58,37,.10) !important;
      text-shadow: none !important;
      font-weight: 700 !important;
    }

    body.xuqi-fantareal input[type="text"],
    body.xuqi-fantareal input[type="password"],
    body.xuqi-fantareal input[type="search"],
    body.xuqi-fantareal textarea,
    body.xuqi-fantareal select {
      border-radius: 14px !important;
      border: 1px solid rgba(99,73,56,.16) !important;
      background: rgba(255,255,255,.68) !important;
      color: var(--fr-text) !important;
      box-shadow: inset 0 1px 0 rgba(255,255,255,.58) !important;
      outline: none !important;
    }

    body.xuqi-fantareal table,
    body.xuqi-fantareal .archive-table {
      border-collapse: separate !important;
      border-spacing: 0 !important;
      border-radius: 18px !important;
      overflow: hidden;
      background: rgba(255,250,244,.82) !important;
      border: 1px solid rgba(99,73,56,.16) !important;
    }

    body.xuqi-fantareal th {
      background: rgba(247,234,217,.86) !important;
      color: var(--fr-text) !important;
    }

    body.xuqi-fantareal td {
      border-color: rgba(99,73,56,.12) !important;
    }

    body.xuqi-fantareal img,
    body.xuqi-fantareal .local-image,
    body.xuqi-fantareal .center-image {
      border-radius: 16px;
      filter: saturate(.84) contrast(.96) sepia(.08) !important;
    }

    body.xuqi-fantareal.xuqi-stage-flesh,
    body.xuqi-fantareal.xuqi-stage-terminal {
      --fr-bg: #16080a;
      --fr-panel: rgba(34, 13, 15, .78);
      --fr-panel-strong: rgba(41, 15, 18, .9);
      --fr-line: rgba(211, 77, 80, .24);
      --fr-text: #ffece6;
      --fr-muted: #d7aaa2;
      --fr-accent: #e25d57;
      --fr-accent-dark: #ff8a78;
      background:
        radial-gradient(circle at 21% 18%, rgba(169, 28, 42, .34), transparent 24rem),
        radial-gradient(circle at 82% 76%, rgba(200, 103, 59, .16), transparent 24rem),
        linear-gradient(135deg, #120607, #261012 52%, #0c0304) !important;
    }

    body.xuqi-fantareal.xuqi-stage-flesh .xuqi-frag,
    body.xuqi-fantareal.xuqi-stage-flesh .post,
    body.xuqi-fantareal.xuqi-stage-flesh .reply,
    body.xuqi-fantareal.xuqi-stage-flesh .question,
    body.xuqi-fantareal.xuqi-stage-flesh .answer,
    body.xuqi-fantareal.xuqi-stage-terminal .xuqi-frag,
    body.xuqi-fantareal.xuqi-stage-terminal .post,
    body.xuqi-fantareal.xuqi-stage-terminal .reply,
    body.xuqi-fantareal.xuqi-stage-terminal .question,
    body.xuqi-fantareal.xuqi-stage-terminal .answer {
      background:
        radial-gradient(circle at 18% 16%, rgba(255, 154, 136, .13), transparent 42%),
        rgba(34,13,15,.82) !important;
      border-color: rgba(211,77,80,.28) !important;
      color: var(--fr-text) !important;
      box-shadow:
        inset 0 1px 0 rgba(255,210,196,.08),
        0 24px 60px rgba(0,0,0,.34) !important;
    }

    @media (max-width: 760px) {
      body.xuqi-fantareal {
        padding: 10px !important;
      }

      body.xuqi-fantareal.xuqi-fragment-board .xuqi-frag {
        width: 100% !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        transform: none !important;
      }
    }
  `;
  document.head.appendChild(runtimeStyle);

  const make = (tag, className, text) => {
    const el = document.createElement(tag);
    el.className = className;
    if (text) el.textContent = text;
    return el;
  };

  const mark = make("div", "xuqi-mark", `xuqi.local / ${route.status}`);
  const rail = make("aside", "xuqi-rail");
  rail.innerHTML = [
    "<strong>绪亓档案</strong>",
    `<span>phase: ${route.stage}</span>`,
    `<span>mode: ${route.mood}</span>`,
    `<span>name: 未登记</span>`,
    `<span>time: 00:00</span>`
  ].join("");

  const waterline = make("div", "xuqi-waterline");
  const meter = make("div", "xuqi-meter");
  const cut = make("div", "xuqi-cut", route.stage === "C" ? "看" : "绪");
  const drift = make("div", "xuqi-drift");
  ["绪", "亓", "未登记", "00:00", "Aimoyu", "浅蓝"].forEach((word) => {
    drift.appendChild(make("span", "", word));
  });

  document.body.append(mark, rail, waterline, meter, drift, cut);

  const replacements = [
    [/陈佳怡/g, "Aimoyu"],
    [/安宁/g, "绪亓"],
    [/我的秘密花园/g, "绪亓的浅蓝日记"],
    [/南城市第一人民医院/g, "蓝湾市档案医院"],
    [/南城市第一医院/g, "蓝湾市档案医院"],
    [/第一医院/g, "蓝湾市档案医院"],
    [/死人可以复活吗？/g, "没有出生的人会被记住吗？"]
  ];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      return node.parentElement && node.parentElement.closest(".xuqi-mark,.xuqi-rail,.xuqi-drift,.xuqi-cut")
        ? NodeFilter.FILTER_REJECT
        : NodeFilter.FILTER_ACCEPT;
    }
  });
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  nodes.forEach((node) => {
    let text = node.nodeValue;
    replacements.forEach(([from, to]) => {
      text = text.replace(from, to);
    });
    node.nodeValue = text;
  });

  document.querySelectorAll("img").forEach((img, index) => {
    if (!img.alt || /陈佳怡|冰淇淋|长颈鹿|妈妈/.test(img.alt)) {
      img.alt = ["浅蓝日记碎片", "梦境记录", "未登记照片"][index % 3];
    }
    img.loading = "lazy";
  });

  const slug = path.split("/").filter(Boolean).slice(-2, -1)[0] || "new";
  const fragmentTargets = document.querySelectorAll(
    ".post, .question, .answer, .record-item, .reply, .archive-info, .timeline-container, .sidebar-widget, .campus-option, .reply-box, .guestbook, .comment-form, .letters-section, .diary-section"
  );
  if (fragmentTargets.length) {
    document.body.classList.add("xuqi-fragment-board");
  }

  fragmentTargets.forEach((el, index) => {
    el.classList.add("xuqi-frag", `xuqi-f${(index % 5) + 1}`);
    const type = el.classList.contains("answer") || el.classList.contains("reply")
      ? "reply"
      : el.classList.contains("question")
        ? "ask"
        : "entry";
    el.setAttribute("data-xuqi-entry", `${type}: ${slug || "root"} / ${String(index + 1).padStart(2, "0")} / ${route.mood}`);
  });

  const pulseTargets = /eye|ear|20152|20153|20154|终局|归档|黑|红/i;
  if (pulseTargets.test(path + title)) {
    setTimeout(() => document.body.classList.add("xuqi-red-pulse"), 1400);
  }

  if (route.stage === "C" || route.stage === "D") {
    const flicker = () => {
      document.body.classList.add("xuqi-cutting");
      setTimeout(() => document.body.classList.remove("xuqi-cutting"), 90);
    };
    setTimeout(flicker, 2200);
    setTimeout(flicker, 4600);
  }

  setTimeout(() => {
    mark.textContent = route.stage === "C"
      ? "xuqi.local / 她没有看见你"
      : route.stage === "D"
        ? "xuqi.local / 链接仍在呼吸"
        : `xuqi.local / ${route.status}`;
  }, 2600);
})();
