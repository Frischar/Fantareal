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
        val current = listPresets()
        savePresets(current.map { if (it.id == id) it.copy(enabled = enabled) else it })
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
}
