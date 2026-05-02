(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const API = (path) => `${API_BASE_PATH}${path}`;

  const outputs = {
    script: { textarea: "script-output", state: "scriptState", warning: "script-warnings", download: "script_index" },
    lines: { textarea: "lines-output", download: "target_lines" },
    worldbook: { textarea: "wb-output", state: "worldbookState", warning: "wb-warnings", download: "worldbook", importEndpoint: "/api/import/worldbook" },
    plot: { textarea: "plot-output", state: "plotState", warning: "plot-warnings", download: "plot_condensation" },
    memory: { textarea: "mem-output", state: "memoryState", warning: "mem-warnings", download: "memories", importEndpoint: "/api/import/memories" },
    preset: { textarea: "pre-output", state: "presetState", warning: "pre-warnings", download: "preset", importEndpoint: "/api/import/preset" },
    rolecard: { textarea: "rc-output", state: "roleState", warning: "rc-warnings", download: "role_card", importEndpoint: "/api/import/card" },
  };

  const CHUNK_CONCURRENCY = 4;
  const CHUNK_RETRY_LIMIT = 2;
  const RUN_STORE_PREFIX = "soul_weaver_run:";
  const PIPELINE_STORE_KEY = "soul_weaver_pipeline_state";

  const state = {
    scriptIndex: null,
    targetLines: "",
    scriptChunks: [],
    targetChunks: [],
    worldbook: null,
    plot: null,
    memory: null,
    preset: null,
    rolecard: null,
  };

  let confirmResolve = null;

  async function post(url, body) {
    const response = await fetch(API(url), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "请求失败");
    return data;
  }

  async function postBlob(url, body) {
    const response = await fetch(API(url), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || "请求失败");
    }
    return response.blob();
  }

  function setStatus(text) {
    $("statusText").textContent = text;
  }

  function setProgress(label, current, total) {
    const panel = $("progressPanel");
    const safeTotal = Math.max(1, Number(total || 1));
    const safeCurrent = Math.max(0, Math.min(safeTotal, Number(current || 0)));
    panel.hidden = false;
    $("progressText").textContent = label;
    $("progressCount").textContent = `${safeCurrent} / ${safeTotal}`;
    $("progressBar").style.width = `${Math.round((safeCurrent / safeTotal) * 100)}%`;
    $("loadingText").textContent = `${label}（${safeCurrent}/${safeTotal}）`;
  }

  function clearProgress() {
    $("progressPanel").hidden = true;
    $("progressBar").style.width = "0%";
    $("progressText").textContent = "等待 chunk 任务";
    $("progressCount").textContent = "0 / 0";
  }

  function showLoading(text) {
    $("loadingText").textContent = text || "处理中...";
    $("loadingOverlay").hidden = false;
  }

  function hideLoading() {
    $("loadingOverlay").hidden = true;
  }

  function showConfirm(title, message) {
    return new Promise((resolve) => {
      $("confirmTitle").textContent = title;
      $("confirmMessage").textContent = message;
      $("confirmDialog").hidden = false;
      confirmResolve = resolve;
    });
  }

  function hideConfirm(value) {
    $("confirmDialog").hidden = true;
    if (confirmResolve) {
      confirmResolve(value);
      confirmResolve = null;
    }
  }

  function esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function settings() {
    return {
      base_url: $("baseUrl").value.trim(),
      api_key: $("apiKey").value.trim(),
      model: $("model").value.trim(),
      temperature: Number($("temperature").value || 0.4),
      max_tokens: Number($("maxTokens").value || 0),
      request_timeout: 600,
    };
  }

  function sourceText() {
    return $("sourceText").value.trim();
  }

  function characterName() {
    return $("characterName").value.trim();
  }

  function mainBaseUrl() {
    return $("mainBaseUrl").value.trim() || window.location.origin;
  }

  function persistPipelineState() {
    try {
      localStorage.setItem(PIPELINE_STORE_KEY, JSON.stringify({
        projectName: $("projectName").value.trim(),
        characterName: characterName(),
        sourceText: $("sourceText").value,
        scriptIndex: state.scriptIndex,
        targetLines: state.targetLines,
        scriptChunks: state.scriptChunks,
        targetChunks: state.targetChunks,
        worldbook: state.worldbook,
        plot: state.plot,
        memory: state.memory,
        preset: state.preset,
        rolecard: state.rolecard,
      }));
    } catch {
      setStatus("浏览器本地存储已满，无法保存流水线状态。");
    }
  }

  function restorePipelineState() {
    let stored = null;
    try {
      stored = JSON.parse(localStorage.getItem(PIPELINE_STORE_KEY) || "null");
    } catch {
      stored = null;
    }
    if (!stored || typeof stored !== "object") return false;
    $("projectName").value = stored.projectName || "";
    $("characterName").value = stored.characterName || "";
    $("sourceText").value = stored.sourceText || "";
    state.scriptIndex = stored.scriptIndex || null;
    state.targetLines = stored.targetLines || "";
    state.scriptChunks = Array.isArray(stored.scriptChunks) ? stored.scriptChunks : [];
    state.targetChunks = Array.isArray(stored.targetChunks) ? stored.targetChunks : [];
    state.worldbook = stored.worldbook || null;
    state.plot = stored.plot || null;
    state.memory = stored.memory || null;
    state.preset = stored.preset || null;
    state.rolecard = stored.rolecard || null;

    if (state.scriptIndex) {
      setOutput("script", state.scriptIndex);
      setOutput("lines", state.targetLines);
      renderCharacterTable(state.scriptIndex.character_table || []);
      setStateText("script", `${state.scriptIndex.total_lines || 0} 句 / ${state.scriptChunks.length || (state.scriptIndex.chunks || []).length || 0} chunks`);
      enableButton("generateWorldbookBtn", true);
      enableButton("generatePlotBtn", true);
      enableButton("generateRoleBtn", true);
      enableButton("script-copyBtn", true);
      enableButton("script-downloadBtn", true);
      enableButton("generatePresetBtn", Boolean(state.targetLines));
      enableButton("lines-copyBtn", Boolean(state.targetLines));
      enableButton("lines-downloadBtn", Boolean(state.targetLines));
    }
    if (state.worldbook) { setOutput("worldbook", state.worldbook); setStateText("worldbook", "已恢复"); enableOutputButtons("wb", true); }
    if (state.plot) {
      setOutput("plot", state.plot);
      setStateText("plot", "已恢复");
      enableButton("plot-copyBtn", true);
      enableButton("plot-downloadBtn", true);
      enableButton("generateMemoryBtn", true);
    }
    if (state.memory) { setOutput("memory", state.memory); setStateText("memory", "已恢复"); enableOutputButtons("mem", true); }
    if (state.preset) { setOutput("preset", state.preset); setStateText("preset", "已恢复"); enableOutputButtons("pre", true); }
    if (state.rolecard) { setOutput("rolecard", state.rolecard); setStateText("rolecard", "已恢复"); enableOutputButtons("rc", true); }
    updateBundleButtons();
    return Boolean(state.scriptIndex || state.worldbook || state.plot || state.memory || state.preset || state.rolecard);
  }

  function setOutput(type, value) {
    const config = outputs[type];
    const textarea = $(config.textarea);
    if (typeof value === "string") textarea.value = value;
    else textarea.value = JSON.stringify(value, null, 2);
  }

  function readJsonOutput(type) {
    const config = outputs[type];
    const text = $(config.textarea).value.trim();
    if (!text) return null;
    try {
      return JSON.parse(text);
    } catch {
      setStatus(`${labelFor(type)} 不是合法 JSON。`);
      return null;
    }
  }

  function labelFor(type) {
    return {
      script: "剧本索引",
      lines: "角色台词",
      worldbook: "世界书",
      plot: "剧情提纯",
      memory: "记忆",
      preset: "预设",
      rolecard: "人设卡",
    }[type] || type;
  }

  function setStateText(type, text) {
    const config = outputs[type];
    if (config?.state) $(config.state).textContent = text;
  }

  function showWarnings(type, warnings) {
    const config = outputs[type];
    if (!config?.warning) return;
    const box = $(config.warning);
    box.innerHTML = "";
    (warnings || []).forEach((warning) => {
      const item = document.createElement("div");
      item.className = "warning-item";
      item.textContent = warning;
      box.appendChild(item);
    });
  }

  function enableButton(id, enabled = true) {
    const button = $(id);
    if (button) button.disabled = !enabled;
  }

  function enableOutputButtons(prefix, enabled = true) {
    ["copyBtn", "downloadBtn", "importBtn"].forEach((suffix) => {
      const button = $(`${prefix}-${suffix}`);
      if (button) button.disabled = !enabled;
    });
  }

  function updateBundleButtons() {
    const hasAny = Boolean(state.worldbook || state.memory || state.preset || state.rolecard);
    enableButton("downloadBundleBtn", hasAny);
    enableButton("importAllBtn", hasAny);
  }

  function switchTab(tabName) {
    document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((content) => content.classList.remove("active"));
    const tab = document.querySelector(`[data-tab="${tabName}"]`);
    const content = $(`tab-${tabName}`);
    if (tab && content) {
      tab.classList.add("active");
      content.classList.add("active");
    }
    document.querySelectorAll(".flow-step").forEach((step) => {
      step.classList.toggle("active", step.dataset.step === tabName);
    });
  }

  function downloadJson(payload, filename) {
    const text = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
    downloadText(text, filename, "application/json;charset=utf-8");
  }

  function downloadText(text, filename, mimeType = "text/plain;charset=utf-8") {
    const blob = new Blob([text], { type: mimeType });
    downloadBlob(blob, filename);
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  function soulBaseName() {
    return (characterName() || $("projectName").value.trim() || "Soul Weaver").replace(/[<>:"/\\|?*\x00-\x1f]/g, "_").trim() || "Soul Weaver";
  }

  function copyText(textareaId) {
    const text = $(textareaId).value.trim();
    if (!text) {
      setStatus("没有可复制的内容。");
      return;
    }
    navigator.clipboard.writeText(text).then(
      () => setStatus("已复制。"),
      () => {
        $(textareaId).select();
        document.execCommand("copy");
        setStatus("已复制。");
      },
    );
  }

  function downloadOutput(type) {
    const config = outputs[type];
    const text = $(config.textarea).value.trim();
    if (!text) {
      setStatus("没有可下载的内容。");
      return;
    }
    if (type === "lines") {
      downloadText(text, "soul_weaver_target_lines.txt");
      setStatus("已下载。");
      return;
    }
    downloadJson(text, `soul_weaver_${config.download}.json`);
    setStatus("已下载。");
  }

  function chunkSummary(chunk) {
    const { content, ...meta } = chunk || {};
    return meta;
  }

  function splitTextIntoChunks(text, prefix = "chunk", targetLines = 300) {
    const clean = String(text || "").trim();
    if (!clean) return [];
    const lines = clean.split(/\r?\n/);
    const chunks = [];
    const chunkSize = Math.max(1, Number(targetLines || 300));
    for (let offset = 0; offset < lines.length; offset += chunkSize) {
      const buffer = lines.slice(offset, offset + chunkSize);
      const content = buffer.join("\n");
      const index = chunks.length + 1;
      chunks.push({
        id: `${prefix}_${String(index).padStart(3, "0")}`,
        index,
        title: `${prefix} ${String(index).padStart(3, "0")}`,
        line_count: buffer.length,
        char_count: content.length,
        content,
      });
    }
    chunks.forEach((chunk) => { chunk.total_chunks = chunks.length; });
    return chunks;
  }

  function runStorageKey(task, chunks) {
    const character = characterName() || "unknown";
    const project = $("projectName").value.trim() || "default";
    const signature = (chunks || [])
      .map((chunk) => `${chunk.id || chunk.index}:${chunk.line_count || 0}:${chunk.char_count || 0}`)
      .join("|");
    return `${RUN_STORE_PREFIX}${task}:${project}:${character}:${signature}`;
  }

  function loadRunState(key, total) {
    try {
      const raw = JSON.parse(localStorage.getItem(key) || "{}");
      if (!Array.isArray(raw.partials) || raw.partials.length !== total) return { partials: new Array(total) };
      return { partials: raw.partials };
    } catch {
      return { partials: new Array(total) };
    }
  }

  function saveRunState(key, partials) {
    try {
      localStorage.setItem(key, JSON.stringify({
        saved_at: new Date().toISOString(),
        partials,
      }));
    } catch {
      setStatus("浏览器本地存储已满，无法保存 chunk 进度。");
    }
  }

  function clearRunState(key) {
    try { localStorage.removeItem(key); } catch { /* ignore */ }
  }

  function generationContext(task) {
    return {
      project_name: $("projectName").value.trim(),
      target_character: characterName(),
      target_character_lines: task === "preset" ? "" : $("lines-output").value.trim(),
      worldbook_output: task === "worldbook" ? "" : $("wb-output").value.trim(),
      plot_condensation: task === "plot" ? "" : $("plot-output").value.trim(),
      memories_output: task === "memory" ? "" : $("mem-output").value.trim(),
      rolecard_requirement: "人设卡 description 最低 6000 字，并无缝衔接真结局后。",
    };
  }

  async function runChunkedGeneration(task, chunks, label, stateType) {
    const usableChunks = (chunks || []).filter((chunk) => String(chunk?.content || "").trim());
    if (!usableChunks.length) throw new Error("没有可用 chunk，请先解析剧本。");
    const totalSteps = usableChunks.length + 1;
    const storeKey = runStorageKey(task, usableChunks);
    const storedRun = loadRunState(storeKey, usableChunks.length);
    const partials = storedRun.partials;
    const failures = [];
    const runSettings = settings();
    const runContext = generationContext(task);
    const runCharacter = characterName();
    let nextIndex = 0;
    let completed = partials.filter(Boolean).length;
    if (completed) {
      setStatus(`已恢复 ${completed}/${usableChunks.length} 个 ${label} chunk，继续跑剩余部分。`);
      setProgress(`${label}：已恢复进度`, completed, totalSteps);
    }

    async function worker() {
      while (nextIndex < usableChunks.length) {
        const index = nextIndex;
        nextIndex += 1;
        if (partials[index]) continue;
        const chunk = usableChunks[index];
        const title = chunk.title || chunk.id || `chunk ${index + 1}`;
        setProgress(`${label}：并行分析 ${title}`, completed, totalSteps);
        setStateText(stateType, `${completed}/${usableChunks.length}`);
        let lastError = null;
        for (let attempt = 1; attempt <= CHUNK_RETRY_LIMIT + 1; attempt += 1) {
          try {
            if (attempt > 1) setProgress(`${label}：重试 ${title}（${attempt - 1}/${CHUNK_RETRY_LIMIT}）`, completed, totalSteps);
            const data = await post("/api/generate/chunk", {
              ...runSettings,
              task,
              source_text: chunk.content,
              chunk_meta: chunkSummary(chunk),
              character_name: runCharacter,
              context: runContext,
            });
            partials[index] = {
              chunk: chunkSummary(chunk),
              output: data.parsed || data.output,
            };
            saveRunState(storeKey, partials);
            lastError = null;
            break;
          } catch (error) {
            lastError = error;
          }
        }
        if (lastError) {
          failures.push({
            index,
            title,
            message: lastError.message || "请求失败",
          });
        }
        completed += 1;
        setProgress(`${label}：已完成 ${completed}/${usableChunks.length}`, completed, totalSteps);
        setStateText(stateType, `${completed}/${usableChunks.length}`);
      }
    }

    const workerCount = Math.min(CHUNK_CONCURRENCY, usableChunks.length);
    await Promise.all(Array.from({ length: workerCount }, () => worker()));
    saveRunState(storeKey, partials);
    if (failures.length) {
      const detail = failures
        .sort((a, b) => a.index - b.index)
        .map((item) => `${item.title}: ${item.message}`)
        .join("；");
      throw new Error(`${failures.length} 个 chunk 失败，已停止合并：${detail}`);
    }
    setProgress(`${label}：合并 chunk`, usableChunks.length, totalSteps);
    let merged;
    try {
      merged = await post("/api/generate/merge", {
        ...runSettings,
        task,
        partials: partials.filter(Boolean),
        character_name: runCharacter,
        context: runContext,
      });
    } catch (error) {
      saveRunState(storeKey, partials);
      throw new Error(`合并失败：${error.message}。已保留全部 chunk 结果，修正后再次点击本按钮会直接重试合并。`);
    }
    clearRunState(storeKey);
    setProgress(`${label}：完成`, totalSteps, totalSteps);
    return merged;
  }

  function renderCharacterTable(characterTable) {
    const root = $("characterTable");
    if (!characterTable?.length) {
      root.innerHTML = '<p class="empty-state">没有识别到角色，请检查 `[角色]:对白`、`「角色」：对白` 或 `【角色】：对白` 格式。</p>';
      return;
    }
    root.innerHTML = "";
    characterTable.forEach((character) => {
      const button = document.createElement("button");
      button.className = "character-row";
      button.type = "button";
      button.innerHTML = `
        <strong>${esc(character.name)}</strong>
        <span>${Number(character.line_count || 0)} 句 / ${Number(character.char_count || 0)} 字</span>
        <small>${esc((character.sample_lines || [])[0] || "")}</small>
      `;
      button.addEventListener("click", () => selectCharacter(character.name));
      root.appendChild(button);
    });
  }

  async function parseScript(options = {}) {
    const text = sourceText();
    if (!text) {
      setStatus("请先粘贴完整 GAL 剧情。");
      return;
    }
    clearProgress();
    showLoading("正在解析剧本和角色表...");
    try {
      const data = await post("/api/parse-script", {
        source_text: text,
        character_name: characterName(),
        save_draft: options.saveDraft !== false,
      });
      state.scriptIndex = data.script_index;
      state.targetLines = data.target_lines || "";
      state.scriptChunks = data.chunks || [];
      state.targetChunks = data.target_chunks || [];
      setOutput("script", data.script_index);
      setOutput("lines", state.targetLines);
      renderCharacterTable(data.script_index?.character_table || []);
      showWarnings("script", data.warnings);
      setStateText("script", `${data.script_index?.total_lines || 0} 句 / ${state.scriptChunks.length || 0} chunks`);
      enableButton("generateWorldbookBtn", true);
      enableButton("generatePlotBtn", true);
      enableButton("generateRoleBtn", true);
      enableButton("script-copyBtn", true);
      enableButton("script-downloadBtn", true);
      enableButton("generatePresetBtn", Boolean(state.targetLines));
      enableButton("lines-copyBtn", Boolean(state.targetLines));
      enableButton("lines-downloadBtn", Boolean(state.targetLines));
      switchTab("script");
      setStatus(`剧本解析完成：完整剧情 ${state.scriptChunks.length || 0} 个 chunk，目标角色 ${state.targetChunks.length || 0} 个 chunk。`);
      persistPipelineState();
      if (options.saveDraft !== false) loadDrafts();
    } catch (error) {
      setStatus(`剧本解析失败：${error.message}`);
    } finally {
      hideLoading();
    }
  }

  async function selectCharacter(name) {
    $("characterName").value = name;
    await parseScript({ saveDraft: false });
    switchTab("lines");
  }

  async function generateWorldbook() {
    if (!sourceText()) {
      setStatus("请先粘贴完整剧情。");
      return;
    }
    const chunks = state.scriptChunks.length ? state.scriptChunks : splitTextIntoChunks(sourceText(), "plot_chunk");
    showLoading("正在按 chunk 提取世界书...");
    setStateText("worldbook", "生成中");
    try {
      const data = await runChunkedGeneration("worldbook", chunks, "世界书", "worldbook");
      state.worldbook = data.result;
      setOutput("worldbook", data.result);
      showWarnings("worldbook", data.warnings);
      setStateText("worldbook", "已生成");
      enableOutputButtons("wb", true);
      updateBundleButtons();
      switchTab("worldbook");
      setStatus("世界书已生成。确认后可以继续剧情提纯。");
      persistPipelineState();
      loadDrafts();
    } catch (error) {
      setStateText("worldbook", "失败");
      setStatus(`世界书生成失败：${error.message}`);
    } finally {
      hideLoading();
    }
  }

  async function generatePlot() {
    if (!sourceText()) {
      setStatus("请先粘贴完整剧情。");
      return;
    }
    const chunks = state.scriptChunks.length ? state.scriptChunks : splitTextIntoChunks(sourceText(), "plot_chunk");
    showLoading("正在按 chunk 提纯完整路线剧情...");
    setStateText("plot", "提纯中");
    try {
      const data = await runChunkedGeneration("plot", chunks, "剧情提纯", "plot");
      state.plot = data.result;
      setOutput("plot", data.result);
      showWarnings("plot", data.warnings);
      setStateText("plot", "已提纯");
      enableButton("plot-copyBtn", true);
      enableButton("plot-downloadBtn", true);
      enableButton("generateMemoryBtn", true);
      enableButton("generateRoleBtn", true);
      switchTab("plot");
      setStatus("剧情提纯完成。确认后可以继续生成记忆。");
      persistPipelineState();
      loadDrafts();
    } catch (error) {
      setStateText("plot", "失败");
      setStatus(`剧情提纯失败：${error.message}`);
    } finally {
      hideLoading();
    }
  }

  async function generateMemory() {
    const source = sourceText();
    if (!source && !$("plot-output").value.trim()) {
      setStatus("请先完成剧情提纯，或粘贴完整剧情。");
      return;
    }
    const chunks = state.scriptChunks.length ? state.scriptChunks : splitTextIntoChunks(source || $("plot-output").value.trim(), "memory_source");
    showLoading("正在按 chunk 生成长期记忆...");
    setStateText("memory", "生成中");
    try {
      const data = await runChunkedGeneration("memory", chunks, "记忆", "memory");
      state.memory = data.result;
      setOutput("memory", data.result);
      showWarnings("memory", data.warnings);
      setStateText("memory", "已生成");
      enableOutputButtons("mem", true);
      updateBundleButtons();
      switchTab("memory");
      setStatus("记忆已生成。确认后可以继续生成预设或人设卡。");
      persistPipelineState();
      loadDrafts();
    } catch (error) {
      setStateText("memory", "失败");
      setStatus(`记忆生成失败：${error.message}`);
    } finally {
      hideLoading();
    }
  }

  async function generatePreset() {
    const lines = $("lines-output").value.trim();
    if (!lines) {
      setStatus("请先解析剧本并选择目标角色，预设只使用该角色单独台词。");
      return;
    }
    const chunks = state.targetChunks.length ? state.targetChunks : splitTextIntoChunks(lines, "target_chunk");
    showLoading("正在按 chunk 从目标角色台词生成预设...");
    setStateText("preset", "生成中");
    try {
      const data = await runChunkedGeneration("preset", chunks, "预设", "preset");
      state.preset = data.result;
      setOutput("preset", data.result);
      showWarnings("preset", data.warnings);
      setStateText("preset", "已生成");
      enableOutputButtons("pre", true);
      updateBundleButtons();
      switchTab("preset");
      setStatus("预设已生成。输出为 Fantareal preset store 格式。");
      persistPipelineState();
      loadDrafts();
    } catch (error) {
      setStateText("preset", "失败");
      setStatus(`预设生成失败：${error.message}`);
    } finally {
      hideLoading();
    }
  }

  function roleCardContext() {
    const context = {
      target_character: characterName(),
      project_name: $("projectName").value.trim(),
      requirement: "生成 Fantareal 角色卡。description 最低 6000 字，first_mes 必须无缝衔接真结局之后。",
      target_character_lines: $("lines-output").value.trim(),
      plot_condensation: readJsonOutput("plot") || $("plot-output").value.trim(),
      memories_output: readJsonOutput("memory") || $("mem-output").value.trim(),
      worldbook_output: readJsonOutput("worldbook") || $("wb-output").value.trim(),
      full_script: sourceText(),
    };
    return JSON.stringify(context, null, 2);
  }

  async function generateRoleCard() {
    const context = roleCardContext();
    if (!sourceText() && !$("lines-output").value.trim() && !$("plot-output").value.trim()) {
      setStatus("请先粘贴完整剧情。");
      return;
    }
    const lineChunks = $("lines-output").value.trim() ? splitTextIntoChunks($("lines-output").value.trim(), "target_chunk") : [];
    const chunks = state.targetChunks.length ? state.targetChunks : (lineChunks.length ? lineChunks : splitTextIntoChunks(sourceText() || context, "role_source"));
    showLoading("正在按 chunk 生成人设卡...");
    setStateText("rolecard", "生成中");
    try {
      const data = await runChunkedGeneration("rolecard", chunks, "人设卡", "rolecard");
      state.rolecard = data.result;
      setOutput("rolecard", data.result);
      showWarnings("rolecard", data.warnings);
      setStateText("rolecard", "已生成");
      enableOutputButtons("rc", true);
      updateBundleButtons();
      switchTab("rolecard");
      setStatus("人设卡已生成。");
      persistPipelineState();
      loadDrafts();
    } catch (error) {
      setStateText("rolecard", "失败");
      setStatus(`人设卡生成失败：${error.message}`);
    } finally {
      hideLoading();
    }
  }

  async function importOne(type, skipConfirm = false) {
    const config = outputs[type];
    const payload = readJsonOutput(type);
    if (!payload) return false;
    if (!skipConfirm) {
      const ok = await showConfirm(`导入${labelFor(type)}`, `确定导入${labelFor(type)}到 Fantareal？`);
      if (!ok) return false;
    }
    showLoading(`正在导入${labelFor(type)}...`);
    try {
      const body = { data: payload, main_base_url: mainBaseUrl() };
      if (type === "worldbook") body.apply_settings = $("wb-applySettings").checked;
      await post(config.importEndpoint, body);
      setStatus(`${labelFor(type)}导入成功。`);
      return true;
    } catch (error) {
      setStatus(`${labelFor(type)}导入失败：${error.message}`);
      return false;
    } finally {
      hideLoading();
    }
  }

  async function importAll() {
    const types = ["worldbook", "memory", "preset", "rolecard"].filter((type) => $(outputs[type].textarea).value.trim());
    if (!types.length) {
      setStatus("没有可导入的素材。");
      return;
    }
    const ok = await showConfirm("导入全部素材", `将依次导入 ${types.map(labelFor).join("、")}。继续吗？`);
    if (!ok) return;
    let successCount = 0;
    for (const type of types) {
      const success = await importOne(type, true);
      if (!success) {
        setStatus(`批量导入中止：${labelFor(type)}导入失败，已成功导入 ${successCount} 项。`);
        return;
      }
      successCount += 1;
    }
    setStatus(`全部可用素材已导入，共 ${successCount} 项。`);
  }

  function bundlePayload() {
    return {
      meta: {
        project_name: $("projectName").value.trim(),
        target_character: characterName(),
        exported_at: new Date().toISOString(),
      },
      name: soulBaseName(),
      script_index: readJsonOutput("script"),
      script_chunks: state.scriptChunks,
      target_character_lines: $("lines-output").value.trim(),
      target_character_chunks: state.targetChunks,
      worldbook_output: readJsonOutput("worldbook"),
      plot_condensation_output: readJsonOutput("plot"),
      memories_output: readJsonOutput("memory"),
      preset_output: readJsonOutput("preset"),
      role_card_output: readJsonOutput("rolecard"),
    };
  }

  function downloadBundle() {
    const payload = bundlePayload();
    const hasAny = payload.worldbook_output || payload.memories_output || payload.preset_output || payload.role_card_output;
    if (!hasAny) {
      setStatus("没有可导出的世界书/记忆/预设/人设卡。");
      return;
    }
    showLoading("正在打包到本机下载目录...");
    post("/api/export/soul-local", payload)
      .then((data) => {
        setStatus(`完整导出已保存：${data.path}`);
      })
      .catch((error) => setStatus(`完整导出失败：${error.message}`))
      .finally(hideLoading);
  }

  async function saveSettings() {
    try {
      await post("/api/settings", settings());
      setStatus("配置已保存。");
    } catch (error) {
      setStatus(`保存失败：${error.message}`);
    }
  }

  async function probeModels() {
    showLoading("正在检测模型...");
    try {
      const data = await post("/api/probe-models", settings());
      const models = data.models || [];
      const list = $("modelList");
      list.innerHTML = "";
      if (models.length) {
        list.hidden = false;
        models.forEach((model) => {
          const item = document.createElement("span");
          item.className = "model-item";
          item.textContent = model;
          item.addEventListener("click", () => {
            $("model").value = model;
            setStatus(`已选择模型：${model}`);
          });
          list.appendChild(item);
        });
        setStatus(`检测到 ${models.length} 个模型。`);
      } else {
        list.hidden = true;
        setStatus(data.detail || "未检测到模型。");
      }
    } catch (error) {
      setStatus(`检测失败：${error.message}`);
    } finally {
      hideLoading();
    }
  }

  async function loadDrafts() {
    try {
      const data = await fetch(API("/api/drafts")).then((response) => response.json());
      renderDrafts(data.drafts || []);
    } catch {
      renderDrafts(INITIAL_DRAFTS || []);
    }
  }

  const draftTypeToTab = {
    script_index: "script",
    worldbook: "worldbook",
    plot: "plot",
    memory: "memory",
    preset: "preset",
    role_card: "rolecard",
  };

  function renderDrafts(drafts) {
    const list = $("draftsList");
    if (!drafts.length) {
      list.innerHTML = '<p class="empty-state">暂无草稿记录。</p>';
      return;
    }
    list.innerHTML = "";
    drafts.forEach((draft) => {
      const tab = draftTypeToTab[draft.type];
      const card = document.createElement("button");
      card.className = "draft-card";
      card.type = "button";
      card.innerHTML = `
        <span class="draft-type">${esc(labelFor(tab || draft.type || "unknown"))}</span>
        <span class="draft-title">${esc(draft.character_name || draft.source_summary || "无标题")}</span>
        <span class="draft-meta">${esc((draft.generated_at || "").replace("T", " ").slice(0, 19))} · ${esc(draft.model || "")}</span>
      `;
      card.addEventListener("click", () => {
        if (!tab || !draft.result) return;
        if (tab === "script") {
          state.scriptIndex = draft.result;
          setOutput("script", draft.result);
          state.targetLines = draft.result.target_lines || "";
          state.scriptChunks = [];
          state.targetChunks = [];
          setOutput("lines", state.targetLines);
          renderCharacterTable(draft.result.character_table || []);
          setStateText("script", `${draft.result.total_lines || 0} 句 / ${(draft.result.chunks || []).length} chunks`);
          enableButton("generateWorldbookBtn", true);
          enableButton("generatePlotBtn", true);
          enableButton("generateRoleBtn", true);
          enableButton("script-copyBtn", true);
          enableButton("script-downloadBtn", true);
          enableButton("generatePresetBtn", Boolean(state.targetLines));
          enableButton("lines-copyBtn", Boolean(state.targetLines));
          enableButton("lines-downloadBtn", Boolean(state.targetLines));
        } else {
          state[tab] = draft.result;
          setOutput(tab, draft.result);
          if (tab === "worldbook") enableOutputButtons("wb", true);
          if (tab === "memory") enableOutputButtons("mem", true);
          if (tab === "preset") enableOutputButtons("pre", true);
          if (tab === "rolecard") enableOutputButtons("rc", true);
          if (tab === "plot") {
            enableButton("plot-copyBtn", true);
            enableButton("plot-downloadBtn", true);
            enableButton("generateMemoryBtn", true);
          }
          setStateText(tab, "已载入");
        }
        if (draft.character_name) $("characterName").value = draft.character_name;
        switchTab(tab);
        setStatus("草稿已载入。");
        updateBundleButtons();
        persistPipelineState();
      });
      list.appendChild(card);
    });
  }

  function bind() {
    document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => switchTab(tab.dataset.tab)));
    document.querySelectorAll(".flow-step").forEach((step) => step.addEventListener("click", () => switchTab(step.dataset.step)));

    $("parseScriptBtn").addEventListener("click", parseScript);
    $("generateWorldbookBtn").addEventListener("click", generateWorldbook);
    $("generatePlotBtn").addEventListener("click", generatePlot);
    $("generateMemoryBtn").addEventListener("click", generateMemory);
    $("generatePresetBtn").addEventListener("click", generatePreset);
    $("generateRoleBtn").addEventListener("click", generateRoleCard);

    $("script-copyBtn").addEventListener("click", () => copyText("script-output"));
    $("script-downloadBtn").addEventListener("click", () => downloadOutput("script"));
    $("lines-copyBtn").addEventListener("click", () => copyText("lines-output"));
    $("lines-downloadBtn").addEventListener("click", () => downloadOutput("lines"));
    $("wb-copyBtn").addEventListener("click", () => copyText("wb-output"));
    $("wb-downloadBtn").addEventListener("click", () => downloadOutput("worldbook"));
    $("plot-copyBtn").addEventListener("click", () => copyText("plot-output"));
    $("plot-downloadBtn").addEventListener("click", () => downloadOutput("plot"));
    $("mem-copyBtn").addEventListener("click", () => copyText("mem-output"));
    $("mem-downloadBtn").addEventListener("click", () => downloadOutput("memory"));
    $("pre-copyBtn").addEventListener("click", () => copyText("pre-output"));
    $("pre-downloadBtn").addEventListener("click", () => downloadOutput("preset"));
    $("rc-copyBtn").addEventListener("click", () => copyText("rc-output"));
    $("rc-downloadBtn").addEventListener("click", () => downloadOutput("rolecard"));

    $("wb-importBtn").addEventListener("click", () => importOne("worldbook"));
    $("mem-importBtn").addEventListener("click", () => importOne("memory"));
    $("pre-importBtn").addEventListener("click", () => importOne("preset"));
    $("rc-importBtn").addEventListener("click", () => importOne("rolecard"));
    $("importAllBtn").addEventListener("click", importAll);
    $("downloadBundleBtn").addEventListener("click", downloadBundle);

    $("saveSettingsBtn").addEventListener("click", saveSettings);
    $("probeModelsBtn").addEventListener("click", probeModels);
    $("confirmYes").addEventListener("click", () => hideConfirm(true));
    $("confirmNo").addEventListener("click", () => hideConfirm(false));
    $("confirmDialog").addEventListener("click", (event) => {
      if (event.target === $("confirmDialog")) hideConfirm(false);
    });
  }

  function init() {
    bind();
    loadDrafts();
    if (restorePipelineState()) setStatus("已恢复上次流水线状态。");
    else setStatus("就绪");
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
