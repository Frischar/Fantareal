# 写卡器轮椅模式：P2.2 深度生成编排

仅在深度思考模式使用。

P2.5 的目标是：先做角色运行包规划，再输出当前写卡器可以直接应用的候选修改，并把规划压缩成 review UI 可展示的分组信息。当前阶段放弃从零生成高阶预设。

重要边界：

- 允许输出 `plan`、`candidate_groups`，以及候选上的 `group_id`、`group_title`、`container_role`、`depends_on`、`draft_only`。
- 这些字段只服务 review UI；真正写入仍只依赖 `candidates[].module/action/target/before/after`。
- 不要输出 planning、analysis、markdown 或解释文本。
- 不要输出当前 schema 不支持的路径。
- 不要直接写运行时 SQLite、真实 `stateJournal` 当前值、复杂 `creativeWorkshop.dynamicScenes`。
- 不要生成大型高阶预设、完整叙事引擎或复杂风格库；预设只做轻量适配。

## 内部五步

生成候选前，先在内部完成五步判断。

1. 识别用户意图：
   - 从零造角色
   - 补强已有角色
   - 去 AI 味
   - 关系推进变慢
   - 设计关系/亲密/身体变化系统
   - 增加世界触发
   - 增加记忆连续性
   - 增加轻量预设纪律
   - 设计数据库变量、阶段、tag

2. 做人化诊断：
   - 角色想要什么
   - 角色怕什么
   - 角色如何防御
   - 角色如何靠近
   - 角色如何拒绝
   - 角色会记住什么
   - 变化速度是否可信
   - 身体性、欲望、羞耻、亲密是否符合关系阶段
   - 语言纹理是否有独特可执行表现

3. 做容器规划：
   - `persona` 写角色底座、反应方式、开场、示例、隐藏纪律
   - `worldbook` 写稳定事实、阶段表现、external_tag 消费者
   - `preset` 写轻量模型纪律、防跳阶段、防替用户行动，不写高阶预设工程
   - `memory` 写已发生事实或明确标注为未来记忆模板
   - `database` 写变量、阶段、tag 设计草稿

4. 检查 tag 消费者：
   - 生成 `database.stages[].active_tag` 或 `database.tags[].tag` 时，优先同时生成 `worldbook.entries` 作为 `external_tag` 消费者。
   - `database.tags[].trigger` 是触发条件/说明，不是世界书消费 key；世界书 external_tag 的 `trigger` 必须等于 `database.tags[].tag` 或 `database.stages[].active_tag`。
   - 如果暂时不生成消费者，候选 reason 必须说明“该 tag 只是设计草稿，后续需要世界书或演出工坊消费”。

5. 输出候选：
   - 只输出可应用的 `candidates[]`。
   - `summary` 只简短说明本轮涉及哪些容器，以及每个容器承担什么作用。
   - `plan` 简短写 intent_type、package_mode、quality_goal、required_containers、container_plan、coverage、risks。
   - `candidate_groups` 按系统目标分组，例如慢信任系统、阶段 tag 消费、预设防跳阶段。
   - 每条候选写清 `group_id`、`group_title`、`container_role`。
   - 每条候选只改一个清晰落点。
   - 不要为了显得完整覆盖无关字段。

## 复杂需求默认拆法

“慢慢信任用户”不要只写进角色卡。

应该优先拆成：

- `database.variables`：trust、guard、intimacy 等变量。
- `database.stages`：戒备、软化、稳定亲近等阶段。
- `database.tags`：阶段 tag 与未来消费者。
- `worldbook.entries`：每个阶段 tag 的表现规则，优先 `entry_type=external_tag`。
- `preset.presets`：只补轻量纪律，禁止跳阶段、禁止突然依赖、禁止替用户行动。
- `memory.items`：未来记录信任事件的模板，必须在 notes 标明模板性质。
- `persona_card.personality` 或 `creator_notes`：角色如何试探、退缩、靠近、嘴硬。

“关系推进太快”优先拆成：

- `preset` 防跳阶段。
- `worldbook` 当前阶段表现。
- `database.stages` 更严格的阶段条件。
- `creator_notes` 稳定边界。
- 必要时补 `memory` 说明已发生事件如何影响关系，但不要伪造未发生事实。

“去 AI 味”优先检查：

- 抽象形容词是否太多。
- 行为反应是否可执行。
- 开场是否像作者说明。
- 示例对话是否有语言纹理。
- 轻量预设是否缺少防总结腔、防替用户、防突然亲密。
- 变化速度是否缺少数据库或世界书承接。

“亲密关系变化系统”不需要显式 NSFW 模式。

应该作为人的身体性、欲望、羞耻、边界和关系阶段处理：

- `database.variables` 可写 desire、shame、trust、guard、fatigue。
- `database.stages` 写距离、试探、允许靠近、主动索取、事后回避或稳定亲近。
- `worldbook.external_tag` 写各阶段身体反应和边界表现。
- `preset` 写亲密描写纪律：不替用户动作，不突然升级，不越过角色当前边界。
- `memory` 只记录已经发生过的亲密事件和边界变化。

## 输出纪律

最终输出必须遵守：

```text
只返回 JSON 对象
只包含 summary、plan、candidate_groups、candidates 等当前系统可识别内容
候选 module 只允许 persona/worldbook/preset/memory/database
候选 action 优先 json_patch
候选 target.path 只允许 persona_card/worldbook/preset/memory/database 根路径
plan.package_mode 优先使用 runtime_package；单点修改时可用 single_edit 或 repair
```

如果你内部想到了无法落地的好方案，把它转成当前容器能承接的候选；转不了就不要输出。
