package com.frischar.fantareal.data.memory

import com.frischar.fantareal.core.AppJson
import com.frischar.fantareal.domain.memory.LongTermMemory
import kotlinx.serialization.json.*
import java.util.UUID

class MemoryService {
    fun parseMemories(jsonText: String): List<LongTermMemory> {
        val root = try {
            AppJson.parseToJsonElement(jsonText)
        } catch (e: Exception) {
            return emptyList()
        }

        val parsed = mutableListOf<LongTermMemory>()

        if (root is JsonArray) {
            for (el in root) {
                if (el is JsonObject) {
                    parseMemory(el)?.let(parsed::add)
                }
            }
        } else if (root is JsonObject) {
            val itemsArr = root["items"]
            if (itemsArr is JsonArray) {
                for (el in itemsArr) {
                    if (el is JsonObject) {
                        parseMemory(el)?.let(parsed::add)
                    }
                }
            } else if (root.containsKey("data") && root["data"] is JsonObject) {
                val dataObj = root["data"] as? JsonObject
                val mesExample = (dataObj?.get("mes_example") as? JsonPrimitive)?.contentOrNull
                if (!mesExample.isNullOrBlank()) {
                    parsed.add(LongTermMemory(
                        id = UUID.randomUUID().toString(),
                        text = mesExample,
                        tags = listOf("mes_example"),
                        createdAt = System.currentTimeMillis()
                    ))
                }
            } else {
                parseMemory(root)?.let(parsed::add)
            }
        }

        return parsed
    }

    private fun parseMemory(obj: JsonObject): LongTermMemory? {
        val id = (obj["id"] as? JsonPrimitive)?.contentOrNull ?: UUID.randomUUID().toString()
        val title = (obj["title"] as? JsonPrimitive)?.contentOrNull ?: ""
        val content = (obj["content"] as? JsonPrimitive)?.contentOrNull
            ?: (obj["text"] as? JsonPrimitive)?.contentOrNull
            ?: ""
        val tags = obj["tags"]?.let {
            if (it is JsonArray) {
                it.mapNotNull { t -> (t as? JsonPrimitive)?.contentOrNull?.trim()?.takeIf(String::isNotBlank) }
            } else if (it is JsonPrimitive) {
                it.contentOrNull
                    ?.split(",", "，", "、", "|")
                    ?.map { tag -> tag.trim() }
                    ?.filter { tag -> tag.isNotBlank() }
            } else null
        } ?: emptyList()
        
        // Use title + notes + content as the combined memory text
        val notes = (obj["notes"] as? JsonPrimitive)?.contentOrNull ?: ""
        val combinedContent = buildString {
            if (title.isNotBlank()) append(title).append(": ")
            append(content)
            if (notes.isNotBlank()) append(" (").append(notes).append(")")
        }
        if (combinedContent.isBlank()) return null

        return LongTermMemory(
            id = id,
            text = combinedContent,
            tags = tags,
            createdAt = System.currentTimeMillis()
        )
    }

    fun exportToJson(memories: List<LongTermMemory>): String {
        val jsonArray = buildJsonArray {
            memories.forEach { mem ->
                add(buildJsonObject {
                    put("id", mem.id)
                    put("content", mem.text)
                    put("tags", buildJsonArray { mem.tags.forEach { add(it) } })
                })
            }
        }
        val root = buildJsonObject {
            put("items", jsonArray)
        }
        return root.toString()
    }
}
