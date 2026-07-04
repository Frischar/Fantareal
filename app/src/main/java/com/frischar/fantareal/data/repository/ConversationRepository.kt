package com.frischar.fantareal.data.repository

import android.content.Context
import com.frischar.fantareal.data.storage.JsonStore
import com.frischar.fantareal.data.storage.StoragePaths
import com.frischar.fantareal.domain.chat.ConversationMessage
import com.frischar.fantareal.domain.chat.MessageRole
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.builtins.ListSerializer

class ConversationRepository(
    val slotRepository: SlotRepository,
    private val jsonStore: JsonStore = JsonStore()
) {
    constructor(context: Context) : this(
        slotRepository = SlotRepository(StoragePaths(context.applicationContext))
    )

    private val repositoryScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val writeMutex = Mutex()
    private val messageListSerializer = ListSerializer(ConversationMessage.serializer())
    private val _messages = MutableStateFlow<List<ConversationMessage>>(emptyList())
    val messages: StateFlow<List<ConversationMessage>> = _messages
    private val initialLoad = repositoryScope.launch { reload() }

    suspend fun reload() {
        val loaded = jsonStore.read(
            slotRepository.currentConversationsFile(),
            messageListSerializer,
            defaultValue = defaultConversation()
        )
        _messages.value = loaded.ifEmpty { defaultConversation() }
    }

    suspend fun switchSlot(slotId: String) {
        slotRepository.switchSlot(slotId)
        reload()
    }

    suspend fun addMessage(msg: ConversationMessage) {
        initialLoad.join()
        mutateMessages { it + msg }
    }

    suspend fun updateMessage(id: String, newContent: String, thinking: String? = null, saveToDisk: Boolean = true) {
        initialLoad.join()
        if (saveToDisk) {
            mutateMessages { current ->
                current.map {
                    if (it.id == id) it.copy(content = newContent, thinking = thinking) else it
                }
            }
        } else {
            _messages.value = _messages.value.map {
                if (it.id == id) it.copy(content = newContent, thinking = thinking) else it
            }
        }
    }

    suspend fun updateMessageBubbles(id: String, bubbles: List<String>, saveToDisk: Boolean = true) {
        initialLoad.join()
        if (saveToDisk) {
            mutateMessages { current ->
                current.map {
                    if (it.id == id) it.copy(bubbles = bubbles) else it
                }
            }
        } else {
            _messages.value = _messages.value.map {
                if (it.id == id) it.copy(bubbles = bubbles) else it
            }
        }
    }

    suspend fun clearMessages() {
        initialLoad.join()
        mutateMessages { emptyList() }
    }

    suspend fun resetConversation(greeting: String?) {
        initialLoad.join()
        mutateMessages { 
            if (greeting.isNullOrBlank()) emptyList()
            else listOf(
                ConversationMessage(
                    id = "welcome",
                    role = MessageRole.Assistant,
                    content = greeting,
                    createdAt = System.currentTimeMillis()
                )
            )
        }
    }

    suspend fun deleteMessage(id: String) {
        initialLoad.join()
        mutateMessages { current -> current.filter { it.id != id } }
    }

    suspend fun deleteMessageAndFollowing(id: String) {
        initialLoad.join()
        mutateMessages { current ->
            val index = current.indexOfFirst { it.id == id }
            if (index != -1) current.take(index) else current
        }
    }

    private suspend fun mutateMessages(transform: (List<ConversationMessage>) -> List<ConversationMessage>) {
        writeMutex.withLock {
            val updated = transform(_messages.value)
            _messages.value = updated
            jsonStore.write(
                slotRepository.currentConversationsFile(),
                messageListSerializer,
                updated
            )
        }
    }

    private fun defaultConversation(): List<ConversationMessage> {
        return listOf(
            ConversationMessage(
                id = "welcome",
                role = MessageRole.Assistant,
                content = "Hello, I am Fantareal. Configure your API key in Settings to begin.",
                createdAt = System.currentTimeMillis()
            )
        )
    }
}
