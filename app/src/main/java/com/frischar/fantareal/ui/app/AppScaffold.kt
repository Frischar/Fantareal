package com.frischar.fantareal.ui.app

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.heightIn
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.Text
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.LocalUriHandler
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.frischar.fantareal.data.AppRepositories
import com.frischar.fantareal.ui.viewmodel.ChatViewModel
import com.frischar.fantareal.ui.viewmodel.MemoryViewModel
import com.frischar.fantareal.ui.viewmodel.PresetViewModel
import com.frischar.fantareal.ui.viewmodel.RoleCardViewModel
import com.frischar.fantareal.ui.viewmodel.SettingsViewModel
import com.frischar.fantareal.ui.viewmodel.WorldbookViewModel
import kotlinx.coroutines.launch

@Composable
fun AppScaffold() {
    val navController = rememberNavController()
    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val repositories = remember(context.applicationContext) {
        AppRepositories(context.applicationContext)
    }
    val settings by repositories.settingsRepository.settings.collectAsState()

    com.frischar.fantareal.ui.theme.FantarealTheme(darkTheme = settings.darkMode) {
        ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet(
                drawerShape = RoundedCornerShape(topEnd = 32.dp, bottomEnd = 32.dp),
                drawerContainerColor = MaterialTheme.colorScheme.surface,
                modifier = Modifier
                    .fillMaxWidth(0.65f)
                    .widthIn(min = 240.dp, max = 360.dp)
            ) {
                Column(modifier = Modifier.fillMaxSize()) {
                    Text("Fantareal", modifier = Modifier.padding(16.dp), style = MaterialTheme.typography.titleLarge)
                    HorizontalDivider(modifier = Modifier.padding(bottom = 8.dp))
                    ScreenRoute.values().forEach { route ->
                        NavigationDrawerItem(
                            label = { Text(route.title) },
                            selected = false,
                            onClick = {
                                scope.launch { drawerState.close() }
                                navController.navigate(route.route) {
                                    popUpTo(ScreenRoute.Chat.route) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp)
                        )
                    }

                    Spacer(modifier = Modifier.weight(1f))
                    
                    androidx.compose.foundation.Image(
                        painter = androidx.compose.ui.res.painterResource(id = com.frischar.fantareal.R.drawable.sidebar_mascot),
                        contentDescription = "Mascot",
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 32.dp)
                            .heightIn(max = 160.dp),
                        contentScale = ContentScale.Fit
                    )

                    val uriHandler = LocalUriHandler.current
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp)
                            .clip(RoundedCornerShape(8.dp))
                            .clickable {
                                uriHandler.openUri("https://discord.gg/fantareal")
                            }
                            .padding(8.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text("discord.gg/fantareal", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary)
                        Text("欢迎来DC频道交流讨论写卡喵~", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
        }
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            if (settings.backgroundImageUri != null) {
                coil.compose.AsyncImage(
                    model = settings.backgroundImageUri,
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize()
                )
            }
            Box(modifier = Modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.background.copy(alpha = settings.backgroundOpacity))) {
                NavHost(
                    navController = navController, 
                    startDestination = ScreenRoute.Chat.route,
                    enterTransition = { androidx.compose.animation.fadeIn(animationSpec = androidx.compose.animation.core.tween(150)) },
                    exitTransition = { androidx.compose.animation.fadeOut(animationSpec = androidx.compose.animation.core.tween(150)) },
                    popEnterTransition = { androidx.compose.animation.fadeIn(animationSpec = androidx.compose.animation.core.tween(150)) },
                    popExitTransition = { androidx.compose.animation.fadeOut(animationSpec = androidx.compose.animation.core.tween(150)) }
                ) {
                composable(ScreenRoute.Chat.route) {
                val chatViewModel: ChatViewModel = viewModel(
                    factory = object : androidx.lifecycle.ViewModelProvider.Factory {
                        @Suppress("UNCHECKED_CAST")
                        override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
                            val orchestrator = com.frischar.fantareal.app.usecase.ChatOrchestrator(
                                conversationRepository = repositories.conversationRepository,
                                settingsRepository = repositories.settingsRepository,
                                personaRepository = repositories.personaRepository,
                                memoryRepository = repositories.memoryRepository,
                                worldbookRepository = repositories.worldbookRepository,
                                presetRepository = repositories.presetRepository,
                                workshopRepository = repositories.workshopRepository,
                                stateJournalRepository = repositories.stateJournalRepository,
                                roleCardService = repositories.roleCardService
                            )
                            return ChatViewModel(orchestrator, repositories.conversationRepository, repositories.personaRepository) as T
                        }
                    }
                )
                val uiState by chatViewModel.uiState.collectAsState()
                val lastMsgId = uiState.messages.lastOrNull()?.id
                val mappedMessages = uiState.messages.map { 
                    com.frischar.fantareal.ui.chat.ChatMessageUiModel(
                        id = it.id,
                        role = if (it.role == com.frischar.fantareal.domain.chat.MessageRole.User) com.frischar.fantareal.ui.chat.UiRole.User else com.frischar.fantareal.ui.chat.UiRole.Assistant,
                        speakerName = if (it.role == com.frischar.fantareal.domain.chat.MessageRole.User) "User" else "AI",
                        avatarUri = if (it.role == com.frischar.fantareal.domain.chat.MessageRole.User) settings.userAvatarUri else settings.aiAvatarUri,
                        content = it.content,
                        createdAtText = "",
                        thinkingText = it.thinking,
                        error = it.error,
                        bubbles = it.bubbles,
                        isStreaming = uiState.isSending && it.id == lastMsgId && it.role == com.frischar.fantareal.domain.chat.MessageRole.Assistant
                    )
                }

                com.frischar.fantareal.ui.chat.ChatScreen(
                    personaName = uiState.personaName,
                    messages = mappedMessages,
                    isSending = uiState.isSending,
                    showAvatar = settings.showAvatar,
                    settings = settings,
                    onSendMessage = chatViewModel::sendMessage,
                    onEndChat = { chatViewModel.endChatAndSummarize() },
                    onDeleteMessage = chatViewModel::deleteMessage,
                    onRegenerateMessage = chatViewModel::regenerateMessage,
                    onOpenDrawer = { scope.launch { drawerState.open() } }
                )
                }
                composable(ScreenRoute.Settings.route) {
                val settingsViewModel: SettingsViewModel = viewModel(
                    factory = object : androidx.lifecycle.ViewModelProvider.Factory {
                        @Suppress("UNCHECKED_CAST")
                        override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
                            return SettingsViewModel(repositories.settingsRepository) as T
                        }
                    }
                )
                val uiState by settingsViewModel.uiState.collectAsState()

                com.frischar.fantareal.ui.settings.SettingsScreen(
                    uiState = uiState,
                    onBaseUrlChange = settingsViewModel::updateApiBaseUrl,
                    onApiKeyChange = settingsViewModel::updateApiKey,
                    onModelNameChange = settingsViewModel::updateModel,
                    onTemperatureChange = settingsViewModel::updateTemperature,
                    onSupportStreamingChange = settingsViewModel::updateSupportStreaming,
                    onOpenaiFormatChange = settingsViewModel::updateOpenaiFormat,
                    onDarkModeChange = settingsViewModel::updateDarkMode,
                    onShowAvatarChange = settingsViewModel::updateShowAvatar,
                    onBackgroundOpacityChange = settingsViewModel::updateBackgroundOpacity,
                    onFontSizeChange = settingsViewModel::updateFontSize,
                    onFontColorChange = settingsViewModel::updateFontColor,
                    onSplitRegexChange = settingsViewModel::updateSplitRegex,
                    onUseSmartSplitChange = settingsViewModel::updateUseSmartSplit,
                    onBackgroundImageUriChange = settingsViewModel::updateBackgroundImageUri,
                    onUserAvatarUriChange = settingsViewModel::updateUserAvatarUri,
                    onAiAvatarUriChange = settingsViewModel::updateAiAvatarUri,
                    onSave = settingsViewModel::save,
                    onOpenDrawer = { scope.launch { drawerState.open() } }
                )
                }
                composable(ScreenRoute.RoleCard.route) {
                val roleCardViewModel: RoleCardViewModel = viewModel(
                    factory = object : androidx.lifecycle.ViewModelProvider.Factory {
                        @Suppress("UNCHECKED_CAST")
                        override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
                            return RoleCardViewModel(
                                repositories.roleCardService,
                                repositories.personaRepository,
                                repositories.conversationRepository,
                                repositories.stateJournalRepository
                            ) as T
                        }
                    }
                )
                val uiState by roleCardViewModel.uiState.collectAsState()
                com.frischar.fantareal.ui.rolecard.RoleCardScreen(
                    uiState = uiState,
                    onImportBytes = roleCardViewModel::importFromBytes,
                    onExportJson = roleCardViewModel::exportJson,
                    onOpenDrawer = { scope.launch { drawerState.open() } }
                )
                }
                composable(ScreenRoute.Memory.route) {
                val memoryViewModel: MemoryViewModel = viewModel(
                    factory = object : androidx.lifecycle.ViewModelProvider.Factory {
                        @Suppress("UNCHECKED_CAST")
                        override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
                            return MemoryViewModel(repositories.memoryRepository, repositories.conversationRepository, repositories.personaRepository) as T
                        }
                    }
                )
                LaunchedEffect(memoryViewModel) {
                    memoryViewModel.reload()
                }
                val uiState by memoryViewModel.uiState.collectAsState()
                com.frischar.fantareal.ui.memory.MemoryScreen(
                    uiState = uiState,
                    onImportBytes = memoryViewModel::importFromBytes,
                    onExportJson = memoryViewModel::exportJson,
                    onDeleteEntry = memoryViewModel::deleteMemory,
                    onOpenDrawer = { scope.launch { drawerState.open() } }
                )
                }
                composable(ScreenRoute.Worldbook.route) {
                val worldbookViewModel: WorldbookViewModel = viewModel(
                    factory = object : androidx.lifecycle.ViewModelProvider.Factory {
                        @Suppress("UNCHECKED_CAST")
                        override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
                            return WorldbookViewModel(repositories.worldbookRepository, repositories.conversationRepository, repositories.personaRepository) as T
                        }
                    }
                )
                val uiState by worldbookViewModel.uiState.collectAsState()
                com.frischar.fantareal.ui.worldbook.WorldbookScreen(
                    uiState = uiState,
                    onImportBytes = worldbookViewModel::importFromBytes,
                    onExportJson = worldbookViewModel::exportJson,
                    onOpenDrawer = { scope.launch { drawerState.open() } }
                )
                }
                composable(ScreenRoute.Preset.route) {
                val presetViewModel: PresetViewModel = viewModel(
                    factory = object : androidx.lifecycle.ViewModelProvider.Factory {
                        @Suppress("UNCHECKED_CAST")
                        override fun <T : androidx.lifecycle.ViewModel> create(modelClass: Class<T>): T {
                            return PresetViewModel(repositories.presetRepository, repositories.conversationRepository, repositories.personaRepository) as T
                        }
                    }
                )
                val uiState by presetViewModel.uiState.collectAsState()
                com.frischar.fantareal.ui.preset.PresetScreen(
                    uiState = uiState,
                    onImportBytes = presetViewModel::importFromBytes,
                    onExportJson = presetViewModel::exportJson,
                    onPresetEnabledChange = presetViewModel::setEnabled,
                    onModuleEnabledChange = presetViewModel::setModuleEnabled,
                    onBlockEnabledChange = presetViewModel::setBlockEnabled,
                    onGroupEnabledChange = presetViewModel::setGroupEnabled,
                    onGroupItemEnabledChange = presetViewModel::setGroupItemEnabled,
                    onOpenDrawer = { scope.launch { drawerState.open() } }
                )
                }

            }
            }
        }
    }
    }
}
