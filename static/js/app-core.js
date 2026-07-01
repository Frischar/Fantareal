(() => {
  const F = (window.Fantareal = window.Fantareal || {});

  F.applyTheme = function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme === "dark" ? "dark" : "light");
  };

  F.applyUiOpacity = function applyUiOpacity(value) {
    const rootEl = document.documentElement;
    const opacity = Math.min(Math.max(Number(value || 0.84), 0.2), 1);
    const theme = rootEl.getAttribute("data-theme") === "dark" ? "dark" : "light";
    const palette = theme === "dark"
      ? { panel: "18, 27, 37", strong: "20, 30, 41", input: "11, 18, 26", user: "34, 52, 70", assistant: "23, 33, 46" }
      : { panel: "255, 250, 244", strong: "255, 250, 244", input: "255, 255, 255", user: "239, 220, 206", assistant: "255, 248, 242" };
    rootEl.style.setProperty("--panel", `rgba(${palette.panel}, ${opacity.toFixed(2)})`);
    rootEl.style.setProperty("--panel-strong", `rgba(${palette.strong}, ${Math.min(opacity + 0.1, 0.98).toFixed(2)})`);
    rootEl.style.setProperty("--input-bg", `rgba(${palette.input}, ${Math.max(opacity - 0.1, 0.16).toFixed(2)})`);
    rootEl.style.setProperty("--user", `rgba(${palette.user}, ${Math.min(opacity + 0.1, 0.98).toFixed(2)})`);
    rootEl.style.setProperty("--assistant", `rgba(${palette.assistant}, ${Math.min(opacity + 0.12, 0.99).toFixed(2)})`);
  };

  F.applyPerformanceMode = function applyPerformanceMode(enabled) {
    document.documentElement.setAttribute("data-performance-mode", enabled ? "on" : "off");
  };

  F.applyBackground = function applyBackground(url, overlay) {
    const normalizedOverlay = Math.min(Math.max(Number(overlay || 0), 0), 0.85);
    document.body.style.setProperty("--background-overlay-opacity", String(normalizedOverlay));
    document.body.style.setProperty("--background-image", url ? `url("${url}")` : "none");
  };

  F.postJson = async function postJson(url, payload) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || "\u8bf7\u6c42\u5931\u8d25");
    }
    return response.json();
  };

  F.escapeHtml = function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  };

  F.escapeAttr = function escapeAttr(value) {
    return F.escapeHtml(value).replaceAll("`", "&#96;");
  };

  F.inferStatusKind = function inferStatusKind(text) {
    const value = String(text || "");
    const hasAny = (items) => items.some((item) => value.includes(item));
    if (hasAny([
      "\u5931\u8d25", "\u9519\u8bef", "\u5f02\u5e38", "\u4e0d\u80fd\u4e3a\u7a7a", "\u4e0d\u53ef\u7528", "\u8bf7\u5148"
    ])) return "error";
    if (hasAny([
      "\u6b63\u5728", "\u4fdd\u5b58\u4e2d", "\u6d4b\u8bd5\u4e2d", "\u6253\u5305", "\u4e0a\u4f20", "\u62c9\u53d6",
      "\u53d8\u66f4", "\u5207\u6362", "\u8c03\u6574", "\u8bfb\u53d6\u4e2d", "\u52a0\u8f7d\u4e2d", "\u5904\u7406\u4e2d"
    ])) return "busy";
    if (hasAny(["\u5df2", "\u6210\u529f", "\u5b8c\u6210", "\u6e05\u7a7a"])) return "success";
    return "idle";
  };


  F.normalizeSearchText = function normalizeSearchText(value) {
    return String(value || "").trim().toLowerCase();
  };

  F.downloadJson = async function downloadJson(url, fallbackName) {
    const response = await fetch(url);
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || "下载失败");
    }
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="?([^";]+)"?/);
    anchor.href = objectUrl;
    anchor.download = match ? decodeURIComponent(match[1]) : fallbackName;
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  };

  F.batchRenderList = async function batchRenderList(container, items, renderItem, options = {}) {
    if (!container || typeof renderItem !== "function") return { rendered: 0, total: 0, cancelled: true };
    const list = Array.isArray(items) ? items : Array.from(items || []);
    const total = list.length;
    const batchSize = Math.max(1, Math.floor(Number(options.batchSize || 12)));
    const clear = options.clear !== false;
    const token = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const nextFrame = () => new Promise((resolve) => {
      const raf = window.requestAnimationFrame || ((callback) => window.setTimeout(callback, 0));
      raf(() => resolve());
    });

    container.dataset.frBatchRenderToken = token;
    const isCurrent = () => container.dataset.frBatchRenderToken === token;
    const stagedNodes = document.createDocumentFragment();
    const commitStagedNodes = () => {
      if (clear) {
        if (typeof container.replaceChildren === "function") {
          container.replaceChildren(stagedNodes);
          return;
        }
        container.textContent = "";
        container.appendChild(stagedNodes);
        return;
      }
      if (stagedNodes.childNodes.length) container.appendChild(stagedNodes);
    };

    if (!total) {
      const emptyNode = typeof options.emptyNode === "function" ? options.emptyNode() : options.emptyNode;
      if (clear && emptyNode) stagedNodes.appendChild(emptyNode);
      if (!isCurrent()) return { rendered: 0, total: 0, cancelled: true };
      commitStagedNodes();
      return { rendered: 0, total: 0, cancelled: !isCurrent() };
    }

    let rendered = 0;
    for (let index = 0; index < total; index += batchSize) {
      if (!isCurrent()) return { rendered, total, cancelled: true };
      const fragment = document.createDocumentFragment();
      const end = Math.min(index + batchSize, total);
      for (let itemIndex = index; itemIndex < end; itemIndex += 1) {
        const node = renderItem(list[itemIndex], itemIndex);
        if (node) fragment.appendChild(node);
      }
      if (!isCurrent()) return { rendered, total, cancelled: true };
      stagedNodes.appendChild(fragment);
      rendered = end;
      if (typeof options.onBatch === "function") {
        options.onBatch({ rendered, total, batchSize });
      }
      if (rendered < total) await nextFrame();
    }

    if (!isCurrent()) return { rendered, total, cancelled: true };
    commitStagedNodes();
    return { rendered, total, cancelled: false };
  };

  F.showToast = function showToast(host, message, type = "info") {
    if (!host || !message) return;
    const toast = document.createElement("div");
    toast.className = `app-toast ${type}`;
    toast.textContent = message;
    host.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("show"));
    window.setTimeout(() => {
      toast.classList.remove("show");
      window.setTimeout(() => toast.remove(), 220);
    }, 2200);
  };
})();
