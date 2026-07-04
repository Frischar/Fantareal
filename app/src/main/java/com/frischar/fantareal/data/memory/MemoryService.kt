package com.frischar.fantareal.data.memory

import com.frischar.fantareal.core.AppJson
import com.frischar.fantareal.domain.memory.LongTermMemory
import java.util.UUID
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.add
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.put

class MemoryService {
    fun parseMemories(jsonText: String): List<LongTermMemory> {
        val root = try {
            AppJson.parseToJsonElement(jsonText)
        } catch (e: Exception) {
            return emptyList()
        }

        val parsed = mutableListOf<LongTermMemory>()

        if (root is JsonArray) {
            for (element in root) {
                if (element is JsonObject) {
                    parseMemory(element)?.let(parsed::add)
                }
            }
        } else if (root is JsonObject) {
            val items = root["items"]
            if (items is JsonArray) {
                for (element in items) {
                    if (element is JsonObject) {
                        parseMemory(element)?.let(parsed::add)
                    }
                }
            } else if (root.containsKey("data") && root["data"] is JsonObject) {
                val dataObject = root["data"] as? JsonObject
                val mesExample = (dataObject?.get("mes_example") as? JsonPrimitive)?.contentOrNull
                if (!mesExample.isNullOrBlank()) {
                    parsed.add(
                        LongTermMemory(
                            id = UUID.randomUUID().toString(),
                            title = "\u793a\u4f8b\u5bf9\u8bdd",
                            text = mesExample,
                            tags = listOf("mes_example"),
                            createdAt = System.currentTimeMillis()
                        )
                    )
                }
            } else {
                parseMemory(root)?.let(parsed::add)
            }
        }

        return parsed
    }

    private fun parseMemory(obj: JsonObject): LongTermMemory? {
        val id = (obj["id"] as? JsonPrimitive)?.contentOrNull ?: UUID.randomUUID().toString()
        val title = (obj["title"] as? JsonPrimitive)?.contentOrNull?.trim().orEmpty()
        val content = (obj["content"] as? JsonPrimitive)?.contentOrNull
            ?: (obj["text"] as? JsonPrimitive)?.contentOrNull
            ?: ""
        val notes = (obj["notes"] as? JsonPrimitive)?.contentOrNull?.trim().orEmpty()
        val tags = parseTags(obj["tags"])

        if (content.isBlank() && title.isBlank() && notes.isBlank()) return null

        return LongTermMemory(
            id = id,
            title = title,
            text = content.trim().ifBlank { notes.ifBlank { title } },
            notes = notes,
            tags = tags,
            createdAt = System.currentTimeMillis()
        )
    }

    private fun parseTags(value: JsonElement?): List<String> {
        return when (value) {
            is JsonArray -> value.mapNotNull { item ->
                (item as? JsonPrimitive)?.contentOrNull?.trim()?.takeIf { it.isNotBlank() }
            }
            is JsonPrimitive -> value.contentOrNull
                ?.split(",", "\uFF0C", "\u3001", "|")
                ?.map { it.trim() }
                ?.filter { it.isNotBlank() }
                .orEmpty()
            else -> emptyList()
        }
    }

    fun exportToJson(memories: List<LongTermMemory>): String {
        val jsonArray = buildJsonArray {
            memories.forEach { memory ->
                add(
                    buildJsonObject {
                        put("id", memory.id)
                        put("title", memory.title)
                        put("content", memory.text)
                        put("notes", memory.notes)
                        put("tags", buildJsonArray { memory.tags.forEach { add(it) } })
                    }
                )
            }
        }
        val root = buildJsonObject {
            put("items", jsonArray)
        }
        return root.toString()
    }
}
