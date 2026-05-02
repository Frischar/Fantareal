# [MOD-DEV] Fantareal 余声 附属 Mod 开发任务书

> **⚠ Token 消耗警告：** 本功能限制性极高且消耗大量 token。一次完整流程（6步全部生成）消耗量极大，开发测试期间累计消耗超过千万 token。强烈建议使用 Token Plan，普通 API 额度可能无法支撑完整流程。

## 1. 项目定位

开发一个 Fantareal 附属 Mod：`余声`。

该 Mod 作为 Fantareal 的 GAL 路线提纯流水线存在，不替代主聊天系统。它允许玩家粘贴从初遇到真结局的完整 GAL 剧本文本，逐步生成世界书、剧情提纯、记忆、预设和人设卡，并生成可被 Fantareal 直接导入的配置素材。

Mod 需要以 Fantareal 原生附属形式存在，目录结构为：

```text
mods/
  soul weaver/
    mod.json
    app.py
    templates/
      index.html
    static/
      soul-weaver.css
      soul-weaver.js
    data/
      drafts.json
```

主程序应能自动发现该 Mod，并通过 `/mods/soul-weaver` 进入页面。

## 2. 核心痛点

玩家在制作 Fantareal 角色时，通常需要手动整理大量剧本内容，包括角色卡、阶段设定、文风预设、长期记忆和世界书词条。这个过程耗时、容易遗漏关键情节，并且不同玩家很难稳定输出符合 Fantareal schema 的 JSON。

Soul Weaver 要解决的问题是：把“原始剧本文本”自动提纯成 Fantareal 可导入素材，让玩家能快速从一段 GAL 剧情中生成完整角色包，并在导入前人工预览、修改和确认。

## 3. 核心逻辑流

1. 玩家进入 `/mods/soul-weaver` 页面。
2. 玩家填写目标角色名、来源作品、主角称呼、关系路线、结局类型，并粘贴原始剧本。
3. Mod 调用 OpenAI 兼容模型接口，执行内部分析流程：
   - 人设提纯：口癖、性格、关系变化、禁忌与边界。
   - 阶段映射：按 A/B/C 阶段整理陌生、熟悉、真结局后的互动规则。
   - 文风生成：生成 Fantareal 预设中的 `extra_prompts` 和 `prompt_groups`。
   - 记忆折叠：把流水账剧情压缩为第一人称长期记忆。
   - 世界书生成：提取地点、组织、术语、共同经历、关键人物等触发词。
4. Mod 返回四类可编辑结果：
   - `role_card_output`
   - `preset_output`
   - `memories_output`
   - `worldbook_output`
5. 玩家可在页面中逐项预览、编辑、复制、下载 JSON。
6. 玩家点击“导入到 Fantareal”后，Mod 调用主程序接口完成导入。

该 Mod 不要求多 Agent 协作，但内部流程需要支持长文本分段处理、分段摘要、二次合并和最终 schema 校验。长剧本输入时，应先生成分段分析，再合成为最终素材。

## 4. Fantareal 对接要求

### 4.1 角色卡输出

输出 Fantareal 原生角色卡 raw JSON，字段必须包含：

```json
{
  "name": "",
  "description": "",
  "personality": "",
  "first_mes": "",
  "mes_example": "",
  "scenario": "",
  "creator_notes": "",
  "tags": [],
  "creativeWorkshop": {
    "enabled": true,
    "items": []
  },
  "plotStages": {
    "A": { "description": "", "rules": "" },
    "B": { "description": "", "rules": "" },
    "C": { "description": "", "rules": "" }
  },
  "personas": {
    "1": {
      "name": "Main Persona",
      "description": "The only active speaking role.",
      "personality": "",
      "scenario": "",
      "creator_notes": "Do not suddenly switch to multi-character output."
    }
  }
}
```

`creativeWorkshop.items` 至少生成 A/B/C 三条阶段规则，字段需兼容 Fantareal 当前格式：

- `id`
- `name`
- `enabled`
- `triggerMode`
- `triggerStage`
- `triggerTempMin`
- `triggerTempMax`
- `actionType`
- `popupTitle`
- `musicPreset`
- `musicUrl`
- `autoplay`
- `loop`
- `volume`
- `imageUrl`
- `imageAlt`
- `note`

建议默认生成三条固定阶段规则：

- `workshop_stage_a`：剧本早期/防备阶段。
- `workshop_stage_b`：剧本中期/熟悉阶段。
- `workshop_stage_c`：真结局/长期陪伴阶段。

### 4.2 预设输出

输出单个 Fantareal 预设 JSON，字段必须包含：

```json
{
  "id": "preset_soul_weaver",
  "name": "角色名 - 灵魂回溯预设",
  "enabled": true,
  "base_system_prompt": "",
  "modules": {
    "no_user_speaking": true,
    "short_paragraph": false,
    "long_paragraph": false,
    "second_person": false,
    "third_person": false,
    "anti_repeat": true,
    "no_closing_feel": true,
    "emotion_detail": true,
    "multi_character_boundary": true,
    "scene_continuation": true,
    "v4f_output_guard": false
  },
  "extra_prompts": [],
  "prompt_groups": []
}
```

`extra_prompts` 用于承载角色专属文风、对白节奏、动作描写倾向、禁用表达等稳定规则。

`prompt_groups` 用于承载可切换风格，例如：

- 日常陪伴
- 剧情延续
- 回忆氛围
- 真结局后恋人感
- 轻喜剧对白

### 4.3 记忆输出

输出 Fantareal 记忆导入格式：

```json
{
  "items": [
    {
      "id": "memory_001",
      "title": "",
      "content": "",
      "tags": [],
      "notes": ""
    }
  ]
}
```

记忆必须使用目标角色第一人称，不写流水账，要写成能长期影响陪伴聊天的记忆切片。

记忆内容应优先包含：

- 初遇
- 关系转折点
- 共同危机
- 角色脆弱时刻
- 告白或真结局
- 重要约定
- 对玩家/主角称呼的变化

### 4.4 世界书输出

输出 Fantareal 世界书格式：

```json
{
  "settings": {
    "enabled": true,
    "max_hits": 6,
    "recursive_scan_enabled": false,
    "recursion_max_depth": 2
  },
  "entries": [
    {
      "id": "worldbook_001",
      "title": "",
      "trigger": "",
      "secondary_trigger": "",
      "content": "",
      "enabled": true,
      "priority": 100,
      "case_sensitive": false,
      "whole_word": false,
      "match_mode": "any",
      "secondary_mode": "all",
      "group": "",
      "entry_type": "keyword",
      "group_operator": "and",
      "chance": 100,
      "sticky_turns": 0,
      "cooldown_turns": 0,
      "order": 100,
      "insertion_position": "after_char_defs",
      "injection_depth": 0,
      "injection_role": "system",
      "injection_order": 100,
      "prompt_layer": "follow_position",
      "recursive_enabled": false,
      "prevent_further_recursion": false,
      "comment": ""
    }
  ]
}
```

世界书用于承载地点、组织、专有名词、共同经历、关系暗号和剧情背景，不应把所有内容硬塞进角色卡。

推荐世界书分组：

- `地点`
- `人物`
- `组织`
- `专有名词`
- `共同经历`
- `关系暗号`
- `结局后状态`

## 5. Mod 页面功能

页面需要包含：

- 原始剧本文本输入区。
- 目标角色名、作品名、玩家称呼、关系路线、结局阶段、文本语言等基础字段。
- 模型配置区：API Base URL、API Key、Model、Temperature、Max Tokens。
- 生成按钮。
- 生成进度与错误提示。
- 四个结果 Tab：角色卡、预设、记忆、世界书。
- JSON 预览与编辑区。
- 下载按钮。
- 一键导入按钮。
- 导入前确认，避免覆盖玩家现有配置。

导入策略：

- 角色卡：调用 `/api/cards/import`。
- 预设：调用 `/api/preset/import`，默认激活新预设。
- 记忆：调用 `/api/memories/import`，追加导入。
- 世界书：调用 `/api/worldbook/import`，默认追加，不覆盖 settings，除非玩家勾选“应用世界书设置”。

## 6. 模型调用要求

Mod 应复用 Worldbook Maker 的 OpenAI 兼容配置思路，允许玩家填写：

- API Base URL
- API Key
- Model
- Temperature
- Max Tokens

生成时必须要求模型只返回 JSON，不输出解释文本。后端需要做 JSON 解析、schema 补全和失败提示。

如果原始剧本文本过长，Mod 应进行分段处理：

1. 分段提取角色事实、对白风格、事件记忆和世界观词条。
2. 合并分段结果。
3. 去重、压缩、按 Fantareal schema 输出最终素材。

## 7. 后端接口建议

Mod 自身建议提供以下接口：

- `GET /`：打开 Soul Weaver 页面。
- `GET /api/settings`：读取模型配置。
- `POST /api/settings`：保存模型配置。
- `POST /api/generate`：根据剧本文本生成四类素材。
- `POST /api/validate`：校验并补全 JSON。
- `POST /api/import/card`：导入角色卡到 Fantareal。
- `POST /api/import/preset`：导入预设到 Fantareal。
- `POST /api/import/memories`：导入记忆到 Fantareal。
- `POST /api/import/worldbook`：导入世界书到 Fantareal。
- `POST /api/import/all`：按玩家确认一次性导入全部素材。

## 8. 生成提示词要求

后端应内置系统提示词，用于约束模型输出：

```text
你是 Fantareal Soul Weaver，一个面向 Fantareal 角色素材制作的剧本提纯引擎。

你会读取玩家提供的 GAL 游戏剧本/对白片段，并生成 Fantareal 可导入的四类 JSON：角色卡、预设、记忆、世界书。

你必须只输出合法 JSON，不输出 Markdown，不输出解释，不输出代码块。

你必须遵守 Fantareal 当前 schema：
- 角色卡使用 role_card_output。
- 预设使用 preset_output。
- 记忆使用 memories_output.items。
- 世界书使用 worldbook_output.settings 与 worldbook_output.entries。

所有字段必须补全。无法确定的信息需要合理推断，但不得编造与原剧本冲突的事实。

记忆必须以目标角色第一人称书写。
角色卡必须适合长期陪伴聊天。
世界书必须拆成可触发的背景词条，不要把整段剧情塞进一个词条。
```

## 9. 输出总 Schema

`POST /api/generate` 的最终结果应为：

```json
{
  "role_card_output": {},
  "preset_output": {},
  "memories_output": {
    "items": []
  },
  "worldbook_output": {
    "settings": {},
    "entries": []
  },
  "meta": {
    "source_title": "",
    "target_character": "",
    "detected_language": "",
    "warnings": []
  }
}
```

## 10. 数据保存

Mod 可在 `mods/soul weaver/data/drafts.json` 保存玩家最近一次生成草稿，避免刷新页面丢失。

草稿内容包括：

- 输入参数
- 原始文本摘要
- 最近一次生成结果
- 生成时间
- 使用的模型名

不要把 API Key 明文写入导出的角色包。若保存本地配置，也应单独保存在 settings 文件中。

## 11. 验收标准

- Fantareal 启动后能在 Mod 列表看到“灵魂回溯”。
- `/mods/soul-weaver` 页面可正常打开。
- 粘贴一段剧本后能生成四类素材。
- 生成结果能被 Fantareal 当前接口成功导入。
- 导入后可在角色卡、预设、记忆、世界书页面看到对应内容。
- 长文本输入不会直接崩溃，至少能提示分段处理或输入过长。
- 不污染主程序核心逻辑，作为附属 Mod 独立存在。

## 12. 实现边界

本任务只要求实现 Fantareal 附属 Mod，不要求修改主聊天核心逻辑。

允许复用现有 `mods/worldbook maker` 的模型配置、HTTP 调用、工作区保存和 JSON 预览思路。

不要求一次生成完美角色，但必须保证输出结构可导入、可编辑、可下载、可回滚。

给你测试用的AI URL:https://token-plan-cn.xiaomimimo.com/v1 KEY:tp-cavqrya1c0ydf9ajvjs6ge2sbegxpd4aqhqcyy9a1c8ij9zu MODEL:mimo-v2.5-pro
