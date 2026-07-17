package com.frischar.fantareal.data.statejournal

import com.frischar.fantareal.data.repository.SlotRepository
import com.frischar.fantareal.data.storage.JsonStore
import com.frischar.fantareal.domain.statejournal.StateJournalConfig
import com.frischar.fantareal.domain.statejournal.StateJournalEngine
import com.frischar.fantareal.domain.statejournal.StateJournalRuntime
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.serialization.json.JsonElement

class StateJournalRepository(
    private val slotRepository: SlotRepository,
    private val jsonStore: JsonStore = JsonStore(),
    val engine: StateJournalEngine = StateJournalEngine()
) {
    private val _runtime = MutableStateFlow<StateJournalRuntime?>(null)
    val runtime: StateFlow<StateJournalRuntime?> = _runtime.asStateFlow()

    suspend fun loadOrInitialize(configElement: JsonElement?): StateJournalRuntime {
        val config = engine.parseConfig(configElement)
        val file = slotRepository.paths.stateJournalRuntimeFile(slotRepository.currentSlotId.value)
        val stored = if (file.exists()) {
            jsonStore.read(file, StateJournalRuntime.serializer(), StateJournalRuntime())
        } else {
            StateJournalRuntime()
        }
        val expectedSignature = engine.configSignature(config)
        val result = stored.takeIf {
            it.configSignature == expectedSignature &&
                it.roles.map { role -> role.roleId }.toSet() == config.roles.filter { role -> role.enabled }.map { role -> role.roleId }.toSet()
        } ?: engine.initialize(config)
        if (result !== stored) {
            jsonStore.write(file, StateJournalRuntime.serializer(), result)
        }
        _runtime.value = result
        return result
    }

    suspend fun reset(configElement: JsonElement?): StateJournalRuntime {
        val config = engine.parseConfig(configElement)
        val result = engine.initialize(config)
        jsonStore.write(
            slotRepository.paths.stateJournalRuntimeFile(slotRepository.currentSlotId.value),
            StateJournalRuntime.serializer(),
            result
        )
        _runtime.value = result
        return result
    }

    suspend fun applyAnalysis(configElement: JsonElement?, rawAnalysis: String): StateJournalRuntime? {
        val config = engine.parseConfig(configElement)
        if (!config.enabled || config.roles.none { it.enabled }) return null
        val analysis = engine.parseAnalysis(rawAnalysis) ?: return null
        val current = loadOrInitialize(configElement)
        val result = engine.applyAnalysis(config, current, analysis)
        jsonStore.write(
            slotRepository.paths.stateJournalRuntimeFile(slotRepository.currentSlotId.value),
            StateJournalRuntime.serializer(),
            result
        )
        _runtime.value = result
        return result
    }

    suspend fun activeStageTags(configElement: JsonElement?): Set<String> {
        val config = engine.parseConfig(configElement)
        val current = loadOrInitialize(configElement)
        return engine.activeStageTags(config, current)
    }

    suspend fun runtimePrompt(configElement: JsonElement?): String {
        val config = engine.parseConfig(configElement)
        val current = loadOrInitialize(configElement)
        return engine.buildRuntimePrompt(config, current)
    }

    suspend fun analysisPrompt(configElement: JsonElement?, assistantContent: String): String {
        val config = engine.parseConfig(configElement)
        val current = loadOrInitialize(configElement)
        return engine.buildAnalysisPrompt(config, current, assistantContent)
    }

    fun parseConfig(configElement: JsonElement?): StateJournalConfig = engine.parseConfig(configElement)
}
