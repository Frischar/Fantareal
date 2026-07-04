package com.frischar.fantareal.domain.memory

import kotlinx.serialization.Serializable

@Serializable
data class LongTermMemory(
    val id: String,
    val title: String = "",
    val text: String,
    val notes: String = "",
    val tags: List<String> = emptyList(),
    val createdAt: Long,
    val updatedAt: Long = createdAt
) {
    fun displayTitle(): String {
        return title.ifBlank {
            text.replace(Regex("\\s+"), " ").trim().take(32).ifBlank { "\u5bf9\u8bdd\u8bb0\u5fc6" }
        }
    }
}

@Serializable
data class MemoryTombstone(
    val id: String,
    val text: String,
    val deletedAt: Long
)
