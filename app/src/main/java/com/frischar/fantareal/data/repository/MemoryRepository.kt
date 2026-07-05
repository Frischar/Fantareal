package com.frischar.fantareal.data.repository

import com.frischar.fantareal.data.storage.JsonStore
import com.frischar.fantareal.domain.memory.LongTermMemory
import com.frischar.fantareal.domain.memory.MemoryTombstone
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.builtins.ListSerializer
import java.util.UUID

class MemoryRepository(
    private val slotRepository: SlotRepository,
    private val jsonStore: JsonStore = JsonStore()
) {
    private val mutex = Mutex()
    private val memorySerializer = ListSerializer(LongTermMemory.serializer())
    private val tombstoneSerializer = ListSerializer(MemoryTombstone.serializer())

    suspend fun listMemories(): List<LongTermMemory> {
        return jsonStore.read(
            slotRepository.paths.memoriesFile(slotRepository.currentSlotId.value),
            memorySerializer,
            defaultValue = emptyList()
        )
    }

    suspend fun listTombstones(): List<MemoryTombstone> {
        return jsonStore.read(
            slotRepository.paths.tombstonesFile(slotRepository.currentSlotId.value),
            tombstoneSerializer,
            defaultValue = emptyList()
        )
    }

    suspend fun addMemory(
        text: String,
        tags: List<String> = emptyList(),
        similarityThreshold: Double = 0.86,
        title: String = "",
        notes: String = ""
    ): LongTermMemory? {
        val normalizedText = text.trim()
        if (normalizedText.isBlank()) return null
        if (isBlockedByTombstone(normalizedText, similarityThreshold)) return null

        return mutex.withLock {
            val current = listMemories()
            val duplicate = current.any { diceCoefficient(it.text, normalizedText) >= similarityThreshold }
            if (duplicate) return@withLock null

            val now = System.currentTimeMillis()
            val memory = LongTermMemory(
                id = UUID.randomUUID().toString(),
                title = title.trim(),
                text = normalizedText,
                notes = notes.trim(),
                tags = tags,
                createdAt = now
            )
            saveMemories(current + memory)
            memory
        }
    }

    suspend fun updateMemory(id: String, text: String, tags: List<String>): LongTermMemory? {
        val normalizedText = text.trim()
        if (normalizedText.isBlank()) return null

        return mutex.withLock {
            var updatedMemory: LongTermMemory? = null
            val updated = listMemories().map { memory ->
                if (memory.id == id) {
                    memory.copy(text = normalizedText, tags = tags, updatedAt = System.currentTimeMillis())
                        .also { updatedMemory = it }
                } else {
                    memory
                }
            }
            saveMemories(updated)
            updatedMemory
        }
    }

    suspend fun deleteMemory(id: String): Boolean {
        return mutex.withLock {
            val current = listMemories()
            val removed = current.firstOrNull { it.id == id } ?: return@withLock false
            saveMemories(current.filterNot { it.id == id })
            saveTombstones(
                listTombstones() + MemoryTombstone(
                    id = UUID.randomUUID().toString(),
                    text = removed.text,
                    deletedAt = System.currentTimeMillis()
                )
            )
            true
        }
    }

    suspend fun clearMemories(clearTombstones: Boolean = false) {
        mutex.withLock {
            saveMemories(emptyList())
            if (clearTombstones) {
                saveTombstones(emptyList())
            }
        }
    }

    suspend fun isBlockedByTombstone(text: String, similarityThreshold: Double = 0.86): Boolean {
        return listTombstones().any { diceCoefficient(it.text, text) >= similarityThreshold }
    }

    suspend fun saveMemories(memories: List<LongTermMemory>) {
        jsonStore.write(
            slotRepository.paths.memoriesFile(slotRepository.currentSlotId.value),
            memorySerializer,
            memories
        )
    }

    private suspend fun saveTombstones(tombstones: List<MemoryTombstone>) {
        jsonStore.write(
            slotRepository.paths.tombstonesFile(slotRepository.currentSlotId.value),
            tombstoneSerializer,
            tombstones
        )
    }

    companion object {
        fun diceCoefficient(left: String, right: String): Double {
            val leftBigrams = bigrams(left)
            val rightBigrams = bigrams(right)
            if (leftBigrams.isEmpty() && rightBigrams.isEmpty()) return 1.0
            if (leftBigrams.isEmpty() || rightBigrams.isEmpty()) return 0.0

            val remaining = rightBigrams.groupingBy { it }.eachCount().toMutableMap()
            var intersection = 0
            for (bigram in leftBigrams) {
                val count = remaining[bigram] ?: 0
                if (count > 0) {
                    intersection += 1
                    if (count == 1) remaining.remove(bigram) else remaining[bigram] = count - 1
                }
            }

            return (2.0 * intersection) / (leftBigrams.size + rightBigrams.size)
        }

        private fun bigrams(value: String): List<String> {
            val compact = value.lowercase().replace(Regex("\\s+"), " ").trim()
            if (compact.length < 2) return if (compact.isBlank()) emptyList() else listOf(compact)
            return compact.windowed(2)
        }
    }
}
