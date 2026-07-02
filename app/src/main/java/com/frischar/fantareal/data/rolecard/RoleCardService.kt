package com.frischar.fantareal.data.rolecard

import com.frischar.fantareal.core.AppJson
import com.frischar.fantareal.data.repository.SlotRepository
import com.frischar.fantareal.data.storage.JsonStore
import com.frischar.fantareal.domain.memory.LongTermMemory
import com.frischar.fantareal.domain.memory.MemoryTombstone
import com.frischar.fantareal.domain.rolecard.PersonaRuntime
import com.frischar.fantareal.domain.rolecard.RoleCard
import com.frischar.fantareal.domain.rolecard.RoleCardImportResult
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.builtins.serializer
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

class RoleCardService(
    private val slotRepository: SlotRepository,
    private val jsonStore: JsonStore = JsonStore()
) {
    suspend fun loadCurrentRoleCard(): RoleCard? {
        val file = slotRepository.paths.currentRoleCardFile(slotRepository.currentSlotId.value)
        if (!file.exists()) return null

        return jsonStore.read(
            file,
            RoleCard.serializer(),
            defaultValue = RoleCard()
        ).takeIf { it.name.isNotBlank() || it.description.isNotBlank() }
    }

    suspend fun importFromJson(jsonText: String, clearMemories: Boolean = false): RoleCardImportResult {
        val card = parseJson(jsonText)
        require(card.hasImportableContent()) { "未识别到可导入的角色卡" }
        return persist(card, jsonText, clearMemories)
    }

    suspend fun importFromBytes(fileName: String, bytes: ByteArray, clearMemories: Boolean = false): RoleCardImportResult {
        val hasPngSignature = bytes.size > PNG_SIGNATURE.size &&
            bytes.take(PNG_SIGNATURE.size).toByteArray().contentEquals(PNG_SIGNATURE)
        val isPng = fileName.endsWith(".png", ignoreCase = true) || hasPngSignature
        val jsonText = if (isPng) {
            extractTavernPngJson(bytes)
        } else {
            bytes.toString(Charsets.UTF_8).removePrefix("\uFEFF")
        }
        return importFromJson(jsonText, clearMemories)
    }

    fun parseJson(jsonText: String): RoleCard {
        return parseRoleCardJson(jsonText)
    }

    fun toPersonaRuntime(card: RoleCard): PersonaRuntime {
        val prompt = buildList {
            addIfNotBlank("Name", card.name)
            addIfNotBlank("Description", card.description)
            addIfNotBlank("Personality", card.personality)
            addIfNotBlank("Scenario", card.scenario)
            addIfNotBlank("Example Dialogue", card.mesExample)
            addIfNotBlank("Creator Notes", card.creatorNotes)
            addIfNotBlank("Plot Stages", formatPlotStages(card.plotStages))
            addIfNotBlank("Character Cast", formatPersonas(card.personas))
        }.joinToString("\n\n")

        return PersonaRuntime(
            name = card.name,
            systemPrompt = prompt,
            greeting = card.firstMes
        )
    }

    suspend fun getRawRoleCard(): String? {
        val file = slotRepository.paths.rawRoleCardFile(slotRepository.currentSlotId.value)
        if (file.exists()) {
            return file.readText(Charsets.UTF_8)
        }
        val card = loadCurrentRoleCard() ?: return null
        return AppJson.encodeToString(RoleCard.serializer(), card)
    }

    private suspend fun persist(card: RoleCard, rawJson: String, clearMemories: Boolean): RoleCardImportResult {
        val slotId = slotRepository.currentSlotId.value
        val persona = toPersonaRuntime(card)

        jsonStore.write(slotRepository.paths.currentRoleCardFile(slotId), RoleCard.serializer(), card)
        jsonStore.write(slotRepository.paths.personaFile(slotId), PersonaRuntime.serializer(), persona)
        slotRepository.paths.rawRoleCardFile(slotId).writeText(rawJson, Charsets.UTF_8)

        if (clearMemories) {
            jsonStore.write(slotRepository.paths.memoriesFile(slotId), ListSerializer(LongTermMemory.serializer()), emptyList())
            jsonStore.write(slotRepository.paths.tombstonesFile(slotId), ListSerializer(MemoryTombstone.serializer()), emptyList())
        }

        return RoleCardImportResult(card, persona, clearMemories)
    }

    fun extractTavernPngJson(bytes: ByteArray): String {
        return PngUtils.extractTavernPngJson(bytes)
    }

    private fun formatPlotStages(element: JsonElement?): String {
        val obj = element as? JsonObject ?: return ""
        return obj.entries.sortedBy { it.key }.joinToString("\n") { (key, value) ->
            val stage = value as? JsonObject
            val label = stage?.stringValue("label")?.takeIf { it.isNotBlank() } ?: key
            val description = stage?.stringValue("description").orEmpty()
            val rules = stage?.stringValue("rules").orEmpty()
            listOf("Stage $label", description, rules)
                .filter { it.isNotBlank() }
                .joinToString(": ")
        }
    }

    private fun formatPersonas(element: JsonElement?): String {
        val obj = element as? JsonObject ?: return ""
        return obj.entries.sortedBy { it.key }.joinToString("\n") { (key, value) ->
            val persona = value as? JsonObject
            val name = persona?.stringValue("name")?.takeIf { it.isNotBlank() } ?: key
            val details = listOf(
                persona?.stringValue("description").orEmpty(),
                persona?.stringValue("personality").orEmpty(),
                persona?.stringValue("scenario").orEmpty(),
                persona?.stringValue("creator_notes", "creatorNotes").orEmpty()
            ).filter { it.isNotBlank() }
            if (details.isEmpty()) name else "$name: ${details.joinToString("; ")}"
        }
    }

    private fun MutableList<String>.addIfNotBlank(label: String, value: String) {
        if (value.isNotBlank()) add("$label:\n${value.trim()}")
    }

    private fun RoleCard.hasImportableContent(): Boolean {
        return listOf(
            name,
            description,
            personality,
            scenario,
            firstMes,
            mesExample,
            creatorNotes
        ).any { it.isNotBlank() } ||
            tags.isNotEmpty() ||
            plotStages != null ||
            personas != null ||
            creativeWorkshop != null
    }

    companion object {
        val PNG_SIGNATURE = byteArrayOf(
            0x89.toByte(),
            0x50,
            0x4E,
            0x47,
            0x0D,
            0x0A,
            0x1A,
            0x0A
        )

        fun parseRoleCardJson(jsonText: String): RoleCard {
            val root = AppJson.parseToJsonElement(jsonText) as? JsonObject
                ?: error("Role card JSON must be an object")
            val data = (root["data"] as? JsonObject)
                ?: (root["persona_card"] as? JsonObject)
                ?: root

            return RoleCard(
                name = data.stringValue("name"),
                description = data.stringValue("description"),
                personality = data.stringValue("personality"),
                scenario = data.stringValue("scenario"),
                firstMes = data.stringValue("first_mes", "firstMes"),
                mesExample = data.stringValue("mes_example", "mesExample"),
                creatorNotes = data.stringValue("creator_notes", "creatorNotes"),
                tags = data["tags"]?.asStringList().orEmpty(),
                plotStages = data["plotStages"],
                personas = data["personas"],
                creativeWorkshop = data["creativeWorkshop"]
            )
        }

        private fun JsonObject.stringValue(vararg keys: String): String {
            return keys.firstNotNullOfOrNull { key ->
                (this[key] as? JsonPrimitive)?.contentOrNull?.trim()?.takeIf { it.isNotBlank() }
            }.orEmpty()
        }

        private fun JsonElement.asStringList(): List<String> {
            if (this is JsonArray) {
                return mapNotNull { (it as? JsonPrimitive)?.contentOrNull?.trim()?.takeIf(String::isNotBlank) }
            }
            (this as? JsonPrimitive)?.contentOrNull?.let { raw ->
                return raw.split(",", "，", "、", "|")
                    .map { it.trim() }
                    .filter { it.isNotBlank() }
            }
            return runCatching {
                AppJson.decodeFromJsonElement(ListSerializer(String.serializer()), this)
            }.getOrDefault(emptyList())
        }
    }
}
