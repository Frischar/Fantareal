package com.frischar.fantareal.data.repository

import com.frischar.fantareal.core.AppJson
import com.frischar.fantareal.data.storage.JsonStore
import com.frischar.fantareal.data.storage.StoragePaths
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.serialization.Serializable

@Serializable
data class ActiveSlotState(
    val slotId: String = StoragePaths.DEFAULT_SLOT_ID
)

class SlotRepository(
    val paths: StoragePaths,
    private val jsonStore: JsonStore = JsonStore()
) {
    private val _currentSlotId = MutableStateFlow(loadActiveSlotId())
    val currentSlotId: StateFlow<String> = _currentSlotId

    init {
        paths.slotDir(_currentSlotId.value)
    }

    suspend fun switchSlot(slotId: String) {
        paths.slotDir(slotId)
        jsonStore.write(paths.activeSlotFile, ActiveSlotState.serializer(), ActiveSlotState(slotId))
        _currentSlotId.value = slotId
    }

    fun currentConversationsFile() = paths.conversationsFile(_currentSlotId.value)

    fun conversationsFile(slotId: String) = paths.conversationsFile(slotId)

    private fun loadActiveSlotId(): String {
        if (!paths.activeSlotFile.exists()) return StoragePaths.DEFAULT_SLOT_ID

        return runCatching {
            AppJson.decodeFromString(
                ActiveSlotState.serializer(),
                paths.activeSlotFile.readText(Charsets.UTF_8)
            ).slotId
        }.getOrDefault(StoragePaths.DEFAULT_SLOT_ID)
    }
}
