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

data class PromptBuildInput(
    val systemRules: String,
    val presetModules: List<String> = emptyList(),
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
        val systemText = buildSystemText(input)
        val historyMessages = input.history
            .filter { it.content.isNotBlank() && it.role != MessageRole.System }
            .takeLast(input.maxHistoryMessages)
            .mapNotNull { message ->
                when (message.role) {
                    MessageRole.User -> LlmMessage("user", message.content)
                    MessageRole.Assistant -> LlmMessage("assistant", message.content)
                    MessageRole.System -> null
                }
            }

        val messages = historyMessages + LlmMessage("user", input.latestUserInput)

        return when (input.providerFormat) {
            PromptProviderFormat.OpenAi -> PromptBuildResult(systemText, messages)
            PromptProviderFormat.Anthropic -> PromptBuildResult(systemText, messages)
        }
    }

    private fun buildSystemText(input: PromptBuildInput): String {
        val sections = buildList {
            add(PromptSection("System Rules", input.systemRules))
            addAll(input.presetModules.map { PromptSection("Preset", it) })
            addAll(input.worldbookBeforePersona.map { PromptSection("Worldbook Before Persona", it) })
            add(PromptSection("Persona", input.persona.systemPrompt))
            if (input.memories.isNotEmpty()) {
                add(PromptSection("Long Term Memory", input.memories.joinToString("\n")))
            }
            addAll(input.worldbookRecent.map { PromptSection("Recent Worldbook", it) })
        }

        return sections
            .filter { it.content.isNotBlank() }
            .joinToString("\n\n") { section ->
                "## ${section.title}\n${section.content.trim()}"
            }
    }
}
