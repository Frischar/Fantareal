(() => {
  "use strict";

  const tabMeta = {
    overview: ["总览", "插件运行状态、数据摘要和快捷操作。"],
    settings: ["生成设置", "承接模型与回复设置。"],
    groups: ["群聊管理", "编辑群聊资料、成员和群级自动行为。"],
    roles: ["角色管理", "维护小手机独立角色资料库。"],
    stickers: ["表情包", "编辑本地 PNG 表情包 manifest。"],
    automation: ["自动行为", "自动插话、空闲触发和频率限制。"],
    prompt: ["Prompt 配置", "管理小手机独立 prompt blocks 与输出契约。"],
    apps: ["应用管理", "管理小手机桌面的轻应用注册表。"],
    channels: ["频道生成", "动态、论坛、邮箱、日记、日程的 seed 与事件。"],
    ui: ["UI 设置", "悬浮球、面板位置和主题设置。"],
    diagnostics: ["诊断", "数据隔离、生成 guard 和运行状态。"],
    data: ["数据工具", "导出、清理和备份工具。"],
  };

  const state = {
    summary: null,
    groups: [],
    roles: [],
    availableRoles: [],
    user: null,
    stickerPacks: [],
    stickers: [],
    manifestRows: [],
    automation: null,
    promptBlocks: [],
    promptPreview: null,
    apps: [],
    channels: [],
    diagnostics: null,
    selectedGroupId: "",
    selectedRoleId: "",
    selectedPackId: "",
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function tagsToText(tags) {
    return Array.isArray(tags) ? tags.join(", ") : "";
  }

  function textToTags(value) {
    return String(value || "")
      .split(/[,，\s]+/)
      .map((item) => item.trim().toLowerCase().replace(/[^a-z0-9_-]+/g, "_").replace(/^_+|_+$/g, ""))
      .filter(Boolean)
      .slice(0, 12);
  }

  function setError(message = "") {
    const box = byId("fmca-error");
    if (!box) return;
    box.textContent = message;
    box.hidden = !message;
  }

  function setToast(message = "") {
    const box = byId("fmca-toast");
    if (!box) return;
    box.textContent = message;
    box.hidden = !message;
    if (message) window.setTimeout(() => setToast(), 2200);
  }

  async function request(path, options = {}) {
    const response = await fetch(`./api${path}`, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || payload.error || `请求失败 (${response.status})`);
    return payload;
  }

  function setTab(name) {
    const tabName = tabMeta[name] ? name : "overview";
    document.querySelectorAll("[data-tab]").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.tab === tabName);
    });
    document.querySelectorAll("[data-panel]").forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.panel === tabName);
    });
    const [title, copy] = tabMeta[tabName];
    byId("fmca-page-title").textContent = title;
    byId("fmca-page-copy").textContent = copy;
    if (window.location.hash.slice(1) !== tabName) {
      window.history.replaceState(null, "", `#${tabName}`);
    }
  }

  function setText(id, value) {
    const element = byId(id);
    if (element) element.textContent = value;
  }

  function renderFacts(containerId, rows) {
    const container = byId(containerId);
    if (!container) return;
    container.innerHTML = rows
      .map(([label, value]) => `<div><dt>${esc(label)}</dt><dd>${esc(value)}</dd></div>`)
      .join("");
  }

  function selectedGroup() {
    return state.groups.find((item) => item.group_id === state.selectedGroupId) || null;
  }

  function selectedRole() {
    return state.roles.find((item) => item.role_id === state.selectedRoleId) || null;
  }

  function selectedPack() {
    return state.stickerPacks.find((item) => item.pack_id === state.selectedPackId) || null;
  }

  function memberCandidates(group) {
    const rows = state.roles
      .filter((role) => role.enabled)
      .map((role) => ({
        role_id: role.role_id,
        name: role.display_name,
        type: "character",
        summary: role.summary || "",
        avatar: role.avatar || "",
      }));
    const seen = new Set(rows.map((item) => item.role_id));
    (group?.members || []).forEach((member) => {
      if (member.type !== "character" || seen.has(member.role_id)) return;
      rows.push(member);
      seen.add(member.role_id);
    });
    return rows.sort((a, b) => a.name.localeCompare(b.name, "zh-Hans-CN"));
  }

  function renderGroups() {
    const container = byId("fmca-group-list");
    if (!container) return;
    if (!state.groups.length) {
      container.innerHTML = '<div class="fmca-empty">暂无群聊。可以先在小手机前台创建，或导入角色后再创建。</div>';
      state.selectedGroupId = "";
      renderGroupEditor();
      return;
    }
    if (!state.selectedGroupId || !state.groups.some((group) => group.group_id === state.selectedGroupId)) {
      state.selectedGroupId = state.groups[0].group_id;
    }
    container.innerHTML = state.groups
      .map((group) => `
        <article class="fmca-list-card">
          <header>
            <div>
              <strong>${esc(group.name)}</strong>
              <span>${esc(group.group_id)} · ${group.members?.length || 0} 人 · 回复 ${esc(group.reply_count || "1-2")}</span>
            </div>
            <button class="fmca-button" type="button" data-action="edit-group" data-group-id="${esc(group.group_id)}">编辑</button>
          </header>
          <p>${esc(group.description || "暂无群聊简介。")}</p>
        </article>
      `)
      .join("");
    renderGroupEditor();
  }

  function renderGroupEditor() {
    const container = byId("fmca-group-editor");
    if (!container) return;
    const group = selectedGroup();
    if (!group) {
      container.innerHTML = '<h3>群聊详情</h3><div class="fmca-placeholder">选择一个群聊后编辑。</div>';
      return;
    }
    const selectedMemberIds = new Set((group.members || []).filter((item) => item.type === "character").map((item) => item.role_id));
    const candidates = memberCandidates(group);
    container.innerHTML = `
      <div class="fmca-editor-header">
        <div>
          <h3>群聊详情</h3>
          <p>${esc(group.group_id)}</p>
        </div>
        <button class="fmca-button fmca-danger" type="button" data-action="delete-group" data-group-id="${esc(group.group_id)}">删除群聊</button>
      </div>
      <form class="fmca-form-grid" data-form="group">
        <label class="fmca-field">
          <span>群名</span>
          <input name="name" maxlength="80" value="${esc(group.name)}" required>
        </label>
        <label class="fmca-field">
          <span>每轮回复角色数</span>
          <select name="reply_count">
            <option value="1" ${group.reply_count === "1" ? "selected" : ""}>1 人</option>
            <option value="1-2" ${group.reply_count !== "1" ? "selected" : ""}>1-2 人</option>
          </select>
        </label>
        <label class="fmca-field is-wide">
          <span>简介</span>
          <textarea name="description" maxlength="500">${esc(group.description || "")}</textarea>
        </label>
        <label class="fmca-check">
          <input type="checkbox" name="allow_role_to_role_reply" ${group.allow_role_to_role_reply !== false ? "checked" : ""}>
          <span>允许角色互相回复</span>
        </label>
        <label class="fmca-check">
          <input type="checkbox" name="allow_auto_interject" ${group.allow_auto_interject ? "checked" : ""}>
          <span>允许本群自动插话</span>
        </label>
        <div class="fmca-member-grid">
          <span>群成员</span>
          <div class="fmca-member-list">
            ${candidates.map((role) => `
              <label>
                <input type="checkbox" name="member" value="${esc(role.role_id)}" ${selectedMemberIds.has(role.role_id) ? "checked" : ""}>
                <span><strong>${esc(role.name)}</strong><br><small class="fmca-muted">${esc(role.summary || role.role_id)}</small></span>
              </label>
            `).join("") || '<div class="fmca-empty">角色库暂无可用角色。</div>'}
          </div>
        </div>
        <div class="fmca-actions">
          <button class="fmca-button fmca-primary" type="submit">保存群聊</button>
        </div>
      </form>
    `;
  }

  function renderRoles() {
    const container = byId("fmca-role-list");
    if (!container) return;
    if (!state.roles.length) {
      container.innerHTML = '<div class="fmca-empty">角色库为空。可以同步当前角色卡，或手动新建角色。</div>';
    } else {
      container.innerHTML = state.roles
        .map((role) => `
          <article class="fmca-list-card${role.enabled ? "" : " is-disabled"}">
            <header>
              <div>
                <strong>${esc(role.display_name)}</strong>
                <span>${esc(role.role_id)} · ${esc(role.source)} · ${role.enabled ? "启用" : "禁用"}</span>
              </div>
              <button class="fmca-button" type="button" data-action="edit-role" data-role-id="${esc(role.role_id)}">编辑</button>
            </header>
            <p>${esc(role.summary || "暂无摘要。")}</p>
          </article>
        `)
        .join("");
    }
    renderRoleEditor();
  }

  function renderRoleEditor() {
    const container = byId("fmca-role-editor");
    if (!container) return;
    const role = selectedRole();
    container.innerHTML = `
      <div class="fmca-editor-header">
        <div>
          <h3>${role ? "编辑角色" : "新建角色"}</h3>
          <p>角色资料只进入小手机 prompt，不写回角色卡。</p>
        </div>
        ${role ? '<button class="fmca-button" type="button" data-action="new-role">新建</button>' : ""}
      </div>
      <form class="fmca-form-grid" data-form="role" data-role-id="${esc(role?.role_id || "")}">
        <label class="fmca-field">
          <span>显示名</span>
          <input name="display_name" maxlength="80" value="${esc(role?.display_name || "")}" required>
        </label>
        <label class="fmca-field">
          <span>Role ID ${role ? "（不可改）" : "（可留空）"}</span>
          <input name="role_id" maxlength="120" value="${esc(role?.role_id || "")}" ${role ? "disabled" : ""}>
        </label>
        <label class="fmca-field">
          <span>别名，逗号分隔</span>
          <input name="aliases" value="${esc(tagsToText(role?.aliases || []))}">
        </label>
        <label class="fmca-field">
          <span>状态</span>
          <input name="status" maxlength="80" value="${esc(role?.status || "online")}">
        </label>
        <label class="fmca-field is-wide">
          <span>摘要</span>
          <textarea name="summary" maxlength="500">${esc(role?.summary || "")}</textarea>
        </label>
        <label class="fmca-field is-wide">
          <span>聊天风格</span>
          <textarea name="chat_style" maxlength="500">${esc(role?.chat_style || "")}</textarea>
        </label>
        <label class="fmca-field">
          <span>偏好 tags</span>
          <input name="preferred_tags" value="${esc(tagsToText(role?.sticker_preferences?.preferred_tags || []))}" placeholder="happy, shy, soft">
        </label>
        <label class="fmca-field">
          <span>屏蔽 tags</span>
          <input name="blocked_tags" value="${esc(tagsToText(role?.sticker_preferences?.blocked_tags || []))}" placeholder="angry">
        </label>
        <label class="fmca-field">
          <span>主动发言权重</span>
          <input name="auto_speak_weight" type="number" min="0" max="10" step="0.1" value="${esc(role?.auto_speak_weight ?? 1)}">
        </label>
        <label class="fmca-check">
          <input type="checkbox" name="enabled" ${role?.enabled === false ? "" : "checked"}>
          <span>启用角色</span>
        </label>
        <div class="fmca-actions">
          <button class="fmca-button fmca-primary" type="submit">${role ? "保存角色" : "创建角色"}</button>
          ${role ? `<button class="fmca-button fmca-danger" type="button" data-action="disable-role" data-role-id="${esc(role.role_id)}">禁用角色</button>` : ""}
        </div>
      </form>
    `;
  }

  function renderStickers() {
    const container = byId("fmca-sticker-list");
    if (!container) return;
    if (!state.selectedPackId) {
      const editable = state.stickerPacks.find((pack) => pack.manifest_editable);
      state.selectedPackId = editable?.pack_id || state.stickerPacks[0]?.pack_id || "";
    }
    container.innerHTML = state.stickerPacks
      .map((pack) => `
        <article class="fmca-list-card">
          <header>
            <div>
              <strong>${esc(pack.label)}</strong>
              <span>${esc(pack.pack_id)} · ${esc(pack.type)} · ${pack.count || 0} 个贴纸</span>
            </div>
            <button class="fmca-button" type="button" data-action="edit-pack" data-pack-id="${esc(pack.pack_id)}">${pack.manifest_editable ? "编辑" : "查看"}</button>
          </header>
          <p>${pack.manifest_editable ? `manifest ${pack.manifest_count || 0} 条 · ${esc(pack.directory || "")}` : "内置贴纸，不写 manifest。"}</p>
        </article>
      `)
      .join("") || '<div class="fmca-empty">暂无表情包。</div>';
    renderStickerEditor();
  }

  function renderStickerEditor() {
    const container = byId("fmca-sticker-editor");
    if (!container) return;
    const pack = selectedPack();
    if (!pack) {
      container.innerHTML = '<h3>Manifest 编辑</h3><div class="fmca-placeholder">选择一个表情包后编辑。</div>';
      return;
    }
    if (!pack.manifest_editable) {
      container.innerHTML = '<h3>Manifest 编辑</h3><div class="fmca-placeholder">内置表情包不支持 manifest 写入。</div>';
      return;
    }
    container.innerHTML = `
      <div class="fmca-editor-header">
        <div>
          <h3>${esc(pack.label)} manifest</h3>
          <p>${esc(pack.directory || "")}</p>
        </div>
        <button class="fmca-button" type="button" data-action="scan-pack" data-pack-id="${esc(pack.pack_id)}">重扫</button>
      </div>
      <form class="fmca-form-grid" data-form="manifest" data-pack-id="${esc(pack.pack_id)}">
        <div class="fmca-manifest-list">
          ${state.manifestRows.map((item, index) => `
            <div class="fmca-manifest-row">
              <div>
                <img class="fmca-sticker-thumb" src="./api${esc(item.url_path)}" alt="${esc(item.label)}" loading="lazy">
                <small>${esc(item.filename)}</small>
                <input type="hidden" name="filename_${index}" value="${esc(item.filename)}">
              </div>
              <label class="fmca-field">
                <span>Label</span>
                <input name="label_${index}" value="${esc(item.label || "")}">
              </label>
              <label class="fmca-field">
                <span>Tags</span>
                <input name="tags_${index}" value="${esc(tagsToText(item.tags || []))}" placeholder="happy, sad, cute">
              </label>
              <label class="fmca-field is-wide">
                <span>Description</span>
                <textarea name="description_${index}" maxlength="120">${esc(item.description || "")}</textarea>
              </label>
            </div>
          `).join("") || '<div class="fmca-empty">未读取到 PNG。</div>'}
        </div>
        <div class="fmca-actions">
          <button class="fmca-button fmca-primary" type="submit">保存 manifest</button>
        </div>
      </form>
    `;
  }

  function renderAutomation() {
    const container = byId("fmca-automation-editor");
    if (!container) return;
    const auto = state.automation?.auto_behavior || state.summary?.settings?.auto_behavior || {};
    const runtime = state.automation?.state || {};
    container.innerHTML = `
      <h3>自动插话设置</h3>
      <form class="fmca-form-grid" data-form="automation">
        <label class="fmca-check">
          <input type="checkbox" name="enabled" ${auto.enabled ? "checked" : ""}>
          <span>启用自动插话</span>
        </label>
        <label class="fmca-check">
          <input type="checkbox" name="active_group_only" ${auto.active_group_only !== false ? "checked" : ""}>
          <span>仅当前打开群聊触发</span>
        </label>
        <label class="fmca-field">
          <span>空闲秒数</span>
          <input name="idle_seconds" type="number" min="15" max="3600" value="${esc(auto.idle_seconds || 90)}">
        </label>
        <label class="fmca-field">
          <span>最小间隔秒数</span>
          <input name="interval_seconds" type="number" min="15" max="3600" value="${esc(auto.interval_seconds || 120)}">
        </label>
        <label class="fmca-field">
          <span>每会话最多轮数</span>
          <input name="max_rounds_per_session" type="number" min="1" max="20" value="${esc(auto.max_rounds_per_session || 3)}">
        </label>
        <label class="fmca-field">
          <span>每小时最多生成</span>
          <input name="max_generations_per_hour" type="number" min="1" max="60" value="${esc(auto.max_generations_per_hour || 6)}">
        </label>
        <div class="fmca-actions">
          <button class="fmca-button fmca-primary" type="submit">保存自动行为</button>
          <button class="fmca-button fmca-danger" type="button" data-action="pause-automation">暂停全部</button>
        </div>
      </form>
      <hr>
      <form class="fmca-form-grid" data-form="automation-test">
        <label class="fmca-field">
          <span>测试群聊</span>
          <select name="group_id">
            ${state.groups.map((group) => `<option value="${esc(group.group_id)}">${esc(group.name)}</option>`).join("")}
          </select>
        </label>
        <div class="fmca-actions">
          <button class="fmca-button" type="submit">测试续聊一次</button>
        </div>
      </form>
      <div class="fmca-placeholder">运行状态：${runtime.paused ? "已暂停" : "未暂停"}${runtime.paused_at ? ` · ${esc(runtime.paused_at)}` : ""}</div>
    `;
  }

  function renderPromptTools() {
    const blocksBox = byId("fmca-prompt-blocks");
    const previewBox = byId("fmca-prompt-preview");
    if (blocksBox) {
      blocksBox.innerHTML = `
        <h3>Prompt Blocks</h3>
        <form class="fmca-form-grid" data-form="prompt-blocks">
          ${(state.promptBlocks || []).map((block, index) => `
            <article class="fmca-mini-card">
              <label class="fmca-check">
                <input type="checkbox" name="enabled_${index}" ${block.enabled ? "checked" : ""} ${block.locked ? "disabled" : ""}>
                <span><strong>${esc(block.label)}</strong> · ${esc(block.block_id)} · order ${esc(block.order)}</span>
              </label>
              <label class="fmca-field is-wide">
                <span>Scope</span>
                <input name="scope_${index}" value="${esc(tagsToText(block.scope || []))}" ${block.locked ? "readonly" : ""}>
              </label>
              <label class="fmca-field is-wide">
                <span>Content</span>
                <textarea name="content_${index}" rows="4" ${block.locked ? "readonly" : ""}>${esc(block.content || "")}</textarea>
              </label>
              <input type="hidden" name="block_id_${index}" value="${esc(block.block_id)}">
              <input type="hidden" name="label_${index}" value="${esc(block.label)}">
              <input type="hidden" name="order_${index}" value="${esc(block.order)}">
              <input type="hidden" name="locked_${index}" value="${block.locked ? "1" : "0"}">
            </article>
          `).join("") || '<div class="fmca-empty">暂无 prompt blocks。</div>'}
          <div class="fmca-actions">
            <button class="fmca-button fmca-primary" type="submit">保存 blocks</button>
          </div>
        </form>
      `;
    }
    if (previewBox) {
      previewBox.textContent = state.promptPreview
        ? JSON.stringify({
            scope: state.promptPreview.scope,
            blocks: (state.promptPreview.blocks || []).map((item) => item.block_id),
            context_preview: state.promptPreview.context_preview,
            assembled_prompt: state.promptPreview.assembled_prompt,
          }, null, 2)
        : "-";
    }
  }

  function renderApps() {
    const container = byId("fmca-app-list");
    if (!container) return;
    container.innerHTML = (state.apps || []).map((app, index) => `
      <article class="fmca-list-card">
        <div class="fmca-list-head">
          <div>
            <strong>${esc(app.label)}</strong>
            <span>${esc(app.app_id)} · ${esc(app.page)} · ${esc(app.stage || "-")}</span>
          </div>
          <label class="fmca-check">
            <input type="checkbox" data-app-enabled="${esc(app.app_id)}" ${app.enabled ? "checked" : ""}>
            <span>启用</span>
          </label>
        </div>
        <div class="fmca-form-grid">
          <label class="fmca-field">
            <span>排序</span>
            <input type="number" data-app-order="${esc(app.app_id)}" value="${esc(app.order ?? (index + 1) * 10)}">
          </label>
          <label class="fmca-field is-wide">
            <span>副标题</span>
            <input data-app-subtitle="${esc(app.app_id)}" value="${esc(app.subtitle || "")}">
          </label>
        </div>
      </article>
    `).join("") || '<div class="fmca-empty">暂无应用。</div>';
  }

  function renderChannels() {
    const container = byId("fmca-channel-list");
    if (!container) return;
    const counts = state.summary?.diagnostics?.channel_event_counts || {};
    container.innerHTML = (state.channels || []).map((channel) => `
      <article class="fmca-list-card">
        <div class="fmca-list-head">
          <div>
            <strong>${esc(channel.label)}</strong>
            <span>${esc(channel.channel_id)} · ${esc(channel.type)} · ${counts[channel.channel_id] || 0} 条</span>
          </div>
          <button class="fmca-button" type="button" data-action="seed-channel" data-channel-id="${esc(channel.channel_id)}">Seed</button>
        </div>
        <p>${esc(channel.description || "暂无描述。")}</p>
      </article>
    `).join("") || '<div class="fmca-empty">暂无频道。</div>';
  }

  function renderDiagnostics() {
    const box = byId("fmca-diagnostics");
    if (!box) return;
    box.textContent = JSON.stringify(state.diagnostics || state.summary?.diagnostics || {}, null, 2);
  }

  function applySettingsForm(settings) {
    byId("fmca-enabled").checked = Boolean(settings.enabled);
    byId("fmca-show-fab").checked = Boolean(settings.show_floating_button);
    byId("fmca-remember-position").checked = Boolean(settings.remember_position);
    byId("fmca-reply-count").value = settings.reply_count === "1" ? "1" : "1-2";
    byId("fmca-max-tokens").value = settings.max_tokens || 500;
    byId("fmca-recent-limit").value = settings.recent_message_limit || 30;
    byId("fmca-role-reply").checked = settings.allow_role_to_role_reply !== false;
  }

  function renderSummary() {
    const summary = state.summary || {};
    const settings = summary.settings || {};
    const model = summary.model_status || {};
    setText("fmca-status", settings.enabled ? "已启用" : "未启用");
    setText("fmca-enabled-state", settings.enabled ? "已启用" : "未启用");
    setText("fmca-groups", String(summary.group_count ?? 0));
    setText("fmca-messages", String(summary.message_count ?? 0));
    setText("fmca-roles", String(summary.role_count ?? 0));
    setText("fmca-stickers", String(summary.sticker_count ?? 0));
    setText("fmca-schema", `v${settings.schema_version || 1}`);
    setText("fmca-apps", String(summary.app_count ?? 0));
    setText("fmca-channel-events", String(summary.channel_event_count ?? 0));
    setText("fmca-notifications", String(summary.notification_count ?? 0));
    setText("fmca-data-dir", summary.data_dir || "data/mobile_chat");
    setText("fmca-model-name", model.model || "未配置");
    setText("fmca-model-url", model.base_url_configured ? "已配置" : "未配置");
    setText("fmca-model-key", model.api_key_configured ? "已配置（已脱敏）" : "未配置");
    setText("fmca-model-temp", String(model.temperature ?? "-"));
    const latestError = summary.latest_error;
    setText(
      "fmca-latest-error",
      latestError
        ? `${latestError.created_at} · ${latestError.group_name}: ${latestError.content}`
        : "暂无错误记录。",
    );
    renderFacts("fmca-auto-facts", [
      ["自动插话", settings.allow_auto_interject ? "已启用" : "关闭"],
      ["空闲触发", `${settings.auto_behavior?.idle_seconds || 90} 秒`],
      ["间隔", `${settings.auto_behavior?.interval_seconds || 120} 秒`],
      ["每小时上限", `${settings.auto_behavior?.max_generations_per_hour || 6} 次`],
    ]);
    renderFacts("fmca-ui-facts", [
      ["悬浮球", settings.show_floating_button ? "显示" : "隐藏"],
      ["记住位置", settings.remember_position ? "开启" : "关闭"],
      ["悬浮球位置", `right ${settings.floating_position?.right ?? 28}, bottom ${settings.floating_position?.bottom ?? 150}`],
      ["面板位置", `right ${settings.panel_position?.right ?? 28}, bottom ${settings.panel_position?.bottom ?? 92}`],
    ]);
    applySettingsForm(settings);
  }

  async function loadManifest(packId) {
    const manifest = await request(`/admin/sticker-packs/${encodeURIComponent(packId)}/manifest`);
    state.selectedPackId = packId;
    state.manifestRows = manifest.stickers || [];
    renderStickers();
  }

  async function refresh() {
    setError();
    try {
      const [summary, groups, roles, stickers, automation, promptBlocks, promptPreview, apps, channels, diagnostics] = await Promise.all([
        request("/admin/summary"),
        request("/groups"),
        request("/admin/roles"),
        request("/admin/sticker-packs"),
        request("/admin/automation"),
        request("/admin/prompt-blocks"),
        request("/admin/prompt-preview?scope=group_chat"),
        request("/admin/apps"),
        request("/admin/channels"),
        request("/admin/diagnostics"),
      ]);
      state.summary = summary;
      state.groups = groups.groups || [];
      state.roles = roles.roles || [];
      state.availableRoles = roles.available || [];
      state.user = roles.user || null;
      state.stickerPacks = stickers.packs || [];
      state.stickers = stickers.stickers || [];
      state.automation = automation;
      state.promptBlocks = promptBlocks.blocks || [];
      state.promptPreview = promptPreview;
      state.apps = apps.apps || [];
      state.channels = channels.channels || [];
      state.diagnostics = diagnostics.diagnostics || null;
      renderSummary();
      renderGroups();
      renderRoles();
      renderStickers();
      renderAutomation();
      renderPromptTools();
      renderApps();
      renderChannels();
      renderDiagnostics();
      const pack = selectedPack();
      if (pack?.manifest_editable && !state.manifestRows.length) {
        await loadManifest(pack.pack_id);
      }
    } catch (error) {
      setText("fmca-status", "读取失败");
      setError(error.message);
    }
  }

  async function saveSettings(event) {
    event.preventDefault();
    setError();
    const payload = {
      enabled: byId("fmca-enabled").checked,
      show_floating_button: byId("fmca-show-fab").checked,
      remember_position: byId("fmca-remember-position").checked,
      reply_count: byId("fmca-reply-count").value,
      max_tokens: Number.parseInt(byId("fmca-max-tokens").value, 10),
      recent_message_limit: Number.parseInt(byId("fmca-recent-limit").value, 10),
      allow_role_to_role_reply: byId("fmca-role-reply").checked,
    };
    try {
      await request("/settings", { method: "POST", body: JSON.stringify(payload) });
      await refresh();
      setToast("设置已保存。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function saveGroup(form) {
    const group = selectedGroup();
    if (!group) return;
    const data = new FormData(form);
    const selected = new Set(data.getAll("member").map(String));
    const members = memberCandidates(group).filter((item) => selected.has(item.role_id));
    try {
      await request(`/groups/${encodeURIComponent(group.group_id)}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: data.get("name"),
          description: data.get("description"),
          members,
          reply_count: data.get("reply_count"),
          allow_role_to_role_reply: data.has("allow_role_to_role_reply"),
          allow_auto_interject: data.has("allow_auto_interject"),
        }),
      });
      await refresh();
      setToast("群聊已保存。");
    } catch (error) {
      setError(error.message);
    }
  }

  function rolePayloadFrom(form) {
    const data = new FormData(form);
    return {
      role_id: data.get("role_id") || undefined,
      display_name: data.get("display_name"),
      aliases: String(data.get("aliases") || "").split(/[,，\n]+/).map((item) => item.trim()).filter(Boolean),
      status: data.get("status"),
      summary: data.get("summary"),
      chat_style: data.get("chat_style"),
      auto_speak_weight: Number.parseFloat(data.get("auto_speak_weight") || "1"),
      enabled: data.has("enabled"),
      sticker_preferences: {
        preferred_tags: textToTags(data.get("preferred_tags")),
        blocked_tags: textToTags(data.get("blocked_tags")),
      },
    };
  }

  async function saveRole(form) {
    const roleId = form.dataset.roleId || "";
    const payload = rolePayloadFrom(form);
    try {
      const result = roleId
        ? await request(`/admin/roles/${encodeURIComponent(roleId)}`, { method: "PATCH", body: JSON.stringify(payload) })
        : await request("/admin/roles", { method: "POST", body: JSON.stringify(payload) });
      state.selectedRoleId = result.role?.role_id || roleId;
      await refresh();
      setToast("角色资料已保存。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function saveManifest(form) {
    const packId = form.dataset.packId;
    const data = new FormData(form);
    const stickers = [];
    for (let index = 0; index < state.manifestRows.length; index += 1) {
      stickers.push({
        filename: data.get(`filename_${index}`),
        label: data.get(`label_${index}`),
        tags: textToTags(data.get(`tags_${index}`)),
        description: data.get(`description_${index}`),
      });
    }
    try {
      const result = await request(`/admin/sticker-packs/${encodeURIComponent(packId)}/manifest`, {
        method: "PUT",
        body: JSON.stringify({ stickers }),
      });
      state.manifestRows = result.stickers || [];
      await refresh();
      setToast("Manifest 已保存。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function saveAutomation(form) {
    const data = new FormData(form);
    try {
      await request("/admin/automation", {
        method: "PATCH",
        body: JSON.stringify({
          enabled: data.has("enabled"),
          active_group_only: data.has("active_group_only"),
          idle_seconds: Number.parseInt(data.get("idle_seconds"), 10),
          interval_seconds: Number.parseInt(data.get("interval_seconds"), 10),
          max_rounds_per_session: Number.parseInt(data.get("max_rounds_per_session"), 10),
          max_generations_per_hour: Number.parseInt(data.get("max_generations_per_hour"), 10),
        }),
      });
      await refresh();
      setToast("自动行为已保存。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function savePromptBlocks(form) {
    const data = new FormData(form);
    const blocks = (state.promptBlocks || []).map((block, index) => ({
      block_id: data.get(`block_id_${index}`) || block.block_id,
      label: data.get(`label_${index}`) || block.label,
      order: Number.parseInt(data.get(`order_${index}`), 10),
      locked: data.get(`locked_${index}`) === "1",
      enabled: block.locked ? block.enabled : data.has(`enabled_${index}`),
      scope: textToTags(data.get(`scope_${index}`)),
      content: data.get(`content_${index}`) || "",
    }));
    try {
      const result = await request("/admin/prompt-blocks", { method: "PUT", body: JSON.stringify({ blocks }) });
      state.promptBlocks = result.blocks || [];
      state.promptPreview = await request("/admin/prompt-preview?scope=group_chat");
      renderPromptTools();
      setToast("Prompt blocks 已保存。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function saveApps() {
    const apps = (state.apps || []).map((app) => ({
      ...app,
      enabled: Boolean(document.querySelector(`[data-app-enabled="${CSS.escape(app.app_id)}"]`)?.checked),
      order: Number.parseInt(document.querySelector(`[data-app-order="${CSS.escape(app.app_id)}"]`)?.value || app.order || 0, 10),
      subtitle: document.querySelector(`[data-app-subtitle="${CSS.escape(app.app_id)}"]`)?.value || app.subtitle || "",
    }));
    try {
      const result = await request("/admin/apps", { method: "PUT", body: JSON.stringify({ apps }) });
      state.apps = result.apps || [];
      renderApps();
      setToast("轻应用注册表已保存。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function refreshPromptPreview() {
    try {
      state.promptPreview = await request("/admin/prompt-preview?scope=group_chat");
      renderPromptTools();
      setToast("Prompt preview 已刷新。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function refreshDiagnostics() {
    try {
      const result = await request("/admin/diagnostics");
      state.diagnostics = result.diagnostics || {};
      renderDiagnostics();
      setToast("诊断已刷新。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function seedChannel(channelId) {
    const channel = state.channels.find((item) => item.channel_id === channelId);
    if (!channel) return;
    if (!window.confirm(`Seed 会真实调用模型，为「${channel.label}」生成内容，继续？`)) return;
    try {
      await request("/admin/seed-channel", {
        method: "POST",
        body: JSON.stringify({ channel_id: channelId, count: channel.seed_count || 5, force: true }),
      });
      await refresh();
      setToast("频道内容已生成。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function testAutomation(form) {
    const data = new FormData(form);
    const groupId = String(data.get("group_id") || "");
    if (!groupId) return;
    if (!window.confirm("测试会真实调用模型生成一次，继续？")) return;
    try {
      await request("/admin/automation/test-once", {
        method: "POST",
        body: JSON.stringify({ group_id: groupId }),
      });
      await refresh();
      setToast("测试续聊已完成。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function resetPosition() {
    setError();
    try {
      await request("/settings", {
        method: "POST",
        body: JSON.stringify({
          floating_position: { right: 28, bottom: 150 },
          panel_position: { right: 28, bottom: 92 },
        }),
      });
      await refresh();
      setToast("位置已复位。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function clearGroups() {
    if (!window.confirm("清空全部小手机群聊和消息记录？此操作无法撤销。")) return;
    setError();
    try {
      await request("/groups", { method: "DELETE" });
      await refresh();
      setToast("群聊记录已清空。");
    } catch (error) {
      setError(error.message);
    }
  }

  async function onClick(event) {
    const button = event.target.closest("[data-action], #fmca-sync-current-card, #fmca-import-group-roles");
    if (!button) return;
    setError();
    try {
      if (button.id === "fmca-sync-current-card") {
        await request("/admin/roles/sync-current-card", { method: "POST" });
        await refresh();
        setToast("已同步当前角色卡。");
        return;
      }
      if (button.id === "fmca-import-group-roles") {
        await request("/admin/roles/import-from-groups", { method: "POST" });
        await refresh();
        setToast("已从群聊导入角色。");
        return;
      }
      const action = button.dataset.action;
      if (action === "edit-group") {
        state.selectedGroupId = button.dataset.groupId || "";
        renderGroups();
      }
      if (action === "delete-group") {
        if (!window.confirm("删除该小手机群聊？")) return;
        await request(`/groups/${encodeURIComponent(button.dataset.groupId || "")}`, { method: "DELETE" });
        state.selectedGroupId = "";
        await refresh();
        setToast("群聊已删除。");
      }
      if (action === "edit-role") {
        state.selectedRoleId = button.dataset.roleId || "";
        renderRoles();
      }
      if (action === "new-role") {
        state.selectedRoleId = "";
        renderRoles();
      }
      if (action === "disable-role") {
        if (!window.confirm("禁用该角色？已存在群聊不会被自动删除。")) return;
        await request(`/admin/roles/${encodeURIComponent(button.dataset.roleId || "")}`, { method: "DELETE" });
        await refresh();
        setToast("角色已禁用。");
      }
      if (action === "edit-pack") {
        state.manifestRows = [];
        const packId = button.dataset.packId || "";
        const pack = state.stickerPacks.find((item) => item.pack_id === packId);
        state.selectedPackId = packId;
        if (pack?.manifest_editable) {
          await loadManifest(packId);
        } else {
          renderStickers();
        }
      }
      if (action === "scan-pack") {
        const result = await request(`/admin/sticker-packs/${encodeURIComponent(button.dataset.packId || "")}/scan`, { method: "POST" });
        state.manifestRows = result.stickers || [];
        renderStickerEditor();
        setToast("表情包已重扫。");
      }
      if (action === "pause-automation") {
        await request("/admin/automation/pause-all", { method: "POST" });
        await refresh();
        setToast("自动行为已暂停。");
      }
      if (action === "refresh-prompt-preview") {
        await refreshPromptPreview();
      }
      if (action === "reset-prompt-blocks") {
        if (!window.confirm("重置 prompt blocks？")) return;
        const result = await request("/admin/prompt-blocks/reset", { method: "POST" });
        state.promptBlocks = result.blocks || [];
        await refreshPromptPreview();
      }
      if (action === "save-apps") {
        await saveApps();
      }
      if (action === "reset-apps") {
        if (!window.confirm("重置轻应用注册表？")) return;
        const result = await request("/admin/apps/reset", { method: "POST" });
        state.apps = result.apps || [];
        renderApps();
        setToast("轻应用已重置。");
      }
      if (action === "seed-channel") {
        await seedChannel(button.dataset.channelId || "");
      }
      if (action === "refresh-diagnostics") {
        await refreshDiagnostics();
      }
      if (action === "reset-generation-guard") {
        const result = await request("/admin/generation-guard/reset", { method: "POST" });
        state.diagnostics = { ...(state.diagnostics || {}), generation_state: result.state };
        await refreshDiagnostics();
      }
    } catch (error) {
      setError(error.message);
    }
  }

  function onSubmit(event) {
    const form = event.target.closest("form[data-form]");
    if (!form) return;
    event.preventDefault();
    setError();
    if (form.dataset.form === "group") void saveGroup(form);
    if (form.dataset.form === "role") void saveRole(form);
    if (form.dataset.form === "manifest") void saveManifest(form);
    if (form.dataset.form === "automation") void saveAutomation(form);
    if (form.dataset.form === "automation-test") void testAutomation(form);
    if (form.dataset.form === "prompt-blocks") void savePromptBlocks(form);
  }

  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => setTab(button.dataset.tab));
  });
  byId("fmca-refresh").addEventListener("click", refresh);
  byId("fmca-settings-form").addEventListener("submit", saveSettings);
  byId("fmca-reset-form").addEventListener("click", () => {
    if (state.summary?.settings) applySettingsForm(state.summary.settings);
  });
  byId("fmca-reset-position").addEventListener("click", resetPosition);
  byId("fmca-clear").addEventListener("click", clearGroups);
  byId("fmca-clear-data").addEventListener("click", clearGroups);
  document.addEventListener("click", (event) => { void onClick(event); });
  document.addEventListener("submit", onSubmit);

  window.addEventListener("hashchange", () => setTab(window.location.hash.slice(1)));
  setTab(window.location.hash.slice(1) || "overview");
  void refresh();
})();
