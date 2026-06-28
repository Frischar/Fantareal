(() => {
  const F = (window.Fantareal = window.Fantareal || {});
  let catalogPromise = null;
  let panelEl = null;
  let activeTarget = null;
  let activeButton = null;

  function escapeHtml(value) {
    const helper = F.escapeHtml;
    if (typeof helper === "function") return helper(value);
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  async function loadCatalog() {
    if (!catalogPromise) {
      catalogPromise = fetch("/api/macro_variables/catalog")
        .then((response) => {
          if (!response.ok) throw new Error("宏目录读取失败");
          return response.json();
        })
        .catch((error) => {
          catalogPromise = null;
          throw error;
        });
    }
    return catalogPromise;
  }

  function resolveTarget(button) {
    const selector = button?.dataset?.macroTarget || "";
    if (!selector) return null;
    const scopeSelector = button.dataset.macroScope || "";
    const scope = scopeSelector ? button.closest(scopeSelector) : null;
    return (scope?.querySelector(selector) || document.querySelector(selector));
  }

  function insertText(target, text) {
    if (!target || typeof target.value !== "string") return;
    const current = target.value || "";
    const start = typeof target.selectionStart === "number" ? target.selectionStart : current.length;
    const end = typeof target.selectionEnd === "number" ? target.selectionEnd : current.length;
    const needsLeftSpace = start > 0 && !/[\s([{（【「『]$/.test(current.slice(0, start));
    const needsRightSpace = end < current.length && !/^[\s\])}，。；、,.!?！？）】」』]/.test(current.slice(end));
    const insertion = `${needsLeftSpace ? " " : ""}${text}${needsRightSpace ? " " : ""}`;
    target.value = `${current.slice(0, start)}${insertion}${current.slice(end)}`;
    const next = start + insertion.length;
    target.focus();
    if (typeof target.setSelectionRange === "function") target.setSelectionRange(next, next);
    target.dispatchEvent(new Event("input", { bubbles: true }));
    target.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function ensurePanel() {
    if (panelEl) return panelEl;
    panelEl = document.createElement("div");
    panelEl.className = "macro-insert-panel";
    panelEl.hidden = true;
    panelEl.innerHTML = `
      <div class="macro-insert-head">
        <div>
          <strong>可用只读宏</strong>
          <span>插入后发送时替换；未知宏会原样保留。</span>
        </div>
        <button type="button" class="macro-insert-close" aria-label="关闭">×</button>
      </div>
      <label class="macro-insert-search">
        <span>筛选</span>
        <input type="search" placeholder="搜索宏、名称或预览" />
      </label>
      <div class="macro-insert-body"></div>
    `;
    document.body.appendChild(panelEl);
    panelEl.querySelector(".macro-insert-close")?.addEventListener("click", closePanel);
    panelEl.querySelector('input[type="search"]')?.addEventListener("input", () => filterPanel());
    panelEl.addEventListener("click", (event) => {
      const button = event.target.closest("[data-macro-value]");
      if (!button) return;
      insertText(activeTarget, button.dataset.macroValue || "");
      closePanel();
    });
    return panelEl;
  }

  function placePanel(button) {
    const panel = ensurePanel();
    const rect = button.getBoundingClientRect();
    const margin = 12;
    const gap = 8;
    const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 1024;
    const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 720;
    const width = Math.min(520, Math.max(340, viewportWidth - margin * 2));
    const maxPanelHeight = Math.max(160, Math.min(620, Math.floor(viewportHeight * 0.72), viewportHeight - margin * 2));
    const spaceBelow = Math.max(0, viewportHeight - rect.bottom - gap - margin);
    const spaceAbove = Math.max(0, rect.top - gap - margin);
    const openAbove = spaceBelow < Math.min(260, maxPanelHeight) && spaceAbove > spaceBelow;
    const availableSpace = openAbove ? spaceAbove : spaceBelow;
    const panelHeight = Math.max(Math.min(180, maxPanelHeight), Math.min(maxPanelHeight, availableSpace || maxPanelHeight));
    const chromeHeight = Math.ceil(
      (panel.querySelector(".macro-insert-head")?.offsetHeight || 0) +
      (panel.querySelector(".macro-insert-search")?.offsetHeight || 0) +
      2
    );
    const bodyHeight = Math.max(96, panelHeight - chromeHeight);
    const left = Math.min(Math.max(margin, rect.left), Math.max(margin, viewportWidth - width - margin));
    const preferredTop = openAbove ? rect.top - gap - panelHeight : rect.bottom + gap;
    const top = Math.min(Math.max(margin, preferredTop), Math.max(margin, viewportHeight - panelHeight - margin));
    panel.style.width = `${width}px`;
    panel.style.left = `${left}px`;
    panel.style.top = `${top}px`;
    panel.style.maxHeight = `${panelHeight}px`;
    panel.style.setProperty("--macro-insert-body-max-height", `${bodyHeight}px`);
  }

  function renderCatalog(catalog) {
    const panel = ensurePanel();
    const body = panel.querySelector(".macro-insert-body");
    const groups = Array.isArray(catalog?.groups) ? catalog.groups : [];
    body.innerHTML = groups.map((group) => {
      const items = Array.isArray(group.items) ? group.items : [];
      return `
        <section class="macro-insert-group" data-macro-group>
          <h3>${escapeHtml(group.title || group.id || "宏")}</h3>
          <div class="macro-insert-items">
            ${items.length ? items.map((item) => {
              const macro = String(item.macro || "");
              return `
                <button type="button" class="macro-insert-item" data-macro-value="${escapeHtml(macro)}" data-macro-search="${escapeHtml([item.label, macro, item.preview, item.description].join(" ").toLowerCase())}">
                  <span class="macro-insert-item-main">
                    <strong>${escapeHtml(item.label || macro)}</strong>
                    <code>${escapeHtml(macro)}</code>
                  </span>
                  <span class="macro-insert-preview">${escapeHtml(item.preview || "未解析")}</span>
                </button>
              `;
            }).join("") : '<p class="macro-insert-empty">当前没有可插入项。</p>'}
          </div>
        </section>
      `;
    }).join("") || '<p class="macro-insert-empty">宏目录为空。</p>';
    filterPanel();
  }

  function filterPanel() {
    if (!panelEl) return;
    const query = String(panelEl.querySelector('input[type="search"]')?.value || "").trim().toLowerCase();
    panelEl.querySelectorAll(".macro-insert-group").forEach((group) => {
      let visibleCount = 0;
      group.querySelectorAll(".macro-insert-item").forEach((item) => {
        const hit = !query || String(item.dataset.macroSearch || "").includes(query);
        item.hidden = !hit;
        if (hit) visibleCount += 1;
      });
      group.hidden = visibleCount === 0;
    });
  }

  function closePanel() {
    if (!panelEl) return;
    panelEl.hidden = true;
    activeTarget = null;
    activeButton = null;
  }

  async function openPanel(button) {
    const target = resolveTarget(button);
    if (!target) return;
    activeTarget = target;
    activeButton = button;
    const panel = ensurePanel();
    panel.hidden = false;
    panel.querySelector(".macro-insert-body").innerHTML = '<p class="macro-insert-empty">正在读取宏目录...</p>';
    placePanel(button);
    try {
      renderCatalog(await loadCatalog());
      placePanel(button);
      panel.querySelector('input[type="search"]')?.focus();
    } catch (error) {
      panel.querySelector(".macro-insert-body").innerHTML = `<p class="macro-insert-empty">${escapeHtml(error.message || "宏目录读取失败")}</p>`;
    }
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-macro-insert]");
    if (button) {
      event.preventDefault();
      if (activeButton === button && panelEl && !panelEl.hidden) {
        closePanel();
      } else {
        openPanel(button);
      }
      return;
    }
    if (panelEl && !panelEl.hidden && !panelEl.contains(event.target)) closePanel();
  });
  window.addEventListener("resize", () => {
    if (activeButton && panelEl && !panelEl.hidden) placePanel(activeButton);
  });

  F.macroInsertPanel = { loadCatalog, close: closePanel };
})();
