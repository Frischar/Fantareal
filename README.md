# Fantareal Android

> Fantareal 的原生 Android 客户端。
> Web 版（Python/FastAPI）位于 [`main`](https://github.com/Frischar/Fantareal/tree/main) 分支；本分支（`android`）是原生 Android 客户端，与 `main` 无共同 git 历史，独立演进。

## 功能

- 原生 Jetpack Compose UI：聊天 / 角色卡 / 世界书 / 记忆 / 预设 / 工坊 / 设置
- 多 LLM 提供商（OpenAI / DeepSeek / OpenRouter / SiliconFlow / MiniMax 等），用户自行配置 Base URL 与 API Key
- 离线欢迎页与内嵌 WebView 资源（`app/src/main/assets/mobile/`）
- API Key 通过 AndroidKeyStore + AES-GCM 加密存储，**无任何硬编码密钥**

## 系统要求

- 运行：Android 8.0（API 26）及以上
- 构建：JDK 17、Android SDK 34（build-tools 34.0.0）、Gradle 8.5（wrapper 已附带）

## 克隆与 Debug 构建

```bash
git clone -b android https://github.com/Frischar/Fantareal.git
cd Fantareal
# 在项目根目录放置 local.properties（不要提交），写入本机 SDK 路径：
#   sdk.dir=C\:\\Users\\<你>\\AppData\\Local\\Android\\Sdk
./gradlew assembleDebug
# 产物：app/build/outputs/apk/debug/app-debug.apk
```

## Release 签名配置

仓库不含任何签名密钥。如需本地构建 release：

1. 复制模板：`cp signing/keystore.properties.example signing/keystore.properties`
2. 用 `keytool` 生成或放入你的 `signing/fantareal.jks`，在 `keystore.properties` 填入真实密码
3. `./gradlew assembleRelease`

`signing/keystore.properties` 与 `*.jks` 已被 `.gitignore` 忽略，永不入库。CI 默认只构建 debug，不接触 release 签名。

## API Key 的安全存储

- `SecretStore.kt` 使用 AndroidKeyStore 生成 AES-GCM 密钥，密文与 IV 存入 EncryptedSharedPreferences
- 代码内无默认 API Key、无默认服务端密钥
- 用户在应用内自行填写并保存

## 安全披露

发现安全漏洞请私下联系，请勿直接开设公开 issue（可使用 GitHub Security Advisory）。

## 协议

本项目依据 **AGPL-3.0** 协议开源（与 `main` 分支一致）。详见 [LICENSE](LICENSE)。

## 致谢

Kotlin · Jetpack Compose · AndroidX · OkHttp · Coil · kotlinx-serialization · JSZip
