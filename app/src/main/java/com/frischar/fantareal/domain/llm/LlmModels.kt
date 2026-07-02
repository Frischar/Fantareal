package com.frischar.fantareal.domain.llm

data class LlmMessage(
    val role: String,
    val content: String
)

data class LlmRequest(
    val model: String,
    val system: String?,
    val messages: List<LlmMessage>,
    val temperature: Double?,
    val stream: Boolean = true
)

sealed interface LlmStreamEvent {
    data class Token(val text: String) : LlmStreamEvent
    data class Error(val message: String) : LlmStreamEvent
    data object Done : LlmStreamEvent
}
