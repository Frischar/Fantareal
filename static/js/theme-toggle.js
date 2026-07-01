(() => {
  const F = window.Fantareal || {};
  const applyTheme = F.applyTheme || ((theme) => document.documentElement.setAttribute("data-theme", theme === "dark" ? "dark" : "light"));
  const applyUiOpacity = F.applyUiOpacity || (() => {});
  const postJson = F.postJson || (async (url, payload) => {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "保存失败");
    return data;
  });

  function getTheme() {
    return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }

  function normalizeTheme(theme) {
    return theme === "dark" ? "dark" : "light";
  }

  function syncThemeControls(theme) {
    const normalizedTheme = normalizeTheme(theme);
    document.querySelectorAll("#theme-select, [data-theme-select]").forEach((control) => {
      if ("value" in control && control.value !== normalizedTheme) {
        control.value = normalizedTheme;
      }
    });
    window.FantarealThemeToggle = {
      ...(window.FantarealThemeToggle || {}),
      theme: normalizedTheme,
    };
    return normalizedTheme;
  }

  function normalizeUiOpacity(value) {
    const opacity = Number(value);
    if (!Number.isFinite(opacity)) return undefined;
    return Math.min(Math.max(opacity, 0.2), 1);
  }

  function readCurrentUiOpacity() {
    const fromApi = normalizeUiOpacity(window.Fantareal?.getUiOpacity?.());
    if (fromApi !== undefined) return fromApi;

    const opacityInput = document.querySelector("#runtime-settings-ui-opacity, #ui-opacity");
    const fromInput = normalizeUiOpacity(opacityInput?.value);
    if (fromInput !== undefined) return fromInput;

    const fromBridge = normalizeUiOpacity(window.FantarealThemeToggle?.uiOpacity);
    if (fromBridge !== undefined) return fromBridge;

    const rootStyle = getComputedStyle(document.documentElement);
    const fromPanelAlpha = normalizeUiOpacity(rootStyle.getPropertyValue("--panel-alpha").trim());
    if (fromPanelAlpha !== undefined) return fromPanelAlpha;

    const panel = rootStyle.getPropertyValue("--panel");
    const alphaMatch = panel.match(/rgba?\([^,]+,[^,]+,[^,]+,\s*([0-9.]+)\s*\)/);
    return normalizeUiOpacity(alphaMatch?.[1]);
  }

  function syncThemeToggleOpacity(opacity) {
    const normalized = normalizeUiOpacity(opacity);
    if (normalized === undefined) return undefined;
    window.FantarealThemeToggle = {
      ...(window.FantarealThemeToggle || {}),
      uiOpacity: normalized,
    };
    return normalized;
  }

  function updateThemeToggle(button, theme) {
    const normalizedTheme = normalizeTheme(theme);
    const nextTheme = normalizedTheme === "dark" ? "light" : "dark";
    button.textContent = normalizedTheme === "dark" ? "🌙" : "🌞";
    button.setAttribute("aria-label", nextTheme === "dark" ? "切换为深色主题" : "切换为浅色主题");
    button.title = nextTheme === "dark" ? "切换为深色主题" : "切换为浅色主题";
  }

  function playThemeTransition(button, nextTheme) {
    if (!button || window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches) return;
    button.classList.remove("is-switching");
    void button.offsetWidth;
    button.classList.add("is-switching");
    window.setTimeout(() => button.classList.remove("is-switching"), 460);
    const burst = document.createElement("span");
    burst.className = "ui-theme-burst";
    burst.dataset.nextTheme = nextTheme;
    document.body.appendChild(burst);
    window.setTimeout(() => burst.remove(), 580);
  }

  async function saveThemePreference(theme, uiOpacity) {
    const data = await fetch("/api/settings").then((response) => response.json());
    const settings = { ...(data.settings || {}), theme };
    const currentOpacity = normalizeUiOpacity(uiOpacity ?? readCurrentUiOpacity());
    if (currentOpacity !== undefined) settings.ui_opacity = currentOpacity;
    await postJson("/api/settings", settings);
  }

  function setThemeStatus(message) {
    const statusTargets = [
      document.getElementById("status-text"),
      document.getElementById("wb-status-pill"),
      document.getElementById("memory-settings-status"),
    ].filter(Boolean);
    if (statusTargets.length) statusTargets[0].textContent = message;
  }

  function initThemeToggle() {
    const button = document.querySelector("[data-theme-toggle]");
    if (!button || button.dataset.themeToggleReady === "true") return;
    button.dataset.themeToggleReady = "true";
    let activeTheme = syncThemeControls(getTheme());
    updateThemeToggle(button, activeTheme);
    document.addEventListener("change", (event) => {
      const target = event.target;
      if (!target?.matches?.("#theme-select, [data-theme-select]")) return;
      activeTheme = syncThemeControls(target.value);
      updateThemeToggle(button, activeTheme);
    });
    button.addEventListener("click", async () => {
      const currentTheme = getTheme();
      const nextTheme = currentTheme === "dark" ? "light" : "dark";
      const currentOpacity = syncThemeToggleOpacity(readCurrentUiOpacity());
      activeTheme = normalizeTheme(nextTheme);
      playThemeTransition(button, activeTheme);
      applyTheme(activeTheme);
      syncThemeControls(activeTheme);
      if (currentOpacity !== undefined) applyUiOpacity(currentOpacity);
      updateThemeToggle(button, activeTheme);
      setThemeStatus(activeTheme === "dark" ? "已切换为深色主题。" : "已切换为浅色主题。");
      try {
        await saveThemePreference(activeTheme, currentOpacity);
      } catch (error) {
        setThemeStatus(`主题保存失败：${error.message}`);
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initThemeToggle);
  } else {
    initThemeToggle();
  }
  window.Fantareal = {
    ...(window.Fantareal || {}),
    syncThemeControls,
  };
})();
