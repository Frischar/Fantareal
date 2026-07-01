package com.frischar.fantareal.domain.preset

import kotlinx.serialization.Serializable

@Serializable
data class PromptPreset(
    val id: String,
    val title: String,
    val content: String,
    val enabled: Boolean = false
)
