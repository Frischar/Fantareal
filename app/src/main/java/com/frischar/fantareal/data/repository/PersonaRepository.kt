package com.frischar.fantareal.data.repository

import com.frischar.fantareal.data.storage.JsonStore
import com.frischar.fantareal.domain.rolecard.PersonaRuntime

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class PersonaRepository(
    private val slotRepository: SlotRepository,
    private val jsonStore: JsonStore = JsonStore()
) {
    private val repositoryScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val _persona = MutableStateFlow(defaultPersona())
    val persona: StateFlow<PersonaRuntime> = _persona.asStateFlow()

    init {
        repositoryScope.launch {
            _persona.value = loadCurrent()
        }
    }

    suspend fun reload() {
        _persona.value = loadCurrent()
    }

    suspend fun loadCurrent(): PersonaRuntime {
        return jsonStore.read(
            slotRepository.paths.personaFile(slotRepository.currentSlotId.value),
            PersonaRuntime.serializer(),
            defaultValue = defaultPersona()
        )
    }

    suspend fun saveCurrent(persona: PersonaRuntime) {
        jsonStore.write(
            slotRepository.paths.personaFile(slotRepository.currentSlotId.value),
            PersonaRuntime.serializer(),
            persona
        )
        _persona.value = persona
    }

    private fun defaultPersona(): PersonaRuntime {
        return PersonaRuntime(
            name = "Fantareal",
            systemPrompt = "You are a helpful AI assistant in Fantareal Android App.",
            greeting = "Hello, I am Fantareal. Configure your API key in Settings to begin."
        )
    }
}
