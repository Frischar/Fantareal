# 写卡器轮椅模式：角色运行包目标

当前阶段不追求从零生成高阶预设。目标是稳定产出一个能跑的 40 分角色运行包。

运行包优先由这些容器共同完成：

- `persona`：角色是谁、如何反应、如何靠近/退缩、语言和边界是什么。
- `worldbook`：稳定事实、阶段表现、关系状态、由 tag 触发的状态规则。
- `memory`：已发生事实；若是未来记录方式，必须明确写成模板，不要冒充记忆。
- `database`：变量、阶段判断、发出的 tag，用来触发世界书或演出工坊。
- `preset`：只做轻量适配纪律，不负责创作高阶叙事引擎。

预设边界：

- 不要尝试生成复杂高阶预设、完整叙事引擎、风格大库或大型 prompt group 系统。
- 只有用户明确要求预设，或当前角色运行包缺少基础防线时，才输出精简 preset 候选。
- preset 候选只写模型纪律：不替用户行动、不跳关系阶段、不突然亲密、不突然完全信任、如何读取角色卡/世界书/记忆/状态。

数据库联动必须优先闭环：

```text
database variable -> database stage/tag -> worldbook external_tag consumer
```

如果生成 `database.stages[].active_tag` 或 `database.tags[].tag`，优先同时生成对应的 `worldbook.entries`：

- `entry_type`: `external_tag`
- `trigger`: 与数据库 tag 完全一致
- `prompt_layer`: `current_state` 或 `dynamic`
- `insertion_position`: `after_char_defs` 或 `in_chat`
- `content`: 命中该 tag 后角色应该如何表现，以及不能越过什么边界

若暂时不能生成消费者，必须在候选 reason/notes 说明该 tag 只是设计草稿。

判断一轮输出是否合格：

1. 角色卡让角色有欲望、边界、反应和语言纹理。
2. 世界书能承载阶段/状态，而不是重复角色卡。
3. 记忆不伪造未发生剧情。
4. 数据库 tag 有消费者或明确标注未闭环。
5. 预设只补基础纪律，不试图替代高阶预设工程。

实体遵从：

- 如果用户给了角色名、世界名、地点名或关系名，必须沿用用户给出的名字。
- 不要从案例、示例或参考材料里借用角色名。
- 如果用户没有给名字，可以用中性占位名，但必须在 reason 中说明这是临时草稿。
