(() => {
  "use strict";

  const API_BASE = (window.CARD_WRITER_API_BASE || "").replace(/\/$/, "");
  const PROJECT_TYPE = "fantareal_card_writer_project";
  const COPILOT_THINKING_MODES = {
    fast: "快速模式",
    deep: "深度思考",
  };

  const VIEW_META = {
    persona: { title: "人设" },
    worldbook: { title: "世界书" },
    preset: { title: "预设" },
    memory: { title: "记忆" },
    database: { title: "数据库" },
    preview: { title: "预览" },
  };

  const PERSONA_FIELDS = [
    { key: "name", label: "角色名", type: "text", placeholder: "角色名", hint: "JSON key: name" },
    { key: "description", label: "角色描述", type: "textarea", rows: 5, placeholder: "角色描述 / 设定简介", spanTwo: true, hint: "JSON key: description" },
    { key: "personality", label: "性格口吻", type: "textarea", rows: 5, placeholder: "性格、说话习惯、气质", spanTwo: true, hint: "JSON key: personality" },
    { key: "scenario", label: "默认场景", type: "textarea", rows: 4, placeholder: "默认场景 / 初始状态", spanTwo: true, hint: "JSON key: scenario" },
    { key: "first_mes", label: "开场白", type: "textarea", rows: 4, placeholder: "角色第一句开场白", spanTwo: true, hint: "JSON key: first_mes" },
    { key: "mes_example", label: "示例对话", type: "textarea", rows: 6, placeholder: "示例对话", spanTwo: true, hint: "JSON key: mes_example" },
    { key: "creator_notes", label: "隐藏规则", type: "textarea", rows: 4, placeholder: "补充规则 / 隐藏说明", spanTwo: true, hint: "JSON key: creator_notes" },
  ];

  const WORLDBOOK_SETTING_FIELDS = [
    { key: "enabled", label: "启用世界书", type: "checkbox" },
    { key: "debug_enabled", label: "调试模式", type: "checkbox" },
    { key: "max_hits", label: "最大命中数", type: "number" },
    { key: "default_case_sensitive", label: "默认区分大小写", type: "checkbox" },
    { key: "default_whole_word", label: "默认整词匹配", type: "checkbox" },
    { key: "default_match_mode", label: "默认主触发匹配模式", type: "text" },
    { key: "default_secondary_mode", label: "默认副触发匹配模式", type: "text" },
    { key: "default_entry_type", label: "默认条目类型", type: "text" },
    { key: "default_group_operator", label: "默认分组运算", type: "text" },
    { key: "default_chance", label: "默认触发概率", type: "number" },
    { key: "default_sticky_turns", label: "默认粘滞轮数", type: "number" },
    { key: "default_cooldown_turns", label: "默认冷却轮数", type: "number" },
    { key: "default_insertion_position", label: "默认插入位置", type: "text" },
    { key: "default_injection_depth", label: "默认注入深度", type: "number" },
    { key: "default_injection_role", label: "默认注入角色", type: "text" },
    { key: "default_injection_order", label: "默认注入顺序", type: "number" },
    { key: "default_prompt_layer", label: "默认提示词层", type: "text" },
    { key: "recursive_scan_enabled", label: "启用递归扫描", type: "checkbox" },
    { key: "recursion_max_depth", label: "递归最大深度", type: "number" },
  ];

  const WORLDBOOK_ENTRY_FIELDS = [
    { key: "title", label: "标题", type: "text" },
    { key: "trigger", label: "主触发词", type: "text" },
    { key: "secondary_trigger", label: "副触发词", type: "text" },
    { key: "entry_type", label: "条目类型", type: "text" },
    { key: "group_operator", label: "分组运算", type: "text" },
    { key: "match_mode", label: "主触发匹配模式", type: "text" },
    { key: "secondary_mode", label: "副触发匹配模式", type: "text" },
    { key: "group", label: "分组", type: "text" },
    { key: "chance", label: "触发概率", type: "number" },
    { key: "sticky_turns", label: "粘滞轮数", type: "number" },
    { key: "cooldown_turns", label: "冷却轮数", type: "number" },
    { key: "order", label: "排序", type: "number" },
    { key: "priority", label: "优先级", type: "number" },
    { key: "insertion_position", label: "插入位置", type: "text" },
    { key: "injection_depth", label: "注入深度", type: "number" },
    { key: "injection_order", label: "注入顺序", type: "number" },
    { key: "injection_role", label: "注入角色", type: "text" },
    { key: "prompt_layer", label: "提示词层", type: "text" },
    { key: "recursive_enabled", label: "允许递归", type: "checkbox" },
    { key: "prevent_further_recursion", label: "阻止继续递归", type: "checkbox" },
    { key: "enabled", label: "启用条目", type: "checkbox" },
    { key: "case_sensitive", label: "区分大小写", type: "checkbox" },
    { key: "whole_word", label: "整词匹配", type: "checkbox" },
    { key: "content", label: "正文内容", type: "textarea", rows: 8, spanTwo: true },
    { key: "comment", label: "备注", type: "textarea", rows: 4, spanTwo: true },
  ];

  const MEMORY_FIELDS = [
    { key: "id", label: "记忆 ID", type: "text" },
    { key: "title", label: "标题", type: "text" },
    { key: "tags", label: "标签", type: "tags" },
    { key: "content", label: "记忆正文", type: "textarea", rows: 8, spanTwo: true },
    { key: "notes", label: "备注", type: "textarea", rows: 4, spanTwo: true },
  ];

  const EXTRA_PROMPT_FIELDS = [
    { key: "id", label: "子提示 ID", type: "text" },
    { key: "name", label: "名称", type: "text" },
    { key: "enabled", label: "启用", type: "checkbox" },
    { key: "order", label: "顺序", type: "number" },
    { key: "content", label: "提示内容", type: "textarea", rows: 5, spanTwo: true },
  ];

  const PRESET_FIELDS = [
    { key: "id", label: "预设 ID", type: "text" },
    { key: "name", label: "名称", type: "text" },
    { key: "enabled", label: "启用", type: "checkbox" },
    { key: "base_system_prompt", label: "基础系统提示词", type: "textarea", rows: 10, spanTwo: true },
  ];

  const DATABASE_VARIABLE_FIELDS = [
    { key: "id", label: "变量 ID", type: "text" },
    { key: "key", label: "变量 key", type: "text", hint: "例如 trust / guard / intimacy" },
    { key: "label", label: "显示名", type: "text" },
    { key: "value_type", label: "值类型", type: "text" },
    { key: "initial_value", label: "初始值", type: "text" },
    { key: "scope", label: "作用域", type: "text" },
    { key: "description", label: "变量含义", type: "textarea", rows: 5, spanTwo: true },
    { key: "write_policy", label: "写入纪律", type: "textarea", rows: 5, spanTwo: true },
    { key: "notes", label: "备注", type: "textarea", rows: 4, spanTwo: true },
  ];

  const DATABASE_STAGE_FIELDS = [
    { key: "id", label: "阶段 ID", type: "text" },
    { key: "role_id", label: "角色 ID", type: "text" },
    { key: "stage_key", label: "阶段 key", type: "text" },
    { key: "title", label: "阶段名", type: "text" },
    { key: "condition", label: "判定条件", type: "textarea", rows: 5, spanTwo: true },
    { key: "active_tag", label: "主 tag", type: "text", spanTwo: true },
    { key: "emits_tags", label: "发出 tags", type: "tags", spanTwo: true },
    { key: "description", label: "阶段表现", type: "textarea", rows: 5, spanTwo: true },
    { key: "notes", label: "备注", type: "textarea", rows: 4, spanTwo: true },
  ];

  const DATABASE_TAG_FIELDS = [
    { key: "id", label: "Tag ID", type: "text" },
    { key: "tag", label: "Tag", type: "text", spanTwo: true },
    { key: "title", label: "显示名", type: "text" },
    { key: "target", label: "目标", type: "text" },
    { key: "trigger", label: "触发说明", type: "textarea", rows: 4, spanTwo: true },
    { key: "description", label: "连接意图", type: "textarea", rows: 5, spanTwo: true },
    { key: "notes", label: "备注", type: "textarea", rows: 4, spanTwo: true },
  ];

  const WORKSHOP_FIELDS = [
    { key: "id", label: "事件 ID", type: "text" },
    { key: "name", label: "事件名", type: "text" },
    { key: "enabled", label: "启用", type: "checkbox" },
    { key: "triggerMode", label: "触发模式", type: "text" },
    { key: "triggerStage", label: "触发阶段", type: "text" },
    { key: "triggerTempMin", label: "最低温度", type: "number" },
    { key: "triggerTempMax", label: "最高温度", type: "number" },
    { key: "actionType", label: "动作类型", type: "text" },
    { key: "popupTitle", label: "弹窗标题", type: "text" },
    { key: "musicPreset", label: "音乐预设", type: "text" },
    { key: "musicUrl", label: "音乐地址", type: "text" },
    { key: "autoplay", label: "自动播放", type: "checkbox" },
    { key: "loop", label: "循环播放", type: "checkbox" },
    { key: "volume", label: "音量", type: "number", step: "0.1" },
    { key: "imageUrl", label: "图片地址", type: "text" },
    { key: "imageAlt", label: "图片替代文本", type: "text" },
    { key: "note", label: "备注", type: "textarea", rows: 4, spanTwo: true },
  ];

  const PERSONA_SUB_FIELDS = [
    { key: "name", label: "persona 名称", type: "text" },
    { key: "description", label: "persona 描述", type: "textarea", rows: 4, spanTwo: true },
    { key: "personality", label: "persona 性格", type: "textarea", rows: 4, spanTwo: true },
    { key: "scenario", label: "persona 场景", type: "textarea", rows: 4, spanTwo: true },
    { key: "creator_notes", label: "persona 备注", type: "textarea", rows: 4, spanTwo: true },
  ];

  const MODULE_LABELS = {
    no_user_speaking: "禁止代替用户说话",
    short_paragraph: "短段落输出",
    long_paragraph: "长段落输出",
    second_person: "偏第二人称",
    third_person: "偏第三人称",
    anti_repeat: "减少重复表达",
    no_closing_feel: "避免收束感",
    emotion_detail: "强化情绪细节",
    multi_character_boundary: "强化多角色边界",
    scene_continuation: "强化场景连续性",
    v4f_output_guard: "V4F 输出保护",
  };

  const DEFAULT_COPILOT_SETTINGS = {
    base_url: "",
    api_key: "",
    model: "",
    request_timeout: 120,
    temperature: 0.8,
    base_system_prompt: "你是缃笺 Card Writer 的结构化写作助手。",
    persona_prompt: "你要为 Fa Card Writer 生成人设卡候选，输出内容必须可直接写入编辑器表单。\n重点要求：\n1. description 写身份、处境、关系起点和稳定事实，不要堆抽象形容词。\n2. personality 写可执行反应：欲望、边界、防御、亲近方式、退缩方式、语言纹理。\n3. scenario 写默认局势和关系张力，不要把完整世界观塞进来。\n4. first_mes 必须是角色真实会说/会做的开场，不写作者说明。\n5. mes_example 只写示例对话和动作节奏，不要代替 {{user}} 做过多决定。\n6. creator_notes 写隐藏纪律：不跳关系阶段、不突然坦白、亲密和身体反应必须符合角色边界。\n7. 如果是分身 persona，只生成当前分身所需字段，不扩写整张主卡。",
    worldbook_prompt: "你要为 Fa Card Writer 生成世界书候选，输出必须适合直接落入当前 entry。\n重点要求：\n1. 一个 entry 只承载一个事实、阶段、地点、组织、秘密或状态表现。\n2. trigger 要便于触发；阶段表现可在 title/comment 中标明未来可由 tag 触发。\n3. content 写成可注入上下文的正文，不写闲聊口吻和作者解释。\n4. 阶段表现应约束“当前会怎样表现”，不要重复整张角色卡。\n5. 优先使用 Fa runtime 可识别的语义：keyword/constant/external_tag、any/all、stable/current_state/dynamic/output_guard。\n6. comment 只写维护备注，不重复正文。",
    preset_prompt: "你要为 Fa Card Writer 生成轻量预设适配候选，不要尝试从零创作高阶预设或大型叙事引擎。\n重点要求：\n1. preset 只做基础适配纪律：不替用户行动、不跳阶段、不突然亲密、不突然完全信任。\n2. base_system_prompt 只写模型如何读取角色卡、世界书、记忆和状态，不写具体世界观百科。\n3. modules 只开启真正需要的开关，避免互相冲突。\n4. extra_prompts 可补充防总结腔、防替用户、防阶段跳跃等短规则。\n5. prompt_groups 默认保持精简；不要生成复杂风格库或大型高阶预设结构。\n6. 更重要的内容优先落到 persona、worldbook、memory、database。",
    memory_prompt: "你要为 Fa Card Writer 生成记忆候选，输出必须适合直接写入 memory item。\n重点要求：\n1. content 聚焦单个已发生事实、事件、关系变化或长期偏好，不写散乱总结。\n2. 不要把未发生的剧情冒充记忆；未发生内容应写到 scenario、worldbook 或 preset。\n3. title 要短而明确，能快速说明这条记忆的主题。\n4. tags 保持精简，便于检索，不要堆很多同义词。\n5. notes 写维护信息、时间线提醒或补充说明，可标明这条记忆会影响哪些关系变量。\n6. 每条记忆应当独立成立，便于后续单独删改。",
    database_prompt: "你要为 Fa Card Writer 生成数据库草稿候选，输出必须只写当前工程里的 database 草稿 JSON，不要尝试写运行时 SQLite 或真实状态库。\n重点要求：\n1. 数据库的意义是记录变量、判断阶段、发出 tag，用来触发世界书或演出工坊。\n2. variables 写可被追踪的状态，例如 trust、guard、intimacy、desire、fatigue、jealousy；必须说明变量含义和写入纪律。\n3. stages 写阶段判断规则和会发出的 tag，例如 state_journal.stage.<role_id>.<stage_key>。\n4. tags 写 tag 与世界书/演出工坊的连接意图，不要写大段剧情正文。\n5. 这是 P1 写卡草稿，只服务于设计和导出；不要伪装成已接入运行时。",
  };

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));

  function apiUrl(path) {
    const normalizedPath = String(path || "");
    if (!normalizedPath) return API_BASE || "";
    if (/^https?:\/\//i.test(normalizedPath)) return normalizedPath;
    return `${API_BASE}${normalizedPath.startsWith("/") ? normalizedPath : `/${normalizedPath}`}`;
  }

  const LOCAL_DRAFT_KEY = "cardWriterDraft:v1";
  const THEME_KEY = "cardWriterTheme:v1";

  function createDefaultCollapsedSections() {
    return {
      messages: false,
      review: false,
      input: false,
      "copilot-plan": false,
      "copilot-package-audit": false,
    };
  }

  let project = normalizeProject(window.CARD_WRITER_BOOTSTRAP || {});
  let copilotSettings = normalizeCopilotSettings(window.CARD_WRITER_COPILOT_SETTINGS || DEFAULT_COPILOT_SETTINGS);
  let currentFilename = "";
  let selectedProjectFilename = "";
  let compileCache = null;
  let autoSaveTimer = null;
  let saveStatusTimer = null;
  let currentView = "persona";
  let selectedIndices = {
    worldbookEntry: 0,
    memoryItem: 0,
    presetItem: 0,
    personaItem: 0,
    databaseVariable: 0,
    databaseStage: 0,
    databaseTag: 0,
  };
  let activeDatabaseKind = "variables";
  let validationCache = [];
  let lastEditingView = "persona";
  let faBinding = null;
  let faApplyPreview = null;
  let faApplySelectedGroupIds = new Set();
  let copilotState = {
    open: false,
    messages: [],
    loading: false,
    pendingReview: null,
    selectedCandidateIds: [],
    collapsedSections: createDefaultCollapsedSections(),
    collapsedCandidateIds: [],
    lastPrompt: "",
    thinkingMode: "fast",
    lastResolvedContext: null,
  };

  let suppressLocalDraftWrite = false;

  function readLocalDraft() {
    try {
      const raw = window.localStorage?.getItem(LOCAL_DRAFT_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch {
      return null;
    }
  }

  function writeLocalDraft(payload) {
    try {
      window.localStorage?.setItem(LOCAL_DRAFT_KEY, JSON.stringify(payload));
    } catch {
      // ignore
    }
  }

  function getCopilotSettingsFormSnapshot() {
    if (!$("#copilotBaseUrl")) {
      return normalizeCopilotSettings(copilotSettings);
    }
    return collectCopilotSettingsForm();
  }

  function buildProjectFingerprint(sourceProject = project) {
    return stableStringify(normalizeProject(sourceProject || {}));
  }

  function buildUnsavedCopilotSettingsDraft() {
    const draft = getCopilotSettingsFormSnapshot();
    return stableStringify(draft) === stableStringify(copilotSettings) ? null : draft;
  }

  function buildPersistedProjectDraft() {
    return structuredCloneCompat(normalizeProject(project));
  }

  function buildPersistedCopilotState(includeReview = true) {
    return {
      open: includeReview ? Boolean(copilotState.open) : false,
      messages: includeReview ? structuredCloneCompat(copilotState.messages || []) : [],
      pendingReview: includeReview && copilotState.pendingReview ? structuredCloneCompat(copilotState.pendingReview) : null,
      selectedCandidateIds: includeReview ? [...(copilotState.selectedCandidateIds || [])] : [],
      collapsedSections: {
        ...createDefaultCollapsedSections(),
        ...(includeReview ? (copilotState.collapsedSections || {}) : {}),
      },
      collapsedCandidateIds: includeReview ? [...(copilotState.collapsedCandidateIds || [])] : [],
      lastPrompt: String(copilotState.lastPrompt || ""),
      thinkingMode: normalizeCopilotThinkingMode(copilotState.thinkingMode),
    };
  }

  function syncProjectFromRenderedFields() {
    if (suppressLocalDraftWrite) return;

    $$('[data-path]').forEach((target) => {
      const path = target.dataset.path;
      if (!path) return;
      const kind = target.type === "checkbox" ? "checkbox" : (target.dataset.valueKind || "text");
      if (path.endsWith('.__key__')) return;
      setByPath(project, path, readInputValue(target, kind));
    });

    $$('[data-json-path]').forEach((target) => {
      const path = target.dataset.jsonPath;
      if (!path) return;
      try {
        const parsed = JSON.parse(target.value || '[]');
        setByPath(project, path, parsed);
      } catch {
        // ignore invalid in-memory json while flushing draft
      }
    });

    const titleInput = $('#projectTitle');
    if (titleInput) {
      project.title = titleInput.value.trim();
    }
    if (!project.title) {
      project.title = String(project.persona_card?.name || '').trim();
    }
  }

  function persistLocalDraft({ includeReview = true, skipSync = false } = {}) {
    if (!skipSync) syncProjectFromRenderedFields();
    writeLocalDraft({
      savedAt: new Date().toISOString(),
      projectFingerprint: buildProjectFingerprint(project),
      projectDraft: buildPersistedProjectDraft(),
      copilotSettingsDraft: buildUnsavedCopilotSettingsDraft(),
      currentView,
      currentFilename,
      activeDatabaseKind,
      selectedIndices: { ...selectedIndices },
      copilotState: buildPersistedCopilotState(includeReview),
    });
  }

  function flushDraftForReload({ includeReview = true, sendAutosave = false } = {}) {
    persistLocalDraft({ includeReview });
    const payload = JSON.stringify(project);
    if (sendAutosave && typeof navigator.sendBeacon === "function") {
      try {
        navigator.sendBeacon(apiUrl("/api/autosave"), new Blob([payload], { type: "application/json" }));
      } catch {
        // ignore
      }
    }
    if (currentFilename && typeof navigator.sendBeacon === "function") {
      try {
        navigator.sendBeacon(apiUrl(`/api/projects/${encodeURIComponent(currentFilename)}`), new Blob([payload], { type: "application/json" }));
      } catch {
        // ignore
      }
    }
  }

  function clearLocalReviewDraft({ keepProjectDraft = true } = {}) {
    const draft = readLocalDraft();
    writeLocalDraft({
      savedAt: new Date().toISOString(),
      projectFingerprint: buildProjectFingerprint(project),
      projectDraft: keepProjectDraft && draft?.projectDraft ? structuredCloneCompat(draft.projectDraft) : buildPersistedProjectDraft(),
      copilotSettingsDraft: buildUnsavedCopilotSettingsDraft(),
      currentView,
      currentFilename,
      activeDatabaseKind,
      selectedIndices: { ...selectedIndices },
      copilotState: buildPersistedCopilotState(false),
    });
  }

  function parseDraftTime(value) {
    const time = Date.parse(String(value || ""));
    return Number.isFinite(time) ? time : 0;
  }

  function restoreLocalDraft({ preferProjectDraft = true } = {}) {
    const draft = readLocalDraft();
    if (!draft) return;

    suppressLocalDraftWrite = true;
    try {
      const workspaceFingerprint = buildProjectFingerprint(project);
      const projectDraft = draft.projectDraft && typeof draft.projectDraft === "object"
        ? normalizeProject(draft.projectDraft)
        : null;
      const draftFingerprint = String(draft.projectFingerprint || "");
      const projectDraftFingerprint = projectDraft ? buildProjectFingerprint(projectDraft) : "";
      if (projectDraft && preferProjectDraft) {
        project = projectDraft;
      }

      const settingsDraft = draft.copilotSettingsDraft ? normalizeCopilotSettings(draft.copilotSettingsDraft) : null;
      if (settingsDraft) {
        copilotSettings = settingsDraft;
        fillCopilotSettingsForm();
      }

      if (draftFingerprint !== workspaceFingerprint && draftFingerprint !== projectDraftFingerprint) {
        clearLocalReviewDraft();
        return;
      }

      const storedState = draft.copilotState || {};
      const storedView = String(draft.currentView || "");
      const storedFilename = String(draft.currentFilename || "");
      if (storedFilename && !preferProjectDraft) {
        currentFilename = storedFilename;
        selectedProjectFilename = storedFilename;
      }
      if (VIEW_META[storedView]) {
        currentView = storedView;
        if (currentView !== "preview") {
          lastEditingView = currentView;
        }
      }

      selectedIndices = {
        ...selectedIndices,
        ...(draft.selectedIndices || {}),
      };
      activeDatabaseKind = normalizeDatabaseKind(draft.activeDatabaseKind || activeDatabaseKind);
      copilotState.open = Boolean(storedState.open);
      copilotState.messages = Array.isArray(storedState.messages) ? storedState.messages.map((item) => ({
        role: item?.role === "user" ? "user" : "assistant",
        text: String(item?.text || ""),
        error: Boolean(item?.error),
      })) : [];
      copilotState.pendingReview = storedState.pendingReview && typeof storedState.pendingReview === "object"
        ? structuredCloneCompat(storedState.pendingReview)
        : null;
      copilotState.selectedCandidateIds = Array.isArray(storedState.selectedCandidateIds)
        ? storedState.selectedCandidateIds.map((item) => String(item || "")).filter(Boolean)
        : [];
      copilotState.collapsedSections = {
        ...createDefaultCollapsedSections(),
        ...(storedState.collapsedSections || {}),
      };
      copilotState.collapsedCandidateIds = Array.isArray(storedState.collapsedCandidateIds)
        ? storedState.collapsedCandidateIds.map((item) => String(item || "")).filter(Boolean)
        : [];
      copilotState.lastPrompt = String(storedState.lastPrompt || "");
      copilotState.thinkingMode = normalizeCopilotThinkingMode(storedState.thinkingMode);
      const promptInput = $("#copilotPrompt");
      if (promptInput && copilotState.lastPrompt) {
        promptInput.value = copilotState.lastPrompt;
      }
    } finally {
      suppressLocalDraftWrite = false;
    }
  }

  function normalizeCopilotThinkingMode(value) {
    return String(value || "").trim().toLowerCase() === "deep" ? "deep" : "fast";
  }

  function setCopilotThinkingMode(mode) {
    copilotState.thinkingMode = normalizeCopilotThinkingMode(mode);
    persistLocalDraft();
    renderCopilotWidget();
  }

  function getStoredTheme() {
    try {
      const stored = localStorage.getItem(THEME_KEY);
      return stored === "dark" ? "dark" : "light";
    } catch {
      return "light";
    }
  }

  function applyTheme(theme) {
    const normalizedTheme = theme === "dark" ? "dark" : "light";
    document.documentElement.dataset.theme = normalizedTheme;
    const toggle = $("#btnThemeToggle");
    if (toggle) {
      toggle.textContent = normalizedTheme === "dark" ? "浅色" : "暗色";
      toggle.setAttribute("aria-pressed", normalizedTheme === "dark" ? "true" : "false");
      toggle.title = normalizedTheme === "dark" ? "切换到浅色模式" : "切换到暗色模式";
    }
  }

  function setTheme(theme) {
    const normalizedTheme = theme === "dark" ? "dark" : "light";
    applyTheme(normalizedTheme);
    try {
      localStorage.setItem(THEME_KEY, normalizedTheme);
    } catch {
      // ignore storage failures
    }
  }

  function toggleTheme() {
    setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
  }


  function normalizeCopilotSettings(raw) {
    const merged = { ...DEFAULT_COPILOT_SETTINGS, ...(raw || {}) };
    merged.base_url = String(merged.base_url || "").trim();
    merged.api_key = String(merged.api_key || "").trim();
    merged.model = String(merged.model || "").trim();
    merged.request_timeout = Math.max(10, Math.min(3600, Number(merged.request_timeout) || DEFAULT_COPILOT_SETTINGS.request_timeout));
    merged.temperature = Math.max(0, Math.min(2, Number(merged.temperature) || DEFAULT_COPILOT_SETTINGS.temperature));
    merged.base_system_prompt = String(merged.base_system_prompt || DEFAULT_COPILOT_SETTINGS.base_system_prompt).trim() || DEFAULT_COPILOT_SETTINGS.base_system_prompt;
    merged.persona_prompt = String(merged.persona_prompt || DEFAULT_COPILOT_SETTINGS.persona_prompt).trim() || DEFAULT_COPILOT_SETTINGS.persona_prompt;
    merged.worldbook_prompt = String(merged.worldbook_prompt || DEFAULT_COPILOT_SETTINGS.worldbook_prompt).trim() || DEFAULT_COPILOT_SETTINGS.worldbook_prompt;
    merged.preset_prompt = String(merged.preset_prompt || DEFAULT_COPILOT_SETTINGS.preset_prompt).trim() || DEFAULT_COPILOT_SETTINGS.preset_prompt;
    merged.memory_prompt = String(merged.memory_prompt || DEFAULT_COPILOT_SETTINGS.memory_prompt).trim() || DEFAULT_COPILOT_SETTINGS.memory_prompt;
    merged.database_prompt = String(merged.database_prompt || DEFAULT_COPILOT_SETTINGS.database_prompt).trim() || DEFAULT_COPILOT_SETTINGS.database_prompt;
    return merged;
  }

  function fillCopilotSettingsForm() {
    if (!$("#copilotBaseUrl")) return;
    $("#copilotBaseUrl").value = copilotSettings.base_url || "";
    $("#copilotApiKey").value = copilotSettings.api_key || "";
    $("#copilotModel").value = copilotSettings.model || "";
    $("#copilotTimeout").value = String(copilotSettings.request_timeout || DEFAULT_COPILOT_SETTINGS.request_timeout);
    $("#copilotTemperature").value = String(copilotSettings.temperature ?? DEFAULT_COPILOT_SETTINGS.temperature);
    $("#copilotBaseSystemPrompt").value = copilotSettings.base_system_prompt || "";
    $("#copilotPersonaPrompt").value = copilotSettings.persona_prompt || "";
    $("#copilotWorldbookPrompt").value = copilotSettings.worldbook_prompt || "";
    $("#copilotPresetPrompt").value = copilotSettings.preset_prompt || "";
    $("#copilotMemoryPrompt").value = copilotSettings.memory_prompt || "";
    $("#copilotDatabasePrompt").value = copilotSettings.database_prompt || "";
    const promptInput = $("#copilotPrompt");
    if (promptInput && copilotState.lastPrompt) {
      promptInput.value = copilotState.lastPrompt;
    }
  }

  function collectCopilotSettingsForm() {
    return normalizeCopilotSettings({
      base_url: $("#copilotBaseUrl")?.value,
      api_key: $("#copilotApiKey")?.value,
      model: $("#copilotModel")?.value,
      request_timeout: $("#copilotTimeout")?.value,
      temperature: $("#copilotTemperature")?.value,
      base_system_prompt: $("#copilotBaseSystemPrompt")?.value,
      persona_prompt: $("#copilotPersonaPrompt")?.value,
      worldbook_prompt: $("#copilotWorldbookPrompt")?.value,
      preset_prompt: $("#copilotPresetPrompt")?.value,
      memory_prompt: $("#copilotMemoryPrompt")?.value,
      database_prompt: $("#copilotDatabasePrompt")?.value,
    });
  }

  function isCopilotSettingsField(target) {
    const id = String(target?.id || "");
    return [
      "copilotBaseUrl",
      "copilotApiKey",
      "copilotModel",
      "copilotTimeout",
      "copilotTemperature",
      "copilotBaseSystemPrompt",
      "copilotPersonaPrompt",
      "copilotWorldbookPrompt",
      "copilotPresetPrompt",
      "copilotMemoryPrompt",
      "copilotDatabasePrompt",
    ].includes(id);
  }

  async function loadCopilotSettings() {
    try {
      const response = await fetch(apiUrl("/api/settings"));
      if (!response.ok) throw new Error("加载 AI 设置失败");
      const data = await response.json();
      copilotSettings = normalizeCopilotSettings(data.settings || DEFAULT_COPILOT_SETTINGS);
      fillCopilotSettingsForm();
    } catch (error) {
      fillCopilotSettingsForm();
      toast(`AI 设置加载失败：${error.message || String(error)}`, "error");
    }
  }

  function openCopilotSettings() {
    fillCopilotSettingsForm();
    persistLocalDraft();
    $("#copilotSettingsDialog")?.showModal();
  }

  async function saveCopilotSettings() {
    const payload = collectCopilotSettingsForm();
    try {
      const response = await fetch(apiUrl("/api/settings"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "保存 AI 设置失败");
      copilotSettings = normalizeCopilotSettings(data.settings || payload);
      fillCopilotSettingsForm();
      persistLocalDraft();
      $("#copilotSettingsDialog")?.close();
      toast("AI 设置已保存");
    } catch (error) {
      toast(`AI 设置保存失败：${error.message || String(error)}`, "error");
    }
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function setCopilotAnchor(position) {
    const layer = $("#copilotLayer");
    if (!layer) return;
    const fabSize = 62;
    const gap = 14;
    const widgetWidth = Math.min(560, Math.max(0, window.innerWidth - 32));
    const rawX = Number(position?.x) || Math.max(12, window.innerWidth - widgetWidth - fabSize - gap - 12);
    const rawY = Number(position?.y) || window.innerHeight - 96;
    const maxX = Math.max(12, window.innerWidth - widgetWidth - fabSize - gap - 12);
    const x = clamp(rawX, 12, maxX);
    const y = clamp(rawY, 12, Math.max(12, window.innerHeight - fabSize - 12));
    layer.dataset.side = "left";
    layer.style.setProperty("--copilot-fab-size", `${fabSize}px`);
    layer.style.setProperty("--copilot-gap", `${gap}px`);
    layer.style.left = `${x}px`;
    layer.style.top = `${y}px`;
    layer.style.right = "auto";
    layer.style.bottom = "auto";
  }

  function bindCopilotDrag() {
    const fab = $("#copilotFab");
    const layer = $("#copilotLayer");
    if (!fab || !layer) return;
    let dragState = null;
    fab.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      dragState = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        originX: layer.offsetLeft,
        originY: layer.offsetTop,
        moved: false,
      };
      fab.setPointerCapture(event.pointerId);
      layer.classList.add("dragging");
    });
    fab.addEventListener("pointermove", (event) => {
      if (!dragState || dragState.pointerId !== event.pointerId) return;
      const deltaX = event.clientX - dragState.startX;
      const deltaY = event.clientY - dragState.startY;
      const moved = Math.abs(deltaX) > 6 || Math.abs(deltaY) > 6;
      if (!moved && !dragState.moved) return;
      dragState.moved = true;
      event.preventDefault();
      setCopilotAnchor({ x: dragState.originX + deltaX, y: dragState.originY + deltaY });
    });
    const endDrag = (event) => {
      if (!dragState || dragState.pointerId !== event.pointerId) return;
      if (fab.hasPointerCapture(event.pointerId)) {
        fab.releasePointerCapture(event.pointerId);
      }
      layer.classList.remove("dragging");
      if (dragState.moved) {
        layer.dataset.dragMoved = "true";
        window.setTimeout(() => {
          delete layer.dataset.dragMoved;
        }, 120);
      }
      dragState = null;
    };
    fab.addEventListener("pointerup", endDrag);
    fab.addEventListener("pointercancel", endDrag);
  }


  function createEmptyProject() {
    return {
      version: 3,
      type: PROJECT_TYPE,
      title: "",
      persona_card: {
        name: "",
        description: "",
        personality: "",
        first_mes: "",
        mes_example: "",
        scenario: "",
        creator_notes: "",
        tags: [],
        creativeWorkshop: { enabled: true, items: [] },
        personas: { "1": { name: "", description: "", personality: "", scenario: "", creator_notes: "" } },
      },
      worldbook: {
        settings: {
          enabled: true,
          debug_enabled: false,
          max_hits: 10,
          default_case_sensitive: false,
          default_whole_word: false,
          default_match_mode: "includes",
          default_secondary_mode: "includes",
          default_entry_type: "lore",
          default_group_operator: "and",
          default_chance: 100,
          default_sticky_turns: 0,
          default_cooldown_turns: 0,
          default_insertion_position: "after_system",
          default_injection_depth: 0,
          default_injection_role: "system",
          default_injection_order: 100,
          default_prompt_layer: "default",
          recursive_scan_enabled: false,
          recursion_max_depth: 3,
        },
        entries: [],
      },
      memory: { items: [] },
      preset: { active_preset_id: "", presets: [] },
      database: {
        enabled: true,
        notes: "",
        variables: [],
        stages: [],
        tags: [],
      },
      updated_at: "",
    };
  }

  function normalizeProject(raw) {
    const base = createEmptyProject();
    const merged = structuredCloneCompat(base);
    if (!raw || typeof raw !== "object") return merged;

    merged.version = Number(raw.version) || 3;
    merged.type = PROJECT_TYPE;
    merged.title = String(raw.title || "").trim();
    merged.updated_at = String(raw.updated_at || "").trim();

    merged.persona_card = { ...merged.persona_card, ...(raw.persona_card || {}) };
    merged.persona_card.tags = splitTags(merged.persona_card.tags || []);
    merged.persona_card.creativeWorkshop = {
      enabled: Boolean(merged.persona_card.creativeWorkshop?.enabled ?? true),
      items: Array.isArray(merged.persona_card.creativeWorkshop?.items) ? merged.persona_card.creativeWorkshop.items.map(normalizeWorkshopItem) : [],
    };
    merged.persona_card.personas = normalizePersonaMap(merged.persona_card.personas || {});

    merged.worldbook = merged.worldbook || {};
    merged.worldbook.settings = { ...base.worldbook.settings, ...(raw.worldbook?.settings || {}) };
    merged.worldbook.entries = Array.isArray(raw.worldbook?.entries) ? raw.worldbook.entries.map(normalizeWorldbookEntry) : [];

    merged.memory = merged.memory || {};
    merged.memory.items = Array.isArray(raw.memory?.items) ? raw.memory.items.map(normalizeMemoryItem) : [];

    merged.preset = merged.preset || {};
    merged.preset.active_preset_id = String(raw.preset?.active_preset_id || "");
    merged.preset.presets = Array.isArray(raw.preset?.presets) ? raw.preset.presets.map(normalizePresetItem) : [];
    if (!merged.preset.active_preset_id && merged.preset.presets.length) {
      merged.preset.active_preset_id = merged.preset.presets[0].id;
    }

    merged.database = normalizeDatabase(raw.database || {});

    if (!merged.title) merged.title = merged.persona_card.name || "";
    return merged;
  }

  function hasDatabaseContent(database) {
    const normalized = normalizeDatabase(database || {});
    return Boolean(
      normalized.notes.trim()
      || normalized.variables.length
      || normalized.stages.length
      || normalized.tags.length
    );
  }

  function looksLikeDatabasePayload(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const keys = Object.keys(value);
    const allowedKeys = new Set(["enabled", "notes", "variables", "stages", "tags"]);
    if (!keys.length || keys.some((key) => !allowedKeys.has(key))) return false;
    if (Array.isArray(value.variables) || Array.isArray(value.stages)) return true;
    return Array.isArray(value.tags)
      && value.tags.some((item) => item && typeof item === "object" && ["tag", "target", "trigger"].some((key) => key in item));
  }

  function inferImportView(parsed, importedProject, serverTarget = "") {
    const target = String(serverTarget || "").trim().toLowerCase();
    if (["persona", "worldbook", "preset", "memory", "database", "preview"].includes(target)) {
      return target;
    }
    const raw = parsed && typeof parsed === "object" ? parsed : {};
    if (raw.type === PROJECT_TYPE) return "preview";
    if ("settings" in raw && "entries" in raw) return "worldbook";
    if ("active_preset_id" in raw || "presets" in raw) return "preset";
    if (looksLikeDatabasePayload(raw)) return "database";
    if (Array.isArray(raw.items)) return "memory";
    if ("personas" in raw || "creativeWorkshop" in raw || ("name" in raw && "first_mes" in raw)) return "persona";
    const normalizedProject = normalizeProject(importedProject || {});
    if (hasDatabaseContent(normalizedProject.database) && !normalizedProject.persona_card.name) return "database";
    return "preview";
  }

  function selectInitialDatabaseKind() {
    if (project.database.variables.length) activeDatabaseKind = "variables";
    else if (project.database.stages.length) activeDatabaseKind = "stages";
    else if (project.database.tags.length) activeDatabaseKind = "tags";
    else activeDatabaseKind = "variables";
  }

  function structuredCloneCompat(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function splitTags(value) {
    if (Array.isArray(value)) return value.map((item) => String(item).trim()).filter(Boolean);
    return String(value || "").split(/[、，,]/).map((item) => item.trim()).filter(Boolean);
  }
  function normalizePersonaMap(value) {
    const result = {};
    if (Array.isArray(value)) {
      value.forEach((item, index) => {
        const rawKey = String(item?.id || index + 1).trim() || "1";
        let key = rawKey;
        let suffix = 2;
        while (result[key]) {
          key = `${rawKey}_${suffix}`;
          suffix += 1;
        }
        result[key] = normalizePersonaValue(item);
      });
    } else {
      Object.entries(value || {}).forEach(([rawKey, item], index) => {
        const baseKey = String(rawKey || index + 1).trim() || String(index + 1);
        let key = baseKey;
        let suffix = 2;
        while (result[key]) {
          key = `${baseKey}_${suffix}`;
          suffix += 1;
        }
        result[key] = normalizePersonaValue(item);
      });
    }
    if (!Object.keys(result).length) {
      result["1"] = normalizePersonaValue({});
    }
    return result;
  }

  function normalizePersonaValue(value) {
    return {
      name: String(value?.name || ""),
      description: String(value?.description || ""),
      personality: String(value?.personality || ""),
      scenario: String(value?.scenario || ""),
      creator_notes: String(value?.creator_notes || ""),
    };
  }

  function normalizeWorldbookEntry(item, index = 0) {
    const merged = {
      id: item?.id || `wb_${Math.random().toString(36).slice(2, 10)}`,
      title: "",
      trigger: "",
      secondary_trigger: "",
      entry_type: "lore",
      group_operator: "and",
      match_mode: "includes",
      secondary_mode: "includes",
      content: "",
      group: "",
      chance: 100,
      sticky_turns: 0,
      cooldown_turns: 0,
      order: index,
      priority: 0,
      insertion_position: "after_system",
      injection_depth: 0,
      injection_order: 100,
      injection_role: "system",
      prompt_layer: "default",
      recursive_enabled: false,
      prevent_further_recursion: false,
      enabled: true,
      case_sensitive: false,
      whole_word: false,
      comment: "",
      ...(item || {}),
    };
    return merged;
  }

  function normalizeMemoryItem(item, index = 0) {
    return {
      id: item?.id || `memory_${String(index + 1).padStart(3, "0")}`,
      title: String(item?.title || ""),
      content: String(item?.content || ""),
      tags: splitTags(item?.tags || []),
      notes: String(item?.notes || ""),
    };
  }

  function normalizePresetItem(item, index = 0) {
    const modules = { ...(item?.modules || {}) };
    return {
      id: item?.id || `preset_${Math.random().toString(36).slice(2, 10)}`,
      name: String(item?.name || `预设 ${index + 1}`),
      enabled: Boolean(item?.enabled ?? true),
      base_system_prompt: String(item?.base_system_prompt || ""),
      modules,
      extra_prompts: Array.isArray(item?.extra_prompts) ? item.extra_prompts.map(normalizeExtraPrompt) : [],
      prompt_groups: Array.isArray(item?.prompt_groups) ? structuredCloneCompat(item.prompt_groups) : [],
    };
  }

  function normalizeDatabaseKind(value) {
    const kind = String(value || "").trim().toLowerCase();
    if (["stage", "stages"].includes(kind)) return "stages";
    if (["tag", "tags"].includes(kind)) return "tags";
    return "variables";
  }

  function normalizeDatabaseVariable(item, index = 0) {
    return {
      id: item?.id || `db_var_${String(index + 1).padStart(3, "0")}`,
      key: String(item?.key || ""),
      label: String(item?.label || ""),
      value_type: String(item?.value_type || "number"),
      initial_value: String(item?.initial_value ?? ""),
      scope: String(item?.scope || "role"),
      description: String(item?.description || ""),
      write_policy: String(item?.write_policy || ""),
      notes: String(item?.notes || ""),
    };
  }

  function normalizeDatabaseStage(item, index = 0) {
    const roleId = String(item?.role_id || "");
    const stageKey = String(item?.stage_key || "");
    const activeTag = String(item?.active_tag || (roleId && stageKey ? `state_journal.stage.${roleId}.${stageKey}` : ""));
    return {
      id: item?.id || `db_stage_${String(index + 1).padStart(3, "0")}`,
      role_id: roleId,
      stage_key: stageKey,
      title: String(item?.title || ""),
      condition: String(item?.condition || ""),
      active_tag: activeTag,
      emits_tags: splitTags(item?.emits_tags || (activeTag ? [activeTag] : [])),
      description: String(item?.description || ""),
      notes: String(item?.notes || ""),
    };
  }

  function normalizeDatabaseTag(item, index = 0) {
    return {
      id: item?.id || `db_tag_${String(index + 1).padStart(3, "0")}`,
      tag: String(item?.tag || ""),
      title: String(item?.title || ""),
      trigger: String(item?.trigger || ""),
      target: String(item?.target || "worldbook"),
      description: String(item?.description || ""),
      notes: String(item?.notes || ""),
    };
  }

  function normalizeDatabaseItem(kind, item, index = 0) {
    const normalizedKind = normalizeDatabaseKind(kind);
    if (normalizedKind === "stages") return normalizeDatabaseStage(item, index);
    if (normalizedKind === "tags") return normalizeDatabaseTag(item, index);
    return normalizeDatabaseVariable(item, index);
  }

  function normalizeDatabase(value) {
    const raw = value && typeof value === "object" ? value : {};
    return {
      enabled: Boolean(raw.enabled ?? true),
      notes: String(raw.notes || ""),
      variables: Array.isArray(raw.variables) ? raw.variables.map(normalizeDatabaseVariable) : [],
      stages: Array.isArray(raw.stages) ? raw.stages.map(normalizeDatabaseStage) : [],
      tags: Array.isArray(raw.tags) ? raw.tags.map(normalizeDatabaseTag) : [],
    };
  }

  function normalizeExtraPrompt(item, index = 0) {
    return {
      id: item?.id || `extra_${Math.random().toString(36).slice(2, 10)}`,
      name: String(item?.name || ""),
      enabled: Boolean(item?.enabled ?? true),
      content: String(item?.content || ""),
      order: Number(item?.order ?? index),
    };
  }

  function normalizeWorkshopItem(item, index = 0) {
    return {
      id: item?.id || `workshop_${Math.random().toString(36).slice(2, 10)}`,
      name: String(item?.name || ""),
      enabled: Boolean(item?.enabled ?? true),
      triggerMode: String(item?.triggerMode || "manual"),
      triggerStage: String(item?.triggerStage || ""),
      triggerTempMin: Number(item?.triggerTempMin ?? 0),
      triggerTempMax: Number(item?.triggerTempMax ?? 1),
      actionType: String(item?.actionType || "note"),
      popupTitle: String(item?.popupTitle || ""),
      musicPreset: String(item?.musicPreset || ""),
      musicUrl: String(item?.musicUrl || ""),
      autoplay: Boolean(item?.autoplay ?? false),
      loop: Boolean(item?.loop ?? false),
      volume: Number(item?.volume ?? 0.7),
      imageUrl: String(item?.imageUrl || ""),
      imageAlt: String(item?.imageAlt || ""),
      note: String(item?.note || ""),
    };
  }

  function ensureSelections() {
    const wbLength = project.worldbook.entries.length;
    const memLength = project.memory.items.length;
    const presetLength = project.preset.presets.length;
    const personaLength = Object.keys(project.persona_card.personas || {}).length;
    const databaseVariableLength = project.database.variables.length;
    const databaseStageLength = project.database.stages.length;
    const databaseTagLength = project.database.tags.length;
    selectedIndices.worldbookEntry = clampIndex(selectedIndices.worldbookEntry, wbLength);
    selectedIndices.memoryItem = clampIndex(selectedIndices.memoryItem, memLength);
    selectedIndices.presetItem = clampIndex(selectedIndices.presetItem, presetLength);
    selectedIndices.personaItem = clampIndex(selectedIndices.personaItem, personaLength);
    selectedIndices.databaseVariable = clampIndex(selectedIndices.databaseVariable, databaseVariableLength);
    selectedIndices.databaseStage = clampIndex(selectedIndices.databaseStage, databaseStageLength);
    selectedIndices.databaseTag = clampIndex(selectedIndices.databaseTag, databaseTagLength);
  }

  function clampIndex(index, length) {
    if (!length) return -1;
    const safe = Number(index);
    if (!Number.isInteger(safe) || safe < 0) return 0;
    if (safe >= length) return length - 1;
    return safe;
  }

  function captureBrowserScrollPositions() {
    const positions = {};
    $$(".browser-list[data-browser-type]").forEach((list) => {
      const type = list.dataset.browserType;
      if (type) positions[type] = list.scrollTop;
    });
    return positions;
  }

  function restoreBrowserScrollPositions(positions) {
    if (!positions) return;
    $$(".browser-list[data-browser-type]").forEach((list) => {
      const type = list.dataset.browserType;
      if (type && Object.prototype.hasOwnProperty.call(positions, type)) {
        list.scrollTop = positions[type];
      }
    });
  }

  function revealActiveBrowserItem(dataType) {
    if (!dataType) return;
    const list = $$(".browser-list[data-browser-type]").find((item) => item.dataset.browserType === dataType);
    const activeItem = list?.querySelector(".browser-item.active");
    activeItem?.scrollIntoView({ block: "nearest" });
  }

  function renderAll(options = {}) {
    const shouldPreserveBrowserScroll = Boolean(options.preserveBrowserScroll);
    const browserScrollPositions = shouldPreserveBrowserScroll ? captureBrowserScrollPositions() : null;

    ensureSelections();
    renderSidebarMeta();
    renderFaBinding();
    renderCurrentView();
    renderPersonaEditor();
    renderWorldbookEditor();
    renderPresetEditor();
    renderMemoryEditor();
    renderDatabaseEditor();
    renderJsonPreviews();
    renderWarnings(validationCache, !validationCache.some((item) => item.level === "error"));
    if (compileCache) renderCardPreview(compileCache);

    if (shouldPreserveBrowserScroll) restoreBrowserScrollPositions(browserScrollPositions);
    if (options.revealBrowserType) revealActiveBrowserItem(options.revealBrowserType);
  }

  function renderSidebarMeta() {
    $("#projectTitle").value = project.title || "";
    const totalBlocks = project.worldbook.entries.length
      + project.memory.items.length
      + project.preset.presets.length
      + project.persona_card.creativeWorkshop.items.length
      + project.database.variables.length
      + project.database.stages.length
      + project.database.tags.length;
    $("#editorStats").textContent = `${totalBlocks} 个块`;
  }

  function clearFaRuntimeState() {
    faBinding = null;
    faApplyPreview = null;
    faApplySelectedGroupIds = new Set();
  }

  function renderFaBinding() {
    const summary = $("#faBindingSummary");
    const meta = $("#faBindingMeta");
    if (!summary || !meta) return;
    const binding = faBinding || {};
    const card = binding.card || {};
    const preset = binding.preset || {};
    const worldbook = binding.worldbook || {};
    const memory = binding.memory || {};
    if (!card.card_uid && !card.name) {
      summary.textContent = "尚未读取当前 Fa 内容。";
      meta.innerHTML = "";
      return;
    }
    summary.textContent = `${card.name || "未命名角色卡"} · ${card.card_uid || "无 card_uid"}`;
    const roles = Array.isArray(card.roles) ? card.roles : [];
    meta.innerHTML = `
      <div class="fa-meta-row"><span>来源</span><strong>${escHtml(card.source_name || "当前角色卡")}</strong></div>
      <div class="fa-meta-row"><span>角色</span><strong>${roles.length} 个</strong></div>
      <div class="fa-meta-row"><span>世界书</span><strong>${Number(worldbook.entry_count || 0)} 条</strong></div>
      <div class="fa-meta-row"><span>预设</span><strong>${escHtml(preset.active_preset_name || preset.active_preset_id || "未启用")}</strong></div>
      <div class="fa-meta-row"><span>记忆</span><strong>${Number(memory.item_count || 0)} 条</strong></div>
    `;
  }

  function resetFaApplySelection(preview) {
    const groups = Array.isArray(preview?.groups) ? preview.groups : [];
    faApplySelectedGroupIds = new Set(
      groups
        .filter((group) => Number(group.item_count || 0) > 0)
        .map((group) => String(group.id || ""))
        .filter(Boolean)
    );
  }

  function renderFaApplyPreview() {
    const root = $("#faApplyPreviewPanel");
    if (!root) return;
    const preview = faApplyPreview;
    if (!preview) {
      root.innerHTML = '<p class="muted">点击“刷新预览”生成增量应用清单。</p>';
      return;
    }
    const groups = Array.isArray(preview.groups) ? preview.groups : [];
    const warnings = Array.isArray(preview.warnings) ? preview.warnings : [];
    const summary = preview.summary || {};
    const binding = preview.binding || faBinding || {};
    root.innerHTML = `
      <div class="fa-preview-summary">
        <div>
          <span>变更</span>
          <strong>${Number(summary.change_count || 0)} 项</strong>
        </div>
        <div>
          <span>提醒</span>
          <strong>${Number(summary.warning_count || 0)} 条</strong>
        </div>
        <div>
          <span>目标</span>
          <strong>${escHtml(binding.card?.name || "当前 Fa")}</strong>
        </div>
      </div>
      ${warnings.length ? `<div class="fa-warning-box">${warnings.slice(0, 6).map((item) => `<p>${escHtml(item)}</p>`).join("")}</div>` : ""}
      <div class="fa-apply-groups">
        ${groups.length ? groups.map((group) => renderFaApplyGroup(group)).join("") : '<div class="empty-state show">没有可应用的增量变化。</div>'}
      </div>
    `;
  }

  function renderFaApplyGroup(group) {
    const groupId = String(group.id || "");
    const itemCount = Number(group.item_count || 0);
    const checked = faApplySelectedGroupIds.has(groupId);
    const disabled = itemCount <= 0;
    const changes = Array.isArray(group.changes) ? group.changes : [];
    const warnings = Array.isArray(group.warnings) ? group.warnings : [];
    return `
      <section class="fa-apply-group${disabled ? " disabled" : ""}">
        <label class="check-chip fa-apply-check">
          <input type="checkbox" data-fa-apply-group="${escAttr(groupId)}" ${checked ? "checked" : ""} ${disabled ? "disabled" : ""} />
          <span>${escHtml(group.title || group.module || groupId)} · ${itemCount} 项</span>
        </label>
        <p class="field-tip">${escHtml(group.description || "")}</p>
        ${warnings.length ? `<div class="fa-group-warnings">${warnings.map((item) => `<p>${escHtml(item)}</p>`).join("")}</div>` : ""}
        <div class="fa-change-list">
          ${changes.slice(0, 8).map((change) => `
            <div class="fa-change-item">
              <span>${escHtml(change.action || "change")}</span>
              <strong>${escHtml(change.label || change.path || "")}</strong>
              <small>${escHtml(change.after_preview || "")}</small>
            </div>
          `).join("")}
          ${changes.length > 8 ? `<div class="fa-change-more">还有 ${changes.length - 8} 项未展开显示。</div>` : ""}
        </div>
      </section>
    `;
  }

  function renderCurrentView() {
    $$(".view-pane").forEach((pane) => pane.classList.remove("active"));
    $(`#view-${currentView}`)?.classList.add("active");
    $$(".nav-chip").forEach((button) => button.classList.toggle("active", button.dataset.view === currentView));
    document.title = `${(VIEW_META[currentView] || VIEW_META.persona).title} - 缃笺`;
    if (currentView !== "preview") {
      lastEditingView = currentView;
    }
    renderCopilotWidget();
  }

  function renderPersonaEditor() {
    const root = $("#personaEditor");
    const personaEntries = Object.entries(project.persona_card.personas || {});
    const selectedPersonaEntry = personaEntries[selectedIndices.personaItem] || ["1", normalizePersonaValue({})];
    const [personaKey, persona] = selectedPersonaEntry;
    root.innerHTML = `
      <div class="editor-card hero-card">
        <div class="card-header-solo">
          <div>
            <h3>角色主体</h3>
            <p class="muted">把写卡时最常改的字段放在最前面，不用来回翻。</p>
          </div>
          <div class="pill-note">主卡字段</div>
        </div>
        <div class="detail-fields-grid">
          ${PERSONA_FIELDS.map((field) => renderFieldControl(field, getAtPath(project, `persona_card.${field.key}`), { path: `persona_card.${field.key}` })).join("")}
          ${renderFieldControl({ key: "tags", label: "标签", type: "tags", spanTwo: true }, project.persona_card.tags, { path: "persona_card.tags" })}
        </div>
      </div>

      <div class="section-browser-layout persona-browser-layout">
        ${renderBrowserPanel({
          title: "分身列表",
          addLabel: "+ 新增分身",
          action: "add-persona-item",
          items: personaEntries.map(([key, item]) => ({ key, ...item })),
          selectedIndex: selectedIndices.personaItem,
          itemLabel: (item, index) => item.name || `分身 ${index + 1}`,
          itemMeta: (item) => `key = ${item.key}`,
          dataType: "persona-item",
          emptyText: "还没有分身。",
        })}
        <div class="item-editor-shell">
          <div class="detail-card active detail-card-large">
            <div class="detail-head">
              <div>
                <h3>${escHtml(getPersonaDisplayName(persona, personaKey, selectedIndices.personaItem))}</h3>
                <p class="muted">支持复制、调序和改 key；顺序会跟着工程一起保存。</p>
              </div>
              <div class="item-toolbar">
                <div class="pill-note">key = ${escHtml(personaKey)}</div>
                <button class="sort-handle" type="button" data-action="copy-persona-item" data-persona-key="${escAttr(personaKey)}">复制</button>
                <button class="sort-handle" type="button" data-action="move-persona-item" data-persona-key="${escAttr(personaKey)}" data-delta="-1">上移</button>
                <button class="sort-handle" type="button" data-action="move-persona-item" data-persona-key="${escAttr(personaKey)}" data-delta="1">下移</button>
                <button class="item-remove-btn" type="button" data-action="remove-persona-item" data-persona-key="${escAttr(personaKey)}">删除</button>
              </div>
            </div>
            <div class="detail-fields-grid">
              ${renderFieldControl({ key: "persona_key", label: "分身 key", type: "text", hint: "导出时将作为 personas 的对象 key。" }, personaKey, { path: `persona_card.personas.${personaKey}.__key__` })}
              ${PERSONA_SUB_FIELDS.map((field) => renderFieldControl(field, persona[field.key], { path: `persona_card.personas.${personaKey}.${field.key}` })).join("")}
            </div>
          </div>
        </div>
      </div>

      <div class="editor-card">
        <div class="card-header-solo">
          <div>
            <h3>Creative Workshop</h3>
            <p class="muted">事件、音乐、图片等附加玩法都放在这里。</p>
          </div>
          <div class="inline-actions">
            <label class="check-chip">
              <input type="checkbox" data-path="persona_card.creativeWorkshop.enabled" ${project.persona_card.creativeWorkshop.enabled ? "checked" : ""} />
              <span>启用 creativeWorkshop</span>
            </label>
            <button class="ghost-button compact" type="button" data-action="add-workshop">+ 事件</button>
          </div>
        </div>
        <div class="stack-list">
          ${project.persona_card.creativeWorkshop.items.length ? project.persona_card.creativeWorkshop.items.map((item, index) => renderWorkshopCard(item, index)).join("") : '<div class="empty-state">还没有 workshop 事件。</div>'}
        </div>
      </div>
    `;
  }

  function renderWorldbookEditor() {
    const root = $("#worldbookEditor");
    const current = project.worldbook.entries[selectedIndices.worldbookEntry];
    root.innerHTML = `
      <div class="editor-card settings-card">
        <div class="card-header-solo">
          <div>
            <h3>全局 settings</h3>
            <p class="muted">先把世界书默认策略设好，再逐条写 entries，会舒服很多。</p>
          </div>
        </div>
        <div class="detail-fields-grid compact-grid">
          ${WORLDBOOK_SETTING_FIELDS.map((field) => renderFieldControl(field, project.worldbook.settings[field.key], { path: `worldbook.settings.${field.key}` })).join("")}
        </div>
      </div>
      <div class="section-browser-layout">
        ${renderBrowserPanel({
          title: "词条列表",
          addLabel: "+ 新增词条",
          action: "add-worldbook-entry",
          items: project.worldbook.entries,
          selectedIndex: selectedIndices.worldbookEntry,
          itemLabel: (item, index) => item.title || `词条 ${index + 1}`,
          itemMeta: (item) => truncateText(item.trigger || item.content || "未填写", 42),
          dataType: "worldbook-entry",
          emptyText: "还没有世界书词条。",
        })}
        <div class="item-editor-shell">
          ${current ? renderWorldbookDetail(current, selectedIndices.worldbookEntry) : '<div class="empty-state show">左边点一个词条后开始编辑。</div>'}
        </div>
      </div>
    `;
  }

  function renderWorldbookDetail(item, index) {
    return `
      <div class="detail-card active detail-card-large">
        <div class="detail-head">
          <div>
            <p class="eyebrow">Entry ${index + 1}</p>
            <h3>${escHtml(item.title || `词条 ${index + 1}`)}</h3>
          </div>
          <div class="item-toolbar">
            <button class="sort-handle" type="button" data-action="move-worldbook-entry" data-index="${index}" data-delta="-1">上移</button>
            <button class="sort-handle" type="button" data-action="move-worldbook-entry" data-index="${index}" data-delta="1">下移</button>
            <button class="item-remove-btn" type="button" data-action="remove-worldbook-entry" data-index="${index}">删除</button>
          </div>
        </div>
        <div class="detail-fields-grid compact-grid">
          ${WORLDBOOK_ENTRY_FIELDS.map((field) => renderFieldControl(field, item[field.key], { path: `worldbook.entries.${index}.${field.key}` })).join("")}
        </div>
      </div>
    `;
  }

  function renderPresetEditor() {
    const root = $("#presetEditor");
    const current = project.preset.presets[selectedIndices.presetItem];
    root.innerHTML = `
      <div class="editor-card settings-card">
        <div class="card-header-solo">
          <div>
            <h3>当前激活预设</h3>
            <p class="muted">切换 active_preset_id 的时候，预览会同步对应预设。</p>
          </div>
        </div>
        <div class="detail-fields-grid">
          ${renderFieldControl({ key: "active_preset_id", label: "当前激活预设 ID", type: "text", spanTwo: true, hint: "决定预览与导出时默认使用哪一个预设。" }, project.preset.active_preset_id, { path: "preset.active_preset_id" })}
        </div>
      </div>
      <div class="section-browser-layout">
        ${renderBrowserPanel({
          title: "预设列表",
          addLabel: "+ 新增预设",
          action: "add-preset-item",
          items: project.preset.presets,
          selectedIndex: selectedIndices.presetItem,
          itemLabel: (item, index) => item.name || `预设 ${index + 1}`,
          itemMeta: (item) => truncateText(item.base_system_prompt || item.id, 42),
          dataType: "preset-item",
          emptyText: "还没有预设。",
        })}
        <div class="item-editor-shell">
          ${current ? renderPresetDetail(current, selectedIndices.presetItem) : '<div class="empty-state show">左边点一个预设后开始编辑。</div>'}
        </div>
      </div>
    `;
  }

  function renderPresetDetail(item, index) {
    const moduleKeys = Object.keys(item.modules || {});
    return `
      <div class="detail-card active detail-card-large">
        <div class="detail-head">
          <div>
            <p class="eyebrow">Preset ${index + 1}</p>
            <h3>${escHtml(item.name || `预设 ${index + 1}`)}</h3>
          </div>
          <div class="item-toolbar">
            <button class="sort-handle" type="button" data-action="move-preset-item" data-index="${index}" data-delta="-1">上移</button>
            <button class="sort-handle" type="button" data-action="move-preset-item" data-index="${index}" data-delta="1">下移</button>
            <button class="item-remove-btn" type="button" data-action="remove-preset-item" data-index="${index}">删除</button>
          </div>
        </div>
        <div class="detail-fields-grid">
          ${PRESET_FIELDS.map((field) => renderFieldControl(field, item[field.key], { path: `preset.presets.${index}.${field.key}` })).join("")}
        </div>
        <section class="sub-card">
          <div class="sub-card-head">
            <strong>模块开关</strong>
            <span class="muted">这里显示中文说明，但底层 JSON key 保持原样不变。</span>
          </div>
          <div class="toggle-grid">
            ${moduleKeys.map((key) => renderFieldControl({ key, label: MODULE_LABELS[key] || key, type: "checkbox", hint: `JSON key: ${key}` }, item.modules[key], { path: `preset.presets.${index}.modules.${key}` })).join("")}
          </div>
        </section>
        <section class="sub-card">
          <div class="sub-card-head">
            <strong>子提示词</strong>
            <button class="ghost-button compact" type="button" data-action="add-extra-prompt" data-index="${index}">+ 子提示</button>
          </div>
          <div class="stack-list">
            ${item.extra_prompts.length ? item.extra_prompts.map((extra, extraIndex) => renderExtraPromptCard(extra, index, extraIndex)).join("") : '<div class="empty-state">还没有 extra prompt。</div>'}
          </div>
        </section>
        <section class="sub-card">
          <div class="sub-card-head">
            <strong>提示词分组</strong>
            <span class="muted">样例没有结构，这里先保留成原始 JSON 编辑。</span>
          </div>
          <div class="field-block span-two">
            <label>提示词分组 JSON</label>
            <textarea rows="8" data-json-path="preset.presets.${index}.prompt_groups">${escHtml(JSON.stringify(item.prompt_groups || [], null, 2))}</textarea>
          </div>
        </section>
      </div>
    `;
  }

  function renderMemoryEditor() {
    const root = $("#memoryEditor");
    const current = project.memory.items[selectedIndices.memoryItem];
    root.innerHTML = `
      <div class="section-browser-layout">
        ${renderBrowserPanel({
          title: "记忆列表",
          addLabel: "+ 新增记忆",
          action: "add-memory-item",
          items: project.memory.items,
          selectedIndex: selectedIndices.memoryItem,
          itemLabel: (item, index) => item.title || `记忆 ${index + 1}`,
          itemMeta: (item) => truncateText(item.notes || item.content || "未填写", 42),
          dataType: "memory-item",
          emptyText: "还没有记忆块。",
        })}
        <div class="item-editor-shell">
          ${current ? renderMemoryDetail(current, selectedIndices.memoryItem) : '<div class="empty-state show">左边点一个记忆块后开始编辑。</div>'}
        </div>
      </div>
    `;
  }

  function renderMemoryDetail(item, index) {
    return `
      <div class="detail-card active detail-card-large">
        <div class="detail-head">
          <div>
            <p class="eyebrow">Memory ${index + 1}</p>
            <h3>${escHtml(item.title || `记忆 ${index + 1}`)}</h3>
          </div>
          <div class="item-toolbar">
            <button class="sort-handle" type="button" data-action="move-memory-item" data-index="${index}" data-delta="-1">上移</button>
            <button class="sort-handle" type="button" data-action="move-memory-item" data-index="${index}" data-delta="1">下移</button>
            <button class="item-remove-btn" type="button" data-action="remove-memory-item" data-index="${index}">删除</button>
          </div>
        </div>
        <div class="detail-fields-grid">
          ${MEMORY_FIELDS.map((field) => renderFieldControl(field, item[field.key], { path: `memory.items.${index}.${field.key}` })).join("")}
        </div>
      </div>
    `;
  }

  function getDatabaseKindMeta(kind) {
    const normalizedKind = normalizeDatabaseKind(kind);
    const map = {
      variables: {
        title: "变量",
        addLabel: "+ 新增变量",
        action: "add-database-variable",
        removeAction: "remove-database-variable",
        moveAction: "move-database-variable",
        dataType: "database-variable",
        indexKey: "databaseVariable",
        emptyText: "还没有变量草稿。",
        fields: DATABASE_VARIABLE_FIELDS,
        itemLabel: (item, index) => item.label || item.key || `变量 ${index + 1}`,
        itemMeta: (item) => truncateText(item.description || item.write_policy || item.key || "未填写", 42),
      },
      stages: {
        title: "阶段",
        addLabel: "+ 新增阶段",
        action: "add-database-stage",
        removeAction: "remove-database-stage",
        moveAction: "move-database-stage",
        dataType: "database-stage",
        indexKey: "databaseStage",
        emptyText: "还没有阶段草稿。",
        fields: DATABASE_STAGE_FIELDS,
        itemLabel: (item, index) => item.title || item.stage_key || `阶段 ${index + 1}`,
        itemMeta: (item) => truncateText(item.active_tag || item.condition || "未填写", 42),
      },
      tags: {
        title: "Tag",
        addLabel: "+ 新增 Tag",
        action: "add-database-tag",
        removeAction: "remove-database-tag",
        moveAction: "move-database-tag",
        dataType: "database-tag",
        indexKey: "databaseTag",
        emptyText: "还没有 tag 草稿。",
        fields: DATABASE_TAG_FIELDS,
        itemLabel: (item, index) => item.title || item.tag || `Tag ${index + 1}`,
        itemMeta: (item) => truncateText(item.target || item.trigger || item.description || "未填写", 42),
      },
    };
    return map[normalizedKind] || map.variables;
  }

  function renderDatabaseEditor() {
    const root = $("#databaseEditor");
    if (!root) return;
    const kind = normalizeDatabaseKind(activeDatabaseKind);
    const meta = getDatabaseKindMeta(kind);
    const items = project.database[kind] || [];
    const selectedIndex = selectedIndices[meta.indexKey] || 0;
    const current = items[selectedIndex];
    root.innerHTML = `
      <div class="editor-card settings-card">
        <div class="card-header-solo">
          <div>
            <h3>数据库设计草稿</h3>
            <p class="muted">这里只记录变量、阶段和 tag 的设计，不写运行时 SQLite。tag 可用于未来触发世界书或演出工坊。</p>
          </div>
          <label class="check-chip">
            <input type="checkbox" data-path="database.enabled" ${project.database.enabled ? "checked" : ""} />
            <span>启用数据库设计</span>
          </label>
        </div>
        <div class="detail-fields-grid">
          ${renderFieldControl({ key: "notes", label: "数据库总备注", type: "textarea", rows: 4, spanTwo: true }, project.database.notes, { path: "database.notes" })}
        </div>
      </div>
      <div class="database-kind-tabs" role="tablist" aria-label="数据库草稿类型">
        ${[
          ["variables", `变量 ${project.database.variables.length}`],
          ["stages", `阶段 ${project.database.stages.length}`],
          ["tags", `Tag ${project.database.tags.length}`],
        ].map(([tabKind, label]) => `
          <button class="database-kind-tab${kind === tabKind ? " active" : ""}" type="button" data-database-kind="${tabKind}" aria-pressed="${kind === tabKind ? "true" : "false"}">${label}</button>
        `).join("")}
      </div>
      <div class="section-browser-layout">
        ${renderBrowserPanel({
          title: `${meta.title}列表`,
          addLabel: meta.addLabel,
          action: meta.action,
          items,
          selectedIndex,
          itemLabel: meta.itemLabel,
          itemMeta: meta.itemMeta,
          dataType: meta.dataType,
          emptyText: meta.emptyText,
        })}
        <div class="item-editor-shell">
          ${current ? renderDatabaseDetail(kind, current, selectedIndex) : `<div class="empty-state show">左边点一个${meta.title}后开始编辑。</div>`}
        </div>
      </div>
    `;
  }

  function renderDatabaseDetail(kind, item, index) {
    const meta = getDatabaseKindMeta(kind);
    const pathRoot = `database.${normalizeDatabaseKind(kind)}.${index}`;
    return `
      <div class="detail-card active detail-card-large">
        <div class="detail-head">
          <div>
            <p class="eyebrow">Database ${meta.title} ${index + 1}</p>
            <h3>${escHtml(meta.itemLabel(item, index))}</h3>
          </div>
          <div class="item-toolbar">
            <button class="sort-handle" type="button" data-action="${meta.moveAction}" data-index="${index}" data-delta="-1">上移</button>
            <button class="sort-handle" type="button" data-action="${meta.moveAction}" data-index="${index}" data-delta="1">下移</button>
            <button class="item-remove-btn" type="button" data-action="${meta.removeAction}" data-index="${index}">删除</button>
          </div>
        </div>
        <div class="detail-fields-grid">
          ${meta.fields.map((field) => renderFieldControl(field, item[field.key], { path: `${pathRoot}.${field.key}` })).join("")}
        </div>
      </div>
    `;
  }

  function renderWorkshopCard(item, index) {
    return `
      <section class="sub-card">
        <div class="sub-card-head">
          <strong>${escHtml(item.name || `事件 ${index + 1}`)}</strong>
          <div class="inline-actions">
            <button class="ghost-button compact danger" type="button" data-action="remove-workshop" data-index="${index}">删除</button>
          </div>
        </div>
        <div class="detail-fields-grid compact-grid">
          ${WORKSHOP_FIELDS.map((field) => renderFieldControl(field, item[field.key], { path: `persona_card.creativeWorkshop.items.${index}.${field.key}` })).join("")}
        </div>
      </section>
    `;
  }

  function renderExtraPromptCard(item, presetIndex, extraIndex) {
    return `
      <section class="sub-card">
        <div class="sub-card-head">
          <strong>${escHtml(item.name || `子提示 ${extraIndex + 1}`)}</strong>
          <div class="inline-actions">
            <button class="ghost-button compact danger" type="button" data-action="remove-extra-prompt" data-index="${presetIndex}" data-extra-index="${extraIndex}">删除</button>
          </div>
        </div>
        <div class="detail-fields-grid">
          ${EXTRA_PROMPT_FIELDS.map((field) => renderFieldControl(field, item[field.key], { path: `preset.presets.${presetIndex}.extra_prompts.${extraIndex}.${field.key}` })).join("")}
        </div>
      </section>
    `;
  }

  function renderBrowserPanel({ title, addLabel, action, items, selectedIndex, itemLabel, itemMeta, dataType, emptyText }) {
    return `
      <aside class="item-browser">
        <div class="browser-head">
          <strong>${escHtml(title)}</strong>
          <button class="ghost-button compact" type="button" data-action="${escAttr(action)}">${escHtml(addLabel)}</button>
        </div>
        <div class="browser-list" data-browser-type="${escAttr(dataType)}">
          ${items.length ? items.map((item, index) => `
            <button class="browser-item${index === selectedIndex ? " active" : ""}" type="button" data-select-type="${escAttr(dataType)}" data-index="${index}">
              <div class="browser-item-head">
                <span class="browser-item-title">${escHtml(itemLabel(item, index))}</span>
                <span class="browser-item-meta">#${index + 1}</span>
              </div>
              <span class="browser-item-meta">${escHtml(itemMeta(item, index))}</span>
            </button>
          `).join("") : `<div class="empty-state compact-empty show">${escHtml(emptyText)}</div>`}
        </div>
      </aside>
    `;
  }

  function renderFieldControl(field, value, meta) {
    const spanClass = field.spanTwo ? " span-two" : "";
    const hintHtml = field.hint ? `<p class="field-help">${escHtml(field.hint)}</p>` : "";
    if (field.type === "checkbox") {
      return `
        <div class="field-block checkbox-block${spanClass}">
          <label class="check-chip large-check">
            <input type="checkbox" data-path="${escAttr(meta.path)}" ${value ? "checked" : ""} />
            <span>${escHtml(field.label)}</span>
          </label>
          ${hintHtml}
        </div>
      `;
    }
    if (field.type === "textarea") {
      return `
        <div class="field-block${spanClass}">
          <label>${escHtml(field.label)}</label>
          <textarea rows="${field.rows || 4}" data-path="${escAttr(meta.path)}" placeholder="${escAttr(field.placeholder || "")}">${escHtml(value ?? "")}</textarea>
          ${hintHtml}
        </div>
      `;
    }
    if (field.type === "tags") {
      return `
        <div class="field-block${spanClass}">
          <label>${escHtml(field.label)}</label>
          <input type="text" data-path="${escAttr(meta.path)}" data-value-kind="tags" value="${escAttr(Array.isArray(value) ? value.join(", ") : String(value || ""))}" placeholder="用逗号分隔" />
          ${hintHtml}
        </div>
      `;
    }
    return `
      <div class="field-block${spanClass}">
        <label>${escHtml(field.label)}</label>
        <input type="${field.type === "number" ? "number" : "text"}" ${field.step ? `step="${escAttr(field.step)}"` : ""} data-path="${escAttr(meta.path)}" data-value-kind="${field.type === "number" ? "number" : "text"}" value="${escAttr(value ?? "")}" placeholder="${escAttr(field.placeholder || "")}" />
        ${hintHtml}
      </div>
    `;
  }

  function resolveCopilotContext() {
    const baseView = currentView === "preview" ? lastEditingView : currentView;
    if (baseView === "persona") {
      const personaEntries = Object.entries(project.persona_card.personas || {});
      const selectedEntry = personaEntries[selectedIndices.personaItem] || null;
      if (selectedEntry) {
        const [key, value] = selectedEntry;
        return {
          module: "persona",
          title: `当前浏览：分身 · ${value.name || key}`,
          subtitle: "AI 将分析整张卡内容并返回候选修改，不会直接覆盖当前表单。",
          focusHint: {
            view: "persona",
            module: "persona",
            title: `当前浏览：分身 · ${value.name || key}`,
            subtitle: `焦点提示：personas.${key}，但 AI 仍会读取 persona_card / worldbook / preset / memory / database。`,
            persona_key: key,
          },
        };
      }
      return {
        module: "persona",
        title: "当前浏览：角色主体",
        subtitle: "AI 将分析整张卡内容并返回候选修改，不会直接覆盖当前表单。",
        focusHint: {
          view: "persona",
          module: "persona",
          title: "当前浏览：角色主体",
          subtitle: "焦点提示：persona_card 主字段，但 AI 仍会读取 persona_card / worldbook / preset / memory / database。",
          persona_key: "",
        },
      };
    }

    if (baseView === "worldbook") {
      const entry = project.worldbook.entries[selectedIndices.worldbookEntry] || {};
      return {
        module: "worldbook",
        title: `当前浏览：世界书 · ${entry.title || `词条 ${selectedIndices.worldbookEntry + 1}`}`,
        subtitle: "AI 将分析整张卡内容并返回候选修改，不会只盯当前词条。",
        focusHint: {
          view: "worldbook",
          module: "worldbook",
          title: `当前浏览：世界书 · ${entry.title || `词条 ${selectedIndices.worldbookEntry + 1}`}`,
          subtitle: "焦点提示仅用于帮助 AI 理解你现在在看哪里，不限制修改范围。",
          worldbook_id: String(entry.id || ""),
        },
      };
    }

    if (baseView === "preset") {
      const item = project.preset.presets[selectedIndices.presetItem] || {};
      return {
        module: "preset",
        title: `当前浏览：预设 · ${item.name || `预设 ${selectedIndices.presetItem + 1}`}`,
        subtitle: "AI 将分析整张卡内容并返回候选修改，不会只改当前预设。",
        focusHint: {
          view: "preset",
          module: "preset",
          title: `当前浏览：预设 · ${item.name || `预设 ${selectedIndices.presetItem + 1}`}`,
          subtitle: "焦点提示仅用于帮助 AI 理解你现在在看哪里，不限制修改范围。",
          preset_id: String(item.id || ""),
        },
      };
    }

    if (baseView === "database") {
      const kind = normalizeDatabaseKind(activeDatabaseKind);
      const meta = getDatabaseKindMeta(kind);
      const index = selectedIndices[meta.indexKey] || 0;
      const item = (project.database[kind] || [])[index] || {};
      const label = meta.itemLabel(item, index);
      return {
        module: "database",
        title: `当前浏览：数据库 · ${label}`,
        subtitle: "AI 将分析整张卡内容并返回候选修改；数据库这里只写设计草稿。",
        focusHint: {
          view: "database",
          module: "database",
          title: `当前浏览：数据库 · ${label}`,
          subtitle: "焦点提示：数据库只写变量、阶段和 tag 设计草稿，不写运行时状态库。",
          database_kind: kind,
          database_id: String(item.id || ""),
        },
      };
    }

    const memoryItem = project.memory.items[selectedIndices.memoryItem] || {};
    return {
      module: "memory",
      title: `当前浏览：记忆 · ${memoryItem.title || `记忆 ${selectedIndices.memoryItem + 1}`}`,
      subtitle: "AI 将分析整张卡内容并返回候选修改，不会只改当前记忆。",
      focusHint: {
        view: "memory",
        module: "memory",
        title: `当前浏览：记忆 · ${memoryItem.title || `记忆 ${selectedIndices.memoryItem + 1}`}`,
        subtitle: "焦点提示仅用于帮助 AI 理解你现在在看哪里，不限制修改范围。",
        memory_id: String(memoryItem.id || ""),
      },
    };
  }

  function getReviewCandidates() {
    return Array.isArray(copilotState.pendingReview?.candidates) ? copilotState.pendingReview.candidates : [];
  }

  function getReviewCandidateGroups(candidates = getReviewCandidates()) {
    const rawGroups = Array.isArray(copilotState.pendingReview?.candidate_groups) ? copilotState.pendingReview.candidate_groups : [];
    const byId = new Map();
    rawGroups.forEach((group) => {
      const groupId = normalizeGroupId(group?.group_id || group?.id);
      if (!groupId) return;
      byId.set(groupId, {
        group_id: groupId,
        group_title: String(group?.group_title || group?.title || groupId).trim(),
        reason: String(group?.reason || "").trim(),
        candidate_ids: Array.isArray(group?.candidate_ids) ? group.candidate_ids.map((id) => String(id || "")).filter(Boolean) : [],
        depends_on: Array.isArray(group?.depends_on) ? group.depends_on.map((id) => normalizeGroupId(id)).filter(Boolean) : [],
        draft_only: Boolean(group?.draft_only),
      });
    });
    candidates.forEach((candidate) => {
      const groupId = normalizeGroupId(candidate?.group_id) || inferCandidateGroupId(candidate);
      if (!byId.has(groupId)) {
        byId.set(groupId, {
          group_id: groupId,
          group_title: candidate?.group_title || inferCandidateGroupTitle(groupId),
          reason: "",
          candidate_ids: [],
          depends_on: [],
          draft_only: false,
        });
      }
      const group = byId.get(groupId);
      const candidateId = String(candidate?.id || "");
      if (candidateId && !group.candidate_ids.includes(candidateId)) {
        group.candidate_ids.push(candidateId);
      }
      if (!group.group_title && candidate?.group_title) group.group_title = candidate.group_title;
      if (candidate?.draft_only) group.draft_only = true;
    });
    return [...byId.values()].filter((group) => group.candidate_ids.length);
  }

  function normalizeGroupId(value) {
    return String(value || "")
      .trim()
      .toLowerCase()
      .replace(/\s+/g, "_")
      .replace(/[^a-z0-9_.:-]+/g, "_")
      .replace(/_+/g, "_")
      .replace(/^_+|_+$/g, "");
  }

  function inferCandidateGroupId(candidate) {
    const path = getCandidatePath(candidate);
    if (path.startsWith("database.")) return "database_mechanism";
    if (path.startsWith("worldbook.")) return "worldbook_context";
    if (path.startsWith("preset.")) return "preset_discipline";
    if (path.startsWith("memory.")) return "memory_continuity";
    if (path.startsWith("persona_card.")) return "persona_foundation";
    return normalizeGroupId(candidate?.module) || "ungrouped";
  }

  function inferCandidateGroupTitle(groupId) {
    const titles = {
      persona_foundation: "角色底座",
      worldbook_context: "世界书承接",
      preset_discipline: "预设纪律",
      memory_continuity: "记忆连续性",
      database_mechanism: "数据库机制",
      tag_consumer_link: "tag 消费闭环",
      ungrouped: "候选修改",
    };
    return titles[groupId] || groupId.replace(/_/g, " ");
  }

  function isSectionCollapsed(sectionKey) {
    return Boolean(copilotState.collapsedSections?.[sectionKey]);
  }

  function toggleSectionCollapsed(sectionKey) {
    copilotState.collapsedSections[sectionKey] = !copilotState.collapsedSections[sectionKey];
    persistLocalDraft();
    renderCopilotWidget();
  }

  function isCandidateCollapsed(candidateId) {
    return copilotState.collapsedCandidateIds.includes(String(candidateId || ""));
  }

  function toggleCandidateCollapsed(candidateId) {
    const normalizedId = String(candidateId || "");
    if (!normalizedId) return;
    if (isCandidateCollapsed(normalizedId)) {
      copilotState.collapsedCandidateIds = copilotState.collapsedCandidateIds.filter((id) => id !== normalizedId);
    } else {
      copilotState.collapsedCandidateIds = [...copilotState.collapsedCandidateIds, normalizedId];
    }
    persistLocalDraft();
    renderCopilotWidget();
  }

  function isCandidateSelected(candidateId) {
    return copilotState.selectedCandidateIds.includes(String(candidateId || ""));
  }

  function ensureSelectedCandidates() {
    const candidates = getReviewCandidates();
    const candidateIds = candidates.map((item) => String(item.id || "")).filter(Boolean);
    copilotState.selectedCandidateIds = copilotState.selectedCandidateIds.filter((id) => candidateIds.includes(id));
    if (!copilotState.selectedCandidateIds.length && candidateIds.length) {
      copilotState.selectedCandidateIds = candidateIds.slice();
    }
  }

  function toggleCandidateSelection(candidateId) {
    const normalizedId = String(candidateId || "");
    if (!normalizedId) return;
    if (isCandidateSelected(normalizedId)) {
      copilotState.selectedCandidateIds = copilotState.selectedCandidateIds.filter((id) => id !== normalizedId);
    } else {
      copilotState.selectedCandidateIds = [...copilotState.selectedCandidateIds, normalizedId];
    }
    persistLocalDraft();
    renderCopilotWidget();
  }

  function getGroupCandidateIds(group) {
    return Array.isArray(group?.candidate_ids) ? group.candidate_ids.map((id) => String(id || "")).filter(Boolean) : [];
  }

  function getGroupSelectionState(group) {
    const ids = getGroupCandidateIds(group);
    const selectedCount = ids.filter((id) => isCandidateSelected(id)).length;
    return {
      ids,
      selectedCount,
      checked: ids.length > 0 && selectedCount === ids.length,
      mixed: selectedCount > 0 && selectedCount < ids.length,
    };
  }

  function toggleCandidateGroupSelection(groupId) {
    const groups = getReviewCandidateGroups();
    const group = groups.find((item) => item.group_id === normalizeGroupId(groupId));
    if (!group) return;
    const state = getGroupSelectionState(group);
    const current = new Set(copilotState.selectedCandidateIds || []);
    if (state.checked) {
      state.ids.forEach((id) => current.delete(id));
    } else {
      state.ids.forEach((id) => current.add(id));
    }
    copilotState.selectedCandidateIds = [...current];
    persistLocalDraft();
    renderCopilotWidget();
  }

  function summarizeCandidateValue(value, maxLen = 120) {
    if (value == null) return "空";
    if (Array.isArray(value)) return value.length ? truncateText(value.map((item) => typeof item === "string" ? item : JSON.stringify(item)).join("，"), maxLen) : "空数组";
    if (typeof value === "object") {
      const important = [value.name, value.title, value.description, value.content, value.base_system_prompt].find((item) => String(item || "").trim());
      return important ? truncateText(String(important), maxLen) : truncateText(JSON.stringify(value, null, 2), maxLen);
    }
    return truncateText(String(value), maxLen) || "空";
  }

  function getCandidatePath(candidate) {
    const target = candidate?.target || {};
    if (candidate?.action === "json_patch" && target.path) return target.path;
    if (candidate?.module === "persona") return target.persona_key ? `persona_card.personas.${target.persona_key}` : "persona_card";
    if (candidate?.module === "worldbook") return target.id ? `worldbook.entries.${target.id}` : "worldbook.entries";
    if (candidate?.module === "preset") return target.id ? `preset.presets.${target.id}` : "preset.presets";
    if (candidate?.module === "memory") return target.id ? `memory.items.${target.id}` : "memory.items";
    if (candidate?.module === "database") {
      const kind = normalizeDatabaseKind(target.kind);
      return target.id ? `database.${kind}.${target.id}` : `database.${kind}`;
    }
    return "候选修改";
  }

  function describeCandidateAction(candidate) {
    const actionLabels = {
      json_patch: { set: "填充", append: "新增", delete: "删除" },
      replace_field: "替换",
      update_array_item: "更新",
      append_array_item: "新增",
    };
    if (candidate?.action === "json_patch") {
      return actionLabels.json_patch[String(candidate.target?.operation || "set").toLowerCase()] || "填充";
    }
    return actionLabels[candidate?.action] || String(candidate?.action || "修改");
  }

  function renderCandidateDiff(candidate, check = analyzeCopilotCandidate(candidate)) {
    const currentValue = summarizeCandidateValue(check.currentValue, 180);
    const expectedValue = summarizeCandidateValue(check.expectedValue, 180);
    const afterValue = summarizeCandidateValue(check.afterValue, 260);
    const expectedBlock = check.expectedValue != null && stableStringify(check.expectedValue) !== stableStringify(check.currentValue)
      ? `<div><span>候选基准</span><p>${escHtml(expectedValue)}</p></div>`
      : "";
    return `
      <div class="copilot-field-map">
        <div class="copilot-path-line">
          <span>JSON 键 · ${escHtml(check.operation)}</span>
          <code>${escHtml(check.path || getCandidatePath(candidate))}</code>
        </div>
        <div class="copilot-field-change${expectedBlock ? " has-expected" : ""}">
          <div>
            <span>当前</span>
            <p>${escHtml(currentValue)}</p>
          </div>
          ${expectedBlock}
          <div>
            <span>将填充</span>
            <p>${escHtml(afterValue)}</p>
          </div>
        </div>
      </div>
    `;
  }

  function describeCandidateTarget(candidate) {
    const moduleLabels = { persona: "人设", worldbook: "世界书", preset: "预设", memory: "记忆", database: "数据库" };
    const target = candidate?.target || {};
    if (candidate?.module === "persona") {
      if (target.persona_key) return `分身 ${target.persona_key}`;
      return "角色主体";
    }
    if (target.id) return `${moduleLabels[candidate.module] || candidate.module} · ${target.id}`;
    return moduleLabels[candidate?.module] || "候选修改";
  }

  function renderCopilotPlan(plan) {
    if (!plan || typeof plan !== "object" || !Object.keys(plan).length) return "";
    const containers = Array.isArray(plan.required_containers) ? plan.required_containers.filter(Boolean) : [];
    const containerPlan = Array.isArray(plan.container_plan) ? plan.container_plan : [];
    const risks = Array.isArray(plan.risks) ? plan.risks.filter(Boolean) : [];
    const coverage = plan.coverage && typeof plan.coverage === "object" ? plan.coverage : {};
    const coverageItems = ["persona", "worldbook", "memory", "database", "preset"]
      .map((key) => ({ key, value: String(coverage[key] || "").trim() }))
      .filter((item) => item.value);
    const content = `
      <div class="copilot-plan-grid">
        ${plan.intent_type ? `<div class="copilot-review-row"><span>意图</span><strong>${escHtml(plan.intent_type)}</strong></div>` : ""}
        ${plan.package_mode ? `<div class="copilot-review-row"><span>模式</span><strong>${escHtml(plan.package_mode)}</strong></div>` : ""}
        ${plan.quality_goal ? `<div class="copilot-review-row"><span>目标</span><p>${escHtml(plan.quality_goal)}</p></div>` : ""}
        ${containers.length ? `<div class="copilot-review-row"><span>容器</span><div class="copilot-chip-row">${containers.map((item) => `<span class="pill-note">${escHtml(item)}</span>`).join("")}</div></div>` : ""}
      </div>
      ${containerPlan.length ? `
        <div class="copilot-plan-list">
          ${containerPlan.map((item) => `
            <div class="copilot-plan-item">
              <strong>${escHtml(item.module || "container")}</strong>
              <p>${escHtml(item.role || "")}</p>
            </div>
          `).join("")}
        </div>
      ` : ""}
      ${coverageItems.length ? `
        <div class="copilot-coverage-grid">
          ${coverageItems.map((item) => `
            <div class="copilot-coverage-item">
              <strong>${escHtml(item.key)}</strong>
              <p>${escHtml(item.value)}</p>
            </div>
          `).join("")}
        </div>
      ` : ""}
      ${risks.length ? `<div class="copilot-warning-list">${risks.map((risk) => `<p>${escHtml(risk)}</p>`).join("")}</div>` : ""}
    `;
    return renderCollapsibleSection({
      key: "copilot-plan",
      title: "生成计划",
      badge: containers.length ? `${containers.length} 个容器` : "",
      collapsed: isSectionCollapsed("copilot-plan"),
      bodyClass: "copilot-plan-body",
      content,
      extraClass: "copilot-plan-section",
    });
  }

  function getCandidateEmittedTags(candidate) {
    if (candidate?.module !== "database") return [];
    const after = candidate?.after && typeof candidate.after === "object" ? candidate.after : {};
    const path = getCandidatePath(candidate);
    const tags = [];
    ["active_tag", "tag"].forEach((key) => {
      const value = String(after[key] || "").trim();
      if (value && !tags.includes(value)) tags.push(value);
    });
    if (!tags.length && path.startsWith("database.stages")) {
      const roleId = String(after.role_id || "").trim();
      const stageKey = String(after.stage_key || "").trim();
      if (roleId && stageKey) tags.push(`state_journal.stage.${roleId}.${stageKey}`);
    }
    splitTags(after.emits_tags || []).forEach((tag) => {
      if (tag && !tags.includes(tag)) tags.push(tag);
    });
    return tags;
  }

  function getCandidateConsumedTags(candidate) {
    if (candidate?.module !== "worldbook") return [];
    const after = candidate?.after && typeof candidate.after === "object" ? candidate.after : {};
    if (String(after.entry_type || "").trim().toLowerCase() !== "external_tag") return [];
    const tags = [];
    ["trigger", "secondary_trigger"].forEach((key) => {
      splitTags(after[key] || "").forEach((tag) => {
        if (tag && !tags.includes(tag)) tags.push(tag);
      });
    });
    return tags;
  }

  function buildCopilotPackageAudit(candidates, plan = {}) {
    const modules = [];
    const emittedTags = [];
    const consumedTags = [];
    candidates.forEach((candidate) => {
      if (candidate?.module && !modules.includes(candidate.module)) modules.push(candidate.module);
      getCandidateEmittedTags(candidate).forEach((tag) => {
        if (!emittedTags.includes(tag)) emittedTags.push(tag);
      });
      getCandidateConsumedTags(candidate).forEach((tag) => {
        if (!consumedTags.includes(tag)) consumedTags.push(tag);
      });
    });
    const allowedRequired = new Set(["persona", "worldbook", "memory", "database", "preset"]);
    let required = Array.isArray(plan?.required_containers)
      ? plan.required_containers.map((item) => String(item || "").trim()).filter((item) => allowedRequired.has(item))
      : [];
    required = [...new Set(required)];
    if (!required.length && String(plan?.package_mode || "") === "runtime_package") {
      required = ["persona", "worldbook", "memory", "database"];
    }
    const missingContainers = required.filter((module) => !modules.includes(module));
    const missingTagConsumers = emittedTags.filter((tag) => !consumedTags.includes(tag));
    const warnings = [];
    if (missingContainers.length) warnings.push(`缺少容器：${missingContainers.join(", ")}`);
    if (missingTagConsumers.length) warnings.push(`tag 未闭环：${missingTagConsumers.join(", ")}`);
    if (!modules.includes("preset")) warnings.push("没有轻量预设适配候选；若已有外部预设可忽略。");
    return {
      package_mode: String(plan?.package_mode || (modules.length > 1 ? "runtime_package" : "single_edit")),
      modules,
      required_containers: required,
      missing_containers: missingContainers,
      emitted_tags: emittedTags,
      consumed_tags: consumedTags,
      missing_tag_consumers: missingTagConsumers,
      has_light_preset: modules.includes("preset"),
      ready: !missingContainers.length && !missingTagConsumers.length,
      warnings,
    };
  }

  function normalizePackageAudit(raw, candidates, plan) {
    const fallback = buildCopilotPackageAudit(candidates, plan);
    if (!raw || typeof raw !== "object") return fallback;
    return {
      ...fallback,
      ...raw,
      modules: Array.isArray(raw.modules) ? raw.modules.map(String).filter(Boolean) : fallback.modules,
      missing_containers: Array.isArray(raw.missing_containers) ? raw.missing_containers.map(String).filter(Boolean) : fallback.missing_containers,
      required_containers: Array.isArray(raw.required_containers) ? raw.required_containers.map(String).filter(Boolean) : fallback.required_containers,
      emitted_tags: Array.isArray(raw.emitted_tags) ? raw.emitted_tags.map(String).filter(Boolean) : fallback.emitted_tags,
      consumed_tags: Array.isArray(raw.consumed_tags) ? raw.consumed_tags.map(String).filter(Boolean) : fallback.consumed_tags,
      missing_tag_consumers: Array.isArray(raw.missing_tag_consumers) ? raw.missing_tag_consumers.map(String).filter(Boolean) : fallback.missing_tag_consumers,
      warnings: Array.isArray(raw.warnings) ? raw.warnings.map(String).filter(Boolean) : fallback.warnings,
      has_light_preset: Boolean(raw.has_light_preset ?? fallback.has_light_preset),
      ready: Boolean(raw.ready ?? fallback.ready),
    };
  }

  function renderCopilotPackageAudit(audit) {
    if (!audit) return "";
    const modules = Array.isArray(audit.modules) ? audit.modules : [];
    const missing = Array.isArray(audit.missing_containers) ? audit.missing_containers : [];
    const emitted = Array.isArray(audit.emitted_tags) ? audit.emitted_tags : [];
    const consumed = Array.isArray(audit.consumed_tags) ? audit.consumed_tags : [];
    const missingTags = Array.isArray(audit.missing_tag_consumers) ? audit.missing_tag_consumers : [];
    const warnings = Array.isArray(audit.warnings) ? audit.warnings : [];
    const content = `
      <div class="copilot-audit-grid">
        <div class="copilot-audit-item">
          <span>容器覆盖</span>
          <strong>${escHtml(modules.length ? modules.join(" / ") : "无")}</strong>
          ${missing.length ? `<p>缺少：${escHtml(missing.join(", "))}</p>` : `<p>关键容器已覆盖。</p>`}
        </div>
        <div class="copilot-audit-item">
          <span>tag 闭环</span>
          <strong>${escHtml(`${consumed.length}/${emitted.length} 已消费`)}</strong>
          ${missingTags.length ? `<p>未消费：${escHtml(missingTags.join(", "))}</p>` : `<p>数据库 tag 有世界书消费者。</p>`}
        </div>
        <div class="copilot-audit-item">
          <span>轻量预设</span>
          <strong>${audit.has_light_preset ? "已覆盖" : "未覆盖"}</strong>
          <p>${audit.has_light_preset ? "只作为适配纪律。" : "已有外部预设时可忽略。"}</p>
        </div>
      </div>
      ${warnings.length ? `<div class="copilot-warning-list">${warnings.map((item) => `<p>${escHtml(item)}</p>`).join("")}</div>` : ""}
    `;
    return renderCollapsibleSection({
      key: "copilot-package-audit",
      title: "运行包验收",
      badge: audit.ready ? "闭环" : "需复查",
      collapsed: isSectionCollapsed("copilot-package-audit"),
      bodyClass: "copilot-audit-body",
      content,
      extraClass: "copilot-audit-section",
    });
  }

  function renderCandidateMeta(candidate) {
    const chips = [];
    if (candidate?.container_role) chips.push(`<span class="pill-note">${escHtml(candidate.container_role)}</span>`);
    if (candidate?.draft_only) chips.push(`<span class="pill-note warning-pill">设计草稿</span>`);
    if (Array.isArray(candidate?.depends_on) && candidate.depends_on.length) {
      chips.push(`<span class="pill-note">依赖 ${escHtml(candidate.depends_on.join(", "))}</span>`);
    }
    if (Array.isArray(candidate?.emits_tags) && candidate.emits_tags.length) {
      chips.push(`<span class="pill-note">发出 ${escHtml(candidate.emits_tags.join(", "))}</span>`);
    }
    if (Array.isArray(candidate?.consumes_tags) && candidate.consumes_tags.length) {
      chips.push(`<span class="pill-note">消费 ${escHtml(candidate.consumes_tags.join(", "))}</span>`);
    }
    const warnings = Array.isArray(candidate?.tag_warnings) ? candidate.tag_warnings.filter(Boolean) : [];
    return `
      ${chips.length ? `<div class="copilot-candidate-meta">${chips.join("")}</div>` : ""}
      ${warnings.length ? `<div class="copilot-tag-warning">${warnings.map((item) => `<p>${escHtml(item)}</p>`).join("")}</div>` : ""}
    `;
  }

  function renderCandidatePreflight(candidate, check = analyzeCopilotCandidate(candidate)) {
    const warnings = Array.isArray(check.warnings) ? check.warnings.filter(Boolean) : [];
    return `
      <div class="copilot-preflight ${escAttr(check.tone)}">
        <div class="copilot-preflight-main">
          <span class="preflight-dot"></span>
          <strong>${escHtml(check.label)}</strong>
          <p>${escHtml(check.reason)}</p>
        </div>
        ${warnings.length ? `<div class="copilot-preflight-warnings">${warnings.map((item) => `<p>${escHtml(item)}</p>`).join("")}</div>` : ""}
      </div>
    `;
  }

  function renderCandidateCard(candidate) {
    const path = getCandidatePath(candidate);
    const actionLabel = describeCandidateAction(candidate);
    const check = analyzeCopilotCandidate(candidate);
    return `
      <article class="copilot-candidate-card simple-candidate-card${isCandidateSelected(candidate.id) ? " selected" : ""} ${escAttr(`preflight-${check.status}`)}">
        <label class="copilot-candidate-toggle-row" data-candidate-toggle="${escAttr(candidate.id || "")}">
          <input type="checkbox" ${isCandidateSelected(candidate.id) ? "checked" : ""} />
          <span class="copilot-candidate-main">
            <strong>${escHtml(path)}</strong>
            <small>${escHtml(actionLabel)} · ${escHtml(candidate.label || "候选修改")}</small>
          </span>
        </label>
        ${renderCandidatePreflight(candidate, check)}
        ${renderCandidateMeta(candidate)}
        ${renderCandidateDiff(candidate, check)}
      </article>
    `;
  }

  function renderCandidateGroup(group, candidatesById) {
    const state = getGroupSelectionState(group);
    const candidates = state.ids.map((id) => candidatesById.get(id)).filter(Boolean);
    const checks = candidates.map((candidate) => analyzeCopilotCandidate(candidate));
    const moduleNames = [...new Set(candidates.map((candidate) => candidate.module).filter(Boolean))];
    const readyCount = checks.filter((check) => check.canApply && check.status === "ready").length;
    const warningCount = checks.filter((check) => check.canApply && check.status === "warning").length;
    const blockedCount = checks.filter((check) => !check.canApply).length;
    const badge = `${state.selectedCount}/${state.ids.length}`;
    return `
      <section class="copilot-candidate-group${state.checked ? " selected" : ""}${state.mixed ? " mixed" : ""}">
        <div class="copilot-group-head">
          <label class="copilot-group-toggle" data-candidate-group-toggle="${escAttr(group.group_id)}">
            <input type="checkbox" ${state.checked ? "checked" : ""} ${state.mixed ? "data-mixed=\"true\"" : ""} />
            <span>
              <strong>${escHtml(group.group_title || group.group_id || "候选组")}</strong>
              <small>${escHtml(group.reason || "这一组候选共同完成一个容器编排目标。")}</small>
            </span>
          </label>
          <div class="copilot-group-meta">
            <span class="pill-note">${escHtml(badge)}</span>
            ${moduleNames.map((item) => `<span class="pill-note">${escHtml(item)}</span>`).join("")}
            ${readyCount ? `<span class="pill-note success-pill">可应用 ${readyCount}</span>` : ""}
            ${warningCount ? `<span class="pill-note warning-pill">提醒 ${warningCount}</span>` : ""}
            ${blockedCount ? `<span class="pill-note danger-pill">拦截 ${blockedCount}</span>` : ""}
            ${group.draft_only ? `<span class="pill-note warning-pill">设计草稿</span>` : ""}
          </div>
        </div>
        ${group.depends_on?.length ? `<p class="copilot-group-deps">依赖：${escHtml(group.depends_on.join(", "))}</p>` : ""}
        <div class="copilot-review-grid simple-review-grid">
          ${candidates.map((candidate) => renderCandidateCard(candidate)).join("")}
        </div>
      </section>
    `;
  }

  function renderCollapsibleSection({ key, title, badge = "", bodyClass = "", collapsed = false, content = "", extraClass = "" }) {
    return `
      <section class="copilot-section${extraClass ? ` ${extraClass}` : ""}${collapsed ? " is-collapsed" : ""}">
        <button class="copilot-section-toggle" type="button" data-collapsible-section="${escAttr(key)}" aria-expanded="${collapsed ? "false" : "true"}">
          <span class="copilot-section-title">${escHtml(title)}</span>
          <span class="copilot-section-meta">
            ${badge ? `<span class="pill-note">${escHtml(badge)}</span>` : ""}
            <span class="copilot-section-arrow">${collapsed ? "展开" : "折叠"}</span>
          </span>
        </button>
        <div class="copilot-section-body${bodyClass ? ` ${bodyClass}` : ""}" ${collapsed ? "hidden" : ""}>
          ${content}
        </div>
      </section>
    `;
  }

  function renderCopilotWidget() {
    const context = resolveCopilotContext();
    copilotState.lastResolvedContext = context;
    const widget = $("#copilotWidget");
    const fab = $("#copilotFab");
    const layer = $("#copilotLayer");
    if (!widget || !fab || !layer) return;
    widget.hidden = !copilotState.open;
    layer.classList.toggle("open", copilotState.open);
    fab.setAttribute("aria-expanded", copilotState.open ? "true" : "false");
    $("#copilotTitle").textContent = "轮椅模式";
    renderCopilotThinkingModeControl();
    renderCopilotMessages();
    const sendButton = $("#copilotSend");
    if (sendButton) {
      sendButton.disabled = copilotState.loading;
      sendButton.textContent = copilotState.loading ? "分析中…" : "发送";
    }
    const messagesRoot = $("#copilotMessages");
    if (messagesRoot) {
      messagesRoot.hidden = false;
    }
  }

  function renderCopilotThinkingModeControl() {
    const inputArea = $("#copilotInputArea");
    const promptInput = $("#copilotPrompt");
    if (!inputArea || !promptInput) return;
    let control = $("#copilotThinkingMode");
    if (!control) {
      control = document.createElement("div");
      control.id = "copilotThinkingMode";
      control.className = "copilot-mode-toggle";
      promptInput.insertAdjacentElement("beforebegin", control);
    }
    const activeMode = normalizeCopilotThinkingMode(copilotState.thinkingMode);
    control.innerHTML = Object.entries(COPILOT_THINKING_MODES).map(([mode, label]) => `
      <button
        class="copilot-mode-button${activeMode === mode ? " active" : ""}"
        type="button"
        data-copilot-mode="${escAttr(mode)}"
        aria-pressed="${activeMode === mode ? "true" : "false"}"
        title="${mode === "deep" ? "读取深度参考，适合从零造角、重构和关系系统" : "读取压缩核心，适合日常补写和小范围修改"}"
      >${escHtml(label)}</button>
    `).join("");
  }

  function renderCopilotReviewMessage() {
    const pending = copilotState.pendingReview;
    if (!pending) return "";
    ensureSelectedCandidates();
    const candidates = getReviewCandidates();
    const selected = candidates.filter((candidate) => isCandidateSelected(candidate.id));
    const reviewChecks = candidates.map((candidate) => analyzeCopilotCandidate(candidate));
    const selectedChecks = (selected.length ? selected : candidates).map((candidate) => analyzeCopilotCandidate(candidate));
    const applyCount = selectedChecks.filter((check) => check.canApply).length;
    const groups = getReviewCandidateGroups(candidates);
    const candidatesById = new Map(candidates.map((candidate) => [String(candidate.id || ""), candidate]));
    const packageAudit = normalizePackageAudit(pending.package_audit, candidates, pending.plan);
    return `
      <div class="copilot-message assistant copilot-message-review">
        <div class="copilot-bubble copilot-review-bubble">
          <div class="copilot-review-actions">
            <button class="primary-button copilot-apply-button" type="button" data-copilot-action="apply">填充 ${applyCount} 条到卡片</button>
            <button class="ghost-button copilot-cancel-button" type="button" data-copilot-action="discard">取消</button>
          </div>
          <p class="muted">${escHtml(pending.summary || "已生成候选修改，点击填充后写入对应 JSON 键。")}</p>
          ${renderCopilotPreflightSummary(reviewChecks, selectedChecks)}
          ${renderCopilotPlan(pending.plan)}
          ${renderCopilotPackageAudit(packageAudit)}
          <div class="copilot-group-list">
            ${groups.length
              ? groups.map((group) => renderCandidateGroup(group, candidatesById)).join("")
              : `<div class="copilot-review-grid simple-review-grid">${candidates.map((candidate) => renderCandidateCard(candidate)).join("")}</div>`}
          </div>
        </div>
      </div>
    `;
  }

  function renderCopilotPreflightSummary(allChecks, selectedChecks) {
    const total = allChecks.length;
    const selectedTotal = selectedChecks.length;
    const ready = selectedChecks.filter((check) => check.canApply && check.status === "ready").length;
    const warnings = selectedChecks.filter((check) => check.canApply && check.status === "warning").length;
    const blocked = selectedChecks.filter((check) => !check.canApply).length;
    const changed = selectedChecks.filter((check) => check.status === "conflict").length;
    const missing = selectedChecks.filter((check) => check.status === "missing").length;
    return `
      <div class="copilot-preflight-summary">
        <div>
          <span>应用预检</span>
          <strong>${escHtml(`${ready + warnings}/${selectedTotal || total} 可写入`)}</strong>
        </div>
        <div class="copilot-chip-row">
          <span class="pill-note success-pill">可应用 ${ready}</span>
          ${warnings ? `<span class="pill-note warning-pill">提醒 ${warnings}</span>` : ""}
          ${blocked ? `<span class="pill-note danger-pill">拦截 ${blocked}</span>` : ""}
          ${changed ? `<span class="pill-note warning-pill">内容变化 ${changed}</span>` : ""}
          ${missing ? `<span class="pill-note danger-pill">目标缺失 ${missing}</span>` : ""}
          <span class="pill-note">全部 ${total}</span>
        </div>
      </div>
    `;
  }

  function renderCopilotMessages() {
    const root = $("#copilotMessages");
    if (!root) return;
    const baseMessage = copilotState.messages.length || copilotState.pendingReview || copilotState.loading ? "" : `
      <div class="copilot-message assistant">
        <div class="copilot-bubble">
          <p>直接说你想生成、补写或修改什么。我会读取当前卡内容，生成后点“填充到卡片”。</p>
        </div>
      </div>
    `;
    const history = copilotState.messages.map((item) => {
      const detailBlock = item.detail ? `
          <details class="copilot-message-detail${item.error ? " is-error" : ""}">
            <summary>${item.error ? "详细报错" : "详细记录"}</summary>
            <pre>${escHtml(item.detail)}</pre>
          </details>
        ` : "";
      return `
      <div class="copilot-message ${escAttr(item.role || "assistant")}">
        <div class="copilot-bubble${item.error ? " is-error" : ""}">
          <strong>${escHtml(item.role === "user" ? "你" : "轮椅模式")}</strong>
          <p>${escHtml(item.text || "")}</p>
          ${detailBlock}
        </div>
      </div>
    `;
    }).join("");
    const review = renderCopilotReviewMessage();
    const loading = copilotState.loading ? `
      <div class="copilot-message assistant">
        <div class="copilot-bubble">
          <strong>轮椅模式</strong>
          <p>正在分析整张卡并整理候选修改……</p>
        </div>
      </div>
    ` : "";
    root.innerHTML = `<div class="copilot-messages-body">${baseMessage + history + review + loading}</div>`;
    $$('input[data-mixed="true"]', root).forEach((input) => {
      input.indeterminate = true;
    });
    const body = root.querySelector(".copilot-messages-body");
    if (body) body.scrollTop = body.scrollHeight;
  }

  function applySelectedCopilotCandidates() {
    const pending = copilotState.pendingReview;
    if (!pending) return;
    ensureSelectedCandidates();
    const candidates = getReviewCandidates();
    const selected = candidates.filter((candidate) => isCandidateSelected(candidate.id));
    const candidatesToApply = selected.length ? selected : candidates;
    if (!candidatesToApply.length) {
      toast("没有可填充的候选修改。", "error");
      return;
    }

    const applied = [];
    const skipped = [];
    const failed = [];
    candidatesToApply.forEach((candidate) => {
      const check = analyzeCopilotCandidate(candidate);
      if (!check.canApply) {
        skipped.push({ candidate, check });
        return;
      }
      if (applyCopilotCandidate(candidate)) {
        applied.push({ candidate, check });
      } else {
        failed.push({ candidate, check });
      }
    });

    const messages = [];
    if (applied.length) {
      messages.push(`已填充 ${applied.length} 条。`);
    }
    if (skipped.length) {
      messages.push(`${skipped.length} 条预检未通过，已跳过。`);
    }
    if (failed.length) {
      messages.push(`${failed.length} 条找不到可写入位置。`);
    }

    copilotState.messages.push({
      role: "assistant",
      text: messages.join(" ") || "这次没有可填充的内容。",
      detail: buildCopilotApplyReceipt(applied, skipped, failed),
      error: !applied.length,
    });

    if (skipped.length || failed.length) {
      const keepIds = new Set([...skipped, ...failed].map((item) => String(item.candidate?.id || "")));
      copilotState.pendingReview = {
        ...pending,
        candidates: candidates.filter((candidate) => keepIds.has(String(candidate.id || ""))),
      };
      copilotState.selectedCandidateIds = copilotState.pendingReview.candidates.map((candidate) => String(candidate.id || "")).filter(Boolean);
      copilotState.collapsedCandidateIds = [];
    } else {
      copilotState.pendingReview = null;
      copilotState.selectedCandidateIds = [];
      copilotState.collapsedCandidateIds = [];
    }

    if (applied.length) {
      focusCopilotCandidate(applied[0].candidate);
      renderAll();
      persistLocalDraft({ skipSync: true });
      flushDraftForReload({ includeReview: false, sendAutosave: true });
      void saveWorkspaceNow({ skipSync: true });
      if (currentFilename) void saveProject(currentFilename, { skipSync: true, silent: true });
      toast(`已填充 ${applied.length} 条修改`);
    } else {
      renderCopilotWidget();
      persistLocalDraft({ skipSync: true });
    }
  }

  function detectCopilotCandidateConflict(candidate) {
    const check = analyzeCopilotCandidate(candidate);
    return check.canApply ? null : check.reason;
  }

  function analyzeCopilotCandidate(candidate) {
    const resolved = resolveCandidateTarget(candidate);
    const path = resolved?.path || getCandidatePath(candidate);
    const operation = String(resolved?.operation || candidate?.target?.operation || candidate?.action || "set").toLowerCase();
    const warnings = Array.isArray(candidate?.tag_warnings) ? candidate.tag_warnings.filter(Boolean).map(String) : [];
    if (candidate?.draft_only) {
      warnings.push("这是设计草稿，应用后仍需人工确认运行时是否消费。");
    }
    if (!resolved) {
      return {
        status: "missing",
        label: "找不到目标",
        tone: "danger",
        canApply: false,
        path,
        operation,
        currentValue: undefined,
        expectedValue: candidate?.before,
        afterValue: candidate?.after,
        reason: "目标位置不存在，可能是条目被删除、移动，或候选路径已经过期。",
        warnings,
      };
    }
    if (!isCandidateAppendLike(candidate, resolved) && candidate?.before != null && stableStringify(resolved.currentValue) !== stableStringify(candidate.before)) {
      return {
        status: "conflict",
        label: "内容已变化",
        tone: "warning",
        canApply: false,
        path,
        operation,
        currentValue: resolved.currentValue,
        expectedValue: candidate.before,
        afterValue: candidate.after,
        reason: "候选生成后目标内容发生变化，为避免覆盖你的新修改已拦截。",
        warnings,
      };
    }
    const hasWarnings = warnings.length > 0;
    return {
      status: hasWarnings ? "warning" : "ready",
      label: hasWarnings ? "可应用，有提醒" : "可应用",
      tone: hasWarnings ? "warning" : "success",
      canApply: true,
      path,
      operation,
      currentValue: resolved.currentValue,
      expectedValue: candidate?.before,
      afterValue: candidate?.after,
      reason: hasWarnings ? "候选可写入，但存在后续承接或草稿提醒。" : "预检通过，目标位置和当前内容匹配。",
      warnings,
    };
  }

  function isCandidateAppendLike(candidate, resolved) {
    return candidate?.action === "append_array_item" || String(resolved?.operation || candidate?.target?.operation || "").toLowerCase() === "append";
  }

  function buildCopilotApplyReceipt(applied, skipped, failed) {
    const lines = [];
    if (applied.length) {
      lines.push("已写入：");
      applied.forEach(({ candidate, check }, index) => {
        lines.push(`${index + 1}. ${check.path || getCandidatePath(candidate)} · ${candidate.label || describeCandidateAction(candidate)}`);
      });
    }
    if (skipped.length) {
      lines.push("已跳过：");
      skipped.forEach(({ candidate, check }, index) => {
        lines.push(`${index + 1}. ${check.path || getCandidatePath(candidate)} · ${check.label} · ${check.reason}`);
      });
    }
    if (failed.length) {
      lines.push("写入失败：");
      failed.forEach(({ candidate, check }, index) => {
        lines.push(`${index + 1}. ${check.path || getCandidatePath(candidate)} · ${candidate.label || describeCandidateAction(candidate)}`);
      });
    }
    return lines.join("\n");
  }

  function resolveCandidateTarget(candidate) {
    const target = candidate?.target || {};
    if (candidate?.action === "json_patch") {
      const path = String(target.path || "").trim();
      if (!path) return null;
      const operation = target.operation || "set";
      if (String(operation).toLowerCase() !== "append" && !hasProjectPath(project, path)) return null;
      return { path, currentValue: getAtPath(project, path), operation };
    }
    if (candidate?.module === "persona") {
      if (target.persona_key) {
        const personas = project.persona_card.personas || {};
        if (!personas[target.persona_key]) return null;
        return {
          path: `persona_card.personas.${target.persona_key}`,
          currentValue: personas[target.persona_key],
        };
      }
      return {
        path: "persona_card",
        currentValue: getPersonaMainSnapshot(),
      };
    }
    if (candidate?.module === "worldbook") {
      const index = project.worldbook.entries.findIndex((item) => String(item.id || "") === String(target.id || ""));
      if (candidate.action === "append_array_item") {
        return { path: `worldbook.entries.${project.worldbook.entries.length}`, currentValue: null, index: project.worldbook.entries.length };
      }
      if (index < 0) return null;
      return { path: `worldbook.entries.${index}`, currentValue: project.worldbook.entries[index], index };
    }
    if (candidate?.module === "preset") {
      const index = project.preset.presets.findIndex((item) => String(item.id || "") === String(target.id || ""));
      if (candidate.action === "append_array_item") {
        return { path: `preset.presets.${project.preset.presets.length}`, currentValue: null, index: project.preset.presets.length };
      }
      if (index < 0) return null;
      return { path: `preset.presets.${index}`, currentValue: project.preset.presets[index], index };
    }
    if (candidate?.module === "database") {
      const kind = normalizeDatabaseKind(target.kind);
      const list = project.database[kind] || [];
      const index = list.findIndex((item) => String(item.id || "") === String(target.id || ""));
      if (candidate.action === "append_array_item") {
        return { path: `database.${kind}.${list.length}`, currentValue: null, index: list.length, kind };
      }
      if (index < 0) return null;
      return { path: `database.${kind}.${index}`, currentValue: list[index], index, kind };
    }
    const index = project.memory.items.findIndex((item) => String(item.id || "") === String(target.id || ""));
    if (candidate.action === "append_array_item") {
      return { path: `memory.items.${project.memory.items.length}`, currentValue: null, index: project.memory.items.length };
    }
    if (index < 0) return null;
    return { path: `memory.items.${index}`, currentValue: project.memory.items[index], index };
  }

  function applyCopilotCandidate(candidate) {
    const resolved = resolveCandidateTarget(candidate);
    if (!resolved) return false;

    if (candidate.action === "json_patch") {
      return applyJsonPatchCandidate(candidate, resolved);
    }

    if (candidate.module === "persona") {
      if (candidate.target?.persona_key) {
        project.persona_card.personas[candidate.target.persona_key] = normalizePersonaValue(candidate.after || {});
        const personaKeys = Object.keys(project.persona_card.personas || {});
        selectedIndices.personaItem = Math.max(0, personaKeys.indexOf(candidate.target.persona_key));
      } else {
        const nextMain = candidate.after || {};
        ["name", "description", "personality", "first_mes", "mes_example", "scenario", "creator_notes"].forEach((key) => {
          if (Object.prototype.hasOwnProperty.call(nextMain, key)) {
            project.persona_card[key] = String(nextMain[key] || "");
          }
        });
        if (Object.prototype.hasOwnProperty.call(nextMain, "tags")) {
          project.persona_card.tags = splitTags(nextMain.tags || []);
        }
        if (!project.title) {
          project.title = String(project.persona_card.name || "").trim();
        }
      }
      return true;
    }

    if (candidate.module === "worldbook") {
      if (candidate.action === "append_array_item") {
        project.worldbook.entries.push(normalizeWorldbookEntry(candidate.after || {}, project.worldbook.entries.length));
        selectedIndices.worldbookEntry = project.worldbook.entries.length - 1;
      } else if (resolved.index >= 0) {
        project.worldbook.entries[resolved.index] = normalizeWorldbookEntry(candidate.after || {}, resolved.index);
        selectedIndices.worldbookEntry = resolved.index;
      }
      return true;
    }

    if (candidate.module === "preset") {
      if (candidate.action === "append_array_item") {
        project.preset.presets.push(normalizePresetItem(candidate.after || {}, project.preset.presets.length));
        selectedIndices.presetItem = project.preset.presets.length - 1;
      } else if (resolved.index >= 0) {
        project.preset.presets[resolved.index] = normalizePresetItem(candidate.after || {}, resolved.index);
        selectedIndices.presetItem = resolved.index;
      }
      if (!project.preset.active_preset_id) {
        project.preset.active_preset_id = project.preset.presets[selectedIndices.presetItem]?.id || "";
      }
      return true;
    }

    if (candidate.module === "database") {
      const kind = normalizeDatabaseKind(resolved.kind || candidate.target?.kind);
      const meta = getDatabaseKindMeta(kind);
      if (candidate.action === "append_array_item") {
        project.database[kind].push(normalizeDatabaseItem(kind, candidate.after || {}, project.database[kind].length));
        selectedIndices[meta.indexKey] = project.database[kind].length - 1;
      } else if (resolved.index >= 0) {
        project.database[kind][resolved.index] = normalizeDatabaseItem(kind, candidate.after || {}, resolved.index);
        selectedIndices[meta.indexKey] = resolved.index;
      }
      activeDatabaseKind = kind;
      return true;
    }

    if (candidate.action === "append_array_item") {
      project.memory.items.push(normalizeMemoryItem(candidate.after || {}, project.memory.items.length));
      selectedIndices.memoryItem = project.memory.items.length - 1;
    } else if (resolved.index >= 0) {
      project.memory.items[resolved.index] = normalizeMemoryItem(candidate.after || {}, resolved.index);
      selectedIndices.memoryItem = resolved.index;
    }
    return true;
  }

  function applyJsonPatchCandidate(candidate, resolved) {
    const operation = String(resolved.operation || "set").toLowerCase();
    const path = String(resolved.path || "").trim();
    if (!isSafeProjectPath(path)) return false;
    if (operation === "delete") {
      return deleteByPath(project, path);
    }
    if (operation === "append") {
      const list = getAtPath(project, path);
      if (Array.isArray(list)) {
        list.push(structuredCloneCompat(candidate.after));
        normalizeProjectAfterJsonPatch(path);
        selectJsonPatchTarget(path, candidate.after);
        return true;
      }
      const parent = getParentAtPath(project, path);
      if (Array.isArray(parent?.container)) {
        parent.container.push(structuredCloneCompat(candidate.after));
        normalizeProjectAfterJsonPatch(path);
        selectJsonPatchTarget(path, candidate.after);
        return true;
      }
      return false;
    }
    setByPath(project, path, structuredCloneCompat(candidate.after));
    normalizeProjectAfterJsonPatch(path);
    selectJsonPatchTarget(path, candidate.after);
    return true;
  }

  function getParentAtPath(target, path) {
    const parts = String(path || "").split(".").filter(Boolean);
    if (!parts.length) return null;
    let ref = target;
    for (let i = 0; i < parts.length - 1; i += 1) {
      ref = ref?.[parts[i]];
      if (ref == null) return null;
    }
    return { container: ref, key: parts[parts.length - 1] };
  }

  function isSafeProjectPath(path) {
    const parts = String(path || "").split(".").filter(Boolean);
    if (!parts.length) return false;
    const blocked = new Set(["__proto__", "prototype", "constructor"]);
    return parts.every((part) => part && !blocked.has(part));
  }

  function hasProjectPath(target, path) {
    if (!isSafeProjectPath(path)) return false;
    const parts = String(path || "").split(".").filter(Boolean);
    let ref = target;
    for (const part of parts) {
      if (Array.isArray(ref)) {
        if (!/^\d+$/.test(part)) return false;
        const index = Number(part);
        if (index < 0 || index >= ref.length) return false;
        ref = ref[index];
      } else if (ref && typeof ref === "object" && Object.prototype.hasOwnProperty.call(ref, part)) {
        ref = ref[part];
      } else {
        return false;
      }
    }
    return true;
  }

  function deleteByPath(target, path) {
    if (!isSafeProjectPath(path)) return false;
    const parent = getParentAtPath(target, path);
    if (!parent?.container) return false;
    if (Array.isArray(parent.container)) {
      const index = Number(parent.key);
      if (!Number.isInteger(index) || index < 0 || index >= parent.container.length) return false;
      parent.container.splice(index, 1);
      return true;
    }
    if (!Object.prototype.hasOwnProperty.call(parent.container, parent.key)) return false;
    delete parent.container[parent.key];
    return true;
  }

  function normalizeProjectAfterJsonPatch(path) {
    if (path.startsWith("persona_card.tags")) {
      project.persona_card.tags = splitTags(project.persona_card.tags || []);
    }
    if (path.startsWith("worldbook.entries")) {
      project.worldbook.entries = project.worldbook.entries.map(normalizeWorldbookEntry);
    }
    if (path.startsWith("memory.items")) {
      project.memory.items = project.memory.items.map(normalizeMemoryItem);
    }
    if (path.startsWith("preset.presets")) {
      project.preset.presets = project.preset.presets.map(normalizePresetItem);
      if (!project.preset.active_preset_id && project.preset.presets.length) {
        project.preset.active_preset_id = project.preset.presets[0].id;
      }
    }
    if (path.startsWith("database")) {
      project.database = normalizeDatabase(project.database);
    }
    if (!project.title && project.persona_card.name) {
      project.title = String(project.persona_card.name || "").trim();
    }
  }

  function selectJsonPatchTarget(path, afterValue) {
    if (path.startsWith("worldbook.entries")) {
      const id = afterValue?.id;
      const index = id ? project.worldbook.entries.findIndex((item) => String(item.id || "") === String(id)) : project.worldbook.entries.length - 1;
      selectedIndices.worldbookEntry = clampIndex(index, project.worldbook.entries.length);
    } else if (path.startsWith("memory.items")) {
      const id = afterValue?.id;
      const index = id ? project.memory.items.findIndex((item) => String(item.id || "") === String(id)) : project.memory.items.length - 1;
      selectedIndices.memoryItem = clampIndex(index, project.memory.items.length);
    } else if (path.startsWith("preset.presets")) {
      const id = afterValue?.id;
      const index = id ? project.preset.presets.findIndex((item) => String(item.id || "") === String(id)) : project.preset.presets.length - 1;
      selectedIndices.presetItem = clampIndex(index, project.preset.presets.length);
    } else if (path.startsWith("database.")) {
      const parts = path.split(".");
      const kind = normalizeDatabaseKind(parts[1]);
      const meta = getDatabaseKindMeta(kind);
      const list = project.database[kind] || [];
      const id = afterValue?.id;
      const index = id ? list.findIndex((item) => String(item.id || "") === String(id)) : list.length - 1;
      activeDatabaseKind = kind;
      selectedIndices[meta.indexKey] = clampIndex(index, list.length);
    }
  }

  function clearCopilotMessages() {
    copilotState.messages = [];
    copilotState.pendingReview = null;
    copilotState.selectedCandidateIds = [];
    copilotState.collapsedCandidateIds = [];
    copilotState.lastPrompt = "";
    const promptInput = $("#copilotPrompt");
    if (promptInput) promptInput.value = "";
    persistLocalDraft();
    renderCopilotWidget();
  }

  function summarizeCopilotError(detailText) {
    const detail = String(detailText || "").trim();
    if (!detail) return "生成失败";
    const match = detail.match(/^(AI 请求失败|AI 返回的不是合法 JSON|AI 返回的 JSON 根节点必须是对象|AI 返回格式无效|AI 返回的根结构无效|未配置 LLM_BASE_URL|API Key 只能包含 ASCII 字符|请输入想让 AI 处理的内容)[:：]?\s*(.*)$/);
    if (match) return match[1];
    const firstLine = detail.split(/\r?\n/)[0].trim();
    return firstLine.length > 120 ? `${firstLine.slice(0, 117)}…` : firstLine;
  }

  function discardCopilotDraft() {
    if (!copilotState.pendingReview) return;
    copilotState.messages.push({ role: "assistant", text: "这轮候选建议已放弃，你可以继续补充要求。" });
    copilotState.pendingReview = null;
    copilotState.selectedCandidateIds = [];
    copilotState.collapsedCandidateIds = [];
    persistLocalDraft();
    renderCopilotWidget();
  }

  function focusCopilotCandidate(candidate) {
    if (!candidate) return;
    if (candidate.action === "json_patch") {
      const path = String(candidate.target?.path || "");
      if (path.startsWith("persona_card")) currentView = "persona";
      else if (path.startsWith("worldbook")) currentView = "worldbook";
      else if (path.startsWith("preset")) currentView = "preset";
      else if (path.startsWith("memory")) currentView = "memory";
      else if (path.startsWith("database")) currentView = "database";
      renderAll();
      focusPath(path);
      return;
    }
    if (candidate.module === "persona") {
      currentView = "persona";
      renderAll();
      const path = candidate.target?.persona_key ? `persona_card.personas.${candidate.target.persona_key}.name` : "persona_card.name";
      focusPath(path);
      return;
    }
    if (candidate.module === "worldbook") {
      currentView = "worldbook";
      const index = project.worldbook.entries.findIndex((item) => String(item.id || "") === String(candidate.after?.id || candidate.target?.id || ""));
      selectedIndices.worldbookEntry = clampIndex(index, project.worldbook.entries.length);
      renderAll();
      focusPath(`worldbook.entries.${selectedIndices.worldbookEntry}.title`);
      return;
    }
    if (candidate.module === "preset") {
      currentView = "preset";
      const index = project.preset.presets.findIndex((item) => String(item.id || "") === String(candidate.after?.id || candidate.target?.id || ""));
      selectedIndices.presetItem = clampIndex(index, project.preset.presets.length);
      renderAll();
      focusPath(`preset.presets.${selectedIndices.presetItem}.name`);
      return;
    }
    if (candidate.module === "database") {
      currentView = "database";
      const kind = normalizeDatabaseKind(candidate.target?.kind);
      const meta = getDatabaseKindMeta(kind);
      const list = project.database[kind] || [];
      const index = list.findIndex((item) => String(item.id || "") === String(candidate.after?.id || candidate.target?.id || ""));
      activeDatabaseKind = kind;
      selectedIndices[meta.indexKey] = clampIndex(index, list.length);
      renderAll();
      focusPath(`database.${kind}.${selectedIndices[meta.indexKey]}.id`);
      return;
    }
    currentView = "memory";
    const index = project.memory.items.findIndex((item) => String(item.id || "") === String(candidate.after?.id || candidate.target?.id || ""));
    selectedIndices.memoryItem = clampIndex(index, project.memory.items.length);
    renderAll();
    focusPath(`memory.items.${selectedIndices.memoryItem}.title`);
  }

  function getPersonaMainSnapshot() {
    return {
      name: String(project.persona_card.name || ""),
      description: String(project.persona_card.description || ""),
      personality: String(project.persona_card.personality || ""),
      first_mes: String(project.persona_card.first_mes || ""),
      mes_example: String(project.persona_card.mes_example || ""),
      scenario: String(project.persona_card.scenario || ""),
      creator_notes: String(project.persona_card.creator_notes || ""),
      tags: splitTags(project.persona_card.tags || []),
    };
  }

  function stableStringify(value) {
    if (value == null) return "null";
    if (Array.isArray(value)) return `[${value.map((item) => stableStringify(item)).join(",")}]`;
    if (typeof value === "object") {
      return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
    }
    return JSON.stringify(value);
  }

  function focusPath(path) {
    const target = document.querySelector(`[data-path="${cssEscape(path)}"]`);
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.focus?.();
  }

  async function sendCopilotPrompt() {
    const input = $("#copilotPrompt");
    const prompt = String(input?.value || "").trim();
    if (!prompt || copilotState.loading) {
      if (!prompt) toast("先写下你想让轮椅模式处理的内容。", "error");
      return;
    }
    const context = resolveCopilotContext();
    copilotState.loading = true;
    copilotState.lastPrompt = prompt;
    copilotState.messages.push({ role: "user", text: prompt });
    persistLocalDraft();
    renderCopilotWidget();
    try {
      const response = await fetch(apiUrl("/api/ai/generate"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project,
          module: context.module,
          prompt,
          current_view: currentView,
          focus_hint: context.focusHint,
          thinking_mode: normalizeCopilotThinkingMode(copilotState.thinkingMode),
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = String(data.detail || `HTTP ${response.status}` || "生成失败").trim();
        const err = new Error(summarizeCopilotError(detail));
        err.detail = detail;
        throw err;
      }
      copilotState.pendingReview = data;
      copilotState.selectedCandidateIds = Array.isArray(data.candidates) ? data.candidates.map((item) => String(item.id || "")).filter(Boolean) : [];
      copilotState.collapsedCandidateIds = [];
      copilotState.collapsedSections.review = false;
      copilotState.messages.push({ role: "assistant", text: data.summary || `已整理出 ${copilotState.selectedCandidateIds.length} 条候选修改，确认后才会应用。` });
      copilotState.lastPrompt = "";
      persistLocalDraft();
      if (input) input.value = "";
    } catch (error) {
      const detail = String(error.detail || error.message || String(error)).trim();
      const summary = summarizeCopilotError(detail);
      copilotState.messages.push({ role: "assistant", text: `生成失败：${summary}`, detail, error: true });
      persistLocalDraft();
      toast(`AI 生成失败：${summary}`, "error");
    } finally {
      copilotState.loading = false;
      renderCopilotWidget();
    }
  }

  async function loadCurrentFaContext() {
    if (!window.confirm("读取当前 Fa 会用当前运行中的角色卡、世界书、预设和标准记忆替换写卡器工作区。继续吗？")) return;
    try {
      setSaveStatus("读取 Fa 中…");
      const response = await fetch(apiUrl("/api/fa/context"));
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "读取当前 Fa 失败");
      project = normalizeProject(data.project || createEmptyProject());
      faBinding = data.binding || null;
      faApplyPreview = null;
      resetFaApplySelection(null);
      currentFilename = "";
      copilotState.pendingReview = null;
      copilotState.selectedCandidateIds = [];
      copilotState.collapsedCandidateIds = [];
      selectInitialDatabaseKind();
      renderAll();
      persistLocalDraft({ includeReview: false, skipSync: true });
      await saveWorkspaceNow({ skipSync: true });
      toast("已读取当前 Fa 内容");
    } catch (error) {
      toast(`读取当前 Fa 失败：${error.message || error}`, "error");
      setSaveStatus("读取失败");
    }
  }

  async function refreshFaApplyPreview({ keepSelection = false } = {}) {
    syncProjectFromRenderedFields();
    const response = await fetch(apiUrl("/api/fa/apply-preview"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "生成应用预览失败");
    faApplyPreview = data;
    faBinding = data.binding || faBinding;
    if (!keepSelection) resetFaApplySelection(data);
    renderFaBinding();
    renderFaApplyPreview();
    return data;
  }

  async function openFaApplyPreview() {
    $("#faApplyDialog")?.showModal();
    const root = $("#faApplyPreviewPanel");
    if (root) root.innerHTML = '<p class="muted">正在生成增量预览……</p>';
    try {
      await refreshFaApplyPreview();
    } catch (error) {
      if (root) root.innerHTML = `<div class="empty-state show">生成预览失败：${escHtml(error.message || error)}</div>`;
      toast(`生成应用预览失败：${error.message || error}`, "error");
    }
  }

  async function applySelectedFaGroups() {
    try {
      if (!faApplyPreview) {
        await refreshFaApplyPreview();
      }
      const selected = Array.from(faApplySelectedGroupIds);
      if (!selected.length) {
        toast("没有选中的应用项。", "error");
        return;
      }
      if (!window.confirm(`确认把 ${selected.length} 个模块的增量变化写回当前 Fa？写入前会自动备份。`)) return;
      const response = await fetch(apiUrl("/api/fa/apply"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project, selected_group_ids: selected }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "应用到 Fa 失败");
      faApplyPreview = data.preview || faApplyPreview;
      faBinding = faApplyPreview?.binding || faBinding;
      resetFaApplySelection(faApplyPreview);
      renderFaBinding();
      renderFaApplyPreview();
      const applied = Array.isArray(data.applied) ? data.applied : [];
      const backups = Array.isArray(data.backups) ? data.backups : [];
      toast(`已应用 ${applied.length} 个模块，备份 ${backups.length} 个文件`);
    } catch (error) {
      toast(`应用到 Fa 失败：${error.message || error}`, "error");
    }
  }

  function bindEvents() {
    $("#btnNew").addEventListener("click", newProject);
    $("#btnOpen").addEventListener("click", openProjectList);
    $("#btnSave").addEventListener("click", () => saveProject());
    $("#btnSaveAs").addEventListener("click", () => saveProject());
    $("#btnImport").addEventListener("click", openImport);
    $("#btnThemeToggle")?.addEventListener("click", toggleTheme);
    $("#btnLoadFaContext")?.addEventListener("click", loadCurrentFaContext);
    $("#btnOpenFaApply")?.addEventListener("click", openFaApplyPreview);
    $("#btnFaApplyRefresh")?.addEventListener("click", () => {
      refreshFaApplyPreview({ keepSelection: true }).catch((error) => toast(`刷新预览失败：${error.message || error}`, "error"));
    });
    $("#btnFaApplyConfirm")?.addEventListener("click", applySelectedFaGroups);
    $("#btnCopilotSettings").addEventListener("click", openCopilotSettings);
    $("#btnCopilotSettingsSave").addEventListener("click", saveCopilotSettings);
    $("#btnImportConfirm").addEventListener("click", confirmImport);
    $("#btnDeleteProject").addEventListener("click", deleteSelectedProject);
    $("#btnCompileInline").addEventListener("click", runCompile);
    $("#copilotPrompt").addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        sendCopilotPrompt();
      }
    });

    $("#projectTitle").addEventListener("input", () => {
      project.title = $("#projectTitle").value.trim();
      scheduleAutosave();
      renderSidebarMeta();
    });

    $$(".nav-chip").forEach((button) => {
      button.addEventListener("click", () => {
        currentView = button.dataset.view || "persona";
        renderCurrentView();
      });
    });

    document.addEventListener("click", (event) => {
      const target = event.target;
      const copilotButton = target.closest("[data-copilot-action]");
      if (copilotButton) {
        const action = copilotButton.dataset.copilotAction;
        if (action === "toggle") {
          if ($("#copilotLayer")?.dataset.dragMoved === "true") return;
          copilotState.open = !copilotState.open;
        } else if (action === "close") {
          copilotState.open = false;
        } else if (action === "send") {
          sendCopilotPrompt();
          return;
        } else if (action === "apply") {
          applySelectedCopilotCandidates();
          return;
        } else if (action === "discard") {
          discardCopilotDraft();
          return;
        } else if (action === "clear") {
          clearCopilotMessages();
          return;
        }
        persistLocalDraft();
        renderCopilotWidget();
        return;
      }

      const modeButton = target.closest("[data-copilot-mode]");
      if (modeButton) {
        setCopilotThinkingMode(modeButton.dataset.copilotMode || "fast");
        return;
      }

      const databaseKindButton = target.closest("[data-database-kind]");
      if (databaseKindButton) {
        activeDatabaseKind = normalizeDatabaseKind(databaseKindButton.dataset.databaseKind);
        renderAll({ preserveBrowserScroll: true });
        return;
      }

      const collapseToggle = target.closest("[data-collapsible-section]");
      if (collapseToggle) {
        toggleSectionCollapsed(collapseToggle.dataset.collapsibleSection || "");
        return;
      }

      const candidateCollapse = target.closest("[data-candidate-collapse]");
      if (candidateCollapse) {
        toggleCandidateCollapsed(candidateCollapse.dataset.candidateCollapse || "");
        return;
      }

      const groupToggle = target.closest("[data-candidate-group-toggle]");
      if (groupToggle) {
        toggleCandidateGroupSelection(groupToggle.dataset.candidateGroupToggle || "");
        return;
      }

      const toggle = target.closest("[data-candidate-toggle]");
      if (toggle) {
        toggleCandidateSelection(toggle.dataset.candidateToggle || "");
        return;
      }

      const exportButton = target.closest("[data-export-target]");
      if (exportButton) {
        confirmExport(exportButton.dataset.exportTarget || "persona");
        return;
      }

      const warningButton = target.closest("[data-warning-path], [data-warning-view]");
      if (warningButton) {
        focusWarningTarget(warningButton);
        return;
      }

      const selectButton = target.closest("[data-select-type]");
      if (selectButton) {
        const index = Number(selectButton.dataset.index);
        const type = selectButton.dataset.selectType;
        if (type === "worldbook-entry") selectedIndices.worldbookEntry = index;
        if (type === "memory-item") selectedIndices.memoryItem = index;
        if (type === "preset-item") selectedIndices.presetItem = index;
        if (type === "persona-item") selectedIndices.personaItem = index;
        if (type === "database-variable") {
          activeDatabaseKind = "variables";
          selectedIndices.databaseVariable = index;
        }
        if (type === "database-stage") {
          activeDatabaseKind = "stages";
          selectedIndices.databaseStage = index;
        }
        if (type === "database-tag") {
          activeDatabaseKind = "tags";
          selectedIndices.databaseTag = index;
        }
        renderAll({ preserveBrowserScroll: true });
        return;
      }

      const actionButton = target.closest("[data-action]");
      if (!actionButton) return;
      handleAction(actionButton);
    });

    document.addEventListener("input", (event) => {
      const target = event.target;
      if (target.matches("[data-fa-apply-group]")) {
        const groupId = String(target.dataset.faApplyGroup || "");
        if (groupId) {
          if (target.checked) faApplySelectedGroupIds.add(groupId);
          else faApplySelectedGroupIds.delete(groupId);
        }
        return;
      }
      if (isCopilotSettingsField(target)) {
        persistLocalDraft();
      }
      if (target.matches("[data-path]")) {
        const path = target.dataset.path;
        const kind = target.type === "checkbox" ? "checkbox" : (target.dataset.valueKind || "text");
        if (path.endsWith(".__key__")) {
          renamePersonaKey(path, String(target.value || "").trim());
          scheduleAutosave();
          persistLocalDraft();
          renderAll();
          return;
        }
        setByPath(project, path, readInputValue(target, kind));
        if (!project.title && path === "persona_card.name") {
          project.title = String(project.persona_card.name || "").trim();
        }
        scheduleAutosave();
        persistLocalDraft();
        renderJsonPreviews();
        if (path.includes("title") || path.includes("name") || path.includes("trigger") || path.includes("notes") || path.includes("content") || path.includes("tags")) {
          renderSidebarMeta();
        }
        return;
      }

      if (target.matches("[data-json-path]")) {
        try {
          const parsed = JSON.parse(target.value || "[]");
          setByPath(project, target.dataset.jsonPath, parsed);
          target.classList.remove("invalid-json");
          scheduleAutosave();
          persistLocalDraft();
          renderJsonPreviews();
        } catch {
          target.classList.add("invalid-json");
        }
      }
    });

    $$(".modal-close").forEach((button) => button.addEventListener("click", () => button.closest("dialog")?.close()));
    $$("dialog").forEach((dialog) => dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    }));

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeAllDialogs();
      const mod = event.ctrlKey || event.metaKey;
      if (!mod) return;
      if (event.key.toLowerCase() === "s") {
        event.preventDefault();
        saveProject();
      }
    });
  }

  function handleAction(button) {
    const action = button.dataset.action;
    const index = Number(button.dataset.index);
    const delta = Number(button.dataset.delta);
    const extraIndex = Number(button.dataset.extraIndex);

    let revealBrowserType = "";

    if (action === "add-workshop") {
      project.persona_card.creativeWorkshop.items.push(normalizeWorkshopItem({}));
    } else if (action === "remove-workshop") {
      project.persona_card.creativeWorkshop.items.splice(index, 1);
    } else if (action === "add-persona-item") {
      const nextKey = getNextPersonaKey();
      project.persona_card.personas[nextKey] = normalizePersonaValue({ name: `分身 ${Object.keys(project.persona_card.personas).length + 1}` });
      selectedIndices.personaItem = Object.keys(project.persona_card.personas).length - 1;
      revealBrowserType = "persona-item";
    } else if (action === "copy-persona-item") {
      if (copyPersonaEntry(button.dataset.personaKey)) revealBrowserType = "persona-item";
    } else if (action === "move-persona-item") {
      if (movePersonaEntry(button.dataset.personaKey, delta)) revealBrowserType = "persona-item";
    } else if (action === "remove-persona-item") {
      const personaKey = button.dataset.personaKey;
      const keys = Object.keys(project.persona_card.personas || {});
      if (keys.length <= 1) {
        toast("至少保留一个 persona。", "error");
        return;
      }
      delete project.persona_card.personas[personaKey];
      selectedIndices.personaItem = clampIndex(selectedIndices.personaItem, Object.keys(project.persona_card.personas).length);
    } else if (action === "add-worldbook-entry") {
      project.worldbook.entries.push(normalizeWorldbookEntry({ order: project.worldbook.entries.length }, project.worldbook.entries.length));
      selectedIndices.worldbookEntry = project.worldbook.entries.length - 1;
      revealBrowserType = "worldbook-entry";
    } else if (action === "remove-worldbook-entry") {
      project.worldbook.entries.splice(index, 1);
      selectedIndices.worldbookEntry = clampIndex(selectedIndices.worldbookEntry, project.worldbook.entries.length);
    } else if (action === "move-worldbook-entry") {
      moveItem(project.worldbook.entries, index, delta);
      selectedIndices.worldbookEntry = clampIndex(index + delta, project.worldbook.entries.length);
      revealBrowserType = "worldbook-entry";
    } else if (action === "add-memory-item") {
      project.memory.items.push(normalizeMemoryItem({}, project.memory.items.length));
      selectedIndices.memoryItem = project.memory.items.length - 1;
      revealBrowserType = "memory-item";
    } else if (action === "remove-memory-item") {
      project.memory.items.splice(index, 1);
      selectedIndices.memoryItem = clampIndex(selectedIndices.memoryItem, project.memory.items.length);
    } else if (action === "move-memory-item") {
      moveItem(project.memory.items, index, delta);
      selectedIndices.memoryItem = clampIndex(index + delta, project.memory.items.length);
      revealBrowserType = "memory-item";
    } else if (action === "add-preset-item") {
      project.preset.presets.push(normalizePresetItem({}, project.preset.presets.length));
      selectedIndices.presetItem = project.preset.presets.length - 1;
      if (!project.preset.active_preset_id) project.preset.active_preset_id = project.preset.presets[selectedIndices.presetItem].id;
      revealBrowserType = "preset-item";
    } else if (action === "remove-preset-item") {
      const removed = project.preset.presets.splice(index, 1)[0];
      if (removed?.id === project.preset.active_preset_id) {
        project.preset.active_preset_id = project.preset.presets[0]?.id || "";
      }
      selectedIndices.presetItem = clampIndex(selectedIndices.presetItem, project.preset.presets.length);
    } else if (action === "move-preset-item") {
      moveItem(project.preset.presets, index, delta);
      selectedIndices.presetItem = clampIndex(index + delta, project.preset.presets.length);
      revealBrowserType = "preset-item";
    } else if (action === "add-database-variable") {
      project.database.variables.push(normalizeDatabaseVariable({}, project.database.variables.length));
      selectedIndices.databaseVariable = project.database.variables.length - 1;
      activeDatabaseKind = "variables";
      revealBrowserType = "database-variable";
    } else if (action === "remove-database-variable") {
      project.database.variables.splice(index, 1);
      selectedIndices.databaseVariable = clampIndex(selectedIndices.databaseVariable, project.database.variables.length);
    } else if (action === "move-database-variable") {
      moveItem(project.database.variables, index, delta);
      selectedIndices.databaseVariable = clampIndex(index + delta, project.database.variables.length);
      activeDatabaseKind = "variables";
      revealBrowserType = "database-variable";
    } else if (action === "add-database-stage") {
      project.database.stages.push(normalizeDatabaseStage({}, project.database.stages.length));
      selectedIndices.databaseStage = project.database.stages.length - 1;
      activeDatabaseKind = "stages";
      revealBrowserType = "database-stage";
    } else if (action === "remove-database-stage") {
      project.database.stages.splice(index, 1);
      selectedIndices.databaseStage = clampIndex(selectedIndices.databaseStage, project.database.stages.length);
    } else if (action === "move-database-stage") {
      moveItem(project.database.stages, index, delta);
      selectedIndices.databaseStage = clampIndex(index + delta, project.database.stages.length);
      activeDatabaseKind = "stages";
      revealBrowserType = "database-stage";
    } else if (action === "add-database-tag") {
      project.database.tags.push(normalizeDatabaseTag({}, project.database.tags.length));
      selectedIndices.databaseTag = project.database.tags.length - 1;
      activeDatabaseKind = "tags";
      revealBrowserType = "database-tag";
    } else if (action === "remove-database-tag") {
      project.database.tags.splice(index, 1);
      selectedIndices.databaseTag = clampIndex(selectedIndices.databaseTag, project.database.tags.length);
    } else if (action === "move-database-tag") {
      moveItem(project.database.tags, index, delta);
      selectedIndices.databaseTag = clampIndex(index + delta, project.database.tags.length);
      activeDatabaseKind = "tags";
      revealBrowserType = "database-tag";
    } else if (action === "add-extra-prompt") {
      project.preset.presets[index].extra_prompts.push(normalizeExtraPrompt({}, project.preset.presets[index].extra_prompts.length));
    } else if (action === "remove-extra-prompt") {
      project.preset.presets[index].extra_prompts.splice(extraIndex, 1);
    }

    scheduleAutosave();
    renderAll({ preserveBrowserScroll: true, revealBrowserType });
  }

  function moveItem(list, index, delta) {
    const target = index + delta;
    if (!Array.isArray(list) || !list[index] || target < 0 || target >= list.length) return;
    [list[index], list[target]] = [list[target], list[index]];
  }

  function movePersonaEntry(personaKey, delta) {
    const entries = Object.entries(project.persona_card.personas || {});
    const index = entries.findIndex(([key]) => key === personaKey);
    const target = index + delta;
    if (index < 0 || target < 0 || target >= entries.length) return false;
    [entries[index], entries[target]] = [entries[target], entries[index]];
    project.persona_card.personas = Object.fromEntries(entries);
    selectedIndices.personaItem = target;
    return true;
  }

  function copyPersonaEntry(personaKey) {
    const entries = Object.entries(project.persona_card.personas || {});
    const index = entries.findIndex(([key]) => key === personaKey);
    if (index < 0) return false;
    const [, persona] = entries[index];
    const baseKey = `${personaKey}_copy`;
    let nextKey = baseKey;
    let suffix = 2;
    while (project.persona_card.personas[nextKey]) {
      nextKey = `${baseKey}_${suffix}`;
      suffix += 1;
    }
    const copied = normalizePersonaValue({
      ...structuredCloneCompat(persona),
      name: persona.name ? `${persona.name}（副本）` : "分身副本",
    });
    entries.splice(index + 1, 0, [nextKey, copied]);
    project.persona_card.personas = Object.fromEntries(entries);
    selectedIndices.personaItem = index + 1;
    return true;
  }

  function getPersonaDisplayName(persona, personaKey, index) {
    const name = String(persona?.name || "").trim();
    if (name) return name;
    return `分身 ${index + 1} · key=${personaKey}`;
  }
  function getNextPersonaKey() {
    const keys = new Set(Object.keys(project.persona_card.personas || {}));
    let next = 1;
    while (keys.has(String(next))) next += 1;
    return String(next);
  }

  function renamePersonaKey(path, nextKeyRaw) {
    const parts = String(path || "").split(".");
    const oldKey = parts[2];
    const nextKey = String(nextKeyRaw || "").trim() || oldKey;
    if (!oldKey || nextKey === oldKey) return;
    if (project.persona_card.personas[nextKey]) {
      toast(`persona key「${nextKey}」已存在。`, "error");
      return;
    }
    const entries = Object.entries(project.persona_card.personas || {});
    const targetIndex = entries.findIndex(([key]) => key === oldKey);
    if (targetIndex < 0) return;
    const nextEntries = entries.map(([key, value], index) => index === targetIndex ? [nextKey, value] : [key, value]);
    project.persona_card.personas = Object.fromEntries(nextEntries);
  }

  function readInputValue(target, kind) {
    if (kind === "checkbox") return Boolean(target.checked);
    if (kind === "number") return target.value === "" ? 0 : Number(target.value);
    if (kind === "tags") return splitTags(target.value);
    return target.value;
  }

  function setByPath(target, path, value) {
    if (!isSafeProjectPath(path)) return false;
    const parts = String(path || "").split(".").filter(Boolean);
    if (!parts.length) return false;
    let ref = target;
    for (let i = 0; i < parts.length - 1; i += 1) {
      const part = parts[i];
      const nextPart = parts[i + 1];
      if (ref[part] == null) {
        ref[part] = /^\d+$/.test(nextPart) ? [] : {};
      }
      ref = ref[part];
    }
    ref[parts[parts.length - 1]] = value;
    return true;
  }

  function getAtPath(target, path) {
    if (!isSafeProjectPath(path)) return undefined;
    return String(path || "").split(".").filter(Boolean).reduce((acc, key) => acc?.[key], target);
  }

  function guessTitle() {
    return String(project.title || project.persona_card.name || "untitled").trim() || "untitled";
  }

  function sanitizeFilename(name) {
    return String(name || "untitled").replace(/[\\/:*?"<>|]/g, "_").trim() || "untitled";
  }

  function setSaveStatus(text) {
    $("#saveStatus").textContent = text;
    clearTimeout(saveStatusTimer);
    saveStatusTimer = setTimeout(() => {
      $("#saveStatus").textContent = "就绪";
    }, 2400);
  }

  function toast(message, level = "") {
    $(".toast")?.remove();
    const el = document.createElement("div");
    el.className = `toast${level === "error" ? " error" : ""}`;
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2600);
  }

  function truncateText(text, maxLen) {
    const normalized = String(text || "").replace(/\s+/g, " ").trim();
    return normalized.length > maxLen ? `${normalized.slice(0, maxLen)}…` : normalized;
  }

  function escHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function escAttr(value) {
    return escHtml(value).replaceAll("'", "&#39;");
  }

  async function openProjectList() {
    selectedProjectFilename = currentFilename;
    const list = $("#projectList");
    list.innerHTML = '<p class="muted">加载中……</p>';
    $("#projectListDialog").showModal();
    try {
      const response = await fetch(apiUrl("/api/projects"));
      if (!response.ok) throw new Error("加载失败");
      const data = await response.json();
      if (!Array.isArray(data.projects) || !data.projects.length) {
        list.innerHTML = '<p class="muted">还没有保存的工程文件。</p>';
        return;
      }
      list.innerHTML = data.projects.map((item) => `
        <div class="project-item${item.filename === selectedProjectFilename ? " selected" : ""}" data-filename="${escAttr(item.filename)}">
          <div>
            <div class="item-title">${escHtml(item.title || item.filename)}</div>
            <div class="item-meta">${escHtml(item.filename)} · ${escHtml(item.updated_at || "")}</div>
          </div>
        </div>`).join("");
      $$(".project-item").forEach((item) => {
        item.addEventListener("click", async () => {
          selectedProjectFilename = item.dataset.filename || "";
          await loadProject(selectedProjectFilename);
          $("#projectListDialog").close();
        });
      });
    } catch (error) {
      list.innerHTML = `<p class="muted">加载失败：${escHtml(error.message || String(error))}</p>`;
    }
  }

  async function loadProject(filename) {
    if (!filename) return;
    try {
      const response = await fetch(apiUrl(`/api/projects/${encodeURIComponent(filename)}`));
      if (!response.ok) throw new Error("工程不存在");
      const data = await response.json();
      project = normalizeProject(data.project || createEmptyProject());
      currentFilename = filename;
      selectedProjectFilename = filename;
      compileCache = null;
      validationCache = [];
      currentView = "persona";
      lastEditingView = "persona";
      copilotState.pendingReview = null;
      copilotState.selectedCandidateIds = [];
      copilotState.collapsedCandidateIds = [];
      selectedIndices = { worldbookEntry: 0, memoryItem: 0, presetItem: 0, personaItem: 0, databaseVariable: 0, databaseStage: 0, databaseTag: 0 };
      activeDatabaseKind = "variables";
      clearFaRuntimeState();
      clearLocalReviewDraft({ keepProjectDraft: false });
      persistLocalDraft({ includeReview: false, skipSync: true });
      void saveWorkspaceNow({ skipSync: true });
      renderAll();
      setSaveStatus(`已加载 ${filename}`);
    } catch (error) {
      toast(`加载失败：${error.message}`, "error");
    }
  }

  async function saveProject(filenameOverride = "", { skipSync = false, silent = false } = {}) {
    if (!skipSync) syncProjectFromRenderedFields();
    project.title = String(project.title || "").trim() || guessTitle();
    const filename = filenameOverride || currentFilename || `${sanitizeFilename(guessTitle())}.cardwork.json`;
    try {
      const response = await fetch(apiUrl(`/api/projects/${encodeURIComponent(filename)}`), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(project),
      });
      if (!response.ok) throw new Error("保存失败");
      const data = await response.json();
      currentFilename = data.filename;
      selectedProjectFilename = data.filename;
      project.updated_at = data.updated_at || "";
      persistLocalDraft({ skipSync: true });
      setSaveStatus("已保存");
      if (!silent) toast(`已保存 ${data.filename}`);
      return true;
    } catch (error) {
      if (!silent) toast(`保存失败：${error.message}`, "error");
      else setSaveStatus("保存失败");
      return false;
    }
  }

  function newProject() {
    if (hasProjectContent() && !window.confirm("当前工程未保存。确定新建吗？")) return;
    project = createEmptyProject();
    currentFilename = "";
    selectedProjectFilename = "";
    compileCache = null;
    validationCache = [];
    currentView = "persona";
    lastEditingView = "persona";
    copilotState.pendingReview = null;
    copilotState.selectedCandidateIds = [];
    copilotState.collapsedCandidateIds = [];
    selectedIndices = { worldbookEntry: 0, memoryItem: 0, presetItem: 0, personaItem: 0, databaseVariable: 0, databaseStage: 0, databaseTag: 0 };
    activeDatabaseKind = "variables";
    clearFaRuntimeState();
    clearLocalReviewDraft();
    renderAll();
    setSaveStatus("新建工程");
  }

  function hasProjectContent() {
    return JSON.stringify(project) !== JSON.stringify(createEmptyProject());
  }

  function openImport() {
    $("#importTextarea").value = "";
    $("#importDialog").showModal();
  }

  async function confirmImport() {
    const raw = $("#importTextarea").value.trim();
    if (!raw) {
      toast("请粘贴 JSON", "error");
      return;
    }
    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch {
      toast("JSON 解析失败，请检查格式。", "error");
      return;
    }
    try {
      const response = await fetch(apiUrl("/api/import-card"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parsed),
      });
      if (!response.ok) throw new Error("导入失败");
      const data = await response.json();
      project = normalizeProject(data.project || createEmptyProject());
      currentFilename = "";
      selectedProjectFilename = "";
      compileCache = null;
      validationCache = [];
      currentView = inferImportView(parsed, data.project, data.import_target);
      lastEditingView = currentView === "preview" ? "persona" : currentView;
      copilotState.pendingReview = null;
      copilotState.selectedCandidateIds = [];
      copilotState.collapsedCandidateIds = [];
      selectedIndices = { worldbookEntry: 0, memoryItem: 0, presetItem: 0, personaItem: 0, databaseVariable: 0, databaseStage: 0, databaseTag: 0 };
      selectInitialDatabaseKind();
      clearFaRuntimeState();
      clearLocalReviewDraft();
      renderAll();
      renderWarnings([], false);
      setSaveStatus("已导入 JSON");
      toast("导入成功");
      $("#importDialog").close();
    } catch (error) {
      toast(`导入失败：${error.message}`, "error");
    }
  }

  function getExportConfig(target) {
    const exportTarget = String(target || "persona").trim().toLowerCase();
    const base = sanitizeFilename(project.title || guessTitle());
    const map = {
      persona: { filename: `${base}的人设.json`, label: "人设", title: "人设卡", accept: ".json" },
      worldbook: { filename: `${base}的世界书.json`, label: "世界书", title: "世界书", accept: ".json" },
      preset: { filename: `${base}的预设.json`, label: "预设", title: "预设", accept: ".json" },
      memory: { filename: `${base}的记忆.json`, label: "记忆", title: "记忆", accept: ".json" },
      database: { filename: `${base}的数据库草稿.json`, label: "数据库", title: "数据库草稿", accept: ".json" },
    };
    return map[exportTarget] || map.persona;
  }

  async function confirmExport(target = "persona") {
    const exportTarget = String(target || "persona").trim().toLowerCase();
    const config = getExportConfig(exportTarget);
    try {
      const response = await fetch(apiUrl("/api/export"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project, filename: config.filename, target: exportTarget }),
      });
      if (!response.ok) throw new Error("导出失败");
      const blob = await response.blob();
      const downloadName = getDownloadFilename(response, config.filename);
      const savedWithPicker = await saveBlobWithPicker(blob, downloadName, config);
      if (!savedWithPicker) {
        downloadBlob(blob, downloadName);
      }
      toast(savedWithPicker ? `已保存 ${config.label}` : `已开始下载 ${downloadName}`);
    } catch (error) {
      toast(`导出失败：${error.message}`, "error");
    }
  }

  async function saveBlobWithPicker(blob, filename, config) {
    if (typeof window.showSaveFilePicker !== "function") return false;
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: filename,
        types: [{
          description: `${config.title} JSON`,
          accept: { "application/json": [config.accept, ".json"] },
        }],
      });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      return true;
    } catch (error) {
      if (error?.name === "AbortError") return true;
      return false;
    }
  }

  function downloadBlob(blob, filename) {
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
  }

  function getDownloadFilename(response, fallback) {
    const disposition = response.headers.get("Content-Disposition") || "";
    const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8Match?.[1]) {
      try {
        return decodeURIComponent(utf8Match[1]);
      } catch {
        return utf8Match[1];
      }
    }
    const plainMatch = disposition.match(/filename="?([^";]+)"?/i);
    return plainMatch?.[1] || fallback;
  }

  async function runCompile() {
    currentView = "preview";
    renderCurrentView();
    try {
      const [compileResponse, validateResponse] = await Promise.all([
        fetch(apiUrl("/api/compile"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(project),
        }),
        fetch(apiUrl("/api/validate"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(project),
        }),
      ]);
      if (!compileResponse.ok) throw new Error("编译失败");
      if (!validateResponse.ok) throw new Error("校验失败");
      const compileData = await compileResponse.json();
      const validateData = await validateResponse.json();
      compileCache = compileData.card || null;
      validationCache = Array.isArray(validateData.warnings) ? validateData.warnings : [];
      renderCardPreview(compileCache || {});
      renderWarnings(validationCache, Boolean(validateData.ok));
      renderJsonPreviews();
    } catch (error) {
      validationCache = [];
      renderWarnings([], false, error.message || String(error));
      $("#cardPreview").innerHTML = `<p class="muted">编译失败：${escHtml(error.message || String(error))}</p>`;
    }
  }

  function renderWarnings(warnings, isOk, errorMessage = "") {
    const statusEl = $("#previewValidationStatus");
    const listEl = $("#previewWarnings");
    if (!statusEl || !listEl) return;

    if (errorMessage) {
      statusEl.textContent = "检查失败";
      statusEl.className = "pill-note warning-pill error";
      listEl.innerHTML = `<div class="empty-state">${escHtml(errorMessage)}</div>`;
      return;
    }

    const items = Array.isArray(warnings) ? warnings : [];
    if (!items.length) {
      statusEl.textContent = isOk ? "通过" : "未检查";
      statusEl.className = `pill-note warning-pill${isOk ? " success" : ""}`;
      listEl.innerHTML = '<div class="empty-state">当前没有校验警告，可以直接导出。</div>';
      return;
    }

    const errorCount = items.filter((item) => item.level === "error").length;
    statusEl.textContent = errorCount ? `有 ${errorCount} 个错误` : `共 ${items.length} 条提醒`;
    statusEl.className = `pill-note warning-pill${errorCount ? " error" : " warning"}`;
    listEl.innerHTML = items.map((item, index) => {
      const target = getWarningTarget(item, index);
      return `
        <button class="warning-item ${escAttr(item.level || "warning")}" type="button" data-warning-index="${index}" data-warning-view="${escAttr(target.view)}" data-warning-path="${escAttr(target.path)}" data-warning-select-type="${escAttr(target.selectType)}" data-warning-select-index="${target.selectIndex}">
          <span class="warning-level">${escHtml(item.level === "error" ? "错误" : "提醒")}</span>
          <strong>${escHtml(item.message || "")}</strong>
          <span class="warning-meta">${escHtml(target.label)}</span>
        </button>
      `;
    }).join("");
  }

  function getWarningTarget(item, index) {
    const field = String(item?.field || "").trim();
    const personaEntries = Object.entries(project.persona_card.personas || {});
    const personaFieldMatch = field.match(/^personas\.([^\.]+)\.(.+)$/);
    if (personaFieldMatch) {
      const personaIndex = personaEntries.findIndex(([key]) => key === personaFieldMatch[1]);
      return {
        view: "persona",
        path: `persona_card.personas.${personaFieldMatch[1]}.${personaFieldMatch[2]}`,
        selectType: "persona-item",
        selectIndex: personaIndex >= 0 ? personaIndex : 0,
        label: `分身 ${personaIndex >= 0 ? personaIndex + 1 : "?"}`,
      };
    }

    const fieldMap = {
      name: { view: "persona", path: "persona_card.name", label: "角色主体 / 角色名" },
      first_mes: { view: "persona", path: "persona_card.first_mes", label: "角色主体 / 开场白" },
      tags: { view: "persona", path: "persona_card.tags", label: "角色主体 / 标签" },
      personality: { view: "persona", path: "persona_card.personality", label: "角色主体 / 性格口吻" },
      mes_example: { view: "persona", path: "persona_card.mes_example", label: "角色主体 / 示例对话" },
      creator_notes: { view: "persona", path: "persona_card.creator_notes", label: "角色主体 / 隐藏规则" },
      project: { view: "persona", path: "persona_card.name", label: "工程内容" },
    };
    return fieldMap[field] || { view: "persona", path: "persona_card.name", label: `警告 ${index + 1}` };
  }

  function focusWarningTarget(button) {
    const view = button.dataset.warningView || "persona";
    const path = button.dataset.warningPath || "";
    const selectType = button.dataset.warningSelectType || "";
    const selectIndex = Number(button.dataset.warningSelectIndex);

    if (selectType === "persona-item") {
      selectedIndices.personaItem = clampIndex(selectIndex, Object.keys(project.persona_card.personas || {}).length);
    } else if (selectType === "worldbook-entry") {
      selectedIndices.worldbookEntry = clampIndex(selectIndex, project.worldbook.entries.length);
    } else if (selectType === "preset-item") {
      selectedIndices.presetItem = clampIndex(selectIndex, project.preset.presets.length);
    } else if (selectType === "memory-item") {
      selectedIndices.memoryItem = clampIndex(selectIndex, project.memory.items.length);
    }

    currentView = view;
    renderAll();

    if (!path) return;
    const selector = `[data-path="${cssEscape(path)}"]`;
    const target = document.querySelector(selector);
    if (!target) return;
    target.scrollIntoView({ behavior: "smooth", block: "center" });
    target.focus?.();
  }

  function cssEscape(value) {
    if (window.CSS?.escape) return window.CSS.escape(String(value || ""));
    return String(value || "").replace(/"/g, '\\"');
  }

  function renderJsonPreviews() {
    const worldbookPreview = $("#worldbookPreview");
    const presetPreview = $("#presetPreview");
    const memoryPreview = $("#memoryPreview");
    const databasePreview = $("#databasePreview");
    if (worldbookPreview) worldbookPreview.textContent = JSON.stringify(project.worldbook || {}, null, 2);
    if (presetPreview) presetPreview.textContent = JSON.stringify(project.preset || {}, null, 2);
    if (memoryPreview) memoryPreview.textContent = JSON.stringify(project.memory || {}, null, 2);
    if (databasePreview) databasePreview.textContent = JSON.stringify(project.database || {}, null, 2);
  }

  function renderCardPreview(card) {
    const sections = [
      ["名称", card.name],
      ["描述", card.description],
      ["性格口吻", card.personality],
      ["默认场景", card.scenario],
      ["开场白", card.first_mes],
      ["示例对话", card.mes_example],
      ["隐藏规则", card.creator_notes],
    ];

    let html = "";
    if (Array.isArray(card.tags) && card.tags.length) {
      html += '<h4>标签</h4><div class="tags-list">';
      card.tags.forEach((tag) => {
        html += `<span class="tag-badge">${escHtml(String(tag))}</span>`;
      });
      html += "</div>";
    }

    sections.forEach(([label, value]) => {
      html += `<h4>${label}</h4>`;
      html += `<div class="field-val">${value ? escHtml(String(value)) : '<span class="muted">未填写</span>'}</div>`;
    });
    if (card.personas && Object.keys(card.personas).length) {
      html += "<h4>Persona</h4>";
      Object.entries(card.personas).forEach(([key, value]) => {
        html += `<div class="field-val"><strong>${escHtml(key)}</strong> · ${escHtml(value.name || "")}`;
        if (value.description) html += `<br>${escHtml(value.description)}`;
        if (value.personality) html += `<br><span class="muted">性格：</span>${escHtml(value.personality)}`;
        html += "</div>";
      });
    }

    $("#cardPreview").innerHTML = html || '<p class="muted">还没有可预览的内容。</p>';
  }

  async function deleteSelectedProject() {
    const filename = selectedProjectFilename || currentFilename;
    if (!filename) {
      toast("还没有选中的工程。", "error");
      return;
    }
    if (!window.confirm(`确定删除 ${filename} 吗？`)) return;
    try {
      const response = await fetch(apiUrl(`/api/projects/${encodeURIComponent(filename)}`), { method: "DELETE" });
      if (!response.ok) throw new Error("删除失败");
      if (currentFilename === filename) {
        currentFilename = "";
        selectedProjectFilename = "";
      }
      toast(`已删除 ${filename}`);
      await openProjectList();
    } catch (error) {
      toast(`删除失败：${error.message}`, "error");
    }
  }

  function closeAllDialogs() {
    $$("dialog[open]").forEach((dialog) => dialog.close());
  }

  function scheduleAutosave() {
    clearTimeout(autoSaveTimer);
    setSaveStatus("编辑中…");
    autoSaveTimer = setTimeout(doAutosave, 350);
  }

  async function saveWorkspaceNow({ skipSync = false } = {}) {
    if (!skipSync) syncProjectFromRenderedFields();
    try {
      const response = await fetch(apiUrl("/api/workspace"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(project),
      });
      if (!response.ok) throw new Error("自动保存失败");
      const data = await response.json();
      project.updated_at = data.updated_at || project.updated_at;
      persistLocalDraft({ skipSync: true });
      setSaveStatus("已自动保存");
      return true;
    } catch {
      setSaveStatus("自动保存失败");
      return false;
    }
  }

  async function doAutosave() {
    await saveWorkspaceNow();
  }

  async function loadAutosave() {
    try {
      const response = await fetch(apiUrl("/api/workspace"));
      if (!response.ok) {
        restoreLocalDraft({ preferProjectDraft: false });
        renderAll();
        renderWarnings([], false);
        return;
      }
      const data = await response.json();
      project = normalizeProject(data.project || createEmptyProject());
      copilotState.pendingReview = null;
      copilotState.selectedCandidateIds = [];
      copilotState.collapsedCandidateIds = [];
      restoreLocalDraft({ preferProjectDraft: false });
      renderAll();
      renderWarnings([], false);
      setSaveStatus("已恢复自动保存");
    } catch {
      restoreLocalDraft({ preferProjectDraft: false });
      renderAll();
      renderWarnings([], false);
    }
  }

  applyTheme(getStoredTheme());
  bindEvents();
  bindCopilotDrag();
  renderAll();
  restoreLocalDraft({ preferProjectDraft: false });
  renderAll();
  setCopilotAnchor({ x: window.innerWidth - 96, y: window.innerHeight - 96 });
  loadCopilotSettings();
  loadAutosave();
  window.addEventListener("beforeunload", () => flushDraftForReload({ sendAutosave: false }));
  window.addEventListener("pagehide", () => flushDraftForReload({ sendAutosave: true }));
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      flushDraftForReload({ sendAutosave: true });
    }
  });
  window.addEventListener("resize", () => setCopilotAnchor({ x: $("#copilotLayer")?.offsetLeft, y: $("#copilotLayer")?.offsetTop }));
})();
