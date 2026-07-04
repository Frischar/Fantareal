package com.frischar.fantareal.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.frischar.fantareal.ui.common.FantarealTopBar
import com.frischar.fantareal.ui.common.GlassPanel
import com.frischar.fantareal.ui.viewmodel.SettingsUiState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    uiState: SettingsUiState,
    onBaseUrlChange: (String) -> Unit,
    onApiKeyChange: (String) -> Unit,
    onModelNameChange: (String) -> Unit,
    onTemperatureChange: (Double) -> Unit,
    onSupportStreamingChange: (Boolean) -> Unit,
    onOpenaiFormatChange: (Boolean) -> Unit,
    onDarkModeChange: (Boolean) -> Unit,
    onShowAvatarChange: (Boolean) -> Unit,
    onBackgroundOpacityChange: (Float) -> Unit,
    onFontSizeChange: (Float) -> Unit,
    onFontColorChange: (String) -> Unit,
    onSplitRegexChange: (String) -> Unit,
    onUseSmartSplitChange: (Boolean) -> Unit,
    onBackgroundImageUriChange: (String?) -> Unit,
    onUserAvatarUriChange: (String?) -> Unit,
    onAiAvatarUriChange: (String?) -> Unit,
    onSave: () -> Unit,
    onOpenDrawer: () -> Unit
) {
    Scaffold(containerColor = androidx.compose.ui.graphics.Color.Transparent, 
        topBar = {
            FantarealTopBar(title = "设置与模型", onOpenDrawer = onOpenDrawer)
        }
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                AppearanceCard(
                    darkMode = uiState.darkMode,
                    showAvatar = uiState.showAvatar,
                    backgroundOpacity = uiState.backgroundOpacity,
                    onDarkModeChange = onDarkModeChange,
                    onShowAvatarChange = onShowAvatarChange,
                    onBackgroundOpacityChange = onBackgroundOpacityChange,
                    fontSize = uiState.fontSize,
                    fontColor = uiState.fontColor,
                    splitRegex = uiState.splitRegex,
                    useSmartSplit = uiState.useSmartSplit,
                    onFontSizeChange = onFontSizeChange,
                    onFontColorChange = onFontColorChange,
                    onSplitRegexChange = onSplitRegexChange,
                    onUseSmartSplitChange = onUseSmartSplitChange,
                    onBackgroundImageUriChange = onBackgroundImageUriChange,
                    onUserAvatarUriChange = onUserAvatarUriChange,
                    onAiAvatarUriChange = onAiAvatarUriChange
                )
            }
            item {
                ApiSettingsCard(
                    uiState = uiState,
                    onBaseUrlChange = onBaseUrlChange,
                    onApiKeyChange = onApiKeyChange,
                    onModelNameChange = onModelNameChange,
                    onTemperatureChange = onTemperatureChange,
                    onSupportStreamingChange = onSupportStreamingChange,
                    onOpenaiFormatChange = onOpenaiFormatChange
                )
            }
            item {
                Button(
                    onClick = onSave,
                    modifier = Modifier.fillMaxWidth(),
                    enabled = !uiState.saved
                ) {
                    Text(if (uiState.saved) "已保存" else "保存设置")
                }
            }
        }
    }
}

@Composable
fun AppearanceCard(
    fontSize: Float,
    fontColor: String,
    splitRegex: String,
    onFontSizeChange: (Float) -> Unit,
    onFontColorChange: (String) -> Unit,
    onSplitRegexChange: (String) -> Unit,
    useSmartSplit: Boolean,
    onUseSmartSplitChange: (Boolean) -> Unit,
    darkMode: Boolean,
    showAvatar: Boolean,
    backgroundOpacity: Float,
    onDarkModeChange: (Boolean) -> Unit,
    onShowAvatarChange: (Boolean) -> Unit,
    onBackgroundOpacityChange: (Float) -> Unit,
    onBackgroundImageUriChange: (String?) -> Unit,
    onUserAvatarUriChange: (String?) -> Unit,
    onAiAvatarUriChange: (String?) -> Unit
) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val bgLauncher = androidx.activity.compose.rememberLauncherForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.OpenDocument()
    ) { uri -> uri?.let { 
        try { context.contentResolver.takePersistableUriPermission(it, android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION) } catch(e: Exception) {}
        onBackgroundImageUriChange(it.toString()) 
    } }
    
    val userAvatarLauncher = androidx.activity.compose.rememberLauncherForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.OpenDocument()
    ) { uri -> uri?.let { 
        try { context.contentResolver.takePersistableUriPermission(it, android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION) } catch(e: Exception) {}
        onUserAvatarUriChange(it.toString()) 
    } }
    
    val aiAvatarLauncher = androidx.activity.compose.rememberLauncherForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.OpenDocument()
    ) { uri -> uri?.let { 
        try { context.contentResolver.takePersistableUriPermission(it, android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION) } catch(e: Exception) {}
        onAiAvatarUriChange(it.toString()) 
    } }

    GlassPanel(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("外观设置", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
            
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text("深色模式")
                Switch(checked = darkMode, onCheckedChange = onDarkModeChange)
            }
            
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text("显示双方头像")
                Switch(checked = showAvatar, onCheckedChange = onShowAvatarChange)
            }

            Column(modifier = Modifier.fillMaxWidth()) {
                Text("全局背景透明度 (左侧=透明，右侧=暗色覆盖)")
                Slider(
                    value = backgroundOpacity,
                    onValueChange = onBackgroundOpacityChange,
                    valueRange = 0f..1f
                )
            }
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                Button(onClick = { bgLauncher.launch(arrayOf("image/*")) }) { Text("更换背景图") }
                Button(onClick = { onBackgroundImageUriChange(null) }) { Text("清除背景图") }
            }
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                Button(onClick = { userAvatarLauncher.launch(arrayOf("image/*")) }) { Text("用户头像") }
                Button(onClick = { aiAvatarLauncher.launch(arrayOf("image/*")) }) { Text("AI头像") }
            }
            Column {
                Text("聊天字体大小: ${String.format("%.1f", fontSize)}")
                Slider(
                    value = fontSize,
                    onValueChange = onFontSizeChange,
                    valueRange = 10f..30f
                )
            }
            Column(modifier = Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = fontColor,
                    onValueChange = onFontColorChange,
                    label = { Text("聊天字体颜色 (如 #FFFFFF，留空使用默认)") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
                val paletteColors = listOf(
                    "", "#FFFFFF", "#000000", "#FF5252", "#FF4081", "#E040FB", "#7C4DFF", 
                    "#536DFE", "#448AFF", "#40C4FF", "#18FFFF", "#64FFDA", "#69F0AE", 
                    "#B2FF59", "#EEFF41", "#FFFF00", "#FFD740", "#FFAB40", "#FF6E40"
                )
                LazyRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(paletteColors) { colorHex ->
                        val isSelected = fontColor.equals(colorHex, ignoreCase = true)
                        Box(
                            modifier = Modifier
                                .size(40.dp)
                                .clip(CircleShape)
                                .background(
                                    if (colorHex.isEmpty()) androidx.compose.ui.graphics.Color.Transparent 
                                    else try { androidx.compose.ui.graphics.Color(android.graphics.Color.parseColor(colorHex)) } catch (e: Exception) { androidx.compose.ui.graphics.Color.Transparent }
                                )
                                .border(
                                    width = if (isSelected) 3.dp else 1.dp,
                                    color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline,
                                    shape = CircleShape
                                )
                                .clickable { onFontColorChange(colorHex) },
                            contentAlignment = Alignment.Center
                        ) {
                            if (colorHex.isEmpty()) {
                                Text("默认", style = MaterialTheme.typography.labelSmall)
                            }
                        }
                    }
                }
            }
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text("子代理切分消息")
                Switch(checked = useSmartSplit, onCheckedChange = onUseSmartSplitChange)
            }
            if (!useSmartSplit) {
                OutlinedTextField(
                    value = splitRegex,
                    onValueChange = onSplitRegexChange,
                    label = { Text("AI输出分段正则切割 (留空则不切割)") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
            }
        }
    }
}

@Composable
fun ApiSettingsCard(
    uiState: SettingsUiState,
    onBaseUrlChange: (String) -> Unit,
    onApiKeyChange: (String) -> Unit,
    onModelNameChange: (String) -> Unit,
    onTemperatureChange: (Double) -> Unit,
    onSupportStreamingChange: (Boolean) -> Unit,
    onOpenaiFormatChange: (Boolean) -> Unit
) {
    GlassPanel(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("API 配置", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)

            OutlinedTextField(
                value = uiState.apiBaseUrl,
                onValueChange = onBaseUrlChange,
                label = { Text("Base URL (如 http://127.0.0.1:5000/v1)") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            OutlinedTextField(
                value = uiState.apiKey,
                onValueChange = onApiKeyChange,
                label = { Text("API Key") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            OutlinedTextField(
                value = uiState.model,
                onValueChange = onModelNameChange,
                label = { Text("Model Name") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            Column {
                Text("Temperature: ${String.format("%.2f", uiState.temperature)}")
                Slider(
                    value = uiState.temperature.toFloat(),
                    onValueChange = { onTemperatureChange(it.toDouble()) },
                    valueRange = 0f..2f
                )
            }

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text("支持流式 (Stream)")
                Switch(checked = uiState.supportStreaming, onCheckedChange = onSupportStreamingChange)
            }

            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text("使用 OpenAI 格式")
                Switch(checked = uiState.openaiFormat, onCheckedChange = onOpenaiFormatChange)
            }
        }
    }
}
