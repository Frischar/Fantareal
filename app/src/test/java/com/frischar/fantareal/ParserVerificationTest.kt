package com.frischar.fantareal

import com.frischar.fantareal.core.AppJson
import com.frischar.fantareal.data.preset.PresetService
import com.frischar.fantareal.data.memory.MemoryService
import com.frischar.fantareal.data.rolecard.RoleCardService
import com.frischar.fantareal.data.worldbook.WorldbookService
import com.frischar.fantareal.domain.llm.LlmMessage
import com.frischar.fantareal.domain.llm.LlmRequest
import com.frischar.fantareal.domain.llm.LlmStreamEvent
import com.frischar.fantareal.domain.llm.OpenAiProvider
import com.frischar.fantareal.domain.memory.LongTermMemory
import com.frischar.fantareal.domain.preset.PromptPreset
import com.frischar.fantareal.domain.rolecard.RoleCard
import com.frischar.fantareal.domain.worldbook.InjectionPosition
import com.frischar.fantareal.domain.worldbook.TriggerLogic
import com.frischar.fantareal.domain.worldbook.TriggerMode
import com.frischar.fantareal.domain.worldbook.WorldbookEntry
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ParserVerificationTest {
    @Test
    fun openAiProviderParsesNonStreamingResponse() = runBlocking {
        val server = MockWebServer()
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody("""{"choices":[{"message":{"content":"Hello from JSON"}}]}""")
        )
        server.start()

        try {
            val events = OpenAiProvider(server.url("/v1").toString(), "")
                .stream(
                    LlmRequest(
                        model = "test-model",
                        system = null,
                        messages = listOf(LlmMessage("user", "hi")),
                        temperature = 0.7,
                        stream = false
                    )
                )
                .toList()

            assertEquals(LlmStreamEvent.Token("Hello from JSON"), events[0])
            assertEquals(LlmStreamEvent.Done, events[1])
        } finally {
            server.shutdown()
        }
    }

    @Test
    fun worldbookParserKeepsNewFieldsAndNormalizesChance() {
        val json = """
            {
              "entries": [
                {
                  "id": "wb_1",
                  "title": "Castle",
                  "primaryTriggers": "Alice|Castle",
                  "secondaryTriggers": "Moon",
                  "content": "Castle lore.",
                  "matchMode": "all",
                  "secondaryMode": "all",
                  "entryType": "keyword",
                  "chance": 50,
                  "caseSensitive": true,
                  "wholeWord": true,
                  "insertionPosition": "before_char_defs",
                  "stickyTurns": 2,
                  "cooldownTurns": 3
                }
              ]
            }
        """.trimIndent()

        val entry = WorldbookService().parseTavernWorldbook(json).single()

        assertEquals(listOf("Alice", "Castle"), entry.primaryTriggers)
        assertEquals(listOf("Moon"), entry.secondaryTriggers)
        assertEquals(TriggerLogic.All, entry.primaryLogic)
        assertEquals(TriggerLogic.All, entry.secondaryLogic)
        assertEquals(TriggerMode.Literal, entry.triggerMode)
        assertEquals(InjectionPosition.BeforePersona, entry.insertionPosition)
        assertEquals(0.5, entry.chance, 0.001)
        assertTrue(entry.caseSensitive)
        assertTrue(entry.wholeWord)
        assertEquals(2, entry.stickyTurns)
        assertEquals(3, entry.cooldownTurns)
    }

    @Test
    fun worldbookParserIgnoresMalformedScalarFields() {
        val json = """
            {
              "data": {
                "character_book": {
                  "entries": [
                    {
                      "uid": {"bad": "shape"},
                      "key": ["Castle"],
                      "content": "Castle lore.",
                      "position": {"bad": "shape"},
                      "chance": {"bad": "shape"},
                      "caseSensitive": {"bad": "shape"}
                    }
                  ]
                }
              }
            }
        """.trimIndent()

        val entry = WorldbookService().parseTavernWorldbook(json).single()

        assertEquals(listOf("Castle"), entry.primaryTriggers)
        assertEquals("Castle lore.", entry.content)
        assertEquals(1.0, entry.chance, 0.001)
    }

    @Test
    fun memoryParserDoesNotCreatePlaceholderForEmptyObject() {
        assertTrue(MemoryService().parseMemories("{}").isEmpty())
    }

    @Test
    fun presetParserExpandsEnabledModules() {
        val json = """
            {
              "presets": [
                {
                  "id": "preset_1",
                  "name": "Story Preset",
                  "enabled": true,
                  "base_system_prompt": "Base rule.",
                  "modules": {
                    "anti_repeat": true,
                    "short_paragraph": true,
                    "long_paragraph": false
                  },
                  "extra_prompts": [
                    {"enabled": true, "content": "Extra rule."},
                    {"enabled": false, "content": "Disabled rule."}
                  ]
                }
              ]
            }
        """.trimIndent()

        val preset = PresetService().parsePresets(json).single()

        assertEquals("preset_1", preset.id)
        assertEquals("Story Preset", preset.title)
        assertTrue(preset.content.contains("Base rule."))
        assertTrue(preset.content.contains("Avoid repeating"))
        assertTrue(preset.content.contains("Keep natural paragraphs short"))
        assertTrue(preset.content.contains("Extra rule."))
        assertTrue(!preset.content.contains("Disabled rule."))
    }

    @Test
    fun exportedCardsCanBeReimportedByImportParsers() {
        val roleCardJson = AppJson.encodeToString(
            RoleCard.serializer(),
            RoleCard(
                name = "Alice",
                description = "A test character.",
                firstMes = "Hello."
            )
        )
        val roleCard = RoleCardService.parseRoleCardJson(roleCardJson)
        assertEquals("Alice", roleCard.name)
        assertEquals("Hello.", roleCard.firstMes)

        val memoryService = MemoryService()
        val memoryJson = memoryService.exportToJson(
            listOf(
                LongTermMemory(
                    id = "memory_1",
                    text = "A saved memory.",
                    tags = listOf("summary"),
                    createdAt = 123L
                )
            )
        )
        val memory = memoryService.parseMemories(memoryJson).single()
        assertEquals("memory_1", memory.id)
        assertEquals("A saved memory.", memory.text)

        val worldbookService = WorldbookService()
        val worldbookJson = worldbookService.exportToJson(
            listOf(
                WorldbookEntry(
                    id = "world_1",
                    title = "Castle",
                    content = "Castle lore.",
                    primaryTriggers = listOf("Castle")
                )
            )
        )
        val worldbookEntry = worldbookService.parseTavernWorldbook(worldbookJson).single()
        assertEquals("world_1", worldbookEntry.id)
        assertEquals(listOf("Castle"), worldbookEntry.primaryTriggers)

        val presetService = PresetService()
        val presetJson = presetService.exportToJson(
            listOf(
                PromptPreset(
                    id = "preset_1",
                    title = "Style",
                    content = "Keep replies concise.",
                    enabled = true
                )
            )
        )
        val preset = presetService.parsePresets(presetJson).single()
        assertEquals("preset_1", preset.id)
        assertEquals("Style", preset.title)
        assertEquals("Keep replies concise.", preset.content)
    }
}
