package com.frischar.fantareal.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.frischar.fantareal.app.usecase.ChatOrchestrator
import com.frischar.fantareal.data.repository.ConversationRepository
import com.frischar.fantareal.domain.chat.ConversationMessage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import com.frischar.fantareal.data.repository.PersonaRepository

data class ChatUiState(
    val messages: List<ConversationMessage> = emptyList(),
    val isSending: Boolean = false,
    val personaName: String = "Fantareal"
)

class ChatViewModel(
    private val orchestrator: ChatOrchestrator,
    private val conversationRepository: ConversationRepository,
    private val personaRepository: PersonaRepository
) : ViewModel() {
    private val isSending = MutableStateFlow(false)

    val uiState: StateFlow<ChatUiState> = combine(
        conversationRepository.messages,
        isSending,
        personaRepository.persona
    ) { messages, sending, persona ->
        ChatUiState(messages = messages, isSending = sending, personaName = persona.name.ifBlank { "Fantareal" })
    }.stateIn(viewModelScope, SharingStarted.Lazily, ChatUiState())

    fun sendMessage(text: String) {
        if (text.isBlank() || isSending.value) return
        viewModelScope.launch {
            isSending.value = true
            try {
                orchestrator.sendMessage(text).collect {
                    // Done
                }
            } catch (e: Exception) {
                e.printStackTrace()
            } finally {
                isSending.value = false
            }
        }
    }

    fun endChatAndSummarize() {
        if (isSending.value) return
        viewModelScope.launch {
            isSending.value = true
            try {
                orchestrator.endChatAndSummarize()
            } catch (e: Exception) {
                e.printStackTrace()
            } finally {
                isSending.value = false
            }
        }
    }

    fun deleteMessage(id: String) {
        if (isSending.value) return
        viewModelScope.launch {
            conversationRepository.deleteMessage(id)
        }
    }

    fun regenerateMessage(id: String) {
        if (isSending.value) return
        viewModelScope.launch {
            val msgs = conversationRepository.messages.value
            val index = msgs.indexOfFirst { it.id == id }
            if (index > 0 && msgs[index].role == com.frischar.fantareal.domain.chat.MessageRole.Assistant) {
                val userMsgIndex = msgs.indexOfLast { it.role == com.frischar.fantareal.domain.chat.MessageRole.User && msgs.indexOf(it) < index }
                if (userMsgIndex != -1) {
                    val textToResend = msgs[userMsgIndex].content
                    conversationRepository.deleteMessageAndFollowing(msgs[userMsgIndex].id)
                    sendMessage(textToResend)
                }
            }
        }
    }
}
