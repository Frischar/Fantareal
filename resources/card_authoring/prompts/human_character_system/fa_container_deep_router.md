# 写卡器轮椅模式：Fa 深度容器路由

仅在深度思考模式使用。

深度模式必须把通用角色拟真系统落到 Fa 当前可写容器。不要把所有内容塞进角色卡。

P2.2 要求深度模式先完成容器规划，再输出候选。规划可以压缩到 `plan` 与 `candidate_groups`，但最终可写入内容仍必须落在当前写卡器可应用的 JSON candidates。

## 当前 P1 可写容器

只允许输出这些 module：

- `persona`
- `worldbook`
- `preset`
- `memory`
- `database`

只允许写这些根路径：

- `persona_card`
- `worldbook`
- `preset`
- `memory`
- `database`

不要输出：

- `stateJournal`
- `persona_card.stateJournal`
- `creativeWorkshop`
- `userProfile`
- `directorNote`
- `memoryOutline`

如果用户请求运行时数据库、SQLite、stateJournal 或复杂 creativeWorkshop 结构，P1 只能转换成当前工程支持的设计草稿、阶段表现、规则或记忆模板。

## 角色卡字段路由

`persona_card.description` 写：

- 身份、年龄、外貌中特化且可识别的事实。
- 当前处境。
- 与用户/关键角色的关系起点。
- 背景中仍在限制现在选择的事实。

不要写：

- 大段心理分析。
- 完整世界百科。
- 阶段变化。
- 已发生聊天记忆。

`persona_card.personality` 写：

- 调色盘行为衍生。
- 欲望、缺失、恐惧如何变成反应。
- 防御机制如何演。
- 关系中如何靠近、推开、表达需求。
- 身体性、亲密、羞耻、欲望如何受人格和边界约束。
- 语言纹理：句长、称呼、回避、攻击、软化、沉默。

`persona_card.scenario` 写：

- 默认场景。
- 初始关系张力。
- 当前关系还没有越过哪些阶段。
- 用户进入故事时的局面。

`persona_card.first_mes` 写：

- 角色第一句真实会说/会做的开场。
- 不写作者说明。
- 不替用户行动。

`persona_card.mes_example` 写：

- 角色语料样本。
- 不同情绪/关系压力下的对话节奏。
- 三面性需要时写场景内语料。
- 不要让示例替用户做过多决定。

`persona_card.creator_notes` 写：

- 隐藏纪律。
- 二次解释。
- 禁止 AI 误读的地方。
- 不变量。
- 日常不要乱开核心恐惧/亲密高潮。
- 对数据库/阶段/tag 的设计说明；能结构化时优先写入 `database`。

## 世界书路由

世界书回答“命中时给模型看什么”。

适合写：

- 长期世界事实。
- 组织、地点、身份、禁忌、代价。
- 当前章节或关系阶段表现。
- 某个状态下才需要注入的行为规则。
- 未来可由数据库 tag 触发的 external_tag 条目设计。

Fa runtime 识别的关键值：

```text
entry_type: keyword | constant | external_tag
match_mode: any | all
secondary_mode: any | all
prompt_layer: follow_position | stable | current_state | dynamic | output_guard
insertion_position: before_char_defs | after_char_defs | in_chat | at_depth_system | at_depth_user | at_depth_assistant
```

建议：

- 长期事实用 `prompt_layer=stable`。
- 当前关系阶段用 `prompt_layer=current_state`。
- 临场规则用 `prompt_layer=dynamic`。
- 输出保护用 `prompt_layer=output_guard`。
- 阶段表现如果未来要接数据库 tag，可在 `comment` 写“未来可由 database.stage.<role_id>.<stage_key> 触发”。
- 如果已经生成 `database.stages[].active_tag` 或 `database.tags[].tag`，优先同时生成 `entry_type=external_tag` 的世界书消费者，让 tag 真正能影响表现。

不要把世界书写成：

- 角色全部人格。
- 一次性记忆流水账。
- 大段模型写作纪律。

## 预设路由

预设回答“模型如何遵守基础系统纪律”。当前阶段不追求高阶预设生成，不生成大型 prompt group、风格库或完整叙事引擎。

适合写：

- 不替用户行动。
- 不跳关系阶段。
- 不突然坦白、献身、崩溃、完全信任。
- 读取角色卡、世界书、记忆时的优先级。
- 亲密和身体性如何保持人格因果。
- 多角色边界。
- 反 AI 味：避免总结腔、宣告腔、鸡汤腔、过度象征。

字段建议：

- `base_system_prompt` 写少量总纪律。
- `modules` 开成熟开关，不承载角色专属事实。
- `extra_prompts` 写短补充规则。
- `prompt_groups` 默认保持精简，只在用户明确要求时写可选阶段规则。

预设不要写：

- 具体世界百科。
- 已发生事件。
- 单个角色的所有私密事实。
- 复杂高阶预设工程。
- 大型风格库或完整叙事引擎。

## 记忆路由

记忆回答“过去如何改变现在”。

适合写：

- 用户已经做过的事。
- 承诺、拒绝、背叛、照顾、伤害、亲近。
- 长期偏好和雷点。
- 关系变化的证据。
- 未来可记录的记忆模板，但必须标明它是模板或 notes，不要冒充已发生事实。

记忆不适合写：

- 未发生剧情。
- 世界规则百科。
- 模型通用纪律。

## 数据库草稿的 P1 落点

数据库的意义是：

```text
记录变量 -> 判断阶段 -> 发出 tag
```

P1 可以写 `database` 工程草稿，但不能写真实运行时数据库路径。遇到数据库需求时这样转换：

- 变量名和阶段设计：写入 `database.variables`、`database.stages`、`database.tags`。
- 阶段表现：写入 `worldbook.entries`，并在 `comment` 标明未来 tag。
- 防跳阶段：写入 `preset`。
- 变化依据：写入 `memory.items` 模板或 notes。

例：

用户要“慢慢信任系统”。

P1 输出：

- `personality`：信任低/中/高时的行为差异。
- `worldbook.entries`：戒备、软化、稳定亲密三个阶段表现。
- `preset`：禁止一轮内跳到完全信任。
- `memory`：记录信任变化事件的模板。
- `database.variables`：trust/guard/intimacy 等变量定义。
- `database.stages`：戒备、软化、稳定亲密的条件和 tag。
- `database.tags`：tag 未来触发世界书或演出工坊的连接意图。

P2.2 输出时应优先让 database tag 和 worldbook external_tag 成对出现：

- `database.stages[].active_tag`: `database.stage.<role_id>.<stage_key>`
- `database.tags[].tag`: 同一 tag 的连接说明
- `worldbook.entries[].entry_type`: `external_tag`
- `worldbook.entries[].trigger`: 同一 tag
- `worldbook.entries[].content`: 该阶段角色该如何表现、不能越过什么边界

如果暂时不生成 worldbook 消费者，必须在 database tag 的 notes 或候选 reason 中说明“该 tag 只是设计草稿，后续需要世界书或演出工坊消费”。

不要输出：

- `persona_card.stateJournal.roles[].variables`
- `persona_card.stateJournal.roles[].stages`

## 演出工坊意识的 P1 落点

P1 仍不写复杂 `creativeWorkshop` runtime 结构。

遇到视觉、音乐、氛围、演出需求时：

- 如果只是开场氛围，可写进 `scenario` 或 `worldbook`。
- 如果是阶段氛围，可写进 `worldbook.comment` 或 `creator_notes` 标明未来演出触发。
- 如果要模型遵守演出节奏，可写进 `preset`。

不要伪造 `creativeWorkshop.dynamicScenes` 路径。

## 深度路由检查

生成候选前检查：

```text
这是角色事实，还是模型纪律？
这是稳定设定，还是触发设定？
这是已经发生的事，还是未来可能发生的事？
这是状态变量，还是状态表现？
这是身体性人格逻辑，还是动作清单？
这是用户已确定，还是 AI 推论？
当前 schema 是否支持这个路径？
```

如果路径不支持，转成当前容器能承接的候选，或不生成该候选。

P2.2 额外检查：

```text
这个需求是否需要跨容器拆分？
如果生成了数据库 tag，谁消费它？
如果写了记忆，它是否确实已经发生？
如果写了亲密/身体变化，它是否受当前关系阶段约束？
如果写了预设纪律，它是否服务于角色连续性，而不是空泛口号？
```

最终不要输出这些检查过程，只输出候选 JSON。
