package com.frischar.fantareal.data.repository

import com.frischar.fantareal.data.storage.JsonStore
import com.frischar.fantareal.domain.worldbook.WorldbookEntry
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.builtins.ListSerializer

class WorldbookRepository(
    private val slotRepository: SlotRepository,
    private val jsonStore: JsonStore = JsonStore()
) {
    private val mutex = Mutex()
    private val serializer = ListSerializer(WorldbookEntry.serializer())

    suspend fun listEntries(): List<WorldbookEntry> {
        return jsonStore.read(
            slotRepository.paths.worldbookFile(slotRepository.currentSlotId.value),
            serializer,
            defaultValue = emptyList()
        )
    }

    suspend fun saveEntries(entries: List<WorldbookEntry>) {
        jsonStore.write(
            slotRepository.paths.worldbookFile(slotRepository.currentSlotId.value),
            serializer,
            entries
        )
    }

    suspend fun upsert(entry: WorldbookEntry) {
        mutex.withLock {
            val current = listEntries()
            val updated = if (current.any { it.id == entry.id }) {
                current.map { if (it.id == entry.id) entry else it }
            } else {
                current + entry
            }
            saveEntries(updated)
        }
    }

    suspend fun delete(id: String): Boolean {
        return mutex.withLock {
            val current = listEntries()
            val updated = current.filterNot { it.id == id }
            saveEntries(updated)
            updated.size != current.size
        }
    }
}
