package com.frischar.fantareal.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.frischar.fantareal.data.repository.WorldbookRepository
import com.frischar.fantareal.domain.worldbook.WorldbookEntry
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

import com.frischar.fantareal.data.repository.ConversationRepository
import com.frischar.fantareal.data.repository.PersonaRepository

data class WorldbookUiState(
    val entries: List<WorldbookEntry> = emptyList(),
    val statusMessage: String? = null,
    val error: String? = null
)

class WorldbookViewModel(
    private val worldbookRepository: WorldbookRepository,
    private val conversationRepository: ConversationRepository,
    private val personaRepository: PersonaRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(WorldbookUiState())
    val uiState: StateFlow<WorldbookUiState> = _uiState.asStateFlow()

    init {
        reload()
    }

    fun reload() {
        viewModelScope.launch {
            _uiState.value = WorldbookUiState(worldbookRepository.listEntries())
        }
    }

    fun importFromBytes(bytes: ByteArray) {
        viewModelScope.launch {
            try {
                val isPng = bytes.size > com.frischar.fantareal.data.rolecard.PngUtils.PNG_SIGNATURE.size && bytes.take(com.frischar.fantareal.data.rolecard.PngUtils.PNG_SIGNATURE.size).toByteArray().contentEquals(com.frischar.fantareal.data.rolecard.PngUtils.PNG_SIGNATURE)
                val jsonText = if (isPng) {
                    com.frischar.fantareal.data.rolecard.PngUtils.extractTavernPngJson(bytes)
                } else {
                    bytes.toString(Charsets.UTF_8).removePrefix("\uFEFF")
                }
                
                val service = com.frischar.fantareal.data.worldbook.WorldbookService()
                val entries = service.parseTavernWorldbook(jsonText)
                if (entries.isNotEmpty()) {
                    worldbookRepository.saveEntries(entries)
                    conversationRepository.resetConversation(personaRepository.persona.value.greeting)
                    _uiState.value = WorldbookUiState(
                        entries = worldbookRepository.listEntries(),
                        statusMessage = "世界书卡已导入并覆盖当前存档"
                    )
                } else {
                    _uiState.value = _uiState.value.copy(error = "未识别到可导入的世界书词条")
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message ?: "世界书导入失败")
            }
        }
    }

    fun exportJson(onExportReady: (String) -> Unit) {
        viewModelScope.launch {
            val service = com.frischar.fantareal.data.worldbook.WorldbookService()
            val entries = worldbookRepository.listEntries()
            val jsonText = service.exportToJson(entries)
            onExportReady(jsonText)
        }
    }
}
