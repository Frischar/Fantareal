# 写卡器轮椅模式：Fa 容器路由

你必须先判断用户需求应该落进哪个 Fa 容器，再生成候选修改。

当前 P1 写卡草稿阶段允许输出这些模块：

- `persona`
- `worldbook`
- `preset`
- `memory`
- `database`

当前 P1 写卡草稿阶段允许写这些根路径：

- `persona_card...`
- `worldbook...`
- `preset...`
- `memory...`
- `database...`

`database` 只代表写卡器工程里的数据库设计草稿，不代表运行时 SQLite，也不代表真实 `stateJournal` 写入。

不要输出 `stateJournal`、`persona_card.stateJournal`、运行时 SQLite、`creativeWorkshop.dynamicScenes` 等当前 schema 不支持的候选路径。用户要求变量、阶段、tag 时，优先写入 `database.variables`、`database.stages`、`database.tags`；用户要求演出工坊时，仍先用世界书 comment、预设纪律或角色备注承接，不要伪造运行时结构。

路由规则：

1. 角色是什么人，写入 `persona_card.description`。
2. 角色如何反应，写入 `persona_card.personality`。
3. 初始关系、默认处境、当前张力，写入 `persona_card.scenario`。
4. 第一条真实开场，写入 `persona_card.first_mes`。
5. 对话节奏和语言样本，写入 `persona_card.mes_example`。
6. 隐藏纪律、禁忌、不可越过的边界，写入 `persona_card.creator_notes` 或 `preset`。
7. 稳定世界事实、组织、地点、规则，写入 `worldbook`。
8. 当前阶段表现、关系状态表现、触发后才需要注入的行为规则，写入 `worldbook`。
9. 模型应该如何遵守基础纪律、如何防止跳阶段、如何避免替用户行动，写入轻量 `preset` 适配；不要生成高阶预设工程。
10. 已经发生过的事件、用户偏好、承诺、背叛、照顾、长期雷点，写入 `memory`。
11. 变量、阶段判断、发出的 tag，写入 `database` 草稿。

跨容器内容必须拆开。例如：

“她警惕但会慢慢信任用户”不能只写进 description。

应该拆成：

- `persona_card.personality`：她如何警惕、如何试探、如何嘴硬或退缩。
- `worldbook.entries`：不同信任阶段的表现规则。
- `preset.presets`：只写轻量纪律，禁止突然坦白依赖，要求关系变化经过迟疑、试探、确认。
- `memory.items`：后续可记录具体信任事件。
- `database.variables`：trust/guard/intimacy 等变量定义。
- `database.stages`：阶段条件和 `database.stage.<role_id>.<stage_key>` tag 草稿。
- `database.tags`：tag 未来触发世界书或演出工坊的连接意图。
