# Fantareal 原生 Android APK 剩余后端需求清单

你好！请将这份需求清单发送给 Claude 或其他负责后端架构的 AI。

当前我已经完成了**原生 Jetpack Compose 界面结构**，并且搭建了最基础的**内存级聊天通信链路**（包含 `ChatOrchestrator`、`OkHttp SSE 流式响应解析` 和基础 `ViewModel`）。但是，要让 Fantareal 成为一个完整的本地化原生 AI 应用，还需要实现大量深层的业务逻辑。

请负责后端的 AI 按照以下模块，使用 **Kotlin / 协程 / Flow** 在 `com.frischar.fantareal` 包下完成后续开发。

---

## 1. 本地文件与多存档系统 (Slot & Storage Management)
**目标**：摆脱内存存储，实现类似于原版 WebUI 的多存档系统。
- **StoragePaths**：负责管理 `context.filesDir/fantareal_runtime/` 下的目录结构，包含 `slots`（存档槽位）、`exports`、`sprites`（立绘缓存）等目录。
- **JsonStore**：提供高可用、原子的 JSON 读写工具（建议结合 `kotlinx.serialization`），保证应用崩溃时文件不损坏。
- **SlotRepository**：管理多个存档槽位（如 slot_1, slot_2），支持切换当前活跃槽位，读写各自独立的 `settings.json`、`conversations.json`。

## 2. 角色卡与设定解析 (Role Card Service)
**目标**：支持主流角色卡导入。
- **文件解析**：读取并解析 V2/Tavern 格式的 JSON/PNG 角色卡，提取 `description`、`personality`、`mesExample`、`firstMes` 等核心字段。
- **Persona 转换**：将角色卡的复杂设定抽取为可执行的 `PersonaRuntime`（系统提示词）。
- **动态应用**：导入角色卡后，能够更新当前 slot 的 `persona.json`，且能够根据用户选择决定是否清理现有的“长期记忆”。

## 3. 世界书引擎 (Worldbook Engine)
**目标**：实现本地化的背景设定动态触发机制。
- **词条管理**：支持常驻词条和关键词触发词条的 CRUD。
- **匹配逻辑**：基于用户当前输入与近期历史，进行 `primaryTriggers` 与 `secondaryTriggers`（支持 AND/OR）的正则/字面量匹配。
- **高级规则**：实现 `chance`（触发概率）、`stickyTurns`（粘滞回合）、`cooldownTurns`（冷却回合）以及防止无限死循环的递归扫描限制。
- **注入定位**：根据词条配置，返回需要注入的层级（如：角色卡前、最后回复前）。

## 4. 记忆系统与墓碑机制 (Memory System)
**目标**：管理长期陪伴的记忆沉淀。
- **记忆库管理**：长期记忆的增删改查。
- **墓碑防复活 (Tombstones)**：被删除的记忆应进入“墓碑记录”，在生成新记忆或 Prompt 提示时，防止 AI 强行把旧的错误设定给“复活”。
- **相似度去重**：提供基于 `bigram Dice 系数` 的文本相似度检测算法，防止对话归档时产生重复的记忆片段。

## 5. 提示词拼装器 (Prompt Builder)
**目标**：将所有零散的数据组装为标准的 LLM 请求结构。
- **组装顺序**：
  1. 主系统规则与安全护栏
  2. 启用的预设模块（如防重复、长段落设定）
  3. 命中的“角色卡前”世界书设定
  4. 角色主设定 (Persona)
  5. 长期记忆与召回记忆
  6. 对话历史 (History)
  7. 命中的“近期聊天”世界书注入
  8. 用户的最新输入
- **Provider 兼容**：输出能够灵活适配 OpenAI 格式（全部合并入 system）或 Anthropic 格式的标准化结构。

## 6. 安全与密钥管理 (Security & Keystore)
**目标**：保护用户的 API Key。
- **SecretStore**：禁止将 `API Key` 明文写入 `settings.json`。必须使用 `Android Keystore System` 生成的密钥结合 `AES-GCM` 对用户填写的 API Key 进行本地加密存储。

## 7. 预设模块与剧情工坊 (Preset & Workshop - 选做/二期)
- **预设库 (Preset Service)**：管理像“防抢话”、“第二人称”、“破冰指令”这样的独立 prompt 模块，支持组合与开关。
- **剧情工坊 (Workshop)**：管理 `temp` 阶段变量（0~2 阶段，3~5 阶段等），根据阶段动态改变预设系统词。

---

**给其他 AI 的建议：**
> 前端已经预留好了 `Repository` 和 `UseCase` 的接入点，目前的 `ChatOrchestrator` 使用的是内存变量（Mock）。
> 你的首要任务是**实现 `JsonStore` 并替换掉 `ConversationRepository` 中的内存 List**，然后依序开发 **PromptBuilder** 和 **RoleCardService**。加油！
