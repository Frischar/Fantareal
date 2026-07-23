# Fantareal Android

> Fantareal 的原生 Android 客户端。
> Web 版（Python/FastAPI）位于 [`main`](https://github.com/TeabyteDev/Fantareal/tree/main) 分支；本分支（`android`）是原生 Android 客户端

## 当前版本

- 应用版本：v1.6.6（versionCode 17）
- 包名：`com.frischar.fantareal`
- 最低要求：Android 8.0（API 26）
- 正式版下载：[Android v1.6.6](https://github.com/TeabyteDev/Fantareal/releases/tag/v1.6.6)

## 功能

- 原生 Jetpack Compose UI：聊天 / 角色卡 / 世界书 / 记忆 / 预设 / 工坊 / 设置
- 多 LLM 提供商（OpenAI / DeepSeek / OpenRouter / SiliconFlow / MiniMax 等），用户自行配置 Base URL 与 API Key
- 离线欢迎页与内嵌 WebView 资源（`app/src/main/assets/mobile/`）
- API Key 通过 AndroidKeyStore + AES-GCM 加密存储，**无任何硬编码密钥**

## 系统要求

- 运行：Android 8.0（API 26）及以上
- 构建：JDK 17、Android SDK 34（build-tools 34.0.0）、Gradle 8.5（wrapper 已附带）
