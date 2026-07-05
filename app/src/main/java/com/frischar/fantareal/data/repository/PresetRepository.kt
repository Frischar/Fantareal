package com.frischar.fantareal.data.repository

import com.frischar.fantareal.data.storage.JsonStore
import com.frischar.fantareal.domain.preset.PromptPreset
import kotlinx.serialization.builtins.ListSerializer

class PresetRepository(
    private val slotRepository: SlotRepository,
    private val jsonStore: JsonStore = JsonStore()
) {
    private val serializer = ListSerializer(PromptPreset.serializer())

    suspend fun listPresets(): List<PromptPreset> {
        val file = slotRepository.paths.slotDir(slotRepository.currentSlotId.value).resolve("presets.json")
        return jsonStore.read(file, serializer, defaultPresets())
    }

    suspend fun savePresets(presets: List<PromptPreset>) {
        val file = slotRepository.paths.slotDir(slotRepository.currentSlotId.value).resolve("presets.json")
        jsonStore.write(file, serializer, presets)
    }

    suspend fun setEnabled(id: String, enabled: Boolean) {
        updatePreset(id) { it.copy(enabled = enabled) }
    }

    suspend fun setModuleEnabled(presetId: String, moduleKey: String, enabled: Boolean) {
        updatePreset(presetId) { preset ->
            val nextModules = preset.modules.map { module ->
                val toggled = if (module.key == moduleKey) module.copy(enabled = enabled) else module
                if (enabled && module.key in moduleMutex[moduleKey].orEmpty()) {
                    toggled.copy(enabled = false)
                } else {
                    toggled
                }
            }
            preset.copy(modules = nextModules)
        }
    }

    suspend fun setBlockEnabled(presetId: String, blockId: String, enabled: Boolean) {
        updatePreset(presetId) { preset ->
            preset.copy(
                extraPrompts = preset.extraPrompts.map { block ->
                    if (block.id == blockId) block.copy(enabled = enabled) else block
                }
            )
        }
    }

    suspend fun setGroupEnabled(presetId: String, groupId: String, enabled: Boolean) {
        updatePreset(presetId) { preset ->
            preset.copy(
                promptGroups = preset.promptGroups.map { group ->
                    if (group.id == groupId) group.copy(enabled = enabled) else group
                }
            )
        }
    }

    suspend fun setGroupItemEnabled(presetId: String, groupId: String, itemId: String, enabled: Boolean) {
        updatePreset(presetId) { preset ->
            preset.copy(
                promptGroups = preset.promptGroups.map { group ->
                    if (group.id != groupId) return@map group

                    val nextSelectedIds = when {
                        enabled && group.selectionMode == "single" -> listOf(itemId)
                        enabled -> (group.selectedIds + itemId).distinct()
                        else -> group.selectedIds.filterNot { it == itemId }
                    }
                    group.copy(
                        selectedIds = nextSelectedIds,
                        items = group.items.map { item ->
                            if (item.id == itemId) item.copy(enabled = enabled) else item
                        }
                    )
                }
            )
        }
    }

    private suspend fun updatePreset(id: String, transform: (PromptPreset) -> PromptPreset) {
        val current = listPresets()
        val next = current.map { preset ->
            if (preset.id == id) {
                transform(preset).withRuntimeContent()
            } else {
                preset
            }
        }
        savePresets(next)
    }

    private fun PromptPreset.withRuntimeContent(): PromptPreset {
        return copy(content = runtimeContent())
    }

    private fun defaultPresets(): List<PromptPreset> {
        return listOf(
            PromptPreset(
                id = "anti_impersonation",
                title = "防抢话",
                content = "不要代替用户发言，不要替用户决定动作、台词或心理活动。",
                enabled = true
            ),
            PromptPreset(
                id = "anti_repeat",
                title = "防重复",
                content = "避免重复使用相同句式、段落结构或口头禅。回复应自然变化。",
                enabled = false
            ),
            PromptPreset(
                id = "third_person_scene",
                title = "第三人称描述",
                content = "涉及剧情描写时使用第三人称叙述，保持画面感与连续性。",
                enabled = true
            )
        )
    }

    companion object {
        private val moduleMutex = mapOf(
            "short_paragraph" to listOf("long_paragraph"),
            "long_paragraph" to listOf("short_paragraph"),
            "second_person" to listOf("third_person"),
            "third_person" to listOf("second_person")
        )
    }
}
