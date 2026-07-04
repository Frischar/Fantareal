package com.frischar.fantareal.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.frischar.fantareal.data.repository.AppSettings
import com.frischar.fantareal.data.repository.SettingsRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SettingsUiState(
    val apiBaseUrl: String = "https://api.openai.com/v1/",
    val apiKey: String = "",
    val model: String = "gpt-4o-mini",
    val temperature: Double = 0.7,
    val supportStreaming: Boolean = true,
    val openaiFormat: Boolean = true,
    val darkMode: Boolean = true,
    val showAvatar: Boolean = true,
    val backgroundOpacity: Float = 0.5f,
    val backgroundImageUri: String? = null,
    val userAvatarUri: String? = null,
    val aiAvatarUri: String? = null,
    val fontSize: Float = 16f,
    val fontColor: String = "",
    val splitRegex: String = "",
    val useSmartSplit: Boolean = true,
    val saved: Boolean = false
)

class SettingsViewModel(
    private val settingsRepository: SettingsRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(settingsRepository.settings.value.toUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    fun updateApiBaseUrl(value: String) {
        _uiState.update { it.copy(apiBaseUrl = value, saved = false) }
    }

    fun updateApiKey(value: String) {
        _uiState.update { it.copy(apiKey = value, saved = false) }
    }

    fun updateModel(value: String) {
        _uiState.update { it.copy(model = value, saved = false) }
    }

    fun updateTemperature(value: Double) {
        _uiState.update { it.copy(temperature = value, saved = false) }
    }

    fun updateSupportStreaming(value: Boolean) {
        _uiState.update { it.copy(supportStreaming = value, saved = false) }
        save()
    }

    fun updateOpenaiFormat(value: Boolean) {
        _uiState.update { it.copy(openaiFormat = value, saved = false) }
        save()
    }

    fun updateDarkMode(value: Boolean) {
        _uiState.update { it.copy(darkMode = value, saved = false) }
        save()
    }

    fun updateShowAvatar(value: Boolean) {
        _uiState.update { it.copy(showAvatar = value, saved = false) }
        save()
    }

    fun updateBackgroundOpacity(value: Float) {
        _uiState.update { it.copy(backgroundOpacity = value, saved = false) }
    }

    fun updateBackgroundImageUri(value: String?) {
        _uiState.update { it.copy(backgroundImageUri = value, saved = false) }
        save()
    }

    fun updateUserAvatarUri(value: String?) {
        _uiState.update { it.copy(userAvatarUri = value, saved = false) }
        save()
    }

    fun updateAiAvatarUri(value: String?) {
        _uiState.update { it.copy(aiAvatarUri = value, saved = false) }
        save()
    }

    fun updateFontSize(value: Float) { _uiState.update { it.copy(fontSize = value, saved = false) } }
    fun updateFontColor(value: String) { _uiState.update { it.copy(fontColor = value, saved = false) } }
    fun updateSplitRegex(value: String) { _uiState.update { it.copy(splitRegex = value, saved = false) } }
    fun updateUseSmartSplit(value: Boolean) {
        _uiState.update { it.copy(useSmartSplit = value, saved = false) }
        save()
    }

    fun save() {
        val current = _uiState.value
        viewModelScope.launch(Dispatchers.IO) {
            settingsRepository.saveSettings(
                AppSettings(
                    apiBaseUrl = current.apiBaseUrl.trim(),
                    apiKey = current.apiKey.trim(),
                    model = current.model.trim(),
                    temperature = current.temperature,
                    supportStreaming = current.supportStreaming,
                    openaiFormat = current.openaiFormat,
                    darkMode = current.darkMode,
                    showAvatar = current.showAvatar,
                    backgroundOpacity = current.backgroundOpacity,
                    backgroundImageUri = current.backgroundImageUri,
                    userAvatarUri = current.userAvatarUri,
                    aiAvatarUri = current.aiAvatarUri,
                    fontSize = current.fontSize,
                    fontColor = current.fontColor,
                    splitRegex = current.splitRegex,
                    useSmartSplit = current.useSmartSplit
                )
            )
            _uiState.update { settingsRepository.settings.value.toUiState(saved = true) }
        }
    }

    private fun AppSettings.toUiState(saved: Boolean = false): SettingsUiState {
        return SettingsUiState(
            apiBaseUrl = apiBaseUrl,
            apiKey = apiKey,
            model = model,
            temperature = temperature,
            supportStreaming = supportStreaming,
            openaiFormat = openaiFormat,
            darkMode = darkMode,
            showAvatar = showAvatar,
            backgroundOpacity = backgroundOpacity,
            backgroundImageUri = backgroundImageUri,
            userAvatarUri = userAvatarUri,
            aiAvatarUri = aiAvatarUri,
            fontSize = fontSize,
            fontColor = fontColor,
            splitRegex = splitRegex,
            useSmartSplit = useSmartSplit,
            saved = saved
        )
    }
}
