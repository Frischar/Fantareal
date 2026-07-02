package com.frischar.fantareal.data.repository

import com.frischar.fantareal.data.storage.JsonStore
import com.frischar.fantareal.domain.workshop.WorkshopState

class WorkshopRepository(
    private val slotRepository: SlotRepository,
    private val jsonStore: JsonStore = JsonStore()
) {
    suspend fun loadState(): WorkshopState {
        return jsonStore.read(
            slotRepository.paths.slotDir(slotRepository.currentSlotId.value).resolve("workshop.json"),
            WorkshopState.serializer(),
            WorkshopState()
        )
    }

    suspend fun saveState(state: WorkshopState) {
        jsonStore.write(
            slotRepository.paths.slotDir(slotRepository.currentSlotId.value).resolve("workshop.json"),
            WorkshopState.serializer(),
            state
        )
    }
}
