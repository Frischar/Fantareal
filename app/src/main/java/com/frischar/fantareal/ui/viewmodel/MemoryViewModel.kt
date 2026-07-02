package com.frischar.fantareal.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.frischar.fantareal.data.repository.MemoryRepository
import com.frischar.fantareal.domain.memory.LongTermMemory
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

import com.frischar.fantareal.data.repository.ConversationRepository
import com.frischar.fantareal.data.repository.PersonaRepository

data class MemoryUiState(
    val memories: List<LongTermMemory> = emptyList(),
    val statusMessage: String? = null,
    val error: String? = null
)

class MemoryViewModel(
    private val memoryRepository: MemoryRepository,
    private val conversationRepository: ConversationRepository,
    private val personaRepository: PersonaRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(MemoryUiState())
    val uiState: StateFlow<MemoryUiState> = _uiState.asStateFlow()

    init {
        reload()
    }

    fun reload() {
        viewModelScope.launch {
            _uiState.value = MemoryUiState(memoryRepository.listMemories())
        }
    }

    fun deleteMemory(id: String) {
        viewModelScope.launch {
            memoryRepository.deleteMemory(id)
            reload()
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
                
                val service = com.frischar.fantareal.data.memory.MemoryService()
                val memories = service.parseMemories(jsonText)
                if (memories.isNotEmpty()) {
                    memoryRepository.saveMemories(memories)
                    conversationRepository.resetConversation(personaRepository.persona.value.greeting)
                    _uiState.value = MemoryUiState(
                        memories = memoryRepository.listMemories(),
                        statusMessage = "记忆卡已导入并覆盖当前存档"
                    )
                } else {
                    _uiState.value = _uiState.value.copy(error = "未识别到可导入的记忆")
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message ?: "记忆导入失败")
            }
        }
    }

    fun exportJson(onExportReady: (String) -> Unit) {
        viewModelScope.launch {
            val service = com.frischar.fantareal.data.memory.MemoryService()
            val memories = memoryRepository.listMemories()
            val jsonText = service.exportToJson(memories)
            onExportReady(jsonText)
        }
    }
}
