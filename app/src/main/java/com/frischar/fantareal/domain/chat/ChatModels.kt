package com.frischar.fantareal.domain.chat

import kotlinx.serialization.Serializable

@Serializable
enum class MessageRole {
    System, User, Assistant
}

@Serializable
data class ConversationMessage(
    val id: String,
    val role: MessageRole,
    val content: String,
    val createdAt: Long,
    val thinking: String? = null,
    val error: Boolean = false
)
