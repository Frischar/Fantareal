# Fantareal Android

> Fantareal 的原生 Android 客户端。
> Web 版（Python/FastAPI）位于 [`PC-webUI`](https://github.com/Frischar/Fantareal/tree/PC-webUI) 分支；PC / macOS 桌面版源码位于 [`PC-HuskarUI`](https://github.com/Frischar/Fantareal/tree/PC-HuskarUI) 分支；本分支（`android`）是原生 Android 客户端。

## 功能

- 原生 Jetpack Compose UI：聊天 / 角色卡 / 世界书 / 记忆 / 预设 / 工坊 / 设置
- 多 LLM 提供商（OpenAI / DeepSeek / OpenRouter / SiliconFlow / MiniMax 等），用户自行配置 Base URL 与 API Key
- 离线欢迎页与内嵌 WebView 资源（`app/src/main/assets/mobile/`）
- API Key 通过 AndroidKeyStore + AES-GCM 加密存储，**无任何硬编码密钥**

## 发布包

正式版统一发布在 [`V1.0.0`](https://github.com/Frischar/Fantareal/releases/tag/V1.0.0)：

- Windows：`Fantareal-win.7z`
- macOS Apple Silicon：`Fantareal-macOS-arm64.zip`
- Android：`Fantareal-Android-v1.6.4.apk`

说明：macOS 包当前为 Apple Silicon / arm64 构建；如果需要 Intel 或 Universal 版本，需要额外的 macOS 构建环境重新打包。

## 系统要求

- Android 运行：Android 8.0（API 26）及以上
- Android 构建：JDK 17、Android SDK 34（build-tools 34.0.0）、Gradle 8.5（wrapper 已附带）
- macOS 运行：Apple Silicon / arm64，下载 `Fantareal-macOS-arm64.zip` 后解压运行；未签名包首次启动可能需要在系统设置中允许打开
