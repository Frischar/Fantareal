package com.frischar.fantareal.ui.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.ui.unit.sp
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.frischar.fantareal.ui.common.GlassPanel
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.combinedClickable
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.foundation.clickable
enum class UiRole { User, Assistant }

data class ChatMessageUiModel(
    val id: String,
    val role: UiRole,
    val speakerName: String,
    val avatarUri: String?,
    val content: String,
    val createdAtText: String,
    val isStreaming: Boolean,
    val spriteTag: String? = null,
    val thinkingText: String? = null,
    val error: Boolean = false,
    val bubbles: List<String>? = null
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(personaName: String = "Fantareal", 
    onOpenDrawer: () -> Unit,
    messages: List<ChatMessageUiModel>,
    isSending: Boolean,
    showAvatar: Boolean = true,
    settings: com.frischar.fantareal.data.repository.AppSettings,
    onSendMessage: (String) -> Unit,
    onEndChat: () -> Unit,
    onDeleteMessage: (String) -> Unit = {},
    onRegenerateMessage: (String) -> Unit = {}
) {
    val listState = rememberLazyListState()

    val isAtBottom by androidx.compose.runtime.remember {
        androidx.compose.runtime.derivedStateOf {
            val visibleItems = listState.layoutInfo.visibleItemsInfo
            if (visibleItems.isEmpty()) true
            else {
                val firstVisibleItem = visibleItems.first()
                firstVisibleItem.index <= 1
            }
        }
    }

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty() && isAtBottom && !listState.isScrollInProgress) {
            listState.animateScrollToItem(0)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .imePadding()
            .background(Color.Transparent)
    ) {
        TopAppBar(
            title = {
                Text(personaName, style = MaterialTheme.typography.titleMedium)
            },
            actions = {
                IconButton(onClick = onEndChat, enabled = !isSending) {
                    Icon(imageVector = Icons.AutoMirrored.Filled.Send, contentDescription = "结束本轮对话并压缩成记忆条目", tint = MaterialTheme.colorScheme.onSurface)
                }
            },
            navigationIcon = {
                IconButton(onClick = onOpenDrawer) {
                    Icon(Icons.Default.Menu, contentDescription = "打开菜单", tint = MaterialTheme.colorScheme.onSurface)
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = Color.Transparent,
                titleContentColor = MaterialTheme.colorScheme.onBackground,
                navigationIconContentColor = MaterialTheme.colorScheme.onBackground
            )
        )

        if (messages.isEmpty()) {
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "说点什么来开始对话吧~",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f)
                )
            }
        } else {
            LazyColumn(
                state = listState,
                reverseLayout = true,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                items(messages.reversed(), key = { it.id }) { msg ->
                    if (msg.role == UiRole.User) {
                        MessageBubble(message = msg, showAvatar = showAvatar, settings = settings, allowRegenerate = true, onDelete = { onDeleteMessage(msg.id) }, onRegenerate = { onRegenerateMessage(msg.id) })
                    } else {
                        Column {
                            val splitRegex = settings.splitRegex
                            val contents = if (settings.useSmartSplit) {
                                if (msg.bubbles.isNullOrEmpty()) {
                                    if (msg.isStreaming) listOf("思考剧情中...") else listOf(msg.content)
                                } else {
                                    msg.bubbles
                                }
                            } else if (splitRegex.isNotBlank()) {
                                try {
                                    val parts = msg.content.split(Regex(splitRegex)).filter { it.isNotBlank() }
                                    val mergedParts = mutableListOf<String>()
                                    for (part in parts) {
                                        if (mergedParts.isNotEmpty() && part.trim().matches(Regex("^[”’\"'\\]）}】》\\s]+$"))) {
                                            mergedParts[mergedParts.size - 1] = mergedParts.last() + part
                                        } else {
                                            mergedParts.add(part)
                                        }
                                    }
                                    mergedParts
                                } catch (e: Exception) {
                                    listOf(msg.content)
                                }
                            } else {
                                if (msg.content.isNotBlank()) listOf(msg.content) else emptyList()
                            }

                            // 1. Status Bubble (only shown when streaming just started and no content yet)
                            val shouldShowStatusBubble = msg.isStreaming && contents.isEmpty()
                            
                            if (shouldShowStatusBubble) {
                                MessageBubble(
                                    message = msg.copy(
                                        content = "正在生成中...",
                                        thinkingText = null,
                                        isStreaming = true
                                    ),
                                    showAvatar = showAvatar,
                                    settings = settings,
                                    isThinkingBubble = false,
                                    allowRegenerate = true,
                                    onDelete = { onDeleteMessage(msg.id) },
                                    onRegenerate = { onRegenerateMessage(msg.id) }
                                )
                            }

                            // 2. Content Bubbles with smooth fade-in animation
                            var visibleCount by androidx.compose.runtime.remember(msg.id) { 
                                androidx.compose.runtime.mutableStateOf(if (msg.isStreaming) 0 else contents.size) 
                            }
                            val currentContentsSize by androidx.compose.runtime.rememberUpdatedState(contents.size)
                            
                            androidx.compose.runtime.LaunchedEffect(msg.id) {
                                while (true) {
                                    if (visibleCount < currentContentsSize) {
                                        kotlinx.coroutines.delay(500)
                                        visibleCount++
                                    } else {
                                        kotlinx.coroutines.delay(100)
                                    }
                                }
                            }

                            contents.forEachIndexed { index, part ->
                                val isVisible = index < visibleCount
                                androidx.compose.animation.AnimatedVisibility(
                                    visible = isVisible,
                                    enter = androidx.compose.animation.fadeIn() + androidx.compose.animation.expandVertically()
                                ) {
                                    Column {
                                        if (index > 0 || shouldShowStatusBubble) Spacer(modifier = Modifier.height(16.dp))
                                        val isLastPart = index == contents.size - 1
                                        MessageBubble(
                                            message = msg.copy(
                                                content = part, 
                                                thinkingText = null,
                                                isStreaming = if (isLastPart) msg.isStreaming else false
                                            ), 
                                            showAvatar = if (!shouldShowStatusBubble && index == 0) showAvatar else false,
                                            settings = settings, 
                                            isThinkingBubble = false,
                                            allowRegenerate = if (!shouldShowStatusBubble && index == 0) true else false,
                                            onDelete = if (!shouldShowStatusBubble && index == 0) { { onDeleteMessage(msg.id) } } else { {} },
                                            onRegenerate = if (!shouldShowStatusBubble && index == 0) { { onRegenerateMessage(msg.id) } } else { {} }
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        ComposerBar(isSending = isSending, onSend = onSendMessage)
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun MessageBubble(
    message: ChatMessageUiModel, 
    showAvatar: Boolean = true, 
    settings: com.frischar.fantareal.data.repository.AppSettings,
    isThinkingBubble: Boolean = false,
    allowRegenerate: Boolean = true,
    onDelete: () -> Unit = {},
    onRegenerate: () -> Unit = {}
) {
    val isUser = message.role == UiRole.User
    var showMenu by remember { mutableStateOf(false) }
    val clipboardManager = LocalClipboardManager.current
    val haptic = LocalHapticFeedback.current

    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start
    ) {
        if (!isUser && showAvatar) {
            if (message.avatarUri != null) {
                coil.compose.AsyncImage(
                    model = message.avatarUri,
                    contentDescription = null,
                    modifier = Modifier
                        .size(40.dp)
                        .clip(CircleShape),
                    contentScale = androidx.compose.ui.layout.ContentScale.Crop
                )
            } else {
                Box(
                    modifier = Modifier
                        .size(40.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.surfaceVariant)
                )
            }
            Spacer(modifier = Modifier.width(8.dp))
        }

        Box(modifier = Modifier.weight(1f, fill = false)) {
            GlassPanel(
                modifier = Modifier
                    .combinedClickable(
                        onClick = {},
                        onLongClick = {
                            haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                            showMenu = true
                        }
                    ),
                shape = RoundedCornerShape(
                    topStart = 16.dp,
                    topEnd = 16.dp,
                    bottomStart = if (isUser) 16.dp else 4.dp,
                    bottomEnd = if (isUser) 4.dp else 16.dp
                ),
                color = if (isUser) MaterialTheme.colorScheme.primary.copy(alpha = 0.2f) else MaterialTheme.colorScheme.surface.copy(alpha = 0.6f),
                borderColor = if (isUser) MaterialTheme.colorScheme.primary.copy(alpha = 0.5f) else MaterialTheme.colorScheme.outline
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    if (!isUser && showAvatar) {
                        Text(
                            text = message.speakerName,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(bottom = 4.dp)
                        )
                    }
                    if (!message.thinkingText.isNullOrBlank()) {
                        var expanded by androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf(false) }
                        androidx.compose.foundation.layout.Column(modifier = Modifier.padding(bottom = 8.dp)) {
                            androidx.compose.foundation.layout.Row(
                                verticalAlignment = Alignment.CenterVertically,
                                modifier = Modifier
                                    .clip(RoundedCornerShape(4.dp))
                                    .clickable { expanded = !expanded }
                                    .padding(vertical = 4.dp, horizontal = 8.dp)
                            ) {
                                Text(
                                    text = "思考过程",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.primary
                                )
                                Icon(
                                    imageVector = if (expanded) Icons.Filled.KeyboardArrowUp else Icons.Filled.KeyboardArrowDown,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.size(16.dp)
                                )
                            }
                            androidx.compose.animation.AnimatedVisibility(visible = expanded) {
                                Text(
                                    text = message.thinkingText,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.8f),
                                    modifier = Modifier
                                        .padding(start = 8.dp, end = 8.dp, bottom = 8.dp)
                                        .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f), RoundedCornerShape(8.dp))
                                        .padding(8.dp)
                                )
                            }
                        }
                    }
                    val displayText = message.content.ifBlank {
                        if (message.isStreaming) "正在生成中..." else ""
                    }
                    if (displayText.isNotBlank()) {
                        val parsedContent = parseMarkdown(displayText, MaterialTheme.colorScheme.surfaceVariant)
                        
                        val defaultColor = MaterialTheme.colorScheme.onSurface
                        val userColor = try {
                            if (settings.fontColor.isNotBlank()) {
                                androidx.compose.ui.graphics.Color(android.graphics.Color.parseColor(settings.fontColor))
                            } else {
                                defaultColor
                            }
                        } catch (e: Exception) {
                            defaultColor
                        }

                        Text(
                            text = parsedContent,
                            color = userColor,
                            fontSize = settings.fontSize.sp
                        )
                    }
                }
            }
            
            DropdownMenu(
                expanded = showMenu,
                onDismissRequest = { showMenu = false }
            ) {
                val copyText = if (isThinkingBubble) message.thinkingText ?: "" else message.content
                DropdownMenuItem(
                    text = { Text("复制") },
                    onClick = {
                        clipboardManager.setText(AnnotatedString(copyText))
                        showMenu = false
                    }
                )
                if (!isUser && allowRegenerate) {
                    DropdownMenuItem(
                        text = { Text("重新生成") },
                        onClick = {
                            onRegenerate()
                            showMenu = false
                        }
                    )
                }
                if (allowRegenerate) {
                    DropdownMenuItem(
                        text = { Text("删除该消息及后续") },
                        onClick = {
                            onDelete()
                            showMenu = false
                        }
                    )
                }
            }
        }

        if (isUser && showAvatar) {
            Spacer(modifier = Modifier.width(8.dp))
            if (message.avatarUri != null) {
                coil.compose.AsyncImage(
                    model = message.avatarUri,
                    contentDescription = null,
                    modifier = Modifier
                        .size(40.dp)
                        .clip(CircleShape),
                    contentScale = androidx.compose.ui.layout.ContentScale.Crop
                )
            } else {
                Box(
                    modifier = Modifier
                        .size(40.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.primary)
                )
            }
        }
    }
}



@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ComposerBar(isSending: Boolean, onSend: (String) -> Unit) {
    var text by remember { mutableStateOf("") }
    val haptic = LocalHapticFeedback.current
    fun submit() {
        val trimmed = text.trim()
        if (trimmed.isNotBlank() && !isSending) {
            haptic.performHapticFeedback(HapticFeedbackType.TextHandleMove)
            onSend(trimmed)
            text = ""
        }
    }

    GlassPanel(
        modifier = Modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .padding(16.dp),
        shape = RoundedCornerShape(24.dp)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            TextField(
                value = text,
                onValueChange = { text = it },
                modifier = Modifier.weight(1f),
                enabled = !isSending,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Default),
                placeholder = { Text("说点什么...", color = MaterialTheme.colorScheme.onSurfaceVariant) },
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = Color.Transparent,
                    unfocusedContainerColor = Color.Transparent,
                    disabledContainerColor = Color.Transparent,
                    focusedIndicatorColor = Color.Transparent,
                    unfocusedIndicatorColor = Color.Transparent,
                    disabledIndicatorColor = Color.Transparent
                ),
                maxLines = 4
            )

            IconButton(
                enabled = !isSending,
                onClick = { submit() },
                modifier = Modifier
                    .background(MaterialTheme.colorScheme.primary, CircleShape)
            ) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.Send,
                    contentDescription = "发送",
                    tint = MaterialTheme.colorScheme.onPrimary
                )
            }
        }
    }
}
