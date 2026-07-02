package com.frischar.fantareal.domain.memory

import kotlinx.serialization.Serializable

@Serializable
data class LongTermMemory(
    val id: String,
    val text: String,
    val tags: List<String> = emptyList(),
    val createdAt: Long,
    val updatedAt: Long = createdAt
)

@Serializable
data class MemoryTombstone(
    val id: String,
    val text: String,
    val deletedAt: Long
)
