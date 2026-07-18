package com.frischar.fantareal.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.frischar.fantareal.data.repository.AppSettings
import com.frischar.fantareal.data.repository.SettingsRepository
import com.frischar.fantareal.domain.llm.ModelProviderPresets
import com.frischar.fantareal.domain.llm.OpenAiProvider
import com.frischar.fantareal.domain.llm.choosePreferredChatModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SettingsUiState(
    val apiBaseUrl: String = "https://api.openai.com/v1/",
    val apiKey: String = "",
    val model: String = "gpt-4o-mini",
    val selectedProviderId: String = "openai",
    val availableModels: List<String> = emptyList(),
    val isFetchingModels: Boolean = false,
    val modelStatus: String = "",
    val modelStatusIsError: Boolean = false,
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
    private var fetchModelsJob: Job? = null

    fun updateApiBaseUrl(value: String) {
        cancelModelFetch()
        _uiState.update {
            it.copy(
                apiBaseUrl = value,
                selectedProviderId = ModelProviderPresets.detect(value).id,
                availableModels = emptyList(),
                modelStatus = "",
                modelStatusIsError = false,
                saved = false
            )
        }
    }

    fun updateApiKey(value: String) {
        cancelModelFetch()
        _uiState.update {
            it.copy(
                apiKey = value,
                availableModels = emptyList(),
                modelStatus = "",
                modelStatusIsError = false,
                saved = false
            )
        }
    }

    fun updateModel(value: String) {
        _uiState.update { it.copy(model = value, modelStatusIsError = false, saved = false) }
    }

    fun selectProviderPreset(presetId: String) {
        cancelModelFetch()
        val preset = ModelProviderPresets.find(presetId)
        _uiState.update {
            it.copy(
                selectedProviderId = preset.id,
                availableModels = emptyList(),
                modelStatus = "",
                modelStatusIsError = false
            )
        }
    }

    fun applyProviderPresetAndFetch() {
        val current = _uiState.value
        val preset = ModelProviderPresets.find(current.selectedProviderId)
        _uiState.update {
            it.copy(
                apiBaseUrl = preset.baseUrl.ifBlank { it.apiBaseUrl },
                model = when {
                    preset.id == "custom" -> it.model
                    preset.recommendedModel.isNotBlank() -> preset.recommendedModel
                    else -> ""
                },
                availableModels = emptyList(),
                modelStatus = "已填入 ${preset.label} 预设。",
                modelStatusIsError = false,
                saved = false
            )
        }
        fetchModels(preset.recommendedModel)
    }

    fun fetchModels() {
        val preset = ModelProviderPresets.find(_uiState.value.selectedProviderId)
        fetchModels(preset.recommendedModel)
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
            _uiState.update { transientState ->
                settingsRepository.settings.value.toUiState(saved = true).copy(
                    selectedProviderId = transientState.selectedProviderId,
                    availableModels = transientState.availableModels,
                    isFetchingModels = transientState.isFetchingModels,
                    modelStatus = transientState.modelStatus,
                    modelStatusIsError = transientState.modelStatusIsError
                )
            }
        }
    }

    private fun fetchModels(recommendedModel: String) {
        cancelModelFetch()
        val current = _uiState.value
        if (current.apiBaseUrl.isBlank()) {
            _uiState.update {
                it.copy(modelStatus = "请先填写 API Base URL。", modelStatusIsError = true)
            }
            return
        }

        val preset = ModelProviderPresets.find(current.selectedProviderId)
        if (preset.requiresApiKey && current.apiKey.isBlank()) {
            _uiState.update {
                it.copy(
                    modelStatus = "预设已填入；请填写 API Key 后再刷新模型列表。",
                    modelStatusIsError = false
                )
            }
            return
        }

        _uiState.update {
            it.copy(
                isFetchingModels = true,
                modelStatus = "正在拉取模型列表…",
                modelStatusIsError = false
            )
        }
        fetchModelsJob = viewModelScope.launch {
            try {
                val models = OpenAiProvider(current.apiBaseUrl.trim(), current.apiKey.trim())
                    .fetchAvailableModels()
                val selected = choosePreferredChatModel(
                    currentModel = current.model,
                    recommendedModel = recommendedModel,
                    availableModels = models
                )
                val currentIsAvailable = current.model.isNotBlank() && current.model in models
                val status = when {
                    models.isEmpty() -> "模型列表为空，可以继续手动填写。"
                    selected.isNotBlank() && selected != current.model ->
                        "已拉取 ${models.size} 个模型，已选择 $selected。"
                    currentIsAvailable -> "已拉取 ${models.size} 个模型，当前模型可用。"
                    else -> "已拉取 ${models.size} 个模型，请从下拉列表选择聊天模型。"
                }
                _uiState.update {
                    it.copy(
                        model = selected.ifBlank { it.model },
                        availableModels = models,
                        isFetchingModels = false,
                        modelStatus = status,
                        modelStatusIsError = false,
                        saved = if (selected.isNotBlank() && selected != current.model) false else it.saved
                    )
                }
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (error: Exception) {
                _uiState.update {
                    it.copy(
                        isFetchingModels = false,
                        modelStatus = error.message ?: "拉取模型失败。",
                        modelStatusIsError = true
                    )
                }
            }
        }
    }

    private fun cancelModelFetch() {
        fetchModelsJob?.cancel()
        fetchModelsJob = null
        _uiState.update { it.copy(isFetchingModels = false) }
    }

    private fun AppSettings.toUiState(saved: Boolean = false): SettingsUiState {
        return SettingsUiState(
            apiBaseUrl = apiBaseUrl,
            apiKey = apiKey,
            model = model,
            selectedProviderId = ModelProviderPresets.detect(apiBaseUrl).id,
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
