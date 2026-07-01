package com.frischar.fantareal.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.frischar.fantareal.data.repository.PresetRepository
import com.frischar.fantareal.domain.preset.PromptPreset
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

import com.frischar.fantareal.data.repository.ConversationRepository
import com.frischar.fantareal.data.repository.PersonaRepository

data class PresetUiState(
    val presets: List<PromptPreset> = emptyList(),
    val statusMessage: String? = null,
    val error: String? = null
)

class PresetViewModel(
    private val presetRepository: PresetRepository,
    private val conversationRepository: ConversationRepository,
    private val personaRepository: PersonaRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(PresetUiState())
    val uiState: StateFlow<PresetUiState> = _uiState.asStateFlow()

    init {
        reload()
    }

    fun reload() {
        viewModelScope.launch {
            _uiState.value = PresetUiState(presetRepository.listPresets())
        }
    }

    fun setEnabled(id: String, enabled: Boolean) {
        viewModelScope.launch {
            presetRepository.setEnabled(id, enabled)
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
                
                val service = com.frischar.fantareal.data.preset.PresetService()
                val presets = service.parsePresets(jsonText)
                if (presets.isNotEmpty()) {
                    presetRepository.savePresets(presets)
                    conversationRepository.resetConversation(personaRepository.persona.value.greeting)
                    _uiState.value = PresetUiState(
                        presets = presetRepository.listPresets(),
                        statusMessage = "预设卡已导入并覆盖当前存档"
                    )
                } else {
                    _uiState.value = _uiState.value.copy(error = "未识别到可导入的预设")
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message ?: "预设导入失败")
            }
        }
    }

    fun exportJson(onExportReady: (String) -> Unit) {
        viewModelScope.launch {
            val service = com.frischar.fantareal.data.preset.PresetService()
            val presets = presetRepository.listPresets()
            val jsonText = service.exportToJson(presets)
            onExportReady(jsonText)
        }
    }
}
