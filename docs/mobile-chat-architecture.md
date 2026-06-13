# 小手机模块架构与修改指南

本文整理 Fantareal `mods/mobile-chat` 模块当前的运行方式、文件职责、数据流和常见修改入口，供后续 UI 与功能开发参考。

## 1. 模块定位

小手机是一个独立的 FastAPI Mod，同时向 Fantareal 主 Chat 页面注入前端资源。

它包含两套界面：

- 主 Chat 内的悬浮球、手机面板和轻应用。
- 独立的小手机后台管理页面。

小手机的数据与主 Chat 历史基本隔离。它会读取当前角色卡、主剧情摘要和记忆作为生成上下文，但群聊、频道事件、通知和电话记录保存在自己的数据目录中。

## 2. 启动与挂载流程

主程序启动时执行以下流程：

```text
Fantareal 启动
  -> 扫描 mods/*/app.py
  -> 读取每个 Mod 的 mod.json
  -> 加载 Mod 暴露的 FastAPI app
  -> 将小手机挂载到 /mods/mobile-chat/app
  -> 把 mod.json 中声明的 CSS/JS 注入主 Chat
  -> mobile-chat-chat.js 在主页面创建悬浮球和手机面板
```

相关文件：

| 文件 | 职责 |
| --- | --- |
| `fantareal/mods_runtime.py` | 扫描、加载和挂载 Mod |
| `fantareal/app.py` | 启动主应用并调用 `mount_discovered_mods()` |
| `mods/mobile-chat/mod.json` | 声明名称、版本和主 Chat hooks |
| `templates/index.html` | 将 Mod 的 CSS/JS hooks 插入主 Chat |
| `mods/mobile-chat/app.py` | 小手机 FastAPI 子应用 |

小手机的实际挂载地址为：

```text
/mods/mobile-chat/app
```

常用地址：

```text
/mods/mobile-chat             小手机后台入口
/mods/mobile-chat/app/        小手机后台页面
/mods/mobile-chat/app/chat    独立聊天展示页
/mods/mobile-chat/app/api/*   小手机 API
```

## 3. 主 Chat 内嵌方式

小手机不是通过 iframe 嵌入主 Chat。

`mobile-chat-chat.js` 被加载后，会直接在主页面的 `body` 中创建：

```html
<div id="fantareal-mobile-chat-root"></div>
```

随后 `render()` 使用字符串模板生成悬浮球和手机面板内容。

初始化入口位于：

```text
mods/mobile-chat/static/mobile-chat-chat.js
  -> init()
  -> document.body.appendChild(root)
  -> render()
  -> loadSettings()
  -> loadStickers()
  -> loadApps()
  -> loadChannels()
```

因此，小手机前台 UI 修改通常不需要修改主 Chat 模板。

## 4. 目录与文件职责

```text
mods/mobile-chat/
├─ app.py
├─ mod.json
├─ prompts/
│  └─ mobile_chat_prompt.txt
├─ templates/
│  ├─ index.html
│  └─ chat.html
└─ static/
   ├─ mobile-chat-chat.js
   ├─ mobile-chat-chat.css
   ├─ mobile-chat-ui.css
   ├─ mobile-chat-admin.js
   ├─ mobile-chat-admin.css
   ├─ test_text_bubble_parts.mjs
   └─ stickers/
```

### `app.py`

小手机的后端主体，负责：

- 设置读写与兼容清洗。
- 群聊、消息和角色资料。
- 动态、论坛、直播、邮箱、日记和日程频道。
- 通知与电话会话。
- Prompt 构建和模型调用。
- 模型 JSON 输出解析。
- 后台管理 API。
- 数据导出和诊断。

该文件体积较大。进行 UI 修改时应尽量避免同时重构后端。

### `mobile-chat-chat.js`

主 Chat 内小手机的前端主体，负责：

- 保存当前前端状态。
- 生成所有手机页面 HTML。
- 处理点击、提交、输入和拖拽事件。
- 请求小手机 API。
- 自动续聊和未读状态。
- 悬浮球与面板位置。

主要渲染函数：

| 函数 | 页面或组件 |
| --- | --- |
| `homeMarkup()` | 手机桌面 |
| `groupsMarkup()` | 群聊列表 |
| `createMarkup()` | 创建群聊 |
| `chatMarkup()` | 聊天消息区 |
| `composerMarkup()` | 聊天输入栏 |
| `settingsMarkup()` | 手机内设置 |
| `stickersMarkup()` | 贴纸页面 |
| `assistMarkup()` | 人物生成 |
| `channelMarkup()` | 各类频道 |
| `notificationsMarkup()` | 通知 |
| `phoneMarkup()` | 电话 |
| `render()` | 整体渲染入口 |

### `mobile-chat-chat.css`

小手机前台的主要视觉样式，包括：

- 悬浮球。
- 手机外框和面板。
- 桌面 App 网格。
- 群聊和气泡。
- 输入栏。
- 各轻应用页面。
- 响应式布局。
- `modern`、`social`、`xianxia`、`apocalypse` 主题覆盖。

### `mobile-chat-ui.css`

提供一层共用 UI 样式和变量映射，统一按钮、卡片、输入框、空状态等基础组件。

### 后台相关文件

| 文件 | 职责 |
| --- | --- |
| `templates/index.html` | 后台页面骨架和各管理面板 |
| `mobile-chat-admin.js` | 后台数据加载、表单和操作 |
| `mobile-chat-admin.css` | 后台视觉样式 |

后台目前提供：

- API 与模型配置。
- 生成参数。
- 工作台与 Prompt 测试。
- 群聊和角色管理。
- 人物生成。
- 表情包管理。
- 自动行为。
- Prompt 配置。
- 应用和频道管理。
- UI 设置。
- 诊断和数据清理。

## 5. 前端状态与渲染

前台状态集中保存在 `mobile-chat-chat.js` 的 `state` 对象中。

主要字段包括：

```text
settings             小手机设置
groups               群聊列表
messages             当前群聊消息
roles                可用角色
apps                 桌面应用注册表
channels             频道列表
channelEvents        各频道事件
notifications        通知
phoneSessions        电话会话
currentGroupId        当前群聊
currentChannelId      当前频道
page                  当前页面
open                  面板是否展开
loading/generating    请求状态
```

当前实现采用整体重新渲染：

```text
状态发生变化
  -> render()
  -> root.innerHTML 被重新生成
  -> 必要时恢复滚动位置
```

修改 UI 时应注意：

- 不要依赖元素在多次 `render()` 之间持续存在。
- 长期状态应放入 `state`，不能只放在 DOM 属性里。
- 新交互通常应接入统一的 `onClick()`、`onSubmit()`、`onInput()` 或 `onChange()`。
- 需要保留列表滚动位置时，应使用已有的滚动恢复方式。

## 6. 主题系统

当前支持：

```text
modern
social
xianxia
apocalypse
```

每次渲染时会设置：

```js
root.dataset.theme = currentTheme();
```

CSS 通过属性选择器覆盖基础样式：

```css
#fantareal-mobile-chat-root[data-theme="social"] {
  /* 主题变量 */
}

#fantareal-mobile-chat-root[data-theme="social"] .fmcp-message-bubble {
  /* social 主题气泡 */
}
```

主题覆盖大致位于 `mobile-chat-chat.css` 第 5290 行以后。

如果只修改 QQ/WX 风格，应优先修改：

```text
#fantareal-mobile-chat-root[data-theme="social"] ...
```

这样可以避免影响其他主题。

主题不仅影响 CSS，也会影响部分界面文案。相关逻辑位于：

```text
currentTheme()
themedLabel()
themedAppCopy()
themedHomeCopy()
```

## 7. 群聊消息生成流程

用户发送消息时：

```text
输入消息
  -> sendMessage()
  -> POST /api/generate
  -> 后端保存用户消息
  -> build_mobile_model_messages()
  -> call_chat_model()
  -> parse_model_mobile_messages()
  -> 保存 AI 消息
  -> 前端重新读取消息
  -> render()
```

主要入口：

| 位置 | 职责 |
| --- | --- |
| `sendMessage()` | 前端发起生成 |
| `POST /api/generate` | 后端生成入口 |
| `build_mobile_model_messages()` | 拼装群聊 Prompt |
| `call_chat_model()` | 请求 Chat Completions 接口 |
| `parse_model_mobile_messages()` | 解析模型 JSON |
| `append_group_messages()` | 保存消息 |

角色续聊使用：

```text
continueChat()
  -> POST /api/continue
  -> generation_mode = role_continue
```

## 8. Prompt 上下文

群聊生成上下文主要包含：

- 群聊名称和简介。
- 群成员。
- 小手机角色资料覆盖。
- 最近的小手机群聊消息。
- 当前用户消息。
- 回复角色数量。
- 是否允许角色互相回复。
- 可用贴纸目录。
- 当前角色卡对应的主剧情摘要和记忆。
- 世界主题提示。
- 后台配置的自定义 Prompt。

小手机会读取主剧情作为最新设定依据，但生成结果仍写入小手机自己的数据目录。

默认 Prompt 文件：

```text
mods/mobile-chat/prompts/mobile_chat_prompt.txt
```

后台自定义 Prompt 开启后，会优先使用组装后的配置。

## 9. API 与模型调用

前端根据当前脚本 URL 自动计算：

```js
const apiBase = `${modBase}/api`;
```

请求最终发往：

```text
/mods/mobile-chat/app/api/*
```

模型调用使用兼容 OpenAI Chat Completions 的接口：

```text
POST {base_url}/chat/completions
```

主要请求字段：

```json
{
  "model": "...",
  "messages": [],
  "temperature": 0.85,
  "max_tokens": 500,
  "stream": false
}
```

模型配置可以：

- 跟随主程序。
- 使用小手机独立配置。

## 10. 数据存储

### 全局配置

```text
data/mobile_chat/settings.json
data/mobile_chat/app_registry.json
data/mobile_chat/channels.json
data/mobile_chat/prompt_blocks.json
data/mobile_chat/automation_state.json
```

### 按角色卡隔离的数据

```text
data/mobile_chat/cards/{card_uid}/
├─ groups.json
├─ role_profiles.json
├─ generation_state.json
├─ notifications.json
├─ parser_diagnostics.json
├─ phone_calls.json
├─ messages/
└─ events/
```

`card_uid` 根据当前角色卡生成。切换角色卡后，小手机会读取该角色卡对应的数据目录。

### 修改数据结构时的注意事项

如果新增或修改持久化字段，应同步检查：

1. Pydantic 请求模型。
2. `DEFAULT_*` 默认值。
3. 对应的 `sanitize_*()` 清洗函数。
4. JSON 读取和写入函数。
5. API 返回结构。
6. 前端 `state` 和渲染逻辑。
7. 旧数据缺少新字段时的默认行为。

## 11. 常见修改入口

### 调整手机尺寸和位置

主要修改：

```text
mobile-chat-chat.css
  .fmcp-fab
  .fmcp-panel
  .fmcp-shell

mobile-chat-chat.js
  panelStyle()
  applyResponsivePositions()
  clampElementPosition()
  persistFloatingPosition()
  persistPanelPosition()
```

### 修改桌面

主要修改：

```text
mobile-chat-chat.js
  homeMarkup()
  themedAppCopy()
  openAppPage()

app.py
  DEFAULT_APP_REGISTRY
```

如果只是隐藏或排序现有 App，可以通过后台应用管理完成，不一定需要改代码。

### 修改聊天气泡

主要修改：

```text
mobile-chat-chat.js
  messageMarkup()
  textBubbleParts()
  textBubbleMarkup()

mobile-chat-chat.css
  .fmcp-message
  .fmcp-message-bubble
  .fmcp-message-meta
  .fmcp-message-foot
```

气泡切分已有测试：

```text
mods/mobile-chat/static/test_text_bubble_parts.mjs
```

### 修改输入栏

主要修改：

```text
mobile-chat-chat.js
  composerMarkup()
  sendMessage()
  sendSticker()
  continueChat()

mobile-chat-chat.css
  .fmcp-composer
  .fmcp-composer-row
  .fmcp-composer-input
  .fmcp-composer-icon
```

### 修改频道页面

主要修改：

```text
feedChannelMarkup()
forumChannelMarkup()
liveChannelMarkup()
mailChannelMarkup()
diaryChannelMarkup()
calendarChannelMarkup()
eventDetailMarkup()
```

后端对应：

```text
GET/POST /api/channels/*
build_channel_*_messages()
parse_channel_*()
```

### 新增一种消息类型

至少需要修改：

1. 后端 `MESSAGE_TYPES`。
2. 请求模型和输入验证。
3. `sanitize_message()`。
4. 模型输出结构与解析函数。
5. `messageMarkup()`。
6. 消息 CSS。
7. 必要的兼容测试。

### 新增轻应用

至少需要修改：

1. `DEFAULT_APP_REGISTRY`。
2. App 图标定义。
3. 页面路由状态。
4. `bodyMarkup()` 或 `channelMarkup()`。
5. `openAppPage()`。
6. 后端 API 和数据结构。
7. 后台应用管理兼容。

如果新应用本质上只是另一种事件流，优先复用现有 channel/event 基座。

## 12. 当前风险点

### 后端单文件过大

`app.py` 同时负责存储、业务、模型、解析和 API。大规模重构容易引入回归。

建议 UI 改造阶段先保持后端结构稳定；确实需要拆分时，再按领域逐步迁移并补充测试。

### 前端整体重绘

每次 `render()` 都会替换根节点内容。新增弹窗、输入草稿、媒体播放或复杂动画时，需要明确哪些状态必须保存在 `state` 中。

### CSS 历史覆盖较多

`mobile-chat-chat.css` 包含多个版本阶段的追加样式。修改基础选择器可能被文件后部覆盖。

排查样式时应重点检查：

- 同一选择器是否在后文重复定义。
- 主题选择器是否覆盖基础样式。
- 移动端媒体查询是否再次覆盖。

### 模型输出依赖 JSON

功能字段变化会影响 Prompt contract 和解析器。修改模型输出结构时，不能只改前端显示。

## 13. 推荐改造顺序

建议将 UI 和功能修改分阶段进行：

1. 明确目标页面和主题。
2. 只调整 CSS，确认视觉方向。
3. 必要时修改对应的 `*Markup()` 结构。
4. 再增加前端交互状态。
5. 最后添加或修改后端 API。
6. 补充解析、数据兼容和交互测试。

对于 `social` 主题，优先从主题覆盖区进行视觉调整，可以把影响范围控制在 QQ/WX 风格内。

## 14. 基础验证

气泡切分测试：

```powershell
node "mods/mobile-chat/static/test_text_bubble_parts.mjs"
```

Python 语法检查：

```powershell
.\.venv\Scripts\python.exe -m compileall -q fantareal "mods/mobile-chat"
```

人工验证至少应覆盖：

- 主 Chat 能正常打开。
- 悬浮球显示、拖动和复位正常。
- 手机面板能打开和关闭。
- 桌面 App 可以进入和返回。
- 群聊消息可以发送、生成和刷新。
- 不同主题显示正常。
- 后台管理页面可以读取设置。
- 切换角色卡后读取对应的小手机数据。
