# Fantareal PC HuskarUI 客户端

这是 Fantareal 的 PC 桌面客户端源码，基于 **Qt 6 + QML + C++ + HuskarUI** 构建。

本分支是一个独立子项目分支，根目录只包含 PC HuskarUI 客户端源码，不包含旧 Python/FastAPI 服务、运行数据、发布包、Qt SDK 或 HuskarUI 本体。

## 目录结构

```text
.
├── CMakeLists.txt
├── README.md
├── cpp/
│   ├── fantarealbridge.cpp
│   ├── fantarealbridge.h
│   └── main.cpp
├── qml/
│   ├── FantarealApp.qml
│   ├── Global.qml
│   ├── controls/
│   └── pages/
├── tests/
└── tools/
```

## 依赖

构建前需要准备：

- Qt `6.7+`
- 支持 C++20 的 MSVC / Clang / GCC
- CMake `3.25+`
- Ninja
- HuskarUI 源码或已安装的 HuskarUI CMake 包

Windows + MSVC 推荐使用 Qt `msvc2019_64` 或兼容 Kit。

## 快速构建

如果使用 HuskarUI 源码 checkout：

```powershell
$env:HUSKARUI_ROOT = "C:\path\to\HuskarUI"
```

运行完整验证构建：

```powershell
.\tools\Verify-HuskarUI.ps1 `
  -QtPrefix "C:\path\to\Qt\6.7.3\msvc2019_64" `
  -HuskarUIRoot $env:HUSKARUI_ROOT `
  -Build
```

验证脚本会自动完成：

- 检查必需源码文件。
- 检查 QML 语法。
- 检查已知 HuskarUI API 误用模式。
- 配置 Release 构建。
- 编译 `FantarealHuskarUI.exe`。
- 运行 CTest。
- 启动 GUI smoke test，检查 Chat / Settings / Routes / Cards / Memory / Worldbook / Preset 页面。

构建产物默认输出到：

```text
build-verify/FantarealHuskarUI.exe
```

`build-verify/` 是构建产物目录，不应提交到仓库。

## 运行数据

客户端默认读取 Fantareal 根目录下的本地数据文件，例如：

```text
data/settings.json
data/conversations.json
data/current_role_card.json
data/preset.json
data/worldbook.json
data/route_forwarding.json
data/card_runtime/cards/*/memories.json
```

也可以通过环境变量指定根目录：

```powershell
$env:FANTAREAL_ROOT = "E:\Fantareal"
```

测试用例不会写入真实 `data/`，而是使用临时目录构造 fixture。

## 当前功能

### Chat 聊天主舞台

- 默认启动页。
- 大面积聊天画布，弱化侧栏和工具台感。
- Enter 发送，Shift + Enter 换行。
- 用户消息立即写入本地对话。
- 支持 OpenAI-compatible `/v1/chat/completions` 请求。
- 支持流式请求，但开启输出切分时不会向 UI 泄露原始回复。
- 支持“重新回复”：删除最后一次 AI 回复后，基于最新用户消息重新生成。
- 支持“结束对话”：追加整理回忆状态、总结长期记忆并清空当前上下文。
- 支持输出切分子代理：主模型回复后交给切分器处理，前端只展示切分后的气泡。
- 子代理失败时使用本地安全切分回退，不阻塞正常聊天。

### Settings 设置

- 编辑模型 Base URL、模型名、温度、历史条数、超时等。
- 编辑 Embedding / Rerank 基础配置。
- 支持背景图片路径与透明度设置。
- 支持输出切分开关。
- API Key 不回显明文：空输入保留旧密钥，非空输入覆盖。
- 保存前自动备份旧文件。

### Routes 模型路由

- 编辑路由开关、POST hook、重试次数、策略等安全字段。
- Provider 支持新增、编辑、删除安全元数据。
- Provider Key 只显示数量/状态，不回显明文。
- 留空保存保留旧 key，输入新 key 才替换。
- 保存前自动备份旧文件。

### Cards 人设卡

- 编辑当前角色卡的安全文本字段。
- 支持导入/激活本地角色卡 JSON。
- 支持同步到 `persona.json`。
- 保留未知字段、Persona、Workshop、State Journal 等嵌套数据。

### Preset 预设

- 编辑当前预设名称、启用状态和模块开关。
- 支持子预设/模块开关。
- 保留其它预设、额外提示词、未知字段。
- 保留旧互斥规则，例如短段/长段、第二人称/第三人称。

### Worldbook 世界书

- 编辑世界书全局设置。
- 编辑词条标题、触发词、类型、启用状态、匹配方式、内容、注入位置等安全字段。
- 支持新增词条。
- 关键字词条必须有触发词。
- 保存前自动备份，保留未知字段。

### Memory 记忆

- 读取当前角色运行时记忆。
- 支持新增和编辑记忆词条。
- 支持 active / archived 状态。
- 标签会自动规范化和去重。
- 保存前自动备份，保留未知字段。

## 开源说明

本分支只作为 Fantareal PC HuskarUI 客户端源码分支。实际使用时需要自行准备 Qt、HuskarUI 和本地 Fantareal 数据目录。

Fantareal 只提供本地部署工具与开源代码，不提供官方在线聊天服务、账号系统、API 中转或内容托管服务。第三方 LLM API、Embedding API、Rerank API 的配置和调用行为由使用者自行负责。
