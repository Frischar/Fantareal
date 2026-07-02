package com.frischar.fantareal.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.frischar.fantareal.data.repository.PersonaRepository
import com.frischar.fantareal.data.rolecard.RoleCardService
import com.frischar.fantareal.domain.rolecard.PersonaRuntime
import com.frischar.fantareal.domain.rolecard.RoleCard
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

import com.frischar.fantareal.data.repository.ConversationRepository

data class RoleCardUiState(
    val roleCard: RoleCard? = null,
    val persona: PersonaRuntime = PersonaRuntime(),
    val statusMessage: String? = null,
    val error: String? = null
)

class RoleCardViewModel(
    private val roleCardService: RoleCardService,
    private val personaRepository: PersonaRepository,
    private val conversationRepository: ConversationRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(RoleCardUiState())
    val uiState: StateFlow<RoleCardUiState> = _uiState.asStateFlow()

    init {
        reload()
    }

    fun reload() {
        viewModelScope.launch {
            val persona = personaRepository.loadCurrent()
            val card = roleCardService.loadCurrentRoleCard()
            _uiState.value = RoleCardUiState(roleCard = card, persona = persona)
        }
    }

    fun importJson(jsonText: String, clearMemories: Boolean = false) {
        viewModelScope.launch {
            runCatching {
                roleCardService.importFromJson(jsonText, clearMemories)
            }.onSuccess { result ->
                personaRepository.reload()
                conversationRepository.resetConversation(result.persona.greeting)
                _uiState.value = RoleCardUiState(
                    roleCard = result.roleCard,
                    persona = result.persona,
                    statusMessage = "角色卡已导入并覆盖当前存档"
                )
            }.onFailure { error ->
                _uiState.update { it.copy(error = error.message ?: "Role card import failed") }
            }
        }
    }

    fun importFromBytes(fileName: String, bytes: ByteArray, clearMemories: Boolean = false) {
        viewModelScope.launch {
            runCatching {
                roleCardService.importFromBytes(fileName, bytes, clearMemories)
            }.onSuccess { result ->
                personaRepository.reload()
                conversationRepository.resetConversation(result.persona.greeting)
                _uiState.value = RoleCardUiState(
                    roleCard = result.roleCard,
                    persona = result.persona,
                    statusMessage = "角色卡已导入并覆盖当前存档"
                )
            }.onFailure { error ->
                _uiState.update { it.copy(error = error.message ?: "Role card import failed") }
            }
        }
    }

    fun exportJson(onExport: (String) -> Unit) {
        viewModelScope.launch {
            val jsonString = roleCardService.getRawRoleCard()
            if (jsonString != null) {
                onExport(jsonString)
            }
        }
    }
}
