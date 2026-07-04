package com.frischar.fantareal.data.repository

import android.content.Context
import android.content.SharedPreferences
import com.frischar.fantareal.data.security.SecretStore
import com.frischar.fantareal.data.storage.JsonStore
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.serialization.Serializable

data class AppSettings(
    val apiBaseUrl: String,
    val apiKey: String,
    val model: String,
    val temperature: Double,
    val supportStreaming: Boolean,
    val openaiFormat: Boolean,
    val darkMode: Boolean,
    val showAvatar: Boolean,
    val backgroundOpacity: Float = 0.5f,
    val backgroundImageUri: String? = null,
    val userAvatarUri: String? = null,
    val aiAvatarUri: String? = null,
    val fontSize: Float = 16f,
    val fontColor: String = "",
    val splitRegex: String = "",
    val useSmartSplit: Boolean = true
)

@Serializable
private data class StoredSettings(
    val apiBaseUrl: String = "https://api.openai.com/v1/",
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
    val useSmartSplit: Boolean = true
)

class SettingsRepository(
    context: Context,
    private val slotRepository: SlotRepository = SlotRepository(com.frischar.fantareal.data.storage.StoragePaths(context.applicationContext))
) {
    private val prefs: SharedPreferences = context.getSharedPreferences("fantareal_settings", Context.MODE_PRIVATE)
    private val secretStore = SecretStore(context.applicationContext)
    private val jsonStore = JsonStore()

    private val _settings = MutableStateFlow(loadSettings())
    val settings: StateFlow<AppSettings> = _settings

    fun loadSettings(): AppSettings {
        val migratedApiKey = migratePlaintextApiKeyIfNeeded()
        val storedSettings = runBlocking {
            jsonStore.read(
                slotRepository.paths.settingsFile(slotRepository.currentSlotId.value),
                StoredSettings.serializer(),
                defaultValue = legacyStoredSettings()
            )
        }
        return AppSettings(
            apiBaseUrl = storedSettings.apiBaseUrl,
            apiKey = migratedApiKey,
            model = storedSettings.model,
            temperature = storedSettings.temperature,
            supportStreaming = storedSettings.supportStreaming,
            openaiFormat = storedSettings.openaiFormat,
            darkMode = storedSettings.darkMode,
            showAvatar = storedSettings.showAvatar,
            backgroundOpacity = storedSettings.backgroundOpacity,
            backgroundImageUri = storedSettings.backgroundImageUri,
            userAvatarUri = storedSettings.userAvatarUri,
            aiAvatarUri = storedSettings.aiAvatarUri,
            fontSize = storedSettings.fontSize,
            fontColor = storedSettings.fontColor,
            splitRegex = storedSettings.splitRegex,
            useSmartSplit = storedSettings.useSmartSplit
        )
    }

    fun saveSettings(newSettings: AppSettings) {
        runBlocking {
            jsonStore.write(
                slotRepository.paths.settingsFile(slotRepository.currentSlotId.value),
                StoredSettings.serializer(),
                StoredSettings(
                    apiBaseUrl = newSettings.apiBaseUrl,
                    model = newSettings.model,
                    temperature = newSettings.temperature,
                    supportStreaming = newSettings.supportStreaming,
                    openaiFormat = newSettings.openaiFormat,
                    darkMode = newSettings.darkMode,
                    showAvatar = newSettings.showAvatar,
                    backgroundOpacity = newSettings.backgroundOpacity,
                    backgroundImageUri = newSettings.backgroundImageUri,
                    userAvatarUri = newSettings.userAvatarUri,
                    aiAvatarUri = newSettings.aiAvatarUri,
                    fontSize = newSettings.fontSize,
                    fontColor = newSettings.fontColor,
                    splitRegex = newSettings.splitRegex,
                    useSmartSplit = newSettings.useSmartSplit
                )
            )
        }
        prefs.edit()
            .putString("apiBaseUrl", newSettings.apiBaseUrl)
            .putString("model", newSettings.model)
            .putFloat("temperature", newSettings.temperature.toFloat())
            .putBoolean("supportStreaming", newSettings.supportStreaming)
            .putBoolean("openaiFormat", newSettings.openaiFormat)
            .putBoolean("darkMode", newSettings.darkMode)
            .putBoolean("showAvatar", newSettings.showAvatar)
            .putFloat("backgroundOpacity", newSettings.backgroundOpacity)
            .putString("backgroundImageUri", newSettings.backgroundImageUri)
            .putString("userAvatarUri", newSettings.userAvatarUri)
            .putString("aiAvatarUri", newSettings.aiAvatarUri)
            .putFloat("fontSize", newSettings.fontSize)
            .putString("fontColor", newSettings.fontColor)
            .putString("splitRegex", newSettings.splitRegex)
            .putBoolean("useSmartSplit", newSettings.useSmartSplit)
            .remove("apiKey")
            .apply()
        secretStore.saveApiKey(newSettings.apiKey)
        _settings.value = newSettings
    }

    suspend fun switchSlot(slotId: String) {
        slotRepository.switchSlot(slotId)
        _settings.value = loadSettings()
    }

    private fun migratePlaintextApiKeyIfNeeded(): String {
        val encryptedApiKey = secretStore.readApiKey()
        if (encryptedApiKey.isNotBlank()) return encryptedApiKey

        val plaintextApiKey = prefs.getString("apiKey", "") ?: ""
        if (plaintextApiKey.isNotBlank()) {
            secretStore.saveApiKey(plaintextApiKey)
            prefs.edit().remove("apiKey").apply()
        }
        return plaintextApiKey
    }

    private fun legacyStoredSettings(): StoredSettings {
        return StoredSettings(
            apiBaseUrl = prefs.getString("apiBaseUrl", "https://api.openai.com/v1/") ?: "https://api.openai.com/v1/",
            model = prefs.getString("model", "gpt-4o-mini") ?: "gpt-4o-mini",
            temperature = prefs.getFloat("temperature", 0.7f).toDouble(),
            supportStreaming = prefs.getBoolean("supportStreaming", true),
            openaiFormat = prefs.getBoolean("openaiFormat", true),
            darkMode = prefs.getBoolean("darkMode", true),
            showAvatar = prefs.getBoolean("showAvatar", true),
            backgroundOpacity = prefs.getFloat("backgroundOpacity", 0.5f),
            backgroundImageUri = prefs.getString("backgroundImageUri", null),
            userAvatarUri = prefs.getString("userAvatarUri", null),
            aiAvatarUri = prefs.getString("aiAvatarUri", null),
            fontSize = prefs.getFloat("fontSize", 16f),
            fontColor = prefs.getString("fontColor", "") ?: "",
            splitRegex = prefs.getString("splitRegex", "") ?: "",
            useSmartSplit = prefs.getBoolean("useSmartSplit", true)
        )
    }
}
