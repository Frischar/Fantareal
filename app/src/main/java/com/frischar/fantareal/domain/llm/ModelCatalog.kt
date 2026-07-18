package com.frischar.fantareal.domain.llm

data class ModelProviderPreset(
    val id: String,
    val label: String,
    val baseUrl: String,
    val recommendedModel: String,
    val helper: String,
    val requiresApiKey: Boolean = true
)

object ModelProviderPresets {
    val all = listOf(
        ModelProviderPreset(
            id = "custom",
            label = "自定义",
            baseUrl = "",
            recommendedModel = "",
            helper = "保留当前填写内容，适合本地或其他 OpenAI-compatible 服务。",
            requiresApiKey = false
        ),
        ModelProviderPreset(
            id = "deepseek",
            label = "DeepSeek",
            baseUrl = "https://api.deepseek.com/v1",
            recommendedModel = "deepseek-chat",
            helper = "填入 DeepSeek 官方兼容地址，并优先选择 deepseek-chat。"
        ),
        ModelProviderPreset(
            id = "openai",
            label = "OpenAI",
            baseUrl = "https://api.openai.com/v1",
            recommendedModel = "gpt-4.1-mini",
            helper = "填入 OpenAI 官方地址；拉取后以账号实际可用模型为准。"
        ),
        ModelProviderPreset(
            id = "minimax",
            label = "MiniMax",
            baseUrl = "https://api.minimaxi.com/v1",
            recommendedModel = "MiniMax-M3",
            helper = "填入 MiniMax 国内官方 OpenAI-compatible 地址。"
        ),
        ModelProviderPreset(
            id = "openrouter",
            label = "OpenRouter",
            baseUrl = "https://openrouter.ai/api/v1",
            recommendedModel = "openrouter/auto",
            helper = "优先使用 openrouter/auto，也可以从账号可用列表中改选。"
        ),
        ModelProviderPreset(
            id = "siliconflow",
            label = "SiliconFlow",
            baseUrl = "https://api.siliconflow.cn/v1",
            recommendedModel = "",
            helper = "填入 SiliconFlow 地址，拉取后从账号可用模型中选择。"
        )
    )

    fun find(id: String): ModelProviderPreset = all.firstOrNull { it.id == id } ?: all.first()

    fun detect(baseUrl: String): ModelProviderPreset {
        val normalized = baseUrl.trim().trimEnd('/').lowercase()
        return all.firstOrNull { preset ->
            preset.baseUrl.isNotBlank() && preset.baseUrl.trimEnd('/').lowercase() == normalized
        } ?: all.first()
    }
}

internal fun choosePreferredChatModel(
    currentModel: String,
    recommendedModel: String,
    availableModels: List<String>
): String {
    val models = availableModels.map(String::trim).filter(String::isNotBlank).distinct()
    val current = currentModel.trim()
    val recommended = recommendedModel.trim()

    if (current in models) return current
    if (recommended in models) return recommended

    val chatCandidates = models.filterNot(::isClearlyNonChatModel)
    return chatCandidates.singleOrNull().orEmpty()
}

private fun isClearlyNonChatModel(model: String): Boolean {
    val normalized = model.lowercase()
    return listOf(
        "embedding",
        "rerank",
        "moderation",
        "whisper",
        "tts",
        "speech",
        "audio",
        "image",
        "dall-e",
        "stable-diffusion",
        "transcription",
        "ocr"
    ).any(normalized::contains) || normalized.startsWith("bge-")
}
