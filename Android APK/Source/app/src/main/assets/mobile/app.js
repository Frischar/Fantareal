/* ═══ Fantareal PE — Main Application ═══ */
(function () {
  'use strict';

  /* ── XuqiNative Bridge ───────────────────────────────────── */
  const Native = window.XuqiNative || {};

  function nativeChat(messages, opts) {
    return new Promise((resolve, reject) => {
      if (Native.postChatAsync) {
        Native.postChatAsync(JSON.stringify({ messages, ...opts }),
          res => { try { resolve(JSON.parse(res)); } catch { resolve({ text: res }); } },
          err => reject(new Error(err)));
      } else if (Native.postChat) {
        try {
          const r = Native.postChat(JSON.stringify({ messages, ...opts }));
          try { resolve(JSON.parse(r)); } catch { resolve({ text: r }); }
        } catch (e) { reject(e); }
      } else {
        reject(new Error('XuqiNative not available'));
      }
    });
  }

  function nativeSaveFile(name, content) {
    return new Promise((resolve, reject) => {
      if (Native.saveTextFileAsync) {
        Native.saveTextFileAsync(name, content,
          () => resolve(), err => reject(new Error(err)));
      } else { reject(new Error('saveTextFileAsync not available')); }
    });
  }

  function nativePickImage() {
    return new Promise((resolve, reject) => {
      if (Native.pickImageAsync) {
        Native.pickImageAsync(
          dataUrl => resolve(dataUrl),
          err => reject(new Error(err)));
      } else { reject(new Error('pickImageAsync not available')); }
    });
  }

  /* ── Constants ────────────────────────────────────────────── */
  const PRESETS = {
    'openai':     { url: 'https://api.openai.com/v1',       model: 'gpt-4.1-mini' },
    'openrouter': { url: 'https://openrouter.ai/api/v1',    model: 'openai/gpt-4.1-mini' },
    'claude':     { url: 'https://api.anthropic.com/v1',     model: 'claude-sonnet-4-20250514' },
    'deepseek':   { url: 'https://api.deepseek.com/v1',     model: 'deepseek-chat' },
    'custom':     { url: '', model: '' }
  };

  const STATE_KEY  = 'xuqi.runtime.state.v1';
  const THEME_KEY  = 'xuqi.theme';
  const PAGE_TITLES = {
    'chat': 'Chat', 'config': 'Config', 'card': 'Card',
    'memory': 'Memory', 'sprite': 'Sprite', 'preview': 'Preview',
    'card-writer': 'Card Writer'
  };

  /* ── State ────────────────────────────────────────────────── */
  let state = {
    config: {
      preset: 'openai', api_url: '', api_key: '', model: '',
      temperature: 0.8, timeout: 60, history_limit: 20, max_tokens: 0,
      memory_summary_length: 'medium', memory_summary_max_chars: 520
    },
    persona: { name: '', greeting: '', prompt: '', description: '', personality: '', scenario: '' },
    card: { name: '', tags: '', description: '', personality: '', scenario: '', first_mes: '', mes_example: '', creator_notes: '', plotStages: { A: { description: '', rules: '' }, B: { description: '', rules: '' }, C: { description: '', rules: '' } } },
    personas: [{}, {}, {}],
    memories: [],
    worldbook: [],
    messages: [],
    sprite_base_path: 'sprites',
    background_url: '',
    background_overlay: 0.42,
    ui_opacity: 0.82
  };

  /* ── Utilities ────────────────────────────────────────────── */
  const $ = s => document.querySelector(s);
  const $$ = s => document.querySelectorAll(s);

  function saveState() {
    try { localStorage.setItem(STATE_KEY, JSON.stringify(state)); } catch {}
  }

  function loadState() {
    try {
      const d = JSON.parse(localStorage.getItem(STATE_KEY));
      if (d) state = { ...state, ...d, config: { ...state.config, ...(d.config || {}) } };
    } catch {}
  }

  function showModal(title, body) {
    $('#modalTitle').textContent = title;
    $('#modalBody').textContent = typeof body === 'string' ? body : JSON.stringify(body, null, 2);
    $('#modalOverlay').classList.add('open');
  }

  function hideModal() { $('#modalOverlay').classList.remove('open'); }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
  }

  /* ── Theme ────────────────────────────────────────────────── */
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.body.classList.toggle('light-theme', theme === 'light');
    const pill = $('#themePill');
    if (pill) pill.textContent = theme === 'dark' ? '暗色模式' : '浅色模式';
    try { localStorage.setItem(THEME_KEY, theme); } catch {}
  }

  function toggleTheme() {
    const cur = document.documentElement.getAttribute('data-theme') || 'dark';
    applyTheme(cur === 'dark' ? 'light' : 'dark');
  }

  function initTheme() {
    const saved = localStorage.getItem(THEME_KEY) || 'dark';
    applyTheme(saved);
    const sel = $('#cfgTheme');
    if (sel) sel.value = saved;
  }

  /* ── Appearance ───────────────────────────────────────────── */
  function applyOpacity(v) {
    document.documentElement.style.setProperty('--panel-alpha', v);
    document.documentElement.style.setProperty('--panel-strong-alpha', Math.min(1, +v + 0.1));
    document.documentElement.style.setProperty('--input-alpha', Math.max(0.4, +v - 0.04));
  }

  function applyBackground(url, overlay) {
    if (url) {
      document.documentElement.style.setProperty('--background-image', `url(${url})`);
    } else {
      document.documentElement.style.setProperty('--background-image', 'none');
    }
    document.documentElement.style.setProperty('--background-overlay-opacity', overlay ?? 0.42);
  }

  /* ── Router ───────────────────────────────────────────────── */
  let currentPage = 'chat';

  function navigateTo(page) {
    currentPage = page;
    $$('.page').forEach(p => p.classList.toggle('active', p.dataset.page === page));
    $$('.navlink').forEach(n => n.classList.toggle('active', n.dataset.page === page));
    $('#pageTitle').textContent = PAGE_TITLES[page] || page;
    closeSidebar();
    document.body.classList.toggle('chat-active', page === 'chat');

    if (page === 'card-writer') {
      const frame = $('#cardWriterFrame');
      if (frame && frame.src === 'about:blank') {
        frame.src = '/card-writer';
      }
    }

    if (page === 'config') refreshConfigPage();
    if (page === 'memory') refreshMemoryPage();
    if (page === 'sprite') refreshSpritePage();
    if (page === 'preview') refreshPreviewPage();
  }

  /* ── Sidebar ──────────────────────────────────────────────── */
  function openSidebar() { $('#sidebarOverlay').classList.add('open'); }
  function closeSidebar() { $('#sidebarOverlay').classList.remove('open'); }

  /* ── Chat ─────────────────────────────────────────────────── */
  let chatBusy = false;

  function addMessage(role, content, meta) {
    const wrap = document.createElement('div');
    wrap.className = `message ${role}`;
    const bubbleWrap = document.createElement('div');
    bubbleWrap.className = 'bubble-wrap';
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = content;
    bubbleWrap.appendChild(bubble);
    if (meta) {
      const m = document.createElement('div');
      m.className = 'message-meta';
      m.textContent = meta;
      bubbleWrap.appendChild(m);
    }
    wrap.appendChild(bubbleWrap);
    $('#messageList').appendChild(wrap);
    wrap.scrollIntoView({ behavior: 'smooth', block: 'end' });
    return bubble;
  }

  async function sendMessage() {
    const input = $('#messageInput');
    const text = input.value.trim();
    if (!text || chatBusy) return;

    input.value = '';
    chatBusy = true;
    $('#statusText').textContent = '思考中...';
    $('#sendBtn').disabled = true;

    addMessage('user', text, new Date().toLocaleTimeString());
    state.messages.push({ role: 'user', content: text });

    const historyCount = state.config.history_limit * 2;
    const recent = state.messages.slice(-historyCount);
    const sysPrompt = buildSystemPrompt();
    const apiMessages = [
      { role: 'system', content: sysPrompt },
      ...recent
    ];

    try {
      const result = await nativeChat(apiMessages, {
        model: state.config.model,
        temperature: state.config.temperature,
        max_tokens: state.config.max_tokens || undefined,
        timeout: state.config.timeout
      });

      const reply = result.text || result.content || result.message || '(empty)';
      const thinkMatch = reply.match(/<think>([\s\S]*?)<\/think>/);
      let displayText = reply;
      let thinkText = '';

      if (thinkMatch) {
        thinkText = thinkMatch[1].trim();
        displayText = reply.replace(/<think>[\s\S]*?<\/think>/, '').trim();
      }

      if (thinkText) {
        const details = document.createElement('details');
        details.className = 'think-box';
        const summary = document.createElement('summary');
        summary.textContent = '💭 思考过程';
        const content = document.createElement('div');
        content.className = 'think-content';
        content.textContent = thinkText;
        details.appendChild(summary);
        details.appendChild(content);
        const bubble = addMessage('assistant', displayText, new Date().toLocaleTimeString());
        bubble.insertBefore(details, bubble.firstChild);
      } else {
        addMessage('assistant', displayText, new Date().toLocaleTimeString());
      }

      state.messages.push({ role: 'assistant', content: reply });
      saveState();
    } catch (e) {
      addMessage('assistant', `错误：${e.message}`, new Date().toLocaleTimeString());
    } finally {
      chatBusy = false;
      $('#statusText').textContent = '就绪';
      $('#sendBtn').disabled = false;
    }
  }

  function buildSystemPrompt() {
    let parts = [];
    if (state.persona.prompt) parts.push(state.persona.prompt);
    if (state.persona.name) parts.push(`你的名字是${state.persona.name}。`);
    if (state.persona.personality) parts.push(`性格：${state.persona.personality}`);
    if (state.persona.scenario) parts.push(`场景：${state.persona.scenario}`);

    if (state.memories.length > 0) {
      const memText = state.memories.map(m => `• ${m.title}: ${m.content}`).join('\n');
      parts.push(`[记忆]\n${memText}`);
    }

    if (state.worldbook.length > 0) {
      const wbText = state.worldbook.map(w => `${w.keyword}: ${w.content}`).join('\n');
      parts.push(`[世界书]\n${wbText}`);
    }

    return parts.join('\n\n') || 'You are a helpful assistant.';
  }

  async function endConversation() {
    if (state.messages.length === 0) { showModal('提示', '当前没有对话记录。'); return; }

    $('#statusText').textContent = '正在生成记忆摘要...';

    try {
      const maxChars = state.config.memory_summary_max_chars || 520;
      const summaryPrompt = [
        { role: 'system', content: `请用中文总结以下对话，不超过${maxChars}个字符。提取关键信息作为记忆。` },
        ...state.messages.slice(-20),
        { role: 'user', content: '请总结这次对话的要点。' }
      ];

      const result = await nativeChat(summaryPrompt, {
        model: state.config.model,
        temperature: 0.3,
        max_tokens: 200
      });

      const summary = result.text || result.content || '';

      if (summary) {
        state.memories.push({
          id: Date.now(),
          title: `对话摘要 ${new Date().toLocaleDateString()}`,
          content: summary,
          tags: ['auto-summary'],
          notes: ''
        });
        saveState();
        showModal('记忆已保存', summary);
      }
    } catch (e) {
      showModal('摘要失败', e.message);
    }

    state.messages = [];
    saveState();
    $('#messageList').innerHTML = '';
    $('#statusText').textContent = '就绪';
  }

  function exportChat() {
    if (state.messages.length === 0) { showModal('提示', '无对话记录。'); return; }
    const text = state.messages.map(m => `[${m.role}]\n${m.content}`).join('\n\n---\n\n');
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `chat_${Date.now()}.txt`;
    a.click(); URL.revokeObjectURL(url);
  }

  /* ── Config Page ──────────────────────────────────────────── */
  function refreshConfigPage() {
    const c = state.config;
    $('#cfgPreset').value = c.preset || 'openai';
    $('#cfgApiUrl').value = c.api_url || '';
    $('#cfgApiKey').value = c.api_key || '';
    $('#cfgModel').value = c.model || '';
    $('#cfgTemp').value = c.temperature ?? 0.8;
    $('#cfgTimeout').value = c.timeout ?? 60;
    $('#cfgHistory').value = c.history_limit ?? 20;
    $('#cfgMaxTokens').value = c.max_tokens ?? 0;
    $('#cfgTheme').value = document.documentElement.getAttribute('data-theme') || 'dark';
    $('#cfgOpacity').value = state.ui_opacity ?? 0.82;
    $('#cfgOpacityVal').textContent = (state.ui_opacity ?? 0.82).toFixed(2);
    $('#cfgOverlay').value = state.background_overlay ?? 0.42;
    $('#cfgOverlayVal').textContent = (state.background_overlay ?? 0.42).toFixed(2);
    $('#cfgBgUrl').value = state.background_url || '';
    $('#cfgMemLen').value = c.memory_summary_length || 'medium';
    $('#cfgMemCustom').classList.toggle('hidden', c.memory_summary_length !== 'custom');
    $('#cfgMemMaxChars').value = c.memory_summary_max_chars || 520;

    $('#cfgStatCard').textContent = state.persona.name || '未加载';
    $('#cfgStatMemory').textContent = state.memories.length;
  }

  function saveConfig() {
    const c = state.config;
    c.preset = $('#cfgPreset').value;
    c.api_url = $('#cfgApiUrl').value.trim();
    c.api_key = $('#cfgApiKey').value.trim();
    c.model = $('#cfgModel').value.trim();
    c.temperature = parseFloat($('#cfgTemp').value) || 0.8;
    c.timeout = parseInt($('#cfgTimeout').value) || 60;
    c.history_limit = parseInt($('#cfgHistory').value) || 20;
    c.max_tokens = parseInt($('#cfgMaxTokens').value) || 0;
    c.memory_summary_length = $('#cfgMemLen').value;
    c.memory_summary_max_chars = parseInt($('#cfgMemMaxChars').value) || 520;

    applyTheme($('#cfgTheme').value);
    saveState();
    showModal('保存成功', '配置已保存。');
  }

  function applyPreset(name) {
    const p = PRESETS[name];
    if (!p) return;
    if (p.url) $('#cfgApiUrl').value = p.url;
    if (p.model) $('#cfgModel').value = p.model;
  }

  async function testConnection() {
    try {
      const result = await nativeChat([{ role: 'user', content: 'Say OK' }], {
        model: $('#cfgModel').value || state.config.model,
        temperature: 0,
        max_tokens: 5
      });
      showModal('连接成功', result.text || result.content || JSON.stringify(result));
    } catch (e) {
      showModal('连接失败', e.message);
    }
  }

  /* ── Card Editor Page ─────────────────────────────────────── */
  function fillCardForm(card) {
    $('#cardName').value = card.name || '';
    $('#cardTags').value = card.tags || '';
    $('#cardDesc').value = card.description || '';
    $('#cardPersonality').value = card.personality || '';
    $('#cardScenario').value = card.scenario || '';
    $('#cardFirstMes').value = card.first_mes || '';
    $('#cardMesExample').value = card.mes_example || '';
    $('#cardCreatorNotes').value = card.creator_notes || '';

    const ps = card.plotStages || {};
    $('#plotADesc').value = (ps.A || {}).description || '';
    $('#plotARules').value = (ps.A || {}).rules || '';
    $('#plotBDesc').value = (ps.B || {}).description || '';
    $('#plotBRules').value = (ps.B || {}).rules || '';
    $('#plotCDesc').value = (ps.C || {}).description || '';
    $('#plotCRules').value = (ps.C || {}).rules || '';

    const personas = card.personas || state.personas || [{}, {}, {}];
    ['p1', 'p2', 'p3'].forEach((prefix, i) => {
      const p = personas[i] || {};
      $(`#${prefix}Name`).value = p.name || '';
      $(`#${prefix}Desc`).value = p.description || '';
      $(`#${prefix}Personality`).value = p.personality || '';
    });
  }

  function buildCardPayload() {
    return {
      name: $('#cardName').value,
      tags: $('#cardTags').value,
      description: $('#cardDesc').value,
      personality: $('#cardPersonality').value,
      scenario: $('#cardScenario').value,
      first_mes: $('#cardFirstMes').value,
      mes_example: $('#cardMesExample').value,
      creator_notes: $('#cardCreatorNotes').value,
      plotStages: {
        A: { description: $('#plotADesc').value, rules: $('#plotARules').value },
        B: { description: $('#plotBDesc').value, rules: $('#plotBRules').value },
        C: { description: $('#plotCDesc').value, rules: $('#plotCRules').value }
      },
      personas: [
        { name: $('#p1Name').value, description: $('#p1Desc').value, personality: $('#p1Personality').value },
        { name: $('#p2Name').value, description: $('#p2Desc').value, personality: $('#p2Personality').value },
        { name: $('#p3Name').value, description: $('#p3Desc').value, personality: $('#p3Personality').value }
      ]
    };
  }

  function saveCard() {
    const card = buildCardPayload();
    state.card = card;
    state.personas = card.personas;
    state.persona = {
      name: card.name, greeting: card.first_mes,
      prompt: card.description, description: card.description,
      personality: card.personality, scenario: card.scenario
    };
    saveState();
    $('#cardStatus').textContent = `已保存 ${card.name || '(未命名)'} ${new Date().toLocaleTimeString()}`;
    updateChatHeader();
  }

  function exportCard() {
    const card = buildCardPayload();
    const json = JSON.stringify(card, null, 2);
    nativeSaveFile(`card_${card.name || 'export'}_${Date.now()}.json`, json)
      .catch(() => {
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `card_${Date.now()}.json`;
        a.click(); URL.revokeObjectURL(url);
      });
  }

  /* ── Memory Page ──────────────────────────────────────────── */
  function refreshMemoryPage() {
    $('#memCount').textContent = state.memories.length;
    const list = $('#memoryList');
    list.innerHTML = '';

    if (state.memories.length === 0) {
      list.innerHTML = '<div class="empty-state">暂无记忆条目。点击"新增记忆"开始添加。</div>';
      return;
    }

    state.memories.forEach((mem, idx) => {
      const card = document.createElement('div');
      card.className = 'memory-card';
      card.innerHTML = `
        <div class="memory-card-head">
          <input value="${esc(mem.title)}" data-idx="${idx}" data-field="title" class="mem-title-input" style="flex:1;font-weight:700;border:none;background:transparent;padding:0;color:var(--text);font-size:15px" />
          <button class="secondary small-chip mem-del" data-idx="${idx}" type="button">删除</button>
        </div>
        <textarea rows="3" data-idx="${idx}" data-field="content" class="mem-content-input">${esc(mem.content)}</textarea>
        <input placeholder="标签（逗号分隔）" value="${esc(Array.isArray(mem.tags) ? mem.tags.join(', ') : mem.tags || '')}" data-idx="${idx}" data-field="tags" class="mem-tags-input" style="font-size:13px" />
      `;
      list.appendChild(card);
    });
  }

  function addMemory() {
    state.memories.push({
      id: Date.now(),
      title: '新记忆',
      content: '',
      tags: [],
      notes: ''
    });
    saveState();
    refreshMemoryPage();
  }

  function saveMemories() {
    $$('.mem-title-input').forEach(el => {
      const idx = parseInt(el.dataset.idx);
      if (state.memories[idx]) state.memories[idx].title = el.value;
    });
    $$('.mem-content-input').forEach(el => {
      const idx = parseInt(el.dataset.idx);
      if (state.memories[idx]) state.memories[idx].content = el.value;
    });
    $$('.mem-tags-input').forEach(el => {
      const idx = parseInt(el.dataset.idx);
      if (state.memories[idx]) state.memories[idx].tags = el.value.split(',').map(t => t.trim()).filter(Boolean);
    });
    saveState();
    $('#memStatus').textContent = `已保存 ${state.memories.length} 条记忆 ${new Date().toLocaleTimeString()}`;
  }

  function deleteMemory(idx) {
    state.memories.splice(idx, 1);
    saveState();
    refreshMemoryPage();
  }

  /* ── Sprite Page ──────────────────────────────────────────── */
  function refreshSpritePage() {
    $('#spritePath').textContent = state.sprite_base_path || '-';
    $('#spriteCount').textContent = '0';
  }

  async function uploadSprite() {
    const tag = $('#spriteTag').value.trim();
    if (!tag) { showModal('提示', '请输入标签名。'); return; }

    try {
      const dataUrl = await nativePickImage();
      $('#spriteStatus').textContent = `已上传 ${tag} ${new Date().toLocaleTimeString()}`;
      showModal('上传成功', `标签 "${tag}" 已上传。`);
    } catch (e) {
      showModal('上传失败', e.message);
    }
  }

  /* ── Preview Page ─────────────────────────────────────────── */
  function refreshPreviewPage() {
    renderPreviewPersona();
    renderPreviewMemory();
    renderPreviewWorldbook();
    renderPreviewPreset();
  }

  function renderPreviewPersona() {
    const p = state.persona;
    const c = state.card;
    const el = $('#previewPersona');
    if (!el) return;

    el.innerHTML = `
      <div class="preview-card">
        <p class="eyebrow">Persona</p>
        <h3>${esc(p.name || '未设置')}</h3>
        ${p.greeting ? `<div class="preview-field"><span class="preview-field-label">开场白：</span><br>${esc(p.greeting)}</div>` : ''}
        ${p.description ? `<div class="preview-field"><span class="preview-field-label">描述：</span><br>${esc(p.description)}</div>` : ''}
        ${p.personality ? `<div class="preview-field"><span class="preview-field-label">性格：</span><br>${esc(p.personality)}</div>` : ''}
        ${p.scenario ? `<div class="preview-field"><span class="preview-field-label">场景：</span><br>${esc(p.scenario)}</div>` : ''}
        ${c.tags ? `<div class="preview-tags">${c.tags.split(',').map(t => `<span class="preview-tag">${esc(t.trim())}</span>`).join('')}</div>` : ''}
      </div>
      ${(c.plotStages && (c.plotStages.A?.description || c.plotStages.B?.description)) ? `
      <div class="preview-section">
        <h3 class="preview-section-head">剧情阶段</h3>
        ${['A', 'B', 'C'].filter(k => c.plotStages[k]?.description).map(k => `
          <div class="preview-card preview-sub-card">
            <strong>${k} 阶段</strong>
            <div class="preview-field">${esc(c.plotStages[k].description)}</div>
            ${c.plotStages[k].rules ? `<div class="preview-field"><span class="preview-field-label">规则：</span>${esc(c.plotStages[k].rules)}</div>` : ''}
          </div>
        `).join('')}
      </div>` : ''}
    `;
  }

  function renderPreviewMemory() {
    const el = $('#previewMemory');
    if (!el) return;

    if (state.memories.length === 0) {
      el.innerHTML = '<div class="preview-empty">暂无记忆条目。</div>';
      return;
    }

    el.innerHTML = `
      <div class="preview-section">
        <h3 class="preview-section-head">记忆库 <span class="preview-count">${state.memories.length}</span></h3>
        ${state.memories.map(m => `
          <div class="preview-card">
            <strong>${esc(m.title)}</strong>
            <div class="preview-field">${esc(m.content)}</div>
            ${m.tags && m.tags.length ? `<div class="preview-tags">${(Array.isArray(m.tags) ? m.tags : [m.tags]).map(t => `<span class="preview-tag">${esc(t)}</span>`).join('')}</div>` : ''}
          </div>
        `).join('')}
      </div>
    `;
  }

  function renderPreviewWorldbook() {
    const el = $('#previewWorldbook');
    if (!el) return;

    if (state.worldbook.length === 0) {
      el.innerHTML = '<div class="preview-empty">暂无世界书条目。</div>';
      return;
    }

    el.innerHTML = `
      <div class="preview-section">
        <h3 class="preview-section-head">世界书 <span class="preview-count">${state.worldbook.length}</span></h3>
        ${state.worldbook.map(w => `
          <div class="preview-card">
            <strong>${esc(w.keyword || w.title || '(未命名)')}</strong>
            <div class="preview-field">${esc(w.content || '')}</div>
            ${w.enabled !== undefined ? `<span class="${w.enabled ? 'preview-pill-on' : 'preview-pill-off'}">${w.enabled ? '启用' : '禁用'}</span>` : ''}
          </div>
        `).join('')}
      </div>
    `;
  }

  function renderPreviewPreset() {
    const el = $('#previewPreset');
    if (!el) return;

    const c = state.config;
    el.innerHTML = `
      <div class="preview-section">
        <h3 class="preview-section-head">模型预设</h3>
        <div class="preview-card">
          <div class="preview-field"><span class="preview-field-label">预设：</span> ${esc(c.preset || 'openai')}</div>
          <div class="preview-field"><span class="preview-field-label">API URL：</span> ${esc(c.api_url || '-')}</div>
          <div class="preview-field"><span class="preview-field-label">模型：</span> ${esc(c.model || '-')}</div>
          <div class="preview-info-row">
            <span>Temp: ${c.temperature ?? 0.8}</span>
            <span>超时: ${c.timeout ?? 60}s</span>
            <span>上下文: ${c.history_limit ?? 20}轮</span>
          </div>
        </div>
      </div>
    `;
  }

  /* ── Preview Tabs ─────────────────────────────────────────── */
  function switchPreviewTab(tab) {
    $$('#previewTabs .preview-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    $$('#previewPanels .preview-panel').forEach(p => p.classList.toggle('active', p.dataset.panel === tab));
  }

  /* ── Import / Export ──────────────────────────────────────── */
  function exportRuntime() {
    const json = JSON.stringify(state, null, 2);
    nativeSaveFile(`runtime_${Date.now()}.json`, json).catch(() => {
      const blob = new Blob([json], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `runtime_${Date.now()}.json`;
      a.click(); URL.revokeObjectURL(url);
    });
  }

  function importBundle(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result);
        if (data.persona) state.persona = { ...state.persona, ...data.persona };
        if (data.card) state.card = { ...state.card, ...data.card };
        if (data.memories) state.memories = data.memories;
        if (data.worldbook) state.worldbook = data.worldbook;
        if (data.config) state.config = { ...state.config, ...data.config };
        if (data.personas) state.personas = data.personas;
        if (data.messages) state.messages = data.messages;
        saveState();
        updateChatHeader();
        if (state.card.name) fillCardForm(state.card);
        showModal('导入成功', `已导入运行包数据。`);
      } catch (e) {
        showModal('导入失败', `解析错误：${e.message}`);
      }
    };
    reader.readAsText(file);
  }

  function renderMessages() {
    const list = $('#messageList');
    list.innerHTML = '';
    state.messages.forEach(m => addMessage(m.role, m.content));
  }

  /* ── Chat Header ──────────────────────────────────────────── */
  function updateChatHeader() {
    $('#chatPersonaName').textContent = state.persona.name || 'Template Character';
    $('#chatGreeting').textContent = state.persona.greeting || '';
  }

  /* ── Event Binding ────────────────────────────────────────── */
  function bindEvents() {
    // Sidebar
    $('#hamburgerBtn').addEventListener('click', openSidebar);
    $('#sidebarClose').addEventListener('click', closeSidebar);
    $('#sidebarOverlay').addEventListener('click', e => {
      if (e.target === $('#sidebarOverlay')) closeSidebar();
    });

    // Navigation
    $$('.navlink').forEach(btn => {
      btn.addEventListener('click', () => navigateTo(btn.dataset.page));
    });

    // Theme
    $('#themeToggleBtn').addEventListener('click', toggleTheme);

    // Modal
    $('#modalClose').addEventListener('click', hideModal);
    $('#modalConfirm').addEventListener('click', hideModal);
    $('#modalOverlay').addEventListener('click', e => {
      if (e.target === $('#modalOverlay')) hideModal();
    });

    // Chat
    $('#sendBtn').addEventListener('click', sendMessage);
    $('#messageInput').addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    $('#endConvBtn').addEventListener('click', endConversation);
    $('#exportChatBtn').addEventListener('click', exportChat);

    // Config
    $('#cfgPreset').addEventListener('change', () => applyPreset($('#cfgPreset').value));
    $('#cfgSaveBtn').addEventListener('click', saveConfig);
    $('#cfgTestBtn').addEventListener('click', testConnection);
    $('#cfgOpacity').addEventListener('input', () => {
      const v = $('#cfgOpacity').value;
      $('#cfgOpacityVal').textContent = parseFloat(v).toFixed(2);
      state.ui_opacity = parseFloat(v);
      applyOpacity(v);
    });
    $('#cfgOverlay').addEventListener('input', () => {
      const v = $('#cfgOverlay').value;
      $('#cfgOverlayVal').textContent = parseFloat(v).toFixed(2);
      state.background_overlay = parseFloat(v);
      applyBackground(state.background_url, v);
    });
    $('#cfgBgUrl').addEventListener('change', () => {
      state.background_url = $('#cfgBgUrl').value.trim();
      applyBackground(state.background_url, state.background_overlay);
      saveState();
    });
    $('#cfgBgFile').addEventListener('change', e => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        state.background_url = reader.result;
        applyBackground(reader.result, state.background_overlay);
        saveState();
        $('#cfgBgUrl').value = '(本地图片)';
      };
      reader.readAsDataURL(file);
    });
    $('#cfgBgClear').addEventListener('click', () => {
      state.background_url = '';
      applyBackground('', state.background_overlay);
      saveState();
      $('#cfgBgUrl').value = '';
    });
    $('#cfgTheme').addEventListener('change', () => applyTheme($('#cfgTheme').value));
    $('#cfgMemLen').addEventListener('change', () => {
      $('#cfgMemCustom').classList.toggle('hidden', $('#cfgMemLen').value !== 'custom');
    });
    $('#cfgMemSave').addEventListener('click', () => {
      state.config.memory_summary_length = $('#cfgMemLen').value;
      state.config.memory_summary_max_chars = parseInt($('#cfgMemMaxChars').value) || 520;
      saveState();
      $('#cfgMemStatus').textContent = '已保存';
    });

    // Import/Export
    $('#exportRuntimeBtn').addEventListener('click', exportRuntime);
    $('#cfgExportState').addEventListener('click', exportRuntime);
    $('#cfgExportBundle').addEventListener('click', exportRuntime);
    $('#cfgBundleImport').addEventListener('change', e => {
      if (e.target.files[0]) importBundle(e.target.files[0]);
    });

    // Card Editor
    $('#cardSaveBtn').addEventListener('click', saveCard);
    $('#cardExportBtn').addEventListener('click', exportCard);

    // Memory
    $('#memAddBtn').addEventListener('click', addMemory);
    $('#memSaveBtn').addEventListener('click', saveMemories);
    $('#memReloadBtn').addEventListener('click', refreshMemoryPage);
    $('#memoryList').addEventListener('click', e => {
      if (e.target.classList.contains('mem-del')) {
        deleteMemory(parseInt(e.target.dataset.idx));
      }
    });

    // Sprite
    $('#spriteUploadBtn').addEventListener('click', uploadSprite);
    $('#spriteRescanBtn').addEventListener('click', refreshSpritePage);

    // Preview tabs
    $$('#previewTabs .preview-tab').forEach(tab => {
      tab.addEventListener('click', () => switchPreviewTab(tab.dataset.tab));
    });
  }

  /* ── Init ─────────────────────────────────────────────────── */
  function init() {
    loadState();
    initTheme();
    applyOpacity(state.ui_opacity ?? 0.82);
    applyBackground(state.background_url, state.background_overlay);
    updateChatHeader();
    fillCardForm(state.card);

    const presetSel = $('#cfgPreset');
    if (presetSel) {
      presetSel.innerHTML = Object.keys(PRESETS).map(k => `<option value="${k}">${k}</option>`).join('');
    }

    renderMessages();
    bindEvents();
    navigateTo('chat');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
