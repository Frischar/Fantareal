package com.frischar.fantareal.data.preset

import com.frischar.fantareal.core.AppJson
import com.frischar.fantareal.domain.preset.PresetBlock
import com.frischar.fantareal.domain.preset.PresetGroup
import com.frischar.fantareal.domain.preset.PresetGroupItem
import com.frischar.fantareal.domain.preset.PresetModule
import com.frischar.fantareal.domain.preset.PromptPreset
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonObjectBuilder
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonArray
import kotlinx.serialization.json.putJsonObject
import java.util.UUID

class PresetService {

    fun parsePresets(jsonText: String): List<PromptPreset> {
        val root = try {
            AppJson.parseToJsonElement(jsonText)
        } catch (_: Exception) {
            return emptyList()
        }

        val presets = collectPresetObjects(root)
            .mapNotNull(::parsePresetObject)
            .distinctBy { it.id }
            .filter { it.runtimeContent().isNotBlank() || it.hasStructuredContent() }
        val activePresetId = (root as? JsonObject)
            ?.get("active_preset_id")
            ?.let { it as? JsonPrimitive }
            ?.contentOrNull
            ?.trim()
            .orEmpty()
        return if (activePresetId.isNotBlank() && presets.any { it.id == activePresetId }) {
            presets.map { it.copy(enabled = it.id == activePresetId) }
        } else {
            presets
        }
    }

    fun exportToJson(presets: List<PromptPreset>): String {
        val activeId = presets.firstOrNull { it.enabled }?.id ?: presets.firstOrNull()?.id.orEmpty()
        return buildJsonObject {
            put("active_preset_id", activeId)
            putJsonArray("presets") {
                presets.forEach { preset ->
                    add(buildJsonObject {
                        put("id", preset.id)
                        put("name", preset.title)
                        put("title", preset.title)
                        put("enabled", preset.enabled)
                        put("content", preset.runtimeContent())
                        if (preset.hasStructuredContent()) {
                            put("base_system_prompt", preset.baseSystemPrompt)
                            putJsonObject("modules") {
                                preset.modules.forEach { module ->
                                    put(module.key, module.enabled)
                                }
                            }
                            putJsonArray("extra_prompts") {
                                preset.extraPrompts.forEach { block ->
                                    add(buildJsonObject {
                                        put("id", block.id)
                                        put("name", block.title)
                                        put("title", block.title)
                                        put("enabled", block.enabled)
                                        put("content", block.content)
                                        put("order", block.order)
                                        putSegmentFields(
                                            placement = block.placement,
                                            role = block.role,
                                            depth = block.depth,
                                            kind = block.kind,
                                            strength = block.strength,
                                            required = block.required,
                                            tokenBudget = block.tokenBudget,
                                            activationTags = block.activationTags
                                        )
                                    })
                                }
                            }
                            putJsonArray("prompt_groups") {
                                preset.promptGroups.forEach { group ->
                                    add(buildJsonObject {
                                        put("id", group.id)
                                        put("name", group.title)
                                        put("title", group.title)
                                        put("enabled", group.enabled)
                                        put("selection_mode", group.selectionMode)
                                        putJsonArray("selected_ids") {
                                            group.selectedIds.forEach { add(JsonPrimitive(it)) }
                                        }
                                        put("order", group.order)
                                        putJsonArray("items") {
                                            group.items.forEach { item ->
                                                add(buildJsonObject {
                                                    put("id", item.id)
                                                    put("name", item.title)
                                                    put("title", item.title)
                                                    put("enabled", item.enabled)
                                                    put("content", item.content)
                                                    put("order", item.order)
                                                    putSegmentFields(
                                                        placement = item.placement,
                                                        role = item.role,
                                                        depth = item.depth,
                                                        kind = item.kind,
                                                        strength = item.strength,
                                                        required = item.required,
                                                        tokenBudget = item.tokenBudget,
                                                        activationTags = item.activationTags
                                                    )
                                                })
                                            }
                                        }
                                    })
                                }
                            }
                        }
                    })
                }
            }
        }.toString()
    }

    private fun collectPresetObjects(element: JsonElement): List<JsonObject> {
        val results = mutableListOf<JsonObject>()
        collectPresetObjects(element, results)
        return results
    }

    private fun collectPresetObjects(element: JsonElement, results: MutableList<JsonObject>) {
        when (element) {
            is JsonArray -> element.forEach { collectPresetObjects(it, results) }
            is JsonObject -> {
                val presetArray = element["presets"] as? JsonArray
                if (presetArray != null) {
                    presetArray.forEach { collectPresetObjects(it, results) }
                    return
                }

                if (looksLikePreset(element)) {
                    results += element
                    return
                }

                element.forEach { (key, child) ->
                    if (key in INTERNAL_PRESET_KEYS) return@forEach
                    if (child is JsonObject || child is JsonArray) {
                        collectPresetObjects(child, results)
                    }
                }
            }
            else -> Unit
        }
    }

    private fun looksLikePreset(element: JsonObject): Boolean {
        if (element.containsKey("base_system_prompt") ||
            element.containsKey("baseSystemPrompt") ||
            element.containsKey("modules") ||
            element.containsKey("extra_prompts") ||
            element.containsKey("prompt_groups")
        ) {
            return true
        }

        val hasPromptText = element.stringField("content").isNotBlank() ||
            element.stringField("prompt").isNotBlank()
        val hasPresetIdentity = element.containsKey("id") ||
            element.containsKey("title") ||
            element.containsKey("name") ||
            element.containsKey("enabled")
        return hasPromptText && hasPresetIdentity
    }

    private fun parsePresetObject(element: JsonObject): PromptPreset? {
        val flatContent = firstText(element, "content", "prompt")
        val basePrompt = firstText(element, "base_system_prompt", "baseSystemPrompt")
        val preset = PromptPreset(
            id = element.stringField("id").ifBlank { UUID.randomUUID().toString() },
            title = firstText(element, "title", "name").ifBlank { "Imported Preset" },
            content = flatContent,
            enabled = element.booleanField("enabled", true),
            baseSystemPrompt = basePrompt,
            modules = parseModules(element["modules"]),
            extraPrompts = parseBlocks(element["extra_prompts"] ?: element["blocks"]),
            promptGroups = parseGroups(element["prompt_groups"] ?: element["groups"])
        )
        val content = if (preset.hasStructuredContent()) {
            preset.runtimeContent().ifBlank { flatContent }
        } else {
            flatContent
        }
        return preset.copy(content = content)
    }

    private fun parseModules(element: JsonElement?): List<PresetModule> {
        if (element == null) return emptyList()
        if (element is JsonArray) {
            return applyModuleMutex(
                element.mapIndexedNotNull { index, item ->
                    val obj = item as? JsonObject ?: return@mapIndexedNotNull null
                    val key = obj.stringField("key").ifBlank { return@mapIndexedNotNull null }
                    PresetModule(
                        key = key,
                        title = firstText(obj, "title", "name").ifBlank { moduleLabel(key) },
                        content = obj.stringField("content").ifBlank { modulePrompt(key) },
                        enabled = obj.booleanField("enabled", false),
                        order = obj.intField("order", moduleOrder(key, index))
                    )
                }
            )
        }

        val obj = element as? JsonObject ?: return emptyList()
        val drafts = mutableMapOf<String, ModuleDraft>()
        obj.forEach { (key, value) ->
            val valueObject = value as? JsonObject
            drafts[key] = ModuleDraft(
                enabled = valueObject?.booleanField("enabled", false) ?: value.booleanValue(default = false),
                title = valueObject?.let { firstText(it, "title", "name") }.orEmpty(),
                content = valueObject?.stringField("content").orEmpty(),
                order = valueObject?.intField("order", moduleOrder(key, drafts.size)) ?: moduleOrder(key, drafts.size)
            )
        }

        val keys = (DEFAULT_PRESET_MODULES.keys + drafts.keys).distinct()
        return applyModuleMutex(
            keys.mapIndexed { index, key ->
                val draft = drafts[key]
                PresetModule(
                    key = key,
                    title = draft?.title?.takeIf { it.isNotBlank() } ?: moduleLabel(key),
                    content = draft?.content?.takeIf { it.isNotBlank() } ?: modulePrompt(key),
                    enabled = draft?.enabled ?: false,
                    order = draft?.order ?: moduleOrder(key, index)
                )
            }
        )
    }

    private fun parseBlocks(element: JsonElement?): List<PresetBlock> {
        val array = element as? JsonArray ?: return emptyList()
        return array.mapIndexedNotNull { index, item ->
            val obj = item as? JsonObject ?: return@mapIndexedNotNull null
            PresetBlock(
                id = obj.stringField("id").ifBlank { "preset-block-${index + 1}" },
                title = firstText(obj, "title", "name").ifBlank { "规则块 ${index + 1}" },
                content = obj.stringField("content").trim(),
                enabled = obj.booleanField("enabled", true),
                order = obj.intField("order", (index + 1) * 100),
                placement = obj.optionalStringField("placement"),
                role = obj.optionalStringField("role"),
                depth = obj.optionalIntField("depth"),
                kind = obj.optionalStringField("kind"),
                strength = obj.optionalStringField("strength"),
                required = obj.optionalBooleanField("required"),
                tokenBudget = obj.optionalIntField("tokenBudget"),
                activationTags = obj.stringListField("activation_tags")
            )
        }
    }

    private fun parseGroups(element: JsonElement?): List<PresetGroup> {
        val array = element as? JsonArray ?: return emptyList()
        return array.mapIndexedNotNull { groupIndex, item ->
            val obj = item as? JsonObject ?: return@mapIndexedNotNull null
            val items = parseGroupItems(obj["items"])
            val validIds = items.map { it.id }.toSet()
            val selectedIds = parseSelectedIds(obj["selected_ids"], validIds).ifEmpty {
                parseSelectedIdsFromItems(obj["items"], items)
            }.let { ids ->
                if (normalizeSelectionMode(obj.stringField("selection_mode")) == "single") ids.take(1) else ids
            }

            PresetGroup(
                id = obj.stringField("id").ifBlank { "preset-group-${groupIndex + 1}" },
                title = firstText(obj, "title", "name").ifBlank { "规则组 ${groupIndex + 1}" },
                enabled = obj.booleanField("enabled", true),
                selectionMode = normalizeSelectionMode(obj.stringField("selection_mode")),
                selectedIds = selectedIds,
                items = items,
                order = obj.intField("order", (groupIndex + 1) * 100)
            )
        }
    }

    private fun parseGroupItems(element: JsonElement?): List<PresetGroupItem> {
        val array = element as? JsonArray ?: return emptyList()
        return array.mapIndexedNotNull { index, item ->
            val obj = item as? JsonObject ?: return@mapIndexedNotNull null
            PresetGroupItem(
                id = obj.stringField("id").ifBlank { "preset-group-item-${index + 1}" },
                title = firstText(obj, "title", "name").ifBlank { "规则项 ${index + 1}" },
                content = obj.stringField("content").trim(),
                enabled = obj.booleanField("enabled", true),
                order = obj.intField("order", index),
                placement = obj.optionalStringField("placement"),
                role = obj.optionalStringField("role"),
                depth = obj.optionalIntField("depth"),
                kind = obj.optionalStringField("kind"),
                strength = obj.optionalStringField("strength"),
                required = obj.optionalBooleanField("required"),
                tokenBudget = obj.optionalIntField("tokenBudget"),
                activationTags = obj.stringListField("activation_tags")
            )
        }
    }

    private fun parseSelectedIds(element: JsonElement?, validIds: Set<String>): List<String> {
        val array = element as? JsonArray ?: return emptyList()
        return array.mapNotNull { selected ->
            selected.stringValue().takeIf { it in validIds }
        }.distinct()
    }

    private fun parseSelectedIdsFromItems(element: JsonElement?, items: List<PresetGroupItem>): List<String> {
        val array = element as? JsonArray ?: return emptyList()
        return array.mapIndexedNotNull { index, item ->
            val obj = item as? JsonObject ?: return@mapIndexedNotNull null
            val selected = obj.booleanField("selected", false) || obj.booleanField("checked", false)
            if (selected) items.getOrNull(index)?.id else null
        }.distinct()
    }

    private fun applyModuleMutex(modules: List<PresetModule>): List<PresetModule> {
        var result = modules
        PRESET_MODULE_MUTEX.forEach { (key, opposites) ->
            if (result.any { it.key == key && it.enabled }) {
                result = result.map { module ->
                    if (module.key in opposites) module.copy(enabled = false) else module
                }
            }
        }
        return result
    }

    private fun normalizeSelectionMode(value: String): String {
        val normalized = value.trim().lowercase()
        return if (normalized in setOf("multi", "multiple", "checkbox", "checkboxes")) "multiple" else "single"
    }

    private fun moduleLabel(key: String): String {
        return PRESET_MODULE_LABELS[key] ?: key
    }

    private fun modulePrompt(key: String): String {
        return PRESET_MODULE_PROMPTS[key].orEmpty()
    }

    private fun moduleOrder(key: String, fallbackIndex: Int): Int {
        return DEFAULT_PRESET_MODULES.keys.indexOf(key).takeIf { it >= 0 } ?: fallbackIndex
    }

    private fun firstText(element: JsonObject, vararg keys: String): String {
        return keys.firstNotNullOfOrNull { key ->
            element.stringField(key).trim().takeIf { it.isNotBlank() }
        }.orEmpty()
    }

    private fun JsonObject.stringField(key: String): String {
        return (this[key] as? JsonPrimitive)?.contentOrNull.orEmpty()
    }

    private fun JsonObject.optionalStringField(key: String): String? {
        return stringField(key).trim().takeIf { it.isNotBlank() }
    }

    private fun JsonObject.booleanField(key: String, default: Boolean): Boolean {
        return this[key].booleanValue(default)
    }

    private fun JsonObject.optionalBooleanField(key: String): Boolean? {
        return (this[key] as? JsonPrimitive)?.booleanOrNull
    }

    private fun JsonObject.intField(key: String, default: Int): Int {
        return (this[key] as? JsonPrimitive)?.intOrNull ?: default
    }

    private fun JsonObject.optionalIntField(key: String): Int? {
        return (this[key] as? JsonPrimitive)?.intOrNull
    }

    private fun JsonObject.stringListField(key: String): List<String> {
        val array = this[key] as? JsonArray ?: return emptyList()
        return array.mapNotNull { item ->
            (item as? JsonPrimitive)?.contentOrNull?.trim()?.takeIf { it.isNotBlank() }
        }.distinct()
    }

    private fun JsonObjectBuilder.putSegmentFields(
        placement: String?,
        role: String?,
        depth: Int?,
        kind: String?,
        strength: String?,
        required: Boolean?,
        tokenBudget: Int?,
        activationTags: List<String>
    ) {
        placement?.takeIf { it.isNotBlank() }?.let { put("placement", it) }
        role?.takeIf { it.isNotBlank() }?.let { put("role", it) }
        depth?.let { put("depth", it.coerceIn(0, 999)) }
        kind?.takeIf { it.isNotBlank() }?.let { put("kind", it) }
        strength?.takeIf { it.isNotBlank() }?.let { put("strength", it) }
        required?.let { put("required", it) }
        tokenBudget?.takeIf { it > 0 }?.let { put("tokenBudget", it) }
        if (activationTags.isNotEmpty()) {
            putJsonArray("activation_tags") {
                activationTags.forEach { add(JsonPrimitive(it)) }
            }
        }
    }

    private fun JsonElement?.booleanValue(default: Boolean): Boolean {
        val primitive = this as? JsonPrimitive ?: return default
        primitive.booleanOrNull?.let { return it }
        return primitive.contentOrNull?.trim()?.lowercase()?.let { value ->
            value in setOf("1", "true", "yes", "on")
        } ?: default
    }

    private fun JsonElement?.stringValue(): String {
        return (this as? JsonPrimitive)?.contentOrNull?.trim().orEmpty()
    }

    private data class ModuleDraft(
        val enabled: Boolean,
        val title: String,
        val content: String,
        val order: Int
    )

    companion object {
        private val INTERNAL_PRESET_KEYS = setOf("modules", "extra_prompts", "prompt_groups", "items")

        val DEFAULT_PRESET_MODULES = linkedMapOf(
            "no_user_speaking" to true,
            "short_paragraph" to false,
            "long_paragraph" to false,
            "second_person" to false,
            "third_person" to false,
            "anti_repeat" to true,
            "no_closing_feel" to true,
            "emotion_detail" to true,
            "multi_character_boundary" to true,
            "scene_continuation" to true,
            "anti_horny" to false,
            "anti_deification" to false,
            "v4f_output_guard" to false
        )

        private val PRESET_MODULE_MUTEX = mapOf(
            "short_paragraph" to listOf("long_paragraph"),
            "long_paragraph" to listOf("short_paragraph"),
            "second_person" to listOf("third_person"),
            "third_person" to listOf("second_person")
        )

        private val PRESET_MODULE_LABELS = mapOf(
            "no_user_speaking" to "防抢话",
            "short_paragraph" to "短段落",
            "long_paragraph" to "长段落",
            "second_person" to "第二人称",
            "third_person" to "第三人称",
            "anti_repeat" to "抗重复",
            "no_closing_feel" to "弱收尾",
            "emotion_detail" to "情绪细节",
            "multi_character_boundary" to "多角色边界",
            "scene_continuation" to "场景延续",
            "anti_horny" to "抗发情",
            "anti_deification" to "抗神化",
            "v4f_output_guard" to "V4F 稳定器"
        )

        private val PRESET_MODULE_PROMPTS = mapOf(
            "no_user_speaking" to "Strictly do not write actions, dialogue, decisions, emotions, or thoughts on behalf of the user. Only describe non-user characters, the environment, and scene changes unless the user explicitly asks otherwise.",
            "short_paragraph" to "Keep natural paragraphs short, usually one or two sentences. Put dialogue in separate paragraphs and avoid dense walls of text.",
            "long_paragraph" to "Use fuller paragraphs that combine action, observation, response, and continuation. Do not fragment every sentence into separate short lines.",
            "second_person" to "When referring to the user, use second person.",
            "third_person" to "When referring to the user, avoid second person and use third-person description instead.",
            "anti_repeat" to "Avoid repeating sentence patterns, scene beats, wording, and endings that have already appeared frequently.",
            "no_closing_feel" to "Do not end with a summary, moral, curtain-call, or strong closing beat. Leave the reply in an ongoing moment.",
            "emotion_detail" to "Prefer observable emotional details from non-user characters, such as gaze, pauses, breath, hand movement, distance, and changes in tone. Avoid replacing description with blunt emotion labels.",
            "multi_character_boundary" to "When multiple characters are present, keep each character's personality, voice, stance, and reactions distinct. Do not mix one character's thoughts, lines, or actions into another.",
            "scene_continuation" to "Continue from the previous turn's actions, emotions, space, and scene state. Do not abruptly reset time, place, relationship stage, or plot direction unless the user clearly changes them.",
            "anti_horny" to "Keep intimate or desire-driven escalation gated by character logic, trust, relationship stage, and scene necessity. Do not force sensual escalation when it does not fit the current moment.",
            "anti_deification" to "Treat the world and NPCs as autonomous. Events, consequences, resources, distance, pain, fatigue, and other characters should follow their own internal logic instead of orbiting the user.",
            "v4f_output_guard" to "Before each reply, apply a near-turn stability guard: obey current character, preset, lore, memory, and output-format constraints; do not explain rules; do not take over the user's actions, speech, thoughts, decisions, emotions, or physical reactions; keep the ending open for continued interaction."
        )
    }
}
