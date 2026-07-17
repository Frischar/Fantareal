package com.frischar.fantareal.domain.statejournal

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

@Serializable
data class StateJournalConfig(
    val version: Int = 1,
    val enabled: Boolean = false,
    val activeStageTags: List<String> = emptyList(),
    val roles: List<StateJournalRoleDefinition> = emptyList()
)

@Serializable
data class StateJournalRoleDefinition(
    val roleId: String,
    val roleName: String,
    val aliases: List<String> = emptyList(),
    val enabled: Boolean = true,
    val initialStage: String = "stage_a",
    val variables: List<StateJournalVariableDefinition> = emptyList(),
    val stages: List<StateJournalStageDefinition> = emptyList(),
    val snapshotFields: List<StateJournalSnapshotFieldDefinition> = emptyList(),
    val settings: StateJournalRoleSettings = StateJournalRoleSettings()
)

@Serializable
data class StateJournalVariableDefinition(
    val key: String,
    val name: String,
    val enabled: Boolean = true,
    val defaultValue: Double = 0.0,
    val minValue: Double = 0.0,
    val maxValue: Double = 100.0,
    val deltaMin: Double? = null,
    val deltaMax: Double? = null,
    val display: Boolean = true,
    val stageRelevant: Boolean = true,
    val instruction: String = ""
)

@Serializable
data class StateJournalStageDefinition(
    val key: String,
    val name: String,
    val enabled: Boolean = true,
    val priority: Int = 0,
    val conditionMode: String = "all",
    val conditions: List<StateJournalStageCondition> = emptyList(),
    val allowRegression: Boolean? = null,
    val confirmTurns: Int? = null,
    val cooldownTurns: Int? = null,
    val activationTag: String = "",
    val emitsTags: List<String> = emptyList()
)

@Serializable
data class StateJournalStageCondition(
    val variable: String,
    val operator: String = ">=",
    val target: JsonElement
)

@Serializable
data class StateJournalSnapshotFieldDefinition(
    val key: String,
    val label: String,
    val enabled: Boolean = true,
    val display: Boolean = true,
    val instruction: String = ""
)

@Serializable
data class StateJournalRoleSettings(
    val allowRegression: Boolean = false,
    val confirmTurns: Int = 1,
    val cooldownTurns: Int = 0
)

@Serializable
data class StateJournalRuntime(
    val version: Int = 1,
    val configSignature: String = "",
    val turnOrdinal: Long = 0,
    val roles: List<StateJournalRoleRuntime> = emptyList(),
    val displayTitle: String = "",
    val displaySummary: String = "",
    val updatedAt: Long = 0
)

@Serializable
data class StateJournalRoleRuntime(
    val roleId: String,
    val roleName: String,
    val variables: List<StateJournalVariableRuntime> = emptyList(),
    val activeStageKey: String = "",
    val activeStageName: String = "",
    val previousStageKey: String = "",
    val previousStageName: String = "",
    val stageChanged: Boolean = false,
    val candidateStageKey: String = "",
    val candidateCount: Int = 0,
    val cooldownUntilTurn: Long = 0,
    val stageReason: String = "",
    val snapshots: Map<String, String> = emptyMap(),
    val updatedAt: Long = 0
)

@Serializable
data class StateJournalVariableRuntime(
    val key: String,
    val name: String,
    val value: Double,
    val maximum: Double,
    val delta: Double = 0.0,
    val reason: String = "",
    val display: Boolean = true
)

data class StateJournalAnalysis(
    val variableUpdates: List<StateJournalVariableUpdate>,
    val characterSnapshots: List<StateJournalCharacterSnapshot>,
    val title: String,
    val summary: String
)

data class StateJournalVariableUpdate(
    val roleId: String,
    val key: String,
    val value: Double?,
    val delta: Double?,
    val reason: String
)

data class StateJournalCharacterSnapshot(
    val roleId: String,
    val fields: Map<String, String>
)
