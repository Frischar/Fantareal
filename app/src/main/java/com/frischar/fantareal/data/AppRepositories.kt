package com.frischar.fantareal.data

import android.content.Context
import com.frischar.fantareal.data.repository.ConversationRepository
import com.frischar.fantareal.data.repository.MemoryRepository
import com.frischar.fantareal.data.repository.PersonaRepository
import com.frischar.fantareal.data.repository.PresetRepository
import com.frischar.fantareal.data.repository.SettingsRepository
import com.frischar.fantareal.data.repository.SlotRepository
import com.frischar.fantareal.data.repository.WorkshopRepository
import com.frischar.fantareal.data.repository.WorldbookRepository
import com.frischar.fantareal.data.rolecard.RoleCardService
import com.frischar.fantareal.data.storage.StoragePaths

class AppRepositories(context: Context) {
    private val appContext = context.applicationContext

    val slotRepository = SlotRepository(StoragePaths(appContext))
    val settingsRepository = SettingsRepository(appContext, slotRepository)
    val conversationRepository = ConversationRepository(slotRepository)
    val personaRepository = PersonaRepository(slotRepository)
    val memoryRepository = MemoryRepository(slotRepository)
    val worldbookRepository = WorldbookRepository(slotRepository)
    val presetRepository = PresetRepository(slotRepository)
    val workshopRepository = WorkshopRepository(slotRepository)
    val roleCardService = RoleCardService(slotRepository)
}
