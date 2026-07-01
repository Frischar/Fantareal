package com.frischar.fantareal.data.preset

import com.frischar.fantareal.core.AppJson
import com.frischar.fantareal.domain.preset.PromptPreset
import kotlinx.serialization.json.*
import java.util.UUID

class PresetService {

    fun parsePresets(jsonText: String): List<PromptPreset> {
        val root = try {
            AppJson.parseToJsonElement(jsonText)
        } catch (e: Exception) {
            return emptyList()
        }

        val parsed = mutableListOf<PromptPreset>()
        extractPresetsRecursively(root, parsed)
        return parsed.filter { it.content.isNotBlank() }
    }

    private fun extractPresetsRecursively(element: JsonElement, results: MutableList<PromptPreset>) {
        when (element) {
            is JsonArray -> {
                for (el in element) {
                    extractPresetsRecursively(el, results)
                }
            }
            is JsonObject -> {
                val content = buildPresetContent(element)
                if (content.isNotBlank()) {
                    val id = (element["id"] as? JsonPrimitive)?.contentOrNull ?: UUID.randomUUID().toString()
                    val title = (element["title"] as? JsonPrimitive)?.contentOrNull
                        ?: (element["name"] as? JsonPrimitive)?.contentOrNull
                        ?: "Imported Preset"
                    val enabled = (element["enabled"] as? JsonPrimitive)?.booleanOrNull ?: true
                    
                    results.add(PromptPreset(id, title, content, enabled))
                }

                // Recursively check all children arrays/objects for more prompts,
                // but avoid re-extracting extra_prompts or prompt_groups since we handled them.
                for ((key, child) in element) {
                    if (key == "modules" || key == "extra_prompts" || key == "prompt_groups" || key == "items") continue
                    if (child is JsonArray || child is JsonObject) {
                        extractPresetsRecursively(child, results)
                    }
                }
            }
            else -> {}
        }
    }

    fun exportToJson(presets: List<PromptPreset>): String {
        val jsonArray = buildJsonArray {
            presets.forEach { preset ->
                add(buildJsonObject {
                    put("id", preset.id)
                    put("title", preset.title)
                    put("content", preset.content)
                    put("enabled", preset.enabled)
                })
            }
        }
        return jsonArray.toString()
    }

    private fun buildPresetContent(element: JsonObject): String {
        val sections = mutableListOf<String>()
        listOf("base_system_prompt", "content", "prompt").firstNotNullOfOrNull { key ->
            (element[key] as? JsonPrimitive)?.contentOrNull?.trim()?.takeIf { it.isNotBlank() }
        }?.let { sections += it }

        val modules = element["modules"] as? JsonObject
        modules?.forEach { (key, value) ->
            if ((value as? JsonPrimitive)?.booleanOrNull == true) {
                PRESET_MODULE_PROMPTS[key]?.let { sections += it }
            }
        }

        val extraPrompts = element["extra_prompts"] as? JsonArray
        extraPrompts?.forEach { extra ->
            val obj = extra as? JsonObject ?: return@forEach
            if (!obj.isEnabled()) return@forEach
            (obj["content"] as? JsonPrimitive)?.contentOrNull?.trim()?.takeIf { it.isNotBlank() }?.let { sections += it }
        }

        val promptGroups = element["prompt_groups"] as? JsonArray
        if (promptGroups != null) {
            for (group in promptGroups) {
                val groupObj = group as? JsonObject ?: continue
                if (!groupObj.isEnabled()) continue
                val items = groupObj["items"] as? JsonArray ?: continue
                for (item in items) {
                    val itemObj = item as? JsonObject ?: continue
                    if (!itemObj.isEnabled()) continue
                    (itemObj["content"] as? JsonPrimitive)?.contentOrNull?.trim()?.takeIf { it.isNotBlank() }?.let { sections += it }
                }
            }
        }

        return sections.joinToString("\n\n")
    }

    private fun JsonObject.isEnabled(): Boolean {
        return (this["enabled"] as? JsonPrimitive)?.booleanOrNull ?: true
    }

    companion object {
        private val PRESET_MODULE_PROMPTS = mapOf(
            "no_user_speaking" to "Strictly do not write actions, dialogue, decisions, emotions, or thoughts on behalf of the user. Only describe non-user characters, the environment, and scene changes unless the user explicitly asks otherwise.",
            "short_paragraph" to "Keep natural paragraphs short, usually one or two sentences. Put dialogue in separate paragraphs and avoid dense walls of text.",
            "long_paragraph" to "Use fuller paragraphs that combine action, observation, response, and continuation. Do not fragment every sentence into separate short lines.",
            "second_person" to "When referring to the user, use second person.",
            "third_person" to "When referring to the user, avoid second person and use third-person description instead.",
            "anti_repeat" to "Avoid repeating sentence patterns, scene beats, wording, and endings that have already appeared frequently.",
            "no_closing_feel" to "Do not end with a summary, moral, curtain-call, or strong closing beat. Leave the reply in an ongoing moment."
        )
    }
}
