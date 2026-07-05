package com.frischar.fantareal.domain.prompt

import com.frischar.fantareal.domain.chat.ConversationMessage
import com.frischar.fantareal.domain.chat.MessageRole
import com.frischar.fantareal.domain.llm.LlmMessage
import com.frischar.fantareal.domain.rolecard.PersonaRuntime

enum class PromptProviderFormat {
    OpenAi,
    Anthropic
}

data class PromptSection(
    val title: String,
    val content: String
)

data class PromptSegment(
    val id: String,
    val title: String = "",
    val content: String,
    val role: String = "system",
    val placement: String = "before_history",
    val order: Int = 0,
    val depth: Int = 0,
    val kind: String = "style",
    val strength: String = "soft",
    val required: Boolean = false,
    val tokenBudget: Int? = null,
    val activationTags: List<String> = emptyList()
)

data class PromptBuildInput(
    val systemRules: String,
    val presetModules: List<String> = emptyList(),
    val presetSegments: List<PromptSegment> = emptyList(),
    val worldbookBeforePersona: List<String> = emptyList(),
    val persona: PersonaRuntime,
    val memories: List<String> = emptyList(),
    val history: List<ConversationMessage> = emptyList(),
    val worldbookRecent: List<String> = emptyList(),
    val latestUserInput: String,
    val providerFormat: PromptProviderFormat = PromptProviderFormat.OpenAi,
    val maxHistoryMessages: Int = 10
)

data class PromptBuildResult(
    val system: String?,
    val messages: List<LlmMessage>
)

class PromptBuilder {
    fun build(input: PromptBuildInput): PromptBuildResult {
        val segments = input.presetSegments
            .filter { it.content.isNotBlank() }
            .sortedWith(compareBy<PromptSegment> { it.order }.thenBy { it.id })
        val prefixMessages = mutableListOf<LlmMessage>()
        val systemText = buildSystemText(input, segments, prefixMessages)
        val history = input.history
            .filter { it.content.isNotBlank() && it.role != MessageRole.System }
            .takeLast(input.maxHistoryMessages)
        val historyMessages = buildHistoryMessages(history, segments)
        val tailMessages = buildList {
            addAll(segmentsToMessages(segmentsAtDepth(segments, 0)))
            addAll(segmentsToMessages(segmentsForPlacement(segments, "output_guard")))
            addAll(segmentsToMessages(segmentsForPlacement(segments, "near_latest_user")))
            add(LlmMessage("user", input.latestUserInput))
        }

        val messages = prefixMessages + historyMessages + tailMessages

        return when (input.providerFormat) {
            PromptProviderFormat.OpenAi -> PromptBuildResult(systemText, messages)
            PromptProviderFormat.Anthropic -> PromptBuildResult(systemText, messages)
        }
    }

    private fun buildHistoryMessages(
        history: List<ConversationMessage>,
        segments: List<PromptSegment>
    ): List<LlmMessage> {
        val messages = mutableListOf<LlmMessage>()
        val historyCount = history.size
        history.forEachIndexed { index, message ->
            val tailDepth = historyCount - index
            messages += segmentsToMessages(segmentsAtDepth(segments, tailDepth))
            when (message.role) {
                MessageRole.User -> messages += LlmMessage("user", message.content)
                MessageRole.Assistant -> messages += LlmMessage("assistant", message.content)
                MessageRole.System -> Unit
            }
        }
        return messages
    }

    private fun buildSystemText(
        input: PromptBuildInput,
        segments: List<PromptSegment>,
        prefixMessages: MutableList<LlmMessage>
    ): String {
        val sections = buildList {
            add(PromptSection("System Rules", input.systemRules))
            addPlacementSections("Preset System Core", segments, "system_core", prefixMessages)
            addAll(input.presetModules.map { PromptSection("Preset", it) })
            addAll(input.worldbookBeforePersona.map { PromptSection("Worldbook Before Persona", it) })
            addPlacementSections("Preset Before Character", segments, "before_character", prefixMessages)
            addPlacementSections("Preset Character", segments, "character", prefixMessages)
            add(PromptSection("Persona", input.persona.systemPrompt))
            addPlacementSections("Preset After Character", segments, "after_character", prefixMessages)
            addPlacementSections("Preset Lore Context", segments, "lore_context", prefixMessages)
            if (input.memories.isNotEmpty()) {
                add(PromptSection("Long Term Memory", input.memories.joinToString("\n")))
            }
            addPlacementSections("Preset Memory Context", segments, "memory_context", prefixMessages)
            addAll(input.worldbookRecent.map { PromptSection("Recent Worldbook", it) })
            addPlacementSections("Preset Before History", segments, "before_history", prefixMessages)
            addPlacementSections("Preset System Format", segments, "system_format", prefixMessages)
        }

        return sections
            .filter { it.content.isNotBlank() }
            .joinToString("\n\n") { section ->
                "## ${section.title}\n${section.content.trim()}"
            }
    }

    private fun MutableList<PromptSection>.addPlacementSections(
        title: String,
        segments: List<PromptSegment>,
        placement: String,
        prefixMessages: MutableList<LlmMessage>
    ) {
        val placementSegments = segmentsForPlacement(segments, placement)
        val systemSections = placementSegments.filter { normalizeRole(it.role) == "system" }
        if (systemSections.isNotEmpty()) {
            add(PromptSection(title, systemSections.joinToString("\n\n") { it.content.trim() }))
        }
        val messageSegments = placementSegments.filter { normalizeRole(it.role) != "system" }
        prefixMessages += segmentsToMessages(messageSegments)
    }

    private fun segmentsForPlacement(segments: List<PromptSegment>, placement: String): List<PromptSegment> {
        return segments
            .filter { it.placement == placement }
            .sortedWith(compareBy<PromptSegment> { it.order }.thenBy { it.id })
    }

    private fun segmentsAtDepth(segments: List<PromptSegment>, depth: Int): List<PromptSegment> {
        return segments
            .filter { it.placement == "at_depth" && it.depth.coerceIn(0, 999) == depth.coerceIn(0, 999) }
            .sortedWith(compareBy<PromptSegment> { it.order }.thenBy { it.id })
    }

    private fun segmentsToMessages(segments: List<PromptSegment>): List<LlmMessage> {
        val messages = mutableListOf<LlmMessage>()
        var pendingRole = ""
        val pendingSections = mutableListOf<String>()

        fun flush() {
            if (pendingSections.isEmpty()) return
            messages += LlmMessage(pendingRole.ifBlank { "system" }, pendingSections.joinToString("\n\n"))
            pendingRole = ""
            pendingSections.clear()
        }

        segments.forEach { segment ->
            val role = normalizeRole(segment.role)
            val content = segment.content.trim()
            if (content.isBlank()) return@forEach
            if (pendingSections.isNotEmpty() && role != pendingRole) {
                flush()
            }
            pendingRole = role
            pendingSections += content
        }
        flush()
        return messages
    }

    private fun normalizeRole(role: String): String {
        val normalized = role.trim().lowercase()
        return when (normalized) {
            "ai", "model" -> "assistant"
            "assistant", "user", "system" -> normalized
            else -> "system"
        }
    }
}
