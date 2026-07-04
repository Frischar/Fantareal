package com.frischar.fantareal.domain.preset

import com.frischar.fantareal.domain.prompt.PromptSegment
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class PromptPreset(
    val id: String,
    val title: String,
    val content: String = "",
    val enabled: Boolean = false,
    @SerialName("base_system_prompt")
    val baseSystemPrompt: String = "",
    val modules: List<PresetModule> = emptyList(),
    @SerialName("extra_prompts")
    val extraPrompts: List<PresetBlock> = emptyList(),
    @SerialName("prompt_groups")
    val promptGroups: List<PresetGroup> = emptyList()
) {
    fun hasStructuredContent(): Boolean {
        return baseSystemPrompt.isNotBlank() ||
            modules.isNotEmpty() ||
            extraPrompts.isNotEmpty() ||
            promptGroups.isNotEmpty()
    }

    fun structuredPromptSections(): List<String> {
        return structuredPromptSegments().map { it.content }
    }

    fun enabledPromptSections(): List<String> {
        return if (enabled) structuredPromptSections() else emptyList()
    }

    fun structuredPromptSegments(): List<PromptSegment> {
        if (!hasStructuredContent()) {
            return content.trim().takeIf { it.isNotBlank() }?.let {
                listOf(
                    PromptSegment(
                        id = "preset.$id.content",
                        title = title,
                        content = it,
                        placement = "before_history",
                        kind = "style",
                        order = 1000
                    )
                )
            }.orEmpty()
        }

        val segments = mutableListOf<PromptSegment>()
        baseSystemPrompt.trim().takeIf { it.isNotBlank() }?.let {
            segments += PromptSegment(
                id = "preset.$id.base_system_prompt",
                title = title.ifBlank { "Base" },
                content = it,
                role = "system",
                placement = "system_core",
                order = 10,
                kind = "base",
                strength = "hard",
                required = true
            )
        }

        modules
            .filter { it.enabled && it.content.isNotBlank() }
            .sortedBy { it.order }
            .forEach { module ->
                val outputGuard = module.key == "v4f_output_guard"
                segments += PromptSegment(
                    id = "preset.$id.module.${module.key}",
                    title = module.title,
                    content = module.content.trim(),
                    role = "system",
                    placement = if (outputGuard) "output_guard" else "system_core",
                    order = if (outputGuard) 900 else 100 + module.order * 10,
                    kind = if (outputGuard) "output_guard" else "output_rule",
                    strength = "hard",
                    required = true
                )
            }

        var sequence = 0
        for (group in promptGroups.sortedBy { it.order }) {
            if (!group.enabled || group.selectedIds.isEmpty()) continue
            val selectedIds = group.selectedIds.toSet()
            for (item in group.items) {
                if (item.id !in selectedIds || !item.enabled || item.content.isBlank()) continue
                sequence += 1
                segments += item.toPromptSegment(
                    id = "preset.$id.group.${group.id}.${item.id}",
                    title = "${group.title} / ${item.title}",
                    content = "[规则组：${group.title} / ${item.title}]\n${item.content.trim()}",
                    defaultOrder = 1000 + group.order + sequence
                )
            }
        }

        extraPrompts
            .filter { it.enabled && it.content.isNotBlank() }
            .forEachIndexed { index, block ->
                segments += block.toPromptSegment(
                    id = "preset.$id.extra.${block.id}",
                    content = "[${block.title}]\n${block.content.trim()}",
                    defaultOrder = 2000 + block.order + index
                )
            }

        return segments.sortedWith(compareBy<PromptSegment> { it.order }.thenBy { it.id })
    }

    fun enabledPromptSegments(): List<PromptSegment> {
        return if (enabled) structuredPromptSegments() else emptyList()
    }

    fun runtimeContent(): String {
        return structuredPromptSections().joinToString("\n\n")
    }

    fun switchableItemCount(): Int {
        return modules.size + extraPrompts.size + promptGroups.size + promptGroups.sumOf { it.items.size }
    }

    fun enabledSwitchableItemCount(): Int {
        return modules.count { it.enabled } +
            extraPrompts.count { it.enabled } +
            promptGroups.count { it.enabled } +
            promptGroups.sumOf { group -> group.items.count { group.isItemSelected(it) } }
    }
}

@Serializable
data class PresetModule(
    val key: String,
    val title: String,
    val content: String = "",
    val enabled: Boolean = false,
    val order: Int = 0
)

@Serializable
data class PresetBlock(
    val id: String,
    val title: String,
    val content: String = "",
    val enabled: Boolean = true,
    val order: Int = 0,
    val placement: String? = null,
    val role: String? = null,
    val depth: Int? = null,
    val kind: String? = null,
    val strength: String? = null,
    val required: Boolean? = null,
    @SerialName("tokenBudget")
    val tokenBudget: Int? = null,
    @SerialName("activation_tags")
    val activationTags: List<String> = emptyList()
) {
    fun metaLabel(): String = segmentMetaLabel(placement, role, depth, kind)
}

@Serializable
data class PresetGroup(
    val id: String,
    val title: String,
    val enabled: Boolean = true,
    @SerialName("selection_mode")
    val selectionMode: String = "single",
    @SerialName("selected_ids")
    val selectedIds: List<String> = emptyList(),
    val items: List<PresetGroupItem> = emptyList(),
    val order: Int = 0
) {
    fun isItemSelected(item: PresetGroupItem): Boolean {
        return item.enabled && selectedIds.contains(item.id)
    }
}

@Serializable
data class PresetGroupItem(
    val id: String,
    val title: String,
    val content: String = "",
    val enabled: Boolean = true,
    val order: Int = 0,
    val placement: String? = null,
    val role: String? = null,
    val depth: Int? = null,
    val kind: String? = null,
    val strength: String? = null,
    val required: Boolean? = null,
    @SerialName("tokenBudget")
    val tokenBudget: Int? = null,
    @SerialName("activation_tags")
    val activationTags: List<String> = emptyList()
) {
    fun metaLabel(): String = segmentMetaLabel(placement, role, depth, kind)
}

private fun PresetBlock.toPromptSegment(id: String, content: String, defaultOrder: Int): PromptSegment {
    return PromptSegment(
        id = id,
        title = title,
        content = content,
        role = normalizePresetRole(role),
        placement = normalizePresetPlacement(placement, "before_history"),
        order = order.takeIf { it > 0 } ?: defaultOrder,
        depth = normalizePresetDepth(depth),
        kind = normalizePresetKind(kind, "style"),
        strength = normalizePresetStrength(strength),
        required = required ?: false,
        tokenBudget = tokenBudget?.takeIf { it > 0 },
        activationTags = activationTags
    )
}

private fun PresetGroupItem.toPromptSegment(
    id: String,
    title: String,
    content: String,
    defaultOrder: Int
): PromptSegment {
    return PromptSegment(
        id = id,
        title = title,
        content = content,
        role = normalizePresetRole(role),
        placement = normalizePresetPlacement(placement, "before_history"),
        order = order.takeIf { it > 0 } ?: defaultOrder,
        depth = normalizePresetDepth(depth),
        kind = normalizePresetKind(kind, "style"),
        strength = normalizePresetStrength(strength),
        required = required ?: false,
        tokenBudget = tokenBudget?.takeIf { it > 0 },
        activationTags = activationTags
    )
}

private fun normalizePresetPlacement(value: String?, default: String): String {
    val normalized = value?.trim().orEmpty()
    return normalized.takeIf { it in presetPlacements } ?: default
}

private fun normalizePresetRole(value: String?): String {
    return when (value?.trim()?.lowercase()) {
        "ai", "model" -> "assistant"
        "assistant", "user", "system" -> value.trim().lowercase()
        else -> "system"
    }
}

private fun normalizePresetDepth(value: Int?): Int {
    return (value ?: 0).coerceIn(0, 999)
}

private fun normalizePresetKind(value: String?, default: String): String {
    val normalized = value?.trim().orEmpty()
    return normalized.takeIf { it in presetKinds } ?: default
}

private fun normalizePresetStrength(value: String?): String {
    val normalized = value?.trim().orEmpty()
    return normalized.takeIf { it in presetStrengths } ?: "soft"
}

private fun segmentMetaLabel(placement: String?, role: String?, depth: Int?, kind: String?): String {
    val parts = mutableListOf<String>()
    parts += normalizePresetPlacement(placement, "before_history")
    parts += normalizePresetRole(role)
    if (normalizePresetPlacement(placement, "before_history") == "at_depth") {
        parts += "d${normalizePresetDepth(depth)}"
    }
    normalizePresetKind(kind, "").takeIf { it.isNotBlank() }?.let { parts += it }
    return parts.joinToString(" · ")
}

private val presetPlacements = setOf(
    "system_core",
    "system_format",
    "before_character",
    "character",
    "after_character",
    "lore_context",
    "memory_context",
    "before_history",
    "at_depth",
    "near_latest_user",
    "output_guard"
)

private val presetKinds = setOf(
    "base",
    "creator_persona",
    "thinking_protocol",
    "format",
    "html_protocol",
    "output_rule",
    "output_guard",
    "style",
    "tone",
    "plot",
    "dialogue",
    "scene",
    "relationship",
    "character_policy",
    "lore_policy",
    "reference",
    "memory",
    "director_note",
    "mod"
)

private val presetStrengths = setOf("hard", "soft")
