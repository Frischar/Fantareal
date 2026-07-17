package com.frischar.fantareal

import com.frischar.fantareal.core.AppJson
import com.frischar.fantareal.data.preset.PresetService
import com.frischar.fantareal.data.memory.MemoryService
import com.frischar.fantareal.data.rolecard.RoleCardService
import com.frischar.fantareal.data.worldbook.WorldbookService
import com.frischar.fantareal.domain.chat.ConversationMessage
import com.frischar.fantareal.domain.chat.MessageRole
import com.frischar.fantareal.domain.llm.LlmMessage
import com.frischar.fantareal.domain.llm.LlmRequest
import com.frischar.fantareal.domain.llm.LlmStreamEvent
import com.frischar.fantareal.domain.llm.OpenAiProvider
import com.frischar.fantareal.domain.memory.LongTermMemory
import com.frischar.fantareal.domain.prompt.PromptBuildInput
import com.frischar.fantareal.domain.prompt.PromptBuilder
import com.frischar.fantareal.domain.prompt.PromptSegment
import com.frischar.fantareal.domain.preset.PresetBlock
import com.frischar.fantareal.domain.preset.PresetGroup
import com.frischar.fantareal.domain.preset.PresetGroupItem
import com.frischar.fantareal.domain.preset.PresetModule
import com.frischar.fantareal.domain.preset.PromptPreset
import com.frischar.fantareal.domain.rolecard.PersonaRuntime
import com.frischar.fantareal.domain.rolecard.RoleCard
import com.frischar.fantareal.domain.worldbook.InjectionPosition
import com.frischar.fantareal.domain.worldbook.TriggerLogic
import com.frischar.fantareal.domain.worldbook.TriggerMode
import com.frischar.fantareal.domain.worldbook.WorldbookEntry
import com.frischar.fantareal.domain.worldbook.WorldbookEngine
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
    fun stateJournalInitialStagesActivateExternalTagWorldbookEntries() {
        val roleCardJson = """
            {
              "name": "Stage Test",
              "stateJournal": {
                "version": 1,
                "enabled": true,
                "roles": [
                  {
                    "role_id": "shen_qixue",
                    "role_name": "沈栖雪",
                    "initial_stage": "stage_a",
                    "stages": [
                      {
                        "stage_key": "stage_a",
                        "stage_name": "A阶段",
                        "activation_tag": "state_journal.stage.shen_qixue.stage_a"
                      }
                    ]
                  }
                ]
              }
            }
        """.trimIndent()
        val worldbookJson = """
            {
              "entries": [
                {
                  "id": "stage_a_entry",
                  "title": "沈栖雪 · A阶段",
                  "entry_type": "external_tag",
                  "activation_tags": ["state_journal.stage.shen_qixue.stage_a"],
                  "content": "A阶段约束",
                  "chance": 100
                },
                {
                  "id": "stage_b_entry",
                  "title": "沈栖雪 · B阶段",
                  "entry_type": "external_tag",
                  "activation_tags": ["state_journal.stage.shen_qixue.stage_b"],
                  "content": "B阶段约束",
                  "chance": 100
                }
              ]
            }
        """.trimIndent()

        val roleCard = RoleCardService.parseRoleCardJson(roleCardJson)
        val activeTags = RoleCardService.activeStageTags(roleCard)
        val entries = WorldbookService().parseTavernWorldbook(worldbookJson)
        val matches = WorldbookEngine().scan(
            entries = entries,
            userInput = "继续整理卷宗",
            recentHistory = emptyList(),
            activeTags = activeTags
        ).matches

        assertEquals(setOf("state_journal.stage.shen_qixue.stage_a"), activeTags)
        assertEquals(2, entries.size)
        assertEquals(listOf("stage_a_entry"), matches.map { it.entry.id })
    }

    @Test
    fun memoryParserDoesNotCreatePlaceholderForEmptyObject() {
        assertTrue(MemoryService().parseMemories("{}").isEmpty())
    }

    @Test
    fun memoryParserPreservesStructuredFieldsAcrossExport() {
        val service = MemoryService()
        val json = """
            {
              "items": [
                {
                  "id": "memory_structured",
                  "title": "阶段总结",
                  "content": "用户确认要把 PE 的结束对话记忆改成结构化提取，并要求保存成功后再清空对话。",
                  "notes": "需要保留 title、content、tags、notes 四个字段。",
                  "tags": ["记忆", "PE", "结构化"]
                }
              ]
            }
        """.trimIndent()

        val parsed = service.parseMemories(json).single()
        assertEquals("memory_structured", parsed.id)
        assertEquals("阶段总结", parsed.title)
        assertEquals("用户确认要把 PE 的结束对话记忆改成结构化提取，并要求保存成功后再清空对话。", parsed.text)
        assertEquals("需要保留 title、content、tags、notes 四个字段。", parsed.notes)
        assertEquals(listOf("记忆", "PE", "结构化"), parsed.tags)

        val reparsed = service.parseMemories(service.exportToJson(listOf(parsed))).single()
        assertEquals(parsed.title, reparsed.title)
        assertEquals(parsed.text, reparsed.text)
        assertEquals(parsed.notes, reparsed.notes)
        assertEquals(parsed.tags, reparsed.tags)
    }

    @Test
    fun memoryParserKeepsLegacyTextMemoriesCompatible() {
        val json = """[{"id":"legacy_memory","text":"Legacy saved memory.","tags":"summary，legacy"}]"""

        val parsed = MemoryService().parseMemories(json).single()

        assertEquals("legacy_memory", parsed.id)
        assertEquals("", parsed.title)
        assertEquals("Legacy saved memory.", parsed.text)
        assertEquals(listOf("summary", "legacy"), parsed.tags)
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
        assertTrue(preset.hasStructuredContent())
        assertTrue(preset.modules.any { it.key == "emotion_detail" })
        assertTrue(preset.modules.first { it.key == "anti_repeat" }.enabled)
        assertTrue(preset.modules.first { it.key == "short_paragraph" }.enabled)
        assertTrue(!preset.modules.first { it.key == "long_paragraph" }.enabled)
        assertTrue(preset.content.contains("Base rule."))
        assertTrue(preset.content.contains("Avoid repeating"))
        assertTrue(preset.content.contains("Keep natural paragraphs short"))
        assertTrue(preset.content.contains("Extra rule."))
        assertTrue(!preset.content.contains("Disabled rule."))
    }

    @Test
    fun presetParserKeepsPromptGroupsAndSelectedItems() {
        val json = """
            {
              "id": "preset_grouped",
              "name": "Grouped Preset",
              "enabled": true,
              "base_system_prompt": "Base rule.",
              "modules": {
                "v4f_output_guard": true,
                "emotion_detail": true
              },
              "prompt_groups": [
                {
                  "id": "tone_group",
                  "name": "Tone",
                  "enabled": true,
                  "selection_mode": "multiple",
                  "selected_ids": ["soft"],
                  "items": [
                    {"id": "soft", "name": "Soft", "content": "Selected group rule."},
                    {"id": "sharp", "name": "Sharp", "content": "Unselected group rule."}
                  ]
                }
              ],
              "extra_prompts": [
                {"id": "extra_1", "name": "Extra", "enabled": true, "content": "Extra rule."}
              ]
            }
        """.trimIndent()

        val preset = PresetService().parsePresets(json).single()
        val runtime = preset.enabledPromptSections().joinToString("\n\n")

        assertEquals("preset_grouped", preset.id)
        assertEquals("Grouped Preset", preset.title)
        assertEquals(listOf("soft"), preset.promptGroups.single().selectedIds)
        assertTrue(preset.modules.first { it.key == "v4f_output_guard" }.enabled)
        assertTrue(runtime.contains("Selected group rule."))
        assertTrue(!runtime.contains("Unselected group rule."))
        assertTrue(runtime.contains("Extra rule."))
    }

    @Test
    fun presetParserPreservesAdvancedSegmentFieldsAcrossExport() {
        val json = """
            {
              "presets": [
                {
                  "id": "preset_advanced",
                  "name": "Advanced Preset",
                  "enabled": true,
                  "extra_prompts": [
                    {
                      "id": "depth_block",
                      "name": "Depth Block",
                      "enabled": true,
                      "content": "Depth rule.",
                      "order": 42,
                      "placement": "at_depth",
                      "role": "assistant",
                      "depth": 7,
                      "kind": "tone",
                      "strength": "hard",
                      "required": true,
                      "tokenBudget": 321,
                      "activation_tags": ["night", "rain"]
                    }
                  ],
                  "prompt_groups": [
                    {
                      "id": "group_advanced",
                      "name": "Advanced Group",
                      "enabled": true,
                      "selection_mode": "single",
                      "selected_ids": ["near_item"],
                      "items": [
                        {
                          "id": "near_item",
                          "name": "Near Item",
                          "enabled": true,
                          "content": "Near latest rule.",
                          "placement": "near_latest_user",
                          "role": "system",
                          "depth": 0,
                          "kind": "plot",
                          "strength": "soft",
                          "required": false,
                          "tokenBudget": 123,
                          "activation_tags": ["turn"]
                        }
                      ]
                    }
                  ]
                }
              ]
            }
        """.trimIndent()

        val service = PresetService()
        val preset = service.parsePresets(json).single()
        val exportedPreset = service.parsePresets(service.exportToJson(listOf(preset))).single()
        val block = exportedPreset.extraPrompts.single()
        val item = exportedPreset.promptGroups.single().items.single()
        val segments = exportedPreset.enabledPromptSegments()

        assertEquals("at_depth", block.placement)
        assertEquals("assistant", block.role)
        assertEquals(7, block.depth)
        assertEquals("tone", block.kind)
        assertEquals("hard", block.strength)
        assertEquals(true, block.required)
        assertEquals(321, block.tokenBudget)
        assertEquals(listOf("night", "rain"), block.activationTags)
        assertEquals("near_latest_user", item.placement)
        assertEquals("plot", item.kind)
        assertTrue(segments.any { it.placement == "at_depth" && it.depth == 7 && it.role == "assistant" })
        assertTrue(segments.any { it.placement == "near_latest_user" && it.content.contains("Near latest rule.") })
    }

    @Test
    fun promptBuilderInjectsPresetSegmentsByPlacementAndDepth() {
        val result = PromptBuilder().build(
            PromptBuildInput(
                systemRules = "System rules.",
                persona = PersonaRuntime(name = "Alice", systemPrompt = "Persona prompt."),
                history = listOf(
                    ConversationMessage("u1", MessageRole.User, "Older user.", 1L),
                    ConversationMessage("a1", MessageRole.Assistant, "Latest assistant.", 2L)
                ),
                latestUserInput = "Current user.",
                presetSegments = listOf(
                    PromptSegment(
                        id = "core",
                        content = "Core preset.",
                        placement = "system_core",
                        order = 1
                    ),
                    PromptSegment(
                        id = "depth1",
                        content = "Depth one preset.",
                        placement = "at_depth",
                        role = "system",
                        depth = 1,
                        order = 1
                    ),
                    PromptSegment(
                        id = "depth0",
                        content = "Depth zero preset.",
                        placement = "at_depth",
                        role = "system",
                        depth = 0,
                        order = 1
                    ),
                    PromptSegment(
                        id = "guard",
                        content = "Output guard preset.",
                        placement = "output_guard",
                        role = "system",
                        order = 1
                    ),
                    PromptSegment(
                        id = "near",
                        content = "Near latest preset.",
                        placement = "near_latest_user",
                        role = "system",
                        order = 1
                    )
                )
            )
        )

        assertTrue(result.system.orEmpty().contains("Core preset."))
        assertEquals("Older user.", result.messages[0].content)
        assertEquals("Depth one preset.", result.messages[1].content)
        assertEquals("Latest assistant.", result.messages[2].content)
        assertEquals("Depth zero preset.", result.messages[3].content)
        assertEquals("Output guard preset.", result.messages[4].content)
        assertEquals("Near latest preset.", result.messages[5].content)
        assertEquals("Current user.", result.messages[6].content)
    }

    @Test
    fun promptPresetRuntimeSectionsRespectNestedSwitches() {
        val preset = PromptPreset(
            id = "preset_nested",
            title = "Nested",
            enabled = true,
            baseSystemPrompt = "Base rule.",
            modules = listOf(
                PresetModule(key = "m1", title = "Module 1", content = "Enabled module.", enabled = true),
                PresetModule(key = "m2", title = "Module 2", content = "Disabled module.", enabled = false)
            ),
            extraPrompts = listOf(
                PresetBlock(id = "b1", title = "Block 1", content = "Enabled block.", enabled = true),
                PresetBlock(id = "b2", title = "Block 2", content = "Disabled block.", enabled = false)
            ),
            promptGroups = listOf(
                PresetGroup(
                    id = "g1",
                    title = "Group 1",
                    enabled = true,
                    selectionMode = "single",
                    selectedIds = listOf("i1"),
                    items = listOf(
                        PresetGroupItem(id = "i1", title = "Item 1", content = "Selected item."),
                        PresetGroupItem(id = "i2", title = "Item 2", content = "Unselected item.")
                    )
                )
            )
        )

        val runtime = preset.enabledPromptSections().joinToString("\n\n")

        assertTrue(runtime.contains("Base rule."))
        assertTrue(runtime.contains("Enabled module."))
        assertTrue(!runtime.contains("Disabled module."))
        assertTrue(runtime.contains("Enabled block."))
        assertTrue(!runtime.contains("Disabled block."))
        assertTrue(runtime.contains("Selected item."))
        assertTrue(!runtime.contains("Unselected item."))
        assertTrue(preset.copy(enabled = false).enabledPromptSections().isEmpty())
    }

    @Test
    fun presetParserUsesActivePresetAndSelectedPromptGroupItems() {
        val json = """
            {
              "active_preset_id": "active_preset",
              "presets": [
                {
                  "id": "default_preset",
                  "name": "Default",
                  "enabled": true,
                  "content": "Default rule."
                },
                {
                  "id": "active_preset",
                  "name": "Active",
                  "enabled": true,
                  "base_system_prompt": "Base rule.",
                  "prompt_groups": [
                    {
                      "id": "style",
                      "enabled": true,
                      "selection_mode": "single",
                      "selected_ids": ["selected"],
                      "items": [
                        {"id": "selected", "enabled": true, "content": "Selected rule."},
                        {"id": "unselected", "enabled": true, "content": "Unselected rule."}
                      ]
                    }
                  ]
                }
              ]
            }
        """.trimIndent()

        val presets = PresetService().parsePresets(json)
        val active = presets.single { it.id == "active_preset" }

        assertTrue(!presets.single { it.id == "default_preset" }.enabled)
        assertTrue(active.enabled)
        assertTrue(active.content.contains("Selected rule."))
        assertTrue(!active.content.contains("Unselected rule."))
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
                    title = "Saved title",
                    text = "A saved memory.",
                    notes = "Saved note.",
                    tags = listOf("summary"),
                    createdAt = 123L
                )
            )
        )
        val memory = memoryService.parseMemories(memoryJson).single()
        assertEquals("memory_1", memory.id)
        assertEquals("Saved title", memory.title)
        assertEquals("A saved memory.", memory.text)
        assertEquals("Saved note.", memory.notes)

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
