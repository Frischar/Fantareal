# Fantareal Android 原生 APK 后端主程序架构设计

版本：v0.1  
日期：2026-06-29  
目标目录：`E:\AI chat 项目\Fantareal-beta\Android APK\Source`

---

## 1. 目标与结论

本设计用于把 Fantareal Android 版从当前的 **WebView + HTML/JS 套壳** 重构为 **原生 Android APK**。

当前 APK 的 Android 层主要是：

- `app/src/main/java/com/frischar/fantareal/MainActivity.kt`：创建 `WebView`，加载 `file:///android_asset/mobile/index.html`。
- `app/src/main/java/com/frischar/fantareal/MobileBridge.kt`：给 Web 前端提供 `XuqiNative` 桥接，负责 OpenAI-compatible `/chat/completions` 非流式请求、文件导出、图片选择。
- `app/src/main/assets/mobile/*.html/js/css`：实际业务大多仍在 Web 前端 JS/localStorage 中。
- `web_source/app.py`：旧桌面 WebUI 的完整后端原型，包含 slot、角色卡、记忆、世界书、LLM 调用、Card Writer 等完整业务。

重构目标不是“把 WebView 里的 JS 换个位置”，而是把业务沉到 Kotlin 后端主程序层：

1. **UI 层只负责渲染与交互。**
2. **后端主程序负责数据、提示词、模型请求、流式输出、记忆归档、世界书命中、角色卡解析、导入导出。**
3. **保留旧数据格式的迁移入口，避免用户已有存档被清空。**
4. **先保留 OpenAI-compatible 网关，后续通过 Provider 抽象扩展 Anthropic Claude 官方 Messages API。**

---

## 2. 当前项目现状摘要

### 2.1 Android 壳层现状

当前 Gradle 项目在：

```text
E:\AI chat 项目\Fantareal-beta\Android APK\Source
```

主要配置：

- Android Gradle Plugin：`8.3.2`
- Kotlin：`1.9.24`
- `compileSdk = 34`
- `minSdk = 26`
- `targetSdk = 34`
- `applicationId = "com.frischar.fantareal"`
- `versionName = "1.5.0-pe"`

当前依赖偏 WebView 壳：

```kotlin
implementation("androidx.core:core-ktx:1.13.1")
implementation("androidx.appcompat:appcompat:1.7.0")
implementation("com.google.android.material:material:1.12.0")
implementation("androidx.activity:activity-ktx:1.9.0")
implementation("androidx.webkit:webkit:1.11.0")
implementation("androidx.constraintlayout:constraintlayout:2.1.4")
```

当前 `activity_main.xml` 只有：

- 一个 `WebView`
- 一个居中的 `ProgressBar`

所以当前 APK 本质仍是套壳。

### 2.2 旧 WebUI 后端现状

旧 WebUI 完整业务集中在：

```text
web_source/app.py
```

它是原生 APK 后端主程序设计的主要参考来源。需要迁移的业务包括：

- 多存档 slot
- settings/persona/conversation/memories/worldbook/current_role_card JSON
- OpenAI-compatible LLM 请求
- OpenAI SSE 流式解析
- prompt/messages 拼装
- 角色卡导入与应用
- 长期记忆、删除记忆墓碑、对话归档总结
- embedding/rerank 召回
- 世界书关键词命中、常驻词条、粘滞、冷却、递归扫描
- 立绘标签解析
- Card Writer 工程格式、编译、验证、AI Copilot

### 2.3 移动端 assets 现状

`app/src/main/assets/mobile/app.js` 已经把许多业务写在 JS/localStorage 里，且比旧 WebUI 多了一些移动端增强功能：

- 全局运行态 `xuqi-mobile-state-v4`
- `runtime.temp` 游戏阶段计数
- `presetStore` 聊天预设模块
- `creativeWorkshop` 创意工坊
- `worldbook` 高级词条结构
- `mergedMemories` / `memoryOutline` 记忆合并与大纲
- `userProfile`
- 前端内置 prompt 预览与模型请求拼装

重构时应把这些 JS 数据结构迁移到 Kotlin 数据层，而不是继续依赖 localStorage。

---

## 3. 总体架构

建议采用分层架构：

```text
UI 层 / Gemini 负责
  ↓ 调用 ViewModel / UseCase
应用层 Application / UseCase
  ↓ 组合业务流程
领域层 Domain Engine
  ↓ 纯业务逻辑：Prompt、记忆、世界书、角色卡、预设
数据层 Repository / Store
  ↓ JSON 文件、加密密钥、MediaStore/SAF、迁移
基础设施层 Infrastructure
  ↓ HTTP Client、Provider、流式解析、日志、错误映射
```

建议核心包结构：

```text
com.frischar.fantareal
  core/
    result/
    time/
    json/
    error/
  data/
    path/
    store/
    migration/
    repository/
    secret/
  domain/
    chat/
    prompt/
    llm/
    memory/
    worldbook/
    rolecard/
    preset/
    workshop/
    sprite/
    cardwriter/
  app/
    usecase/
    service/
  ui/
    ... 由前端/原生 UI 侧维护
```

后端主程序不直接依赖具体页面，只暴露稳定 UseCase：

```text
ChatUseCase.sendMessage()
ChatUseCase.endConversation()
SettingsUseCase.saveModelConfig()
RoleCardUseCase.importRoleCard()
MemoryUseCase.saveMemories()
WorldbookUseCase.saveWorldbook()
RuntimeUseCase.exportRuntimeBackup()
```

---

## 4. Android 数据根目录设计

### 4.1 私有数据根目录

建议所有运行数据放在：

```text
context.filesDir/fantareal_runtime/
```

结构：

```text
fantareal_runtime/
  runtime_version.json
  save_slots.json
  slots/
    slot_1/
      settings.json
      persona.json
      conversations.json
      current_role_card.json
      memories.json
      merged_memories.json
      memory_outline.json
      memory_tombstones.json
      worldbook.json
      preset_store.json
      workshop_runtime.json
      user_profile.json
      sprites/
      uploads/
    slot_2/
    slot_3/
  cards/
    template_role_card.json
  card_writer/
    workspace.cardwork.json
    projects/
    autosaves/
    exports/
  exports/
  import_cache/
```

### 4.2 为什么先用 JSON 而不是直接 Room

第一阶段建议继续使用 JSON 文件：

- 与旧 `web_source/data/slots/*` 兼容。
- 与移动端 `xuqi-mobile-state-v4` 导出备份兼容。
- 方便用户手动导入/导出。
- 对角色卡、世界书、Card Writer 这种嵌套结构更自然。

后续如果聊天记录很多，再把 `conversations.json` 与 memory 索引迁到 Room。迁移接口保持一致即可。

### 4.3 密钥保存

API Key 不建议继续明文写入 `settings.json`。

建议：

- `settings.json` 保存非敏感配置：baseUrl、model、timeout、historyLimit、providerType 等。
- API Key 保存到 `SecretStore`。
- `SecretStore` 用 Android Keystore 包裹数据密钥，再用 AES-GCM 加密具体 key。
- 导出运行态备份时默认不导出密钥；如果用户明确选择“包含 API Key”，必须二次确认。

---

## 5. 核心数据模型

### 5.1 SaveSlotRegistry

```kotlin
data class SaveSlotRegistry(
    val activeSlot: String,
    val slots: List<SaveSlotMeta>
)

data class SaveSlotMeta(
    val id: String,
    val name: String
)
```

默认：

```text
slot_1 / slot_2 / slot_3
```

第一阶段继续固定 3 个槽位，后续再支持新增/删除。

### 5.2 RuntimeSettings

```kotlin
data class RuntimeSettings(
    val providerType: ProviderType,
    val apiBaseUrl: String,
    val model: String,
    val modelPreset: String,
    val temperature: Double,
    val timeoutSec: Int,
    val historyLimit: Int,
    val maxTokens: Int,
    val theme: String,
    val uiOpacity: Double,
    val backgroundImageUri: String,
    val backgroundOverlay: Double,
    val embeddingBaseUrl: String,
    val embeddingModel: String,
    val embeddingFields: List<String>,
    val retrievalTopK: Int,
    val rerankEnabled: Boolean,
    val rerankBaseUrl: String,
    val rerankModel: String,
    val rerankTopN: Int
)

enum class ProviderType {
    OpenAICompatible,
    AnthropicMessages,
    Custom
}
```

敏感字段另存：

```kotlin
data class SecretRefs(
    val chatApiKeyRef: String,
    val embeddingApiKeyRef: String,
    val rerankApiKeyRef: String
)
```

### 5.3 ConversationMessage

兼容旧格式时要同时支持 `created_at` 与 `createdAt`。

```kotlin
data class ConversationMessage(
    val role: MessageRole,
    val content: String,
    val createdAt: Long
)

enum class MessageRole {
    System,
    User,
    Assistant
}
```

写新数据时建议统一 `createdAt` 毫秒时间戳；导出给用户时再格式化中文时间。

### 5.4 MemoryItem

```kotlin
data class MemoryItem(
    val id: String,
    val title: String,
    val content: String,
    val tags: List<String>,
    val notes: String
)
```

### 5.5 MemoryTombstone

```kotlin
data class MemoryTombstone(
    val id: String,
    val title: String,
    val content: String,
    val tags: List<String>,
    val notes: String,
    val deletedAt: Long
)
```

用途：

- 记忆页删除后写入。
- prompt 中提示模型不要复活旧记忆。
- 自动总结结果写入前做相似度拦截。

### 5.6 Worldbook

当前移动端已经有高级世界书结构，建议直接迁移高级结构，而不是只保留旧 WebUI 的简单 map。

```kotlin
data class WorldbookStore(
    val settings: WorldbookSettings,
    val entries: List<WorldbookEntry>
)
```

核心字段：

```kotlin
data class WorldbookEntry(
    val id: String,
    val title: String,
    val primaryTriggers: String,
    val secondaryTriggers: String,
    val entryType: WorldbookEntryType,
    val groupOperator: TriggerGroupOperator,
    val matchMode: MatchMode,
    val secondaryMode: MatchMode,
    val content: String,
    val group: String,
    val chance: Int,
    val stickyTurns: Int,
    val cooldownTurns: Int,
    val order: Int,
    val injectionPosition: InjectionPosition,
    val injectionDepth: Int,
    val injectionOrder: Int,
    val injectionRole: MessageRole,
    val recursiveEnabled: Boolean,
    val preventFurtherRecursion: Boolean,
    val enabled: Boolean,
    val caseSensitive: Boolean,
    val wholeWord: Boolean,
    val comment: String
)
```

旧 `worldbook.json` 如果是 map：

```json
{
  "触发词": "设定正文"
}
```

迁移成：

```json
{
  "settings": { ...默认设置... },
  "entries": [
    {
      "title": "触发词",
      "primaryTriggers": "触发词",
      "content": "设定正文",
      "entryType": "keyword"
    }
  ]
}
```

### 5.7 RoleCard

保留当前角色卡字段：

```kotlin
data class RoleCard(
    val name: String,
    val description: String,
    val personality: String,
    val firstMes: String,
    val mesExample: String,
    val scenario: String,
    val creatorNotes: String,
    val tags: List<String>,
    val plotStages: Map<String, PlotStage>,
    val personas: Map<String, PersonaCard>,
    val creativeWorkshop: CreativeWorkshop?
)
```

`current_role_card.json` 保存：

```kotlin
data class CurrentRoleCard(
    val sourceName: String,
    val raw: RoleCard
)
```

### 5.8 PersonaRuntime

```kotlin
data class PersonaRuntime(
    val name: String,
    val greeting: String,
    val systemPrompt: String
)
```

从角色卡导入时由 `RoleCardService.derivePersona()` 生成。

---

## 6. 后端模块设计

### 6.1 StoragePaths

职责：

- 生成根目录、slot 目录、sprites 目录、exports 目录。
- 确保目录存在。
- 对文件名做安全清洗。
- 隔离外部导入缓存。

接口：

```kotlin
interface StoragePaths {
    val rootDir: File
    val slotsDir: File
    fun slotDir(slotId: String): File
    fun slotFile(slotId: String, name: String): File
    fun spritesDir(slotId: String): File
    fun exportsDir(): File
}
```

### 6.2 JsonStore

职责：

- 原子读写 JSON。
- 写入时先写临时文件，再 rename。
- 解析失败时返回默认值并保留坏文件备份。
- 所有 sanitize 在 repository 层完成。

接口：

```kotlin
interface JsonStore {
    suspend fun <T> read(path: File, serializer: KSerializer<T>, default: T): T
    suspend fun <T> write(path: File, serializer: KSerializer<T>, value: T)
}
```

### 6.3 SlotRepository

职责：

- 读取/保存 `save_slots.json`。
- active slot 切换。
- 重命名 slot。
- 重置 slot。
- 生成 slot summary。

### 6.4 SettingsRepository

职责：

- 读取/保存当前 slot 的 settings。
- 与 SecretStore 合并成运行时配置。
- 导入旧 settings 时拆出 API key。

运行时输出：

```kotlin
data class ChatRuntimeConfig(
    val providerType: ProviderType,
    val apiBaseUrl: String,
    val apiKey: String,
    val model: String,
    val temperature: Double,
    val timeoutSec: Int,
    val maxTokens: Int,
    val historyLimit: Int
)
```

### 6.5 ConversationRepository

职责：

- 读取聊天记录。
- 追加 user/assistant。
- 清空当前聊天。
- 导出文本/JSON。
- 对旧数据做 role 与乱码清洗。

### 6.6 RoleCardService

职责：

- 解析导入 JSON。
- 支持 `data` 包裹格式。
- 尝试修复常见 JSON 截断/代码块包裹。
- normalize 字段。
- 生成 persona runtime。
- 应用到当前 slot。

应用角色卡时建议行为：

1. 写入 `current_role_card.json`。
2. 更新 `persona.json`。
3. 重置 `temp` 阶段计数。
4. 默认不清空长期记忆、世界书、预设，除非用户勾选“导入时重置运行态”。

当前移动端说明中已经倾向“切换角色卡不清空全局运行态”，所以新原生版也应遵循这个方向。

### 6.7 PresetService

职责：

- 管理聊天预设库。
- 把启用模块编译成 prompt。
- 支持导入/导出预设卡。

典型模块：

- 防抢话
- 短段落
- 长段落
- 第二人称
- 第三人称
- 防重复
- 不收束

### 6.8 WorldbookEngine

职责：

- 根据当前用户输入 + 最近聊天记录匹配词条。
- 处理常驻、关键词、二级触发、AND/OR、chance、sticky、cooldown、递归扫描。
- 按 insertionPosition/injectionDepth/injectionRole 输出 prompt 注入计划。

输出：

```kotlin
data class WorldbookMatchResult(
    val selectedEntries: List<WorldbookEntryHit>,
    val buckets: WorldbookBuckets,
    val debug: WorldbookDebugInfo,
    val nextRuntime: WorldbookRuntimeState
)
```

### 6.9 MemoryService

职责：

- 管理长期记忆。
- 管理删除墓碑。
- 相似度去重。
- 对话结束后总结为长期记忆。
- 记忆合并、记忆大纲可以作为第二阶段功能。

第一阶段策略：

- 固定注入所有短记忆，保持旧版本行为。
- 提供开关：`memoryInjectMode = all | topK | pinnedOnly`。
- 记忆数量超过阈值后提示用户合并或启用召回。

相似度沿用旧逻辑：

- NFKC 归一化。
- 只保留中英文数字。
- bigram Dice 系数。
- 超阈值判重复。

### 6.10 RetrievalService

职责：

- embedding 请求。
- cosine similarity。
- topK 召回。
- rerank 请求。

Provider：

- Embedding 继续走 OpenAI-compatible `/embeddings`。
- Rerank 继续走 `/rerank` 兼容接口。
- Anthropic 当前不作为 embedding/rerank 默认提供方。

### 6.11 PromptBuilder

职责：

把所有上下文组装成 provider-neutral 的内部 prompt：

```kotlin
data class PromptBuildResult(
    val systemBlocks: List<PromptBlock>,
    val messages: List<ChatMessageParam>,
    val previewText: String,
    val worldbookMatches: List<WorldbookEntryHit>,
    val tokenHints: TokenHints?
)
```

推荐逻辑顺序：

1. 主系统规则。
2. 当前启用预设。
3. 世界书：角色卡前。
4. 角色卡/persona systemPrompt。
5. 世界书：角色卡后。
6. 用户资料。
7. 长期记忆/召回记忆。
8. 已删除记忆 guard。
9. 世界书回答约束。
10. 最近历史。
11. 世界书 in-chat 注入。
12. 当前用户输入。

OpenAI-compatible provider 可把 systemBlocks 合并成一个 `role=system` message。  
Anthropic Messages provider 可把稳定主规则放到 top-level `system`，把每轮世界书/召回上下文按 provider 能力映射。

### 6.12 ChatOrchestrator

职责：

- 接收用户输入。
- 写入 user message。
- 构建 prompt。
- 调 LLM provider。
- 将流式事件传给 UI。
- 成功后写入 assistant message。
- 失败时保存错误气泡或仅返回错误，由 UI 决定。

接口：

```kotlin
interface ChatOrchestrator {
    fun sendMessage(input: String): Flow<ChatEvent>
    suspend fun endConversation(): EndConversationResult
}

sealed interface ChatEvent {
    data class Started(val requestId: String) : ChatEvent
    data class PromptReady(val preview: String) : ChatEvent
    data class TokenDelta(val text: String) : ChatEvent
    data class ThinkingDelta(val text: String) : ChatEvent
    data class SpriteTagDetected(val tag: String) : ChatEvent
    data class Completed(val fullText: String, val visibleText: String) : ChatEvent
    data class Failed(val error: AppError) : ChatEvent
}
```

### 6.13 LlmProvider

统一聊天模型接口：

```kotlin
interface LlmProvider {
    suspend fun complete(request: LlmRequest): LlmResponse
    fun stream(request: LlmRequest): Flow<LlmStreamEvent>
}
```

内部请求：

```kotlin
data class LlmRequest(
    val model: String,
    val system: String?,
    val messages: List<LlmMessage>,
    val temperature: Double?,
    val maxTokens: Int?,
    val timeoutSec: Int,
    val responseFormat: ResponseFormat?,
    val purpose: LlmPurpose
)
```

`purpose` 用于区分：

- 普通聊天
- 测试连接
- 对话总结
- JSON 修复
- 记忆合并
- Card Writer Copilot

### 6.14 SpriteService

职责：

- 解析 `[表情:标签]`。
- 在流式输出中尽早识别标签。
- 返回 visible text。
- 管理 slot 的立绘图片列表。

注意迁移时修复旧代码里的乱码默认值：

```text
骞抽潤 -> 平静
```

---

## 7. LLM Provider 设计

### 7.1 OpenAI-compatible Provider

这是第一阶段默认 provider，兼容：

- OpenAI
- DeepSeek
- OpenRouter
- SiliconFlow
- MiniMax 兼容入口
- 其它 `/chat/completions` 网关

请求：

```http
POST {baseUrl}/chat/completions
Authorization: Bearer <apiKey>
Content-Type: application/json
```

非流式 body：

```json
{
  "model": "...",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.85,
  "stream": false,
  "max_tokens": 4096
}
```

流式 body：

```json
{
  "model": "...",
  "messages": [...],
  "temperature": 0.85,
  "stream": true,
  "max_tokens": 4096
}
```

流式解析：

```text
data: {"choices":[{"delta":{"content":"..."}}]}
data: [DONE]
```

需要兼容：

- `choices[0].message.content`
- `choices[0].text`
- `output_text`
- `reply`
- content 数组片段

### 7.2 Anthropic Messages Provider

第二阶段可扩展直连 Claude 官方 API。

默认模型建议：

```text
claude-opus-4-8
```

官方 Messages API 关键点：

- endpoint：`POST /v1/messages`
- 不使用 `/chat/completions`。
- `system` 是顶层字段，`messages` 只放 user/assistant。
- 响应是 content blocks，不是 `choices[0]`。
- 流式事件是 Anthropic event，不是 OpenAI SSE delta。
- Opus 4.8 / 4.7 使用 adaptive thinking：`thinking: {type: "adaptive"}`。
- Opus 4.8 / 4.7 / Fable 5 不要发送 `temperature`、`top_p`、`top_k`。
- 不要使用 assistant prefill 强制 JSON。
- JSON 输出应使用 structured outputs：`output_config.format`。
- 要检查 `stop_reason`，尤其 `refusal`、`max_tokens`、`end_turn`。

Anthropic request 概念映射：

```json
{
  "model": "claude-opus-4-8",
  "max_tokens": 16000,
  "system": "稳定系统提示词",
  "messages": [
    {"role": "user", "content": "..."}
  ],
  "thinking": {"type": "adaptive"},
  "output_config": {"effort": "high"}
}
```

用于对话总结的 structured output：

```json
{
  "output_config": {
    "format": {
      "type": "json_schema",
      "schema": {
        "type": "object",
        "properties": {
          "title": {"type": "string"},
          "content": {"type": "string"},
          "tags": {"type": "array", "items": {"type": "string"}},
          "notes": {"type": "string"}
        },
        "required": ["title", "content", "tags", "notes"],
        "additionalProperties": false
      }
    }
  }
}
```

Android 实现策略：

- 如果官方 Java SDK 在 Android 环境、依赖体积、minSdk、网络栈上验证可用，则用官方 SDK。
- 如果 SDK 与 Android 运行环境不适配，则在 `AnthropicMessagesProvider` 内部以 raw HTTPS 实现同一 Messages API 语义。
- UI 与业务层不关心 provider 内部使用 SDK 还是 raw HTTP。

### 7.3 Provider Capability

不同 provider 支持不同能力，必须显式建模：

```kotlin
data class ProviderCapability(
    val supportsStreaming: Boolean,
    val supportsTemperature: Boolean,
    val supportsMaxTokens: Boolean,
    val supportsResponseFormatJsonObject: Boolean,
    val supportsStructuredOutput: Boolean,
    val supportsThinking: Boolean,
    val supportsSystemMessages: Boolean,
    val supportsEmbeddings: Boolean,
    val supportsRerank: Boolean
)
```

示例：

- OpenAI-compatible：通常支持 `temperature`、`max_tokens`、`stream`，不一定支持 `response_format`。
- Claude Opus 4.8 direct：支持 streaming、structured outputs、adaptive thinking；不发送 temperature。
- DeepSeek/OpenRouter 等：按实际网关判断。

Provider 要负责过滤不兼容参数，不能让 UI 直接拼请求。

---

## 8. 流式输出设计

后端统一事件：

```kotlin
sealed interface LlmStreamEvent {
    data class TextDelta(val text: String) : LlmStreamEvent
    data class ThinkingDelta(val text: String) : LlmStreamEvent
    data class Metadata(val requestId: String? = null, val model: String? = null) : LlmStreamEvent
    data class Completed(val response: LlmResponse) : LlmStreamEvent
    data class Failed(val error: AppError) : LlmStreamEvent
}
```

UI 不直接解析 SSE，只消费 `Flow<ChatEvent>`。

OpenAI-compatible provider：

- `delta.content` -> `TextDelta`
- `[DONE]` -> `Completed`
- HTTP error -> `Failed`

Anthropic provider：

- `content_block_delta` text -> `TextDelta`
- thinking delta -> `ThinkingDelta`
- `message_delta.stop_reason` -> 记录 stop reason
- `message_stop` -> `Completed`

这样 Gemini 前端只要做统一流式渲染，不需要知道 provider 差异。

---

## 9. 错误处理设计

统一错误：

```kotlin
sealed class AppError(
    open val message: String,
    open val cause: Throwable? = null
) {
    data class MissingModelConfig(...) : AppError(...)
    data class AuthenticationFailed(...) : AppError(...)
    data class PermissionDenied(...) : AppError(...)
    data class RateLimited(val retryAfterSec: Int?) : AppError(...)
    data class ProviderOverloaded(...) : AppError(...)
    data class NetworkUnavailable(...) : AppError(...)
    data class Timeout(...) : AppError(...)
    data class InvalidResponse(...) : AppError(...)
    data class JsonParseFailed(...) : AppError(...)
    data class RefusedByModel(...) : AppError(...)
    data class StorageFailed(...) : AppError(...)
}
```

HTTP 映射：

| HTTP | AppError | 用户提示 |
|---|---|---|
| 400 | InvalidResponse / BadRequest | 请求参数不兼容，请检查模型和 provider 设置 |
| 401 | AuthenticationFailed | API Key 无效或缺失 |
| 403 | PermissionDenied | 当前 Key 没有该模型权限 |
| 404 | InvalidResponse | 模型名或接口地址不存在 |
| 408 | Timeout | 请求超时 |
| 413 | InvalidResponse | 上下文过长或请求体过大 |
| 429 | RateLimited | 触发限流，稍后重试 |
| 500+ | ProviderOverloaded | 服务端错误或过载 |
| 529 | ProviderOverloaded | 模型服务过载 |

Claude direct 特殊处理：

- `stop_reason == "refusal"`：返回 `RefusedByModel`，不要把空 content 当成功。
- `stop_reason == "max_tokens"`：提示输出被截断，可增大 maxTokens 或继续生成。
- Fable 5 如启用，建议配置 fallback 到 `claude-opus-4-8`，但 Fable 5 不作为本项目默认模型。

重试策略：

- 自动重试：408、409、425、429、500-599、529。
- 最多 2 次，指数退避。
- 流式请求如果已经产生可见文本，中途失败不自动重放，应提示“回复中断，可点继续”。

---

## 10. 聊天发送完整流程

```text
用户点击发送
  ↓
ChatUseCase.sendMessage(input)
  ↓
校验模型配置
  ↓
ConversationRepository.append(user)
  ↓
PromptBuilder.build(slot, input)
  ├─ PresetService.compileActivePreset()
  ├─ WorldbookEngine.match()
  ├─ MemoryService.loadPromptMemories()
  ├─ RetrievalService.retrieve() 可选
  └─ RoleCardService.currentPersona()
  ↓
LlmProvider.stream()
  ↓
SpriteService.extractTagIncrementally()
  ↓
Flow<ChatEvent> 给 UI 渲染
  ↓
Completed 后 ConversationRepository.append(assistant raw)
  ↓
保存 worldbook runtime / workshop runtime
```

失败处理：

- user message 已写入时，不自动删除。
- assistant 是否写入错误气泡由设置控制：
  - 默认写入：`出错了：...`
  - 可选不写入，只让 UI toast。

---

## 11. 对话结束归档流程

```text
用户点击“结束当前对话”
  ↓
ConversationRepository.load()
  ↓
Runtime.temp += 1
  ↓
MemoryService.summarizeConversation()
  ├─ 短对话：直接总结
  ├─ 长对话：分段压缩 -> 最终 JSON 总结
  ├─ JSON 解析失败：修复请求
  └─ 仍失败：本地 fallback memory
  ↓
MemoryService.checkTombstoneSimilarity()
  ↓
MemoryService.checkExistingSimilarity()
  ↓
写入 memories 或跳过重复
  ↓
清空 conversations
  ↓
触发 CreativeWorkshop 阶段刷新
```

Claude direct provider 下，总结建议用 structured outputs，减少 JSON 修复回合。

---

## 12. 旧数据迁移策略

### 12.1 迁移源

需要支持三类旧数据：

1. `web_source/data/slots/*` 目录中的 Python WebUI JSON。
2. 移动端 WebView 导出的 `xuqi_mobile_state.json`。
3. 旧 assets/localStorage 用户手动导出的运行态备份。

### 12.2 迁移器

```kotlin
interface RuntimeMigrator {
    suspend fun detect(input: Uri): RuntimeBackupType
    suspend fun importToSlot(input: Uri, targetSlotId: String): ImportResult
    suspend fun exportSlot(slotId: String, includeSecrets: Boolean): Uri
}
```

导入原则：

- 不静默覆盖当前 slot，必须弹确认。
- 导入前自动生成当前 slot 备份。
- 坏字段跳过并记录 warning。
- API Key 默认不导入，除非备份里明确包含且用户确认。

---

## 13. Card Writer 迁移边界

Card Writer 很大，建议第三阶段迁移。

第一阶段只保证：

- 原生聊天可用。
- 角色卡导入/编辑/应用/导出可用。
- 记忆、世界书、预设可用。

Card Writer 后续模块：

```text
CardWriterRepository
CardWriterCompiler
CardWriterValidator
CardWriterImportExportService
CardWriterCopilotService
```

AI Copilot 请求：

- OpenAI-compatible：继续用 `response_format: {"type":"json_object"}`，但必须能力探测。
- Anthropic direct：使用 structured outputs。
- Copilot 候选必须由用户确认后才能应用，不自动改工程。

---

## 14. 建议新增依赖

如果改为 Kotlin + 原生 UI，后端建议：

```kotlin
implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:<version>")
implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:<version>")
implementation("com.squareup.okhttp3:okhttp:<version>")
implementation("androidx.datastore:datastore-preferences:<version>")
implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:<version>")
```

如 UI 采用 Jetpack Compose：

```kotlin
implementation("androidx.activity:activity-compose:<version>")
implementation("androidx.compose.ui:ui:<version>")
implementation("androidx.compose.material3:material3:<version>")
implementation("androidx.lifecycle:lifecycle-runtime-compose:<version>")
```

如暂时保留 XML View，也可以不引入 Compose，但 Gemini 做前端美化时更推荐 Compose。

---

## 15. 分阶段实施计划

### 阶段 1：原生聊天闭环

目标：完全不依赖 WebView 完成基础聊天。

必须完成：

- 数据根目录与 JSON store。
- settings + secret store。
- slot repository。
- conversation repository。
- persona/current role card 基础读取。
- OpenAI-compatible provider 非流式 + 流式。
- PromptBuilder 基础版。
- ChatOrchestrator。
- Chat UI 消费 `Flow<ChatEvent>`。
- 导入/导出运行态备份。

### 阶段 2：角色与长期玩法

目标：恢复 Fantareal 的核心特色。

- 角色卡导入/应用/导出。
- 世界书高级匹配。
- 长期记忆、墓碑、自动归档总结。
- 预设模块。
- 用户资料。
- 创意工坊阶段 temp。
- 立绘标签与图片管理。

### 阶段 3：增强智能

- embedding 召回。
- rerank。
- 记忆合并。
- 记忆大纲。
- Prompt 预览与调试面板。
- token 估算/上下文长度提示。

### 阶段 4：Card Writer

- 工程管理。
- 编译/验证。
- 导入/导出。
- AI Copilot。

### 阶段 5：多 Provider

- Anthropic Messages provider。
- Provider capability UI。
- structured output。
- Claude streaming event parser。
- 更细错误提示与 fallback。

---

## 16. 给前端的稳定接口边界

前端不应直接操作：

- JSON 文件。
- API Key 明文。
- HTTP provider。
- Prompt 拼装细节。
- 世界书运行时状态。
- 记忆去重与墓碑。

前端只消费 ViewModel 暴露的状态：

```kotlin
data class ChatUiState(
    val activeSlotName: String,
    val personaName: String,
    val messages: List<ChatMessageUiModel>,
    val isSending: Boolean,
    val statusText: String,
    val currentSpriteTag: String?,
    val promptPreview: String?,
    val errorDialog: ErrorDialogState?
)
```

并调用意图：

```kotlin
sealed interface ChatIntent {
    data class Send(val text: String) : ChatIntent
    data object EndConversation : ChatIntent
    data object ExportChat : ChatIntent
    data object PreviewPrompt : ChatIntent
    data object StopGeneration : ChatIntent
}
```

这样 Gemini 可以专心做 UI，不会破坏后端业务。

---

## 17. 风险清单

1. **WebView 资产里已有大量 JS 业务。** 迁移时不要遗漏移动端新增功能，例如 `presetStore`、`creativeWorkshop`、`worldbookRuntime`、`mergedMemories`。
2. **OpenAI-compatible 与 Claude direct 协议差异很大。** 必须通过 provider 抽象隔离。
3. **API Key 安全。** 原 Web 方案可明文存 localStorage，新原生版不能继续这样。
4. **长对话 token 成本。** 当前固定注入全部记忆，长期使用会膨胀；需要策略化。
5. **流式失败恢复。** 已输出一半时不能简单自动重试。
6. **角色卡导入是否清空运行态。** 当前移动端说明倾向不清空，需要明确为默认行为。
7. **世界书格式分裂。** 旧 WebUI 简单 map，移动端/卡写器高级格式，需要统一迁移。
8. **中文乱码。** 旧代码里有乱码错误提示和默认立绘标签，迁移时统一修复。

---

## 18. 最小可验证标准

第一阶段完成后，应能验证：

1. 安装 APK 后不加载任何 HTML/WebView。
2. 配置 OpenAI-compatible API 后能测试连接。
3. 能发送消息并流式显示回复。
4. 关闭 App 再打开，聊天记录仍在。
5. 切换 slot 后聊天、角色、记忆隔离。
6. 导入角色卡后聊天 persona 改变。
7. 结束对话后生成一条长期记忆并清空当前聊天。
8. 世界书触发词能影响回复。
9. API Key 不出现在导出的普通运行态备份里。
10. 无网络/401/429/超时都有中文可理解错误提示。

---

## 19. 推荐下一步

1. 新建 Kotlin 后端包结构，不急着删除 WebView 旧代码。
2. 先实现 `JsonStore + SlotRepository + SettingsRepository + ConversationRepository`。
3. 再实现 `OpenAICompatibleProvider.stream()`。
4. 接一个极简原生 ChatScreen 验证流式闭环。
5. 确认闭环后再迁移世界书、记忆、角色卡。

这条路线能避免一次性重写全部功能导致不可验证。先让原生 APK 真正“能聊”，再把 Fantareal 的灵魂一点点迁回来。
