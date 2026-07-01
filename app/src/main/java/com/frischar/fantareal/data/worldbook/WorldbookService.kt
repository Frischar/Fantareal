package com.frischar.fantareal.data.worldbook

import com.frischar.fantareal.core.AppJson
import com.frischar.fantareal.domain.worldbook.WorldbookEntry
import com.frischar.fantareal.domain.worldbook.TriggerMode
import com.frischar.fantareal.domain.worldbook.TriggerLogic
import com.frischar.fantareal.domain.worldbook.InjectionPosition
import kotlinx.serialization.json.*
import java.util.UUID

class WorldbookService {

    fun parseTavernWorldbook(jsonText: String): List<WorldbookEntry> {
        val root = try {
            AppJson.parseToJsonElement(jsonText)
        } catch (e: Exception) {
            return emptyList()
        }

        val entriesElement = when (root) {
            is JsonArray -> root
            is JsonObject -> root["entries"]
                ?: root["items"]
                ?: (root["worldbook"] as? JsonObject)?.get("entries")
                ?: ((root["data"] as? JsonObject)?.get("character_book") as? JsonObject)?.get("entries")
            else -> null
        }
            ?: return emptyList()

        val parsedEntries = mutableListOf<WorldbookEntry>()

        if (entriesElement is JsonObject) {
            for ((_, entryEl) in entriesElement) {
                if (entryEl is JsonObject) {
                    parsedEntries.add(parseEntry(entryEl))
                }
            }
        } else if (entriesElement is JsonArray) {
            for (entryEl in entriesElement) {
                if (entryEl is JsonObject) {
                    parsedEntries.add(parseEntry(entryEl))
                }
            }
        }

        return parsedEntries.filter { it.content.isNotBlank() && (it.constant || it.primaryTriggers.isNotEmpty()) }
    }

    private fun parseEntry(obj: JsonObject): WorldbookEntry {
        val uid = obj.stringValue("uid", "id")
            .takeIf { it.isNotBlank() }
            ?: UUID.randomUUID().toString()
            
        val comment = obj.stringValue("comment", "title")
            
        val content = obj.stringValue("content")
        
        val entryType = obj.stringValue("entry_type", "entryType")
        val constant = obj.booleanValue("constant")
            ?: entryType.equals("constant", ignoreCase = true)
        
        val primaryTriggers = triggerList(obj["key"] ?: obj["keys"] ?: obj["trigger"] ?: obj["primaryTriggers"] ?: obj["primary_triggers"])
        val secondaryTriggers = triggerList(
            obj["keysecondary"] ?: obj["secondary_keys"] ?: obj["secondary_trigger"] ?: obj["secondaryTriggers"] ?: obj["secondary_triggers"]
        )

        val posStr = obj.stringValue("insertion_position", "insertionPosition")
        val posInt = (obj["position"] as? JsonPrimitive)?.intOrNull
        val insertionPosition = when {
            posStr.contains("before_char", ignoreCase = true) || posStr.contains("before_persona", ignoreCase = true) -> InjectionPosition.BeforePersona
            posStr.contains("after_char", ignoreCase = true) || posStr.contains("after_system", ignoreCase = true) -> InjectionPosition.RecentChat
            posStr.contains("in_chat", ignoreCase = true) -> InjectionPosition.RecentChat
            posStr.contains("before_author", ignoreCase = true) || posStr.contains("before_reply", ignoreCase = true) || posStr.contains("bottom", ignoreCase = true) -> InjectionPosition.BeforeReply
            posInt == 0 -> InjectionPosition.BeforePersona // typically "before char"
            posInt == 1 -> InjectionPosition.RecentChat    // typically "after char / in chat"
            posInt == 2 -> InjectionPosition.BeforeReply   // typically "bottom / before author note"
            else -> InjectionPosition.RecentChat
        }

        val matchMode = obj.stringValue("match_mode", "matchMode")
        val secondaryMode = obj.stringValue("secondary_mode", "secondaryMode", "group_operator", "groupOperator")
        val triggerMode = if (matchMode.contains("regex", ignoreCase = true)) TriggerMode.Regex else TriggerMode.Literal
        val primaryLogic = if (matchMode.equals("all", ignoreCase = true)) TriggerLogic.All else TriggerLogic.Any
        val secondaryLogic = when {
            secondaryMode.equals("all", ignoreCase = true) -> TriggerLogic.All
            secondaryMode.equals("and", ignoreCase = true) -> TriggerLogic.All
            else -> TriggerLogic.Any
        }

        val enabled = obj.booleanValue("enabled") ?: true
        val chance = normalizeChance((obj["chance"] as? JsonPrimitive)?.doubleOrNull ?: 1.0)

        return WorldbookEntry(
            id = uid,
            title = comment.ifBlank { "Imported Entry" },
            content = content,
            enabled = enabled,
            constant = constant,
            primaryTriggers = primaryTriggers,
            primaryLogic = primaryLogic,
            secondaryTriggers = secondaryTriggers,
            secondaryLogic = secondaryLogic,
            triggerMode = triggerMode,
            caseSensitive = obj.booleanValue("case_sensitive", "caseSensitive") ?: false,
            wholeWord = obj.booleanValue("whole_word", "wholeWord") ?: false,
            chance = chance,
            stickyTurns = obj.intValue("sticky_turns", "stickyTurns"),
            cooldownTurns = obj.intValue("cooldown_turns", "cooldownTurns"),
            insertionPosition = insertionPosition,
            priority = obj.intValue("priority", "order", "injection_order", "injectionOrder")
        )
    }

    fun exportToJson(entries: List<WorldbookEntry>): String {
        val jsonEntries = buildJsonObject {
            entries.forEachIndexed { index, entry ->
                put(index.toString(), buildJsonObject {
                    put("uid", entry.id)
                    put("key", buildJsonArray { entry.primaryTriggers.forEach { add(it) } })
                    put("keysecondary", buildJsonArray { entry.secondaryTriggers.forEach { add(it) } })
                    put("comment", entry.title)
                    put("content", entry.content)
                    put("constant", entry.constant)
                    put("chance", entry.chance)
                    put("sticky_turns", entry.stickyTurns)
                    put("cooldown_turns", entry.cooldownTurns)
                    put("case_sensitive", entry.caseSensitive)
                    put("whole_word", entry.wholeWord)
                    put("match_mode", if (entry.triggerMode == TriggerMode.Regex) "regex" else if (entry.primaryLogic == TriggerLogic.All) "all" else "any")
                    put("secondary_mode", if (entry.secondaryLogic == TriggerLogic.All) "all" else "any")
                    put("priority", entry.priority)
                    val posInt = when (entry.insertionPosition) {
                        InjectionPosition.BeforePersona -> 0
                        InjectionPosition.RecentChat -> 1
                        InjectionPosition.BeforeReply -> 2
                    }
                    put("position", posInt)
                })
            }
        }

        val root = buildJsonObject {
            put("entries", jsonEntries)
        }

        return root.toString()
    }

    private fun triggerList(element: JsonElement?): List<String> {
        return when (element) {
            is JsonArray -> element.flatMap { triggerList(it) }
            is JsonPrimitive -> element.contentOrNull
                ?.split(",", "，", "、", "|", "\n")
                ?.map { it.trim() }
                ?.filter { it.isNotBlank() }
                .orEmpty()
            else -> emptyList()
        }
    }

    private fun normalizeChance(raw: Double): Double {
        return if (raw > 1.0) (raw / 100.0).coerceIn(0.0, 1.0) else raw.coerceIn(0.0, 1.0)
    }

    private fun JsonObject.stringValue(vararg keys: String): String {
        return keys.firstNotNullOfOrNull { key ->
            (this[key] as? JsonPrimitive)?.contentOrNull?.trim()?.takeIf { it.isNotBlank() }
        }.orEmpty()
    }

    private fun JsonObject.booleanValue(vararg keys: String): Boolean? {
        return keys.firstNotNullOfOrNull { key ->
            (this[key] as? JsonPrimitive)?.booleanOrNull
        }
    }

    private fun JsonObject.intValue(vararg keys: String): Int {
        return keys.firstNotNullOfOrNull { key ->
            (this[key] as? JsonPrimitive)?.intOrNull
        } ?: 0
    }
}
