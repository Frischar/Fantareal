package com.frischar.fantareal.domain.worldbook

import kotlinx.serialization.Serializable

@Serializable
enum class TriggerLogic {
    Any,
    All
}

@Serializable
enum class TriggerMode {
    Literal,
    Regex
}

@Serializable
enum class InjectionPosition {
    BeforePersona,
    RecentChat,
    BeforeReply
}

@Serializable
data class WorldbookEntry(
    val id: String,
    val title: String,
    val content: String,
    val enabled: Boolean = true,
    val constant: Boolean = false,
    val activationTags: List<String> = emptyList(),
    val primaryTriggers: List<String> = emptyList(),
    val primaryLogic: TriggerLogic = TriggerLogic.Any,
    val secondaryTriggers: List<String> = emptyList(),
    val secondaryLogic: TriggerLogic = TriggerLogic.Any,
    val triggerMode: TriggerMode = TriggerMode.Literal,
    val caseSensitive: Boolean = false,
    val wholeWord: Boolean = false,
    val chance: Double = 1.0,
    val stickyTurns: Int = 0,
    val cooldownTurns: Int = 0,
    val insertionPosition: InjectionPosition = InjectionPosition.RecentChat,
    val priority: Int = 0
)

data class WorldbookMatch(
    val entry: WorldbookEntry,
    val position: InjectionPosition
)

data class WorldbookScanResult(
    val matches: List<WorldbookMatch>
)
