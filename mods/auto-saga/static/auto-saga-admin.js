(() => {
  "use strict";

  const API = "./api";
  const elements = {
    enabled: document.getElementById("enabledInput"),
    autoInteract: document.getElementById("autoInteractInput"),
    observerMode: document.getElementById("observerModeInput"),
    showSilent: document.getElementById("showSilentInput"),
    characterList: document.getElementById("characterList"),
    selectImport: document.getElementById("selectImportButton"),
    syncCurrent: document.getElementById("syncPersonaButton"),
    fileInput: document.getElementById("roleCardFileInput"),
    turn: document.getElementById("turnValue"),
    heroTurn: document.getElementById("heroTurn"),
    envTime: document.getElementById("envTime"),
    envPlace: document.getElementById("envPlace"),
    envWeather: document.getElementById("envWeather"),
    modelStatus: document.getElementById("modelStatus"),
    modelName: document.getElementById("modelName"),
    modelBaseUrl: document.getElementById("modelBaseUrl"),
    toast: document.getElementById("toast"),
  };
  let currentCharacters = [];

  async function request(path, options = {}) {
    const response = await fetch(API + path, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    return payload;
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

  function shorten(value, max) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    return text.length > max ? `${text.slice(0, max)}…` : text;
  }

  function toast(message, error = false) {
    elements.toast.textContent = message;
    elements.toast.classList.toggle("error", error);
    elements.toast.classList.add("visible");
    clearTimeout(elements.toast._timer);
    elements.toast._timer = setTimeout(() => elements.toast.classList.remove("visible"), 2800);
  }

  function render(state) {
    const settings = state.settings || {};
    elements.enabled.checked = Boolean(settings.enabled);
    elements.autoInteract.checked = Boolean(settings.auto_interact);
    elements.observerMode.checked = Boolean(settings.observer_mode);
    elements.showSilent.checked = Boolean(settings.show_silent);
    elements.turn.textContent = String(state.turn || 0);
    elements.heroTurn.textContent = String(state.turn || 0);
    elements.envTime.textContent = state.env?.time || "未设置";
    elements.envPlace.textContent = state.env?.place || "未设置";
    elements.envWeather.textContent = state.env?.weather || "未设置";

    const model = state.model_config || {};
    elements.modelStatus.textContent = model.configured ? "已配置" : "未配置";
    elements.modelStatus.classList.toggle("configured", Boolean(model.configured));
    elements.modelName.textContent = model.model || "未设置";
    elements.modelBaseUrl.textContent = model.base_url || "未设置";

    currentCharacters = Array.isArray(state.characters)
      ? state.characters.map((character) => ({ ...character }))
      : [];
    if (!currentCharacters.length) {
      elements.characterList.innerHTML = '<div class="empty-state">尚未加入角色。请选择角色卡导入，或导入当前角色卡。</div>';
      return;
    }
    elements.characterList.innerHTML = currentCharacters.map((character, index) => `
      <article class="character-item">
        <span class="character-mark">${escapeHtml((character.name || "角").slice(0, 1))}</span>
        <div>
          <strong>${escapeHtml(character.name || "角色")}</strong>
          <p>${escapeHtml(shorten(character.persona || "暂无人设说明", 150))}</p>
        </div>
        <div class="character-tools">
          <span class="trust-chip">信任 ${Number(character.trust ?? 50)}</span>
          <button type="button" data-character-delete="${index}">删除</button>
        </div>
      </article>
    `).join("");
  }

  async function saveSettings(patch) {
    try {
      render(await request("/settings", {
        method: "POST",
        body: JSON.stringify(patch),
      }));
      toast("配置已保存");
    } catch (error) {
      toast(`保存失败：${error.message}`, true);
    }
  }

  async function importCurrentCard() {
    try {
      const payload = await request("/current-card-characters");
      const characters = Array.isArray(payload.characters) ? payload.characters : [];
      if (!characters.length) throw new Error("当前角色卡没有可导入的角色资料");
      render(await request("/characters/merge", {
        method: "POST",
        body: JSON.stringify({ characters }),
      }));
      toast(`已导入 ${characters.length} 个角色`);
    } catch (error) {
      toast(`导入失败：${error.message}`, true);
    }
  }

  async function importSelectedFile(file) {
    if (!file) return;
    const suffix = file.name.split(".").pop()?.toLowerCase();
    if (!["json", "txt"].includes(suffix)) {
      throw new Error("请选择 Fantareal JSON 或 TXT 角色卡");
    }
    const rawJson = await file.text();
    const state = await request("/characters/import-card", {
      method: "POST",
      body: JSON.stringify({ raw_json: rawJson }),
    });
    render(state);
    toast(`已从 ${file.name} 导入 ${state.imported_count} 个角色`);
  }

  async function saveCharacters(characters) {
    render(await request("/characters", {
      method: "POST",
      body: JSON.stringify({ characters }),
    }));
  }

  elements.enabled.addEventListener("change", () => {
    saveSettings({ enabled: elements.enabled.checked });
  });
  elements.showSilent.addEventListener("change", () => {
    saveSettings({ show_silent: elements.showSilent.checked });
  });
  elements.autoInteract.addEventListener("change", () => {
    saveSettings({ auto_interact: elements.autoInteract.checked });
  });
  elements.observerMode.addEventListener("change", () => {
    saveSettings({ observer_mode: elements.observerMode.checked });
  });
  elements.selectImport.addEventListener("click", () => elements.fileInput.click());
  elements.syncCurrent.addEventListener("click", importCurrentCard);
  elements.fileInput.addEventListener("change", async () => {
    const file = elements.fileInput.files?.[0];
    elements.fileInput.value = "";
    try {
      await importSelectedFile(file);
    } catch (error) {
      toast(`导入失败：${error.message}`, true);
    }
  });
  elements.characterList.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-character-delete]");
    if (!button) return;
    const index = Number(button.dataset.characterDelete);
    const character = currentCharacters[index];
    if (!character || !window.confirm(`删除角色“${character.name}”？`)) return;
    try {
      await saveCharacters(currentCharacters.filter((_item, itemIndex) => itemIndex !== index));
      toast("角色已删除");
    } catch (error) {
      toast(`删除失败：${error.message}`, true);
    }
  });
  document.getElementById("resetButton").addEventListener("click", async () => {
    if (!window.confirm("确定清空自动叙事的回合、事件和历史吗？")) return;
    try {
      render(await request("/reset", { method: "POST", body: "{}" }));
      toast("叙事状态已重置");
    } catch (error) {
      toast(`重置失败：${error.message}`, true);
    }
  });

  request("/state").then(render).catch((error) => toast(`读取失败：${error.message}`, true));
})();
