# 给 Gemini 3.1 Pro High 的 Fantareal 原生 APK 前端设计协作文档

版本：v0.1  
日期：2026-06-29  
协作方式：Claude 负责后端主程序架构与业务边界，Gemini 负责原生 Android 前端美化与交互设计。  
关联文档：`docs/原生APK后端主程序架构设计.md`

---

## 1. 写给 Gemini 的开场说明

你好，Gemini。

这个项目叫 **Fantareal**，是一个偏长期陪伴、角色扮演、记忆沉淀、世界书设定触发的 Android AI 聊天应用。当前 APK 仍然是 `WebView + HTML/JS` 套壳，我们准备推翻这套方案，重做成真正的 **原生 Android APK**。

Claude 这边会负责：

- 后端主程序架构。
- 数据层与存档。
- LLM Provider。
- prompt 拼装。
- 记忆、世界书、角色卡、预设、创意工坊等业务逻辑。
- 流式输出与错误处理。

希望你负责：

- 原生 Android 前端结构。
- 页面信息架构。
- 高质量视觉设计。
- 动效与交互细节。
- Compose/XML 组件拆分。
- 让 Fantareal 真正像一个漂亮、沉浸、顺滑的“AI 角色陪伴 App”，而不是把网页搬进手机。

请把本文件当成协作边界说明。前端可以大胆美化，但不要把核心业务逻辑重新塞回 UI 层。

---

## 2. 项目定位

Fantareal 不是普通 ChatGPT 套壳，而是一个以“角色陪伴 + 记忆 + 世界书 + 角色卡”为核心的本地 AI 聊天应用。

关键词：

- 长期陪伴
- 多角色/单角色角色卡
- 本地存档
- 长期记忆
- 世界书设定触发
- 预设规则模块
- 立绘/头像/背景
- 创意工坊阶段事件
- 对话结束归档成记忆
- 可调模型接口

前端设计要尽量体现：

1. **沉浸感**：像进入一个私人聊天空间，而不是工具后台。
2. **可配置但不压迫**：功能很多，但不要让设置页像工程面板吓到用户。
3. **长期关系感**：记忆、角色卡、世界书都应被设计成“角色世界的一部分”。
4. **本地安全感**：用户要知道数据在手机本地，API Key 不被随便导出。
5. **原生流畅感**：滑动、键盘、底栏、抽屉、过渡都要符合 Android 原生体验。

---

## 3. 技术建议

优先建议使用 **Jetpack Compose + Material 3**。

理由：

- 页面状态复杂，Compose 更适合响应式状态渲染。
- 聊天流式输出、底部输入框、抽屉、配置表单、卡片编辑器都适合 Compose 组件化。
- 后续主题系统、动态背景、毛玻璃/半透明层、动画更好维护。

如果因为项目现有 XML/AppCompat 基础选择 XML，也可以，但仍建议保持以下架构：

```text
UI Composable / View
  ↓
ViewModel
  ↓
UseCase / Backend Service
  ↓
Repository / Provider
```

前端不要直接：

- 读写 JSON 文件。
- 拼模型请求。
- 管理 API Key 明文。
- 自己做 prompt 拼装。
- 自己做世界书命中。
- 自己做记忆去重。

这些都由后端主程序提供。

---

## 4. 推荐视觉方向

### 4.1 主风格关键词

建议主视觉走：

> **“梦境聊天终端 × 私人角色手帐 × 轻拟物玻璃卡片”**

不要做成普通企业工具风，也不要做成太泛的紫色渐变 AI 风。

整体氛围：

- 夜间柔和。
- 半透明面板。
- 角色卡像手帐/档案卡。
- 记忆像收藏的碎片。
- 世界书像设定索引或魔法书目录。
- 聊天页像一个沉浸式场景。

### 4.2 色彩建议

默认暗色主题：

```text
背景底色：#0E111A / #101520
主面板：rgba(24, 30, 44, 0.72)
次级面板：rgba(255, 255, 255, 0.06)
主高亮：#7AA8FF
情感高亮：#F7B7D2
幻想高亮：#B79CFF
警告/错误：#FF8A8A
成功：#7FE0B0
文字主色：#F4F7FB
文字次级：#A9B4C7
描边：rgba(255,255,255,0.12)
```

浅色主题：

```text
背景底色：#F5F0EA
主面板：rgba(255,255,255,0.78)
次级面板：#EFE7DD
主高亮：#5F7EEA
情感高亮：#E98EB8
幻想高亮：#9B7AF2
文字主色：#212431
文字次级：#697086
描边：rgba(40,40,60,0.12)
```

注意：不要只做紫色渐变。Fantareal 可以有幻想感，但要更细腻、更私人。

### 4.3 字体与排版

中文优先使用系统字体即可，但排版要有层级：

- 页面大标题：稍大、留白足。
- 卡片标题：中等粗细。
- 正文：舒适行高，聊天气泡不要太拥挤。
- 元信息：小字号、低对比。

聊天正文建议：

- 行高至少 `1.45`。
- 气泡内边距要宽。
- 长文本要可读，避免每行过长。
- 支持角色名、时间、状态的小型 meta。

### 4.4 动效建议

应加入少量自然动效：

- 页面切换：轻微 fade + slide。
- 抽屉出现：背景模糊/遮罩 + 侧滑。
- 聊天气泡：新消息从底部轻轻浮入。
- 流式输出：文字逐步出现，不要闪烁。
- 发送按钮：请求中变为 loading/停止按钮。
- 记忆卡片：展开/折叠时自然过渡。
- 世界书命中：可用小徽章提示“命中 N 条”，不要打断聊天。

动效要“轻”，不要让用户觉得花哨拖慢。

---

## 5. 页面结构建议

建议主导航保留 7 个核心页，但视觉上不要像旧 Web 侧边栏那样拥挤。

主页面：

1. 聊天
2. 设置
3. 预设
4. 角色卡
5. 创意工坊
6. 记忆库
7. 世界书

移动端推荐结构：

- 聊天页为默认首页。
- 左侧抽屉或底部导航承载主入口。
- 高频入口放聊天页顶部/底部快捷按钮。
- 复杂配置页分组折叠。

### 5.1 应用框架

```text
MainActivity
  └─ FantarealApp
      ├─ AppScaffold
      │   ├─ TopBar / SceneHeader
      │   ├─ NavigationDrawer 或 BottomNav
      │   ├─ RouteHost
      │   └─ GlobalDialogHost / ToastHost
      └─ ViewModels
```

推荐用 Navigation Drawer，因为功能较多；底部导航只适合 3-5 个高频页。

如果使用底部导航，可只放：

- 聊天
- 角色
- 记忆
- 设置

其它页面从设置或更多菜单进入。

---

## 6. 聊天页设计

聊天页是最重要的页面，建议优先打磨。

### 6.1 布局结构

```text
┌────────────────────────────┐
│ 顶部场景栏                  │
│ 角色名 / 当前存档 / 命中状态 │
├────────────────────────────┤
│                            │
│ 背景图 / 立绘层             │
│                            │
│ 消息列表                    │
│  - 角色开场白               │
│  - user bubble             │
│  - assistant bubble        │
│                            │
├────────────────────────────┤
│ 快捷操作：设置/角色/结束/导出 │
├────────────────────────────┤
│ 输入框 + 发送/停止按钮       │
└────────────────────────────┘
```

### 6.2 顶部场景栏

显示：

- 当前角色名。
- 当前 slot 名称。
- 当前阶段：A/B/C 或 temp 值，可做成小徽章。
- 世界书命中状态：例如“世界书 2”。
- 设置入口。

顶部栏应透明或半透明，和背景融合。

### 6.3 消息气泡

用户消息：

- 靠右。
- 颜色稍亮或主高亮低透明。
- 可显示头像/昵称，但不要抢戏。

角色消息：

- 靠左。
- 使用更柔和的面板。
- 支持角色头像/立绘表情。
- 支持流式输出。
- 支持“思考/调试内容”折叠，但默认隐藏。

消息模型 UI：

```kotlin
data class ChatMessageUiModel(
    val id: String,
    val role: UiRole,
    val speakerName: String,
    val avatarUri: String?,
    val content: String,
    val createdAtText: String,
    val isStreaming: Boolean,
    val spriteTag: String?,
    val thinkingText: String?,
    val error: Boolean
)
```

### 6.4 输入区

输入区要像现代聊天 App：

- 圆角大输入框。
- 支持多行输入。
- Enter 行为在手机上不重要，重点是软键盘适配。
- 发送中显示停止按钮。
- 长按/菜单可后续扩展：插入记忆、选择表情、导入图片。

### 6.5 流式输出体验

后端会提供统一事件：

- Started
- PromptReady
- TokenDelta
- ThinkingDelta
- SpriteTagDetected
- Completed
- Failed

前端表现：

- Started：输入框禁用或发送按钮变停止。
- TokenDelta：追加到当前 assistant 气泡。
- SpriteTagDetected：切换头像/立绘表情。
- ThinkingDelta：如果开启调试，写入折叠区域。
- Completed：取消 loading，保存滚动位置。
- Failed：气泡变错误态，提供重试按钮。

---

## 7. 设置页设计

设置页要分组，不要一屏塞满。

建议分区：

1. 模型接口
2. 输出参数
3. 嵌入/重排
4. 外观与背景
5. 数据与备份
6. 高级调试

### 7.1 模型接口卡片

字段：

- 接口预设：自定义 / OpenAI / DeepSeek / OpenRouter / SiliconFlow / MiniMax / Anthropic Direct
- API URL
- API Key
- 模型名
- 测试连接按钮

API Key 输入要有：

- 显示/隐藏按钮。
- “仅保存在本机加密存储”的提示。
- 保存成功反馈。

### 7.2 Provider 能力提示

当前后端会做 Provider 抽象。前端可以展示能力标签：

```text
支持流式
支持 temperature
支持 JSON 输出
支持 Claude structured output
支持 embedding
支持 rerank
```

如果用户选 Anthropic Direct，需要提示：

- Opus 4.8/4.7 不使用 temperature。
- JSON 输出走 structured output。
- 默认推荐 `claude-opus-4-8`。

但这只是 UI 提示，具体请求过滤由后端处理。

---

## 8. 角色卡页面设计

角色卡页建议做成“角色档案馆”。

### 8.1 页面结构

```text
角色卡总览
  ├─ 当前角色卡摘要
  ├─ 主角色信息
  ├─ 多 persona 列表
  ├─ 剧情阶段 A/B/C
  ├─ 创意工坊入口
  └─ 导入 / 导出 / 应用
```

### 8.2 视觉建议

- 用档案卡片样式。
- 角色名醒目。
- tags 作为小胶囊。
- `first_mes` 做成开场白预览。
- 多角色 persona 使用横向卡片或列表。
- plotStages 用时间线或阶段卡。

### 8.3 交互重点

- 导入角色卡后，不要自动清空运行态，除非用户明确选择。
- 应用角色卡后，应明显提示当前聊天 persona 已更新。
- 编辑字段要有保存状态：未保存 / 已保存。
- 大文本编辑建议全屏编辑器。

---

## 9. 记忆库页面设计

记忆库是 Fantareal 的灵魂之一，不要设计成普通 JSON 列表。

### 9.1 页面结构

```text
记忆库
  ├─ 长期记忆列表
  ├─ 合并记忆
  ├─ 记忆大纲
  ├─ 已删除记忆 / 墓碑
  └─ 导入 / 导出 / 合并 / 搜索
```

### 9.2 记忆卡片

每条记忆显示：

- title
- content 摘要
- tags
- notes 可折叠
- 编辑 / 删除 / 置顶 后续可扩展

删除时：

- 必须二次确认。
- 文案说明：删除后会进入“失效记录”，用于阻止模型把旧记忆写回来。

### 9.3 记忆归档反馈

用户点击“结束当前对话”后：

- 不要只 toast。
- 建议弹一个轻量结果卡：
  - 生成了哪条记忆。
  - 是否因重复跳过。
  - 是否因已删除记忆拦截。
  - temp 阶段是否变化。

---

## 10. 世界书页面设计

世界书可设计成“设定索引”。

### 10.1 页面结构

```text
世界书
  ├─ 启用开关
  ├─ 全局设置：最大命中数、大小写、整词、递归
  ├─ 词条列表
  ├─ 词条编辑器
  └─ 调试/命中测试
```

### 10.2 词条卡片

显示：

- title
- primaryTriggers
- secondaryTriggers
- entryType：常驻/关键词
- enabled 状态
- chance / sticky / cooldown 小标签
- insertionPosition 小标签

编辑器可分 tab：

1. 基础
2. 触发
3. 注入
4. 高级
5. 备注

### 10.3 命中调试

建议提供“输入一句话测试命中”的调试区：

- 用户输入测试文本。
- 前端调用后端 `WorldbookEngine.previewMatch()`。
- 展示命中词条、注入位置、丢弃原因。

这对高级用户很重要。

---

## 11. 预设页面设计

预设页面是 prompt 模块管理。

建议：

- 左侧/顶部是预设库列表。
- 右侧/下方是当前预设编辑。
- 模块开关使用清晰的 Switch + 说明。
- 额外 prompt 用卡片编辑。

预设模块示例：

- 防抢话
- 短段落
- 长段落
- 第二人称
- 第三人称
- 防重复
- 不收束

前端只编辑 preset 数据，不负责编译最终 prompt。编译由后端 `PresetService` 完成。

---

## 12. 创意工坊页面设计

创意工坊与 `temp` 阶段有关。它不是核心第一阶段，但建议预留入口。

当前阶段规则：

```text
A 阶段：temp = 0 ~ 2
B 阶段：temp = 3 ~ 5
C 阶段：temp >= 6
```

页面应显示：

- 当前 temp。
- 当前阶段。
- 每个阶段绑定动作。
- 动作类型：播放音乐 / 弹出图片。
- 触发历史。

视觉上可以做成“剧情阶段板”。

---

## 13. 导入/导出与文件选择

前端需要调用后端/系统能力完成：

- 导入角色卡 JSON。
- 导入预设卡。
- 导入记忆卡。
- 导入世界书卡。
- 导出聊天记录。
- 导出当前角色卡。
- 导出运行态备份。
- 上传背景图。
- 上传头像/立绘图片。

Android 推荐使用：

- Storage Access Framework。
- 系统 Photo Picker。
- MediaStore 或 app 私有目录。

UI 要清楚提示：

- 普通备份默认不含 API Key。
- 导入会覆盖哪些数据。
- 导入前会自动备份当前 slot。

---

## 14. 前后端状态边界

后端建议给前端 ViewModel 暴露这些状态。

### 14.1 ChatUiState

```kotlin
data class ChatUiState(
    val activeSlotName: String,
    val personaName: String,
    val stageText: String,
    val messages: List<ChatMessageUiModel>,
    val isSending: Boolean,
    val statusText: String,
    val currentSpriteTag: String?,
    val worldbookHitCount: Int,
    val promptPreview: String?,
    val errorDialog: ErrorDialogState?
)
```

### 14.2 SettingsUiState

```kotlin
data class SettingsUiState(
    val providerType: ProviderType,
    val presets: List<ModelPresetUiModel>,
    val apiBaseUrl: String,
    val model: String,
    val hasApiKey: Boolean,
    val temperature: Double?,
    val timeoutSec: Int,
    val historyLimit: Int,
    val maxTokens: Int,
    val capability: ProviderCapabilityUiModel,
    val appearance: AppearanceUiModel
)
```

### 14.3 前端 Intent

```kotlin
sealed interface AppIntent {
    data class SendMessage(val text: String) : AppIntent
    data object StopGeneration : AppIntent
    data object EndConversation : AppIntent
    data object PreviewPrompt : AppIntent
    data class SwitchSlot(val slotId: String) : AppIntent
    data class SaveSettings(val form: SettingsForm) : AppIntent
    data class ImportRoleCard(val uri: Uri) : AppIntent
    data object ExportRuntimeBackup : AppIntent
}
```

前端只发 intent，不直接操作业务文件。

---

## 15. 后端会提供的关键能力

你可以假设后端会逐步提供以下能力：

```kotlin
class ChatViewModel : ViewModel {
    val uiState: StateFlow<ChatUiState>
    fun send(text: String)
    fun stop()
    fun endConversation()
    fun previewPrompt()
}

class SettingsViewModel : ViewModel {
    val uiState: StateFlow<SettingsUiState>
    fun save(form: SettingsForm)
    fun testConnection()
}

class RoleCardViewModel : ViewModel {
    val uiState: StateFlow<RoleCardUiState>
    fun importCard(uri: Uri)
    fun applyEdit(form: RoleCardForm)
    fun exportCurrentCard()
}

class MemoryViewModel : ViewModel {
    val uiState: StateFlow<MemoryUiState>
    fun saveMemory(item: MemoryItemForm)
    fun deleteMemory(id: String)
    fun mergeSelected(ids: List<String>)
}

class WorldbookViewModel : ViewModel {
    val uiState: StateFlow<WorldbookUiState>
    fun saveEntry(form: WorldbookEntryForm)
    fun testMatch(text: String)
}
```

如果你做 UI 原型时后端暂时未完成，可先用 fake ViewModel/mock state，但请保持接口形状接近上述边界。

---

## 16. 第一阶段 UI 最小范围

为了尽快替代 WebView，第一阶段前端最小可做：

1. 原生聊天页。
2. 设置页：API URL / API Key / model / 测试连接。
3. 存档切换与重命名。
4. 角色卡导入与当前角色摘要。
5. 记忆列表基础展示。
6. 世界书基础列表展示。
7. 导出运行态备份。

第一阶段不必完整做：

- Card Writer。
- 复杂记忆合并。
- 完整创意工坊。
- 高级世界书所有字段。

但 UI 架构要给它们预留入口。

---

## 17. 组件拆分建议

```text
ui/
  app/
    FantarealApp.kt
    AppScaffold.kt
    AppNavigation.kt
  theme/
    FantarealTheme.kt
    Colors.kt
    Typography.kt
  chat/
    ChatScreen.kt
    ChatTopBar.kt
    MessageList.kt
    MessageBubble.kt
    ComposerBar.kt
    PromptPreviewSheet.kt
  settings/
    SettingsScreen.kt
    ModelConfigCard.kt
    ProviderCapabilityChips.kt
    AppearanceCard.kt
  rolecard/
    RoleCardScreen.kt
    RoleSummaryCard.kt
    PersonaList.kt
    PlotStageTimeline.kt
  memory/
    MemoryScreen.kt
    MemoryCard.kt
    MemoryArchiveResultSheet.kt
  worldbook/
    WorldbookScreen.kt
    WorldbookEntryCard.kt
    WorldbookEditorSheet.kt
    WorldbookMatchDebugSheet.kt
  preset/
    PresetScreen.kt
  workshop/
    WorkshopScreen.kt
  common/
    GlassPanel.kt
    FantarealButton.kt
    SectionHeader.kt
    EmptyState.kt
    ConfirmDialog.kt
```

---

## 18. 可访问性与手机适配

必须注意：

- 所有按钮有 contentDescription。
- 文字不依赖低对比颜色。
- 支持系统字体缩放。
- 输入框被键盘顶起时不遮挡。
- 横屏至少不崩。
- 小屏设备上设置页字段不要挤成两列。
- 长文本编辑器支持全屏。
- 所有危险操作有确认对话框。

---

## 19. 不要做的事

请避免：

1. 不要继续用 WebView 承载主 UI。
2. 不要把 JS/localStorage 逻辑复制到 Compose 里。
3. 不要让 UI 直接拼 `/chat/completions` 请求。
4. 不要让 UI 直接读写 API Key 明文。
5. 不要把 prompt 拼装散落在 Composable 中。
6. 不要把所有高级设置铺满首屏。
7. 不要用泛紫渐变 + Inter/Roboto 的普通 AI 模板感。
8. 不要为了酷炫牺牲聊天文本可读性。
9. 不要在流式输出时频繁重组整个列表导致卡顿。
10. 不要让“结束对话”这种关键动作没有结果反馈。

---

## 20. 期望交付物

如果你来负责前端，希望你输出：

1. 原生 Android 页面结构方案。
2. Jetpack Compose 主题与基础组件。
3. 聊天页完整实现或高保真代码原型。
4. 设置页与角色卡页基础实现。
5. 记忆/世界书页面的组件骨架。
6. 与 ViewModel 的状态/Intent 对接说明。
7. 如果要改后端接口，请先在文档中说明原因，不要直接把业务逻辑挪到 UI。

---

## 21. 一句话协作约定

Claude 负责让 Fantareal 的“脑”和“记忆”变成可靠的原生后端；Gemini 负责让 Fantareal 的“脸”和“触感”变得漂亮、沉浸、像真正值得长期使用的手机 App。

希望我们不要只是复刻旧网页，而是一起把 Fantareal 做成一个真正有灵魂的原生 Android 应用。
