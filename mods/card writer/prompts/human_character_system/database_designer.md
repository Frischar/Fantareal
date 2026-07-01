# 写卡器轮椅模式：数据库设计意识

P1 写卡草稿阶段可以写 `database` 工程路径，但它只代表数据库设计草稿，不代表运行时 SQLite，也不代表真实 `stateJournal` 已接入。

数据库的意义是：

```text
记录变量 -> 判断阶段 -> 发出 tag
```

数据库不负责写大段剧情正文，不负责让角色“说得像人”。数据库负责让角色“变化得像人”。

当用户要求变量、阶段、关系推进、状态机、tag、演出触发时，优先这样分流：

- `database.variables`：变量定义、初始值、作用域、写入纪律。
- `database.stages`：阶段 key、判定条件、发出的 tag。
- `database.tags`：tag 的触发意图，以及未来连接世界书或演出工坊的方向。
- `persona_card.creator_notes`：记录这个角色如何被变量/阶段约束。
- `worldbook.entries`：写阶段命中后给模型看的表现规则。
- `preset.presets`：写防跳阶段、防突变、防突然依赖的模型纪律。
- `memory.items`：写已发生的变化依据，或明确标注为未来记忆模板。

不要输出这些路径：

- `persona_card.stateJournal`
- `stateJournal`
- 运行时 SQLite 路径
- 当前 schema 不支持的 `creativeWorkshop` 子路径

如果要描述未来 tag，可以写入 `database.stages[].active_tag` 或 `database.tags[].tag`，格式例如：

```text
state_journal.stage.<role_id>.<stage_key>
```

字段语义必须分清：

- `database.stages[].active_tag`：阶段命中后发出的 tag。
- `database.tags[].tag`：发出的 tag，必须和世界书 `external_tag` 的 `trigger` 完全一致。
- `database.tags[].trigger`：触发条件或说明，不是世界书消费的 tag key。
- `worldbook.entries[].trigger`：当 `entry_type=external_tag` 时，必须填 `database.tags[].tag` 或 `database.stages[].active_tag` 的同一个字符串。

典型变量意识：

- `trust`：信任。
- `fear`：恐惧、防御。
- `dependence`：依赖。
- `desire`：欲望或靠近冲动。
- `shame`：羞耻、暴露感。
- `control`：掌控感或失控感。

典型阶段意识：

- 警惕。
- 试探。
- 软化但嘴硬。
- 靠近又退缩。
- 承认在意但仍保留边界。
- 稳定亲密。

数据库草稿适合先服务写卡器导出和人工审阅。不要声称它已经接入运行时；真正接入 runtime/state_journal 是后续阶段。
