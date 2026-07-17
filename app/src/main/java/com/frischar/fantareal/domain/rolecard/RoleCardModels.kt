package com.frischar.fantareal.domain.rolecard

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

@Serializable
data class RoleCard(
    val name: String = "",
    val description: String = "",
    val personality: String = "",
    val scenario: String = "",
    @SerialName("first_mes")
    val firstMes: String = "",
    @SerialName("mes_example")
    val mesExample: String = "",
    @SerialName("creator_notes")
    val creatorNotes: String = "",
    val tags: List<String> = emptyList(),
    val plotStages: JsonElement? = null,
    val personas: JsonElement? = null,
    val stateJournal: JsonElement? = null,
    val creativeWorkshop: JsonElement? = null
)

@Serializable
data class PersonaRuntime(
    val name: String = "",
    val systemPrompt: String = "",
    val greeting: String = ""
)

data class RoleCardImportResult(
    val roleCard: RoleCard,
    val persona: PersonaRuntime,
    val clearedMemories: Boolean
)
