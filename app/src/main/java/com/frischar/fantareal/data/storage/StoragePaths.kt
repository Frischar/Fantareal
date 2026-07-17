package com.frischar.fantareal.data.storage

import android.content.Context
import java.io.File

class StoragePaths(context: Context) {
    val runtimeDir: File = File(context.filesDir, RUNTIME_DIR)
    val slotsDir: File = File(runtimeDir, "slots")
    val exportsDir: File = File(runtimeDir, "exports")
    val spritesDir: File = File(runtimeDir, "sprites")
    val activeSlotFile: File = File(runtimeDir, "active_slot.json")

    init {
        ensureRoot()
    }

    fun ensureRoot() {
        runtimeDir.mkdirs()
        slotsDir.mkdirs()
        exportsDir.mkdirs()
        spritesDir.mkdirs()
    }

    fun slotDir(slotId: String): File {
        val safeSlotId = sanitizeSlotId(slotId)
        return File(slotsDir, safeSlotId).also { it.mkdirs() }
    }

    fun conversationsFile(slotId: String): File = File(slotDir(slotId), "conversations.json")

    fun settingsFile(slotId: String): File = File(slotDir(slotId), "settings.json")

    fun personaFile(slotId: String): File = File(slotDir(slotId), "persona.json")

    fun currentRoleCardFile(slotId: String): File = File(slotDir(slotId), "current_role_card.json")

    fun rawRoleCardFile(slotId: String): File = File(slotDir(slotId), "raw_role_card.json")

    fun memoriesFile(slotId: String): File = File(slotDir(slotId), "memories.json")

    fun tombstonesFile(slotId: String): File = File(slotDir(slotId), "memory_tombstones.json")

    fun worldbookFile(slotId: String): File = File(slotDir(slotId), "worldbook.json")

    fun stateJournalRuntimeFile(slotId: String): File = File(slotDir(slotId), "state_journal_runtime.json")

    private fun sanitizeSlotId(slotId: String): String {
        val normalized = slotId.trim()
        require(normalized.matches(SLOT_ID_PATTERN)) {
            "Invalid slot id: $slotId"
        }
        return normalized
    }

    companion object {
        const val RUNTIME_DIR = "fantareal_runtime"
        const val DEFAULT_SLOT_ID = "slot_1"

        private val SLOT_ID_PATTERN = Regex("[A-Za-z0-9_-]+")
    }
}
