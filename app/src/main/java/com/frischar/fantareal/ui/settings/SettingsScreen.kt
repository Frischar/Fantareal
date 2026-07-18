package com.frischar.fantareal.ui.settings

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.frischar.fantareal.domain.llm.ModelProviderPresets
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
    onProviderPresetChange: (String) -> Unit,
    onApplyProviderPreset: () -> Unit,
    onFetchModels: () -> Unit,
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
                    onProviderPresetChange = onProviderPresetChange,
                    onApplyProviderPreset = onApplyProviderPreset,
                    onFetchModels = onFetchModels,
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
    onProviderPresetChange: (String) -> Unit,
    onApplyProviderPreset: () -> Unit,
    onFetchModels: () -> Unit,
    onTemperatureChange: (Double) -> Unit,
    onSupportStreamingChange: (Boolean) -> Unit,
    onOpenaiFormatChange: (Boolean) -> Unit
) {
    var modelPickerVisible by remember { mutableStateOf(false) }
    var modelSearchQuery by remember { mutableStateOf("") }
    val selectedPreset = ModelProviderPresets.find(uiState.selectedProviderId)
    val modelOptions = buildList {
        if (uiState.model.isNotBlank() && uiState.model !in uiState.availableModels) {
            add(uiState.model)
        }
        addAll(uiState.availableModels)
    }

    GlassPanel(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    "模型服务",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary
                )
                Text(
                    "选择服务商，填写凭据并获取账号可用模型。",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f)
            ) {
                Column(
                    modifier = Modifier.padding(vertical = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        "服务商预设",
                        modifier = Modifier.padding(horizontal = 12.dp),
                        style = MaterialTheme.typography.labelLarge
                    )
                    LazyRow(
                        modifier = Modifier.fillMaxWidth(),
                        contentPadding = PaddingValues(horizontal = 12.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(ModelProviderPresets.all, key = { it.id }) { preset ->
                            FilterChip(
                                selected = preset.id == selectedPreset.id,
                                onClick = { onProviderPresetChange(preset.id) },
                                label = { Text(preset.label) },
                                enabled = !uiState.isFetchingModels
                            )
                        }
                    }
                    Text(
                        selectedPreset.helper,
                        modifier = Modifier.padding(horizontal = 12.dp),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            OutlinedTextField(
                value = uiState.apiBaseUrl,
                onValueChange = onBaseUrlChange,
                label = { Text("API Base URL") },
                placeholder = { Text("http://127.0.0.1:5000/v1") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            OutlinedTextField(
                value = uiState.apiKey,
                onValueChange = onApiKeyChange,
                label = { Text("API Key") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                visualTransformation = PasswordVisualTransformation(),
                supportingText = { Text("使用系统密钥加密保存在本机") }
            )

            Button(
                onClick = onApplyProviderPreset,
                modifier = Modifier.fillMaxWidth(),
                enabled = !uiState.isFetchingModels
            ) {
                Text(if (uiState.isFetchingModels) "正在获取模型…" else "应用预设并获取模型")
            }

            HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.18f))

            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("聊天模型", style = MaterialTheme.typography.titleSmall)

                OutlinedTextField(
                    value = uiState.model,
                    onValueChange = onModelNameChange,
                    label = { Text("Model Name") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    trailingIcon = {
                        TextButton(
                            onClick = {
                                modelSearchQuery = ""
                                modelPickerVisible = true
                            },
                            enabled = !uiState.isFetchingModels && modelOptions.isNotEmpty()
                        ) {
                            Text("选择")
                        }
                    }
                )

                if (modelPickerVisible) {
                    ModelPickerDialog(
                        models = modelOptions,
                        selectedModel = uiState.model,
                        searchQuery = modelSearchQuery,
                        onSearchQueryChange = { modelSearchQuery = it },
                        onSelectModel = { modelName ->
                            onModelNameChange(modelName)
                            modelPickerVisible = false
                        },
                        onDismiss = { modelPickerVisible = false }
                    )
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    if (uiState.modelStatus.isNotBlank()) {
                        Text(
                            text = uiState.modelStatus,
                            modifier = Modifier.weight(1f),
                            style = MaterialTheme.typography.bodySmall,
                            color = if (uiState.modelStatusIsError) {
                                MaterialTheme.colorScheme.error
                            } else {
                                MaterialTheme.colorScheme.onSurfaceVariant
                            }
                        )
                    } else {
                        Spacer(modifier = Modifier.weight(1f))
                    }
                    TextButton(
                        onClick = onFetchModels,
                        enabled = !uiState.isFetchingModels
                    ) {
                        val countSuffix = uiState.availableModels.takeIf { it.isNotEmpty() }
                            ?.let { " (${it.size})" }
                            .orEmpty()
                        Text(if (uiState.isFetchingModels) "获取中…" else "刷新模型$countSuffix")
                    }
                }
            }

            HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.18f))

            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("生成参数", style = MaterialTheme.typography.titleSmall)
                    Text(
                        String.format("%.2f", uiState.temperature),
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
                Slider(
                    value = uiState.temperature.toFloat(),
                    onValueChange = { onTemperatureChange(it.toDouble()) },
                    valueRange = 0f..2f
                )
            }

            SettingsToggleRow(
                title = "流式响应",
                description = "生成时逐步显示回复内容",
                checked = uiState.supportStreaming,
                onCheckedChange = onSupportStreamingChange
            )

            SettingsToggleRow(
                title = "OpenAI 兼容格式",
                description = "使用 chat/completions 请求结构",
                checked = uiState.openaiFormat,
                onCheckedChange = onOpenaiFormatChange
            )
        }
    }
}

@Composable
private fun ModelPickerDialog(
    models: List<String>,
    selectedModel: String,
    searchQuery: String,
    onSearchQueryChange: (String) -> Unit,
    onSelectModel: (String) -> Unit,
    onDismiss: () -> Unit
) {
    val filteredModels = if (searchQuery.isBlank()) {
        models
    } else {
        models.filter { it.contains(searchQuery.trim(), ignoreCase = true) }
    }

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp, vertical = 48.dp),
            contentAlignment = Alignment.Center
        ) {
            Surface(
                modifier = Modifier
                    .widthIn(max = 480.dp)
                    .fillMaxWidth(),
                shape = RoundedCornerShape(24.dp),
                color = MaterialTheme.colorScheme.surface,
                tonalElevation = 8.dp,
                border = BorderStroke(
                    width = 1.dp,
                    color = MaterialTheme.colorScheme.outline.copy(alpha = 0.22f)
                )
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text("选择聊天模型", style = MaterialTheme.typography.titleMedium)
                            Text(
                                "共 ${models.size} 个候选模型",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        TextButton(onClick = onDismiss) {
                            Text("关闭")
                        }
                    }

                    OutlinedTextField(
                        value = searchQuery,
                        onValueChange = onSearchQueryChange,
                        label = { Text("搜索模型") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )

                    if (filteredModels.isEmpty()) {
                        Text(
                            "没有匹配的模型",
                            modifier = Modifier.padding(vertical = 24.dp),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    } else {
                        LazyColumn(
                            modifier = Modifier.heightIn(max = 360.dp),
                            verticalArrangement = Arrangement.spacedBy(4.dp)
                        ) {
                            items(filteredModels, key = { it }) { modelName ->
                                val selected = modelName == selectedModel
                                Surface(
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(12.dp),
                                    color = if (selected) {
                                        MaterialTheme.colorScheme.primary.copy(alpha = 0.12f)
                                    } else {
                                        MaterialTheme.colorScheme.surface
                                    }
                                ) {
                                    Row(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .heightIn(min = 56.dp)
                                            .clickable { onSelectModel(modelName) }
                                            .padding(horizontal = 8.dp, vertical = 4.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        RadioButton(selected = selected, onClick = null)
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text(
                                            modelName,
                                            modifier = Modifier.weight(1f),
                                            style = MaterialTheme.typography.bodyLarge,
                                            maxLines = 2,
                                            overflow = TextOverflow.Ellipsis
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SettingsToggleRow(
    title: String,
    description: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(2.dp)
        ) {
            Text(title, style = MaterialTheme.typography.bodyLarge)
            Text(
                description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Spacer(modifier = Modifier.width(12.dp))
        Switch(checked = checked, onCheckedChange = onCheckedChange)
    }
}
