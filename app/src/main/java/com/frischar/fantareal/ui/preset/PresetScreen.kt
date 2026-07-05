package com.frischar.fantareal.ui.preset

import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.frischar.fantareal.domain.preset.PresetBlock
import com.frischar.fantareal.domain.preset.PresetGroup
import com.frischar.fantareal.domain.preset.PresetGroupItem
import com.frischar.fantareal.domain.preset.PresetModule
import com.frischar.fantareal.domain.preset.PromptPreset
import com.frischar.fantareal.ui.common.FantarealTopBar
import com.frischar.fantareal.ui.common.GlassPanel
import com.frischar.fantareal.ui.viewmodel.PresetUiState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PresetScreen(
    uiState: PresetUiState,
    onImportBytes: (ByteArray) -> Unit,
    onExportJson: ((String) -> Unit) -> Unit,
    onPresetEnabledChange: (String, Boolean) -> Unit,
    onModuleEnabledChange: (String, String, Boolean) -> Unit,
    onBlockEnabledChange: (String, String, Boolean) -> Unit,
    onGroupEnabledChange: (String, String, Boolean) -> Unit,
    onGroupItemEnabledChange: (String, String, String, Boolean) -> Unit,
    onOpenDrawer: () -> Unit
) {
    val context = LocalContext.current
    val exportLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("application/json")
    ) { uri ->
        uri?.let { destUri ->
            onExportJson { jsonString ->
                context.contentResolver.openOutputStream(destUri)?.use { output ->
                    output.write(jsonString.toByteArray(Charsets.UTF_8))
                }
                Toast.makeText(context, "导出成功", Toast.LENGTH_SHORT).show()
            }
        }
    }
    val importLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        try {
            val bytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
            if (bytes != null) {
                onImportBytes(bytes)
            }
        } catch (_: Exception) {
            Toast.makeText(context, "读取失败", Toast.LENGTH_SHORT).show()
        }
    }

    Scaffold(
        containerColor = Color.Transparent,
        topBar = {
            FantarealTopBar(title = "预设（指令集）", onOpenDrawer = onOpenDrawer)
        }
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            item {
                PresetWorkbenchPanel(
                    totalCount = uiState.presets.size,
                    enabledCount = uiState.presets.count { it.enabled },
                    switchCount = uiState.presets.sumOf { it.switchableItemCount() },
                    enabledSwitchCount = uiState.presets.sumOf { it.enabledSwitchableItemCount() }
                )
            }
            item {
                PresetActionPanel(
                    onImport = { importLauncher.launch("*/*") },
                    onExport = { exportLauncher.launch("presets_export.json") }
                )
            }
            if (!uiState.statusMessage.isNullOrBlank()) {
                item {
                    PresetNoticePanel(
                        text = uiState.statusMessage,
                        isError = false
                    )
                }
            }
            if (!uiState.error.isNullOrBlank()) {
                item {
                    PresetNoticePanel(
                        text = uiState.error,
                        isError = true
                    )
                }
            }
            if (uiState.presets.isEmpty()) {
                item {
                    PresetEmptyState()
                }
            } else {
                itemsIndexed(uiState.presets, key = { _, preset -> preset.id }) { index, preset ->
                    PresetCard(
                        preset = preset,
                        index = index,
                        isActive = preset.enabled,
                        onToggle = { active -> onPresetEnabledChange(preset.id, active) },
                        onModuleEnabledChange = onModuleEnabledChange,
                        onBlockEnabledChange = onBlockEnabledChange,
                        onGroupEnabledChange = onGroupEnabledChange,
                        onGroupItemEnabledChange = onGroupItemEnabledChange
                    )
                }
            }
        }
    }
}

@Composable
private fun PresetWorkbenchPanel(
    totalCount: Int,
    enabledCount: Int,
    switchCount: Int,
    enabledSwitchCount: Int
) {
    GlassPanel(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        color = MaterialTheme.colorScheme.surface.copy(alpha = 0.54f),
        borderColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.24f)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Text(
                text = "Preset library",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = "全局预设库",
                style = MaterialTheme.typography.titleLarge,
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = "导入 PC 预设后，可以直接查看和切换内置模块、规则块、分组与词条。",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
            Spacer(modifier = Modifier.height(14.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                PresetMetric(label = "预设总数", value = totalCount.toString(), modifier = Modifier.weight(1f))
                PresetMetric(label = "启用中", value = enabledCount.toString(), modifier = Modifier.weight(1f))
            }
            if (switchCount > 0) {
                Spacer(modifier = Modifier.height(10.dp))
                PresetMetric(
                    label = "分项开关",
                    value = "$enabledSwitchCount/$switchCount",
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }
    }
}

@Composable
private fun PresetMetric(label: String, value: String, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.42f),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.18f))
    ) {
        Column(modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp)) {
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = value,
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

@Composable
private fun PresetActionPanel(onImport: () -> Unit, onExport: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        PresetActionButton(
            text = "导入并覆盖",
            onClick = onImport,
            modifier = Modifier.weight(1f)
        )
        PresetActionButton(
            text = "导出预设",
            onClick = onExport,
            modifier = Modifier.weight(1f)
        )
    }
}

@Composable
private fun PresetActionButton(text: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier.height(52.dp),
        shape = RoundedCornerShape(18.dp),
        colors = ButtonDefaults.outlinedButtonColors(
            containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.28f),
            contentColor = MaterialTheme.colorScheme.primary
        ),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = 0.28f)),
        contentPadding = PaddingValues(horizontal = 10.dp)
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.Bold,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
    }
}

@Composable
private fun PresetNoticePanel(text: String, isError: Boolean) {
    val color = if (isError) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        color = color.copy(alpha = 0.12f),
        border = BorderStroke(1.dp, color.copy(alpha = 0.32f))
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
            style = MaterialTheme.typography.bodyMedium,
            color = color,
            fontWeight = FontWeight.SemiBold
        )
    }
}

@Composable
private fun PresetEmptyState() {
    GlassPanel(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(22.dp),
        color = MaterialTheme.colorScheme.surface.copy(alpha = 0.46f),
        borderColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.18f)
    ) {
        Column(
            modifier = Modifier.padding(22.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "当前没有任何预设记录",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "可以导入 PC 端导出的预设 JSON，导入后会覆盖当前预设库。",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
fun PresetCard(
    preset: PromptPreset,
    index: Int,
    isActive: Boolean,
    onToggle: (Boolean) -> Unit,
    onModuleEnabledChange: (String, String, Boolean) -> Unit,
    onBlockEnabledChange: (String, String, Boolean) -> Unit,
    onGroupEnabledChange: (String, String, Boolean) -> Unit,
    onGroupItemEnabledChange: (String, String, String, Boolean) -> Unit
) {
    val accent = MaterialTheme.colorScheme.primary
    val hasDetails = preset.hasStructuredContent()
    var expanded by rememberSaveable(preset.id) { mutableStateOf(index == 0 && hasDetails) }

    GlassPanel(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(22.dp),
        color = MaterialTheme.colorScheme.surface.copy(alpha = if (isActive) 0.64f else 0.48f),
        borderColor = if (isActive) accent.copy(alpha = 0.48f) else MaterialTheme.colorScheme.outline.copy(alpha = 0.20f)
    ) {
        Column(modifier = Modifier.padding(18.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.Top
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        PresetIndexBadge(index = index + 1, isActive = isActive)
                        Spacer(modifier = Modifier.width(8.dp))
                        PresetStateChip(text = if (isActive) "启用" else "停用", isActive = isActive)
                    }
                    Spacer(modifier = Modifier.height(10.dp))
                    Text(
                        text = preset.title.ifBlank { "未命名预设" },
                        style = MaterialTheme.typography.titleLarge,
                        color = if (isActive) accent else MaterialTheme.colorScheme.onSurface,
                        fontWeight = FontWeight.Bold,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )
                }
                Spacer(modifier = Modifier.width(14.dp))
                Switch(
                    checked = isActive,
                    onCheckedChange = onToggle,
                    colors = presetSwitchColors()
                )
            }
            Spacer(modifier = Modifier.height(14.dp))
            Text(
                text = preset.runtimeContent().ifBlank { "这个预设还没有可注入内容。" },
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = if (expanded) 7 else 4,
                overflow = TextOverflow.Ellipsis
            )
            Spacer(modifier = Modifier.height(14.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "${preset.runtimeContent().length} 字",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    if (preset.switchableItemCount() > 0) {
                        Text(
                            text = "分项 ${preset.enabledSwitchableItemCount()}/${preset.switchableItemCount()} 已开启",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                if (hasDetails) {
                    TextButton(onClick = { expanded = !expanded }) {
                        Text(
                            text = if (expanded) "收起分项" else "展开分项",
                            fontWeight = FontWeight.Bold
                        )
                    }
                } else {
                    Text(
                        text = if (isActive) "聊天时会注入" else "保留但不注入",
                        style = MaterialTheme.typography.labelMedium,
                        color = if (isActive) accent else MaterialTheme.colorScheme.onSurfaceVariant,
                        fontWeight = if (isActive) FontWeight.Bold else FontWeight.Medium
                    )
                }
            }

            if (expanded && hasDetails) {
                Spacer(modifier = Modifier.height(14.dp))
                PresetDetailList(
                    preset = preset,
                    onModuleEnabledChange = onModuleEnabledChange,
                    onBlockEnabledChange = onBlockEnabledChange,
                    onGroupEnabledChange = onGroupEnabledChange,
                    onGroupItemEnabledChange = onGroupItemEnabledChange
                )
            }
        }
    }
}

@Composable
private fun PresetDetailList(
    preset: PromptPreset,
    onModuleEnabledChange: (String, String, Boolean) -> Unit,
    onBlockEnabledChange: (String, String, Boolean) -> Unit,
    onGroupEnabledChange: (String, String, Boolean) -> Unit,
    onGroupItemEnabledChange: (String, String, String, Boolean) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        if (preset.baseSystemPrompt.isNotBlank()) {
            PresetReadOnlySection(
                title = "基础指令",
                description = "随总开关注入",
                content = preset.baseSystemPrompt
            )
        }
        if (preset.modules.isNotEmpty()) {
            PresetModuleSection(
                presetId = preset.id,
                modules = preset.modules,
                onModuleEnabledChange = onModuleEnabledChange
            )
        }
        if (preset.promptGroups.isNotEmpty()) {
            PresetGroupSection(
                presetId = preset.id,
                groups = preset.promptGroups,
                onGroupEnabledChange = onGroupEnabledChange,
                onGroupItemEnabledChange = onGroupItemEnabledChange
            )
        }
        if (preset.extraPrompts.isNotEmpty()) {
            PresetBlockSection(
                presetId = preset.id,
                blocks = preset.extraPrompts,
                onBlockEnabledChange = onBlockEnabledChange
            )
        }
    }
}

@Composable
private fun PresetReadOnlySection(title: String, description: String, content: String) {
    PresetSectionSurface(title = title, description = description) {
        Text(
            text = content,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface,
            maxLines = 5,
            overflow = TextOverflow.Ellipsis
        )
    }
}

@Composable
private fun PresetModuleSection(
    presetId: String,
    modules: List<PresetModule>,
    onModuleEnabledChange: (String, String, Boolean) -> Unit
) {
    PresetSectionSurface(title = "内置模块", description = "${modules.count { it.enabled }}/${modules.size} 已开启") {
        modules.forEachIndexed { index, module ->
            if (index > 0) PresetDivider()
            PresetToggleRow(
                title = module.title,
                description = module.content.ifBlank { module.key },
                checked = module.enabled,
                onCheckedChange = { checked -> onModuleEnabledChange(presetId, module.key, checked) }
            )
        }
    }
}

@Composable
private fun PresetBlockSection(
    presetId: String,
    blocks: List<PresetBlock>,
    onBlockEnabledChange: (String, String, Boolean) -> Unit
) {
    PresetSectionSurface(title = "规则块", description = "${blocks.count { it.enabled }}/${blocks.size} 已开启") {
        blocks.forEachIndexed { index, block ->
            if (index > 0) PresetDivider()
            PresetToggleRow(
                title = block.title,
                description = "${block.metaLabel()}\n${block.content.ifBlank { "空规则块" }}",
                checked = block.enabled,
                onCheckedChange = { checked -> onBlockEnabledChange(presetId, block.id, checked) }
            )
        }
    }
}

@Composable
private fun PresetGroupSection(
    presetId: String,
    groups: List<PresetGroup>,
    onGroupEnabledChange: (String, String, Boolean) -> Unit,
    onGroupItemEnabledChange: (String, String, String, Boolean) -> Unit
) {
    PresetSectionSurface(title = "规则分组", description = "${groups.count { it.enabled }}/${groups.size} 组开启") {
        groups.forEachIndexed { groupIndex, group ->
            if (groupIndex > 0) PresetDivider()
            PresetToggleRow(
                title = group.title,
                description = if (group.selectionMode == "multiple") "多选分组" else "单选分组",
                checked = group.enabled,
                onCheckedChange = { checked -> onGroupEnabledChange(presetId, group.id, checked) }
            )
            if (group.items.isNotEmpty()) {
                Spacer(modifier = Modifier.height(8.dp))
                group.items.forEachIndexed { itemIndex, item ->
                    if (itemIndex > 0) PresetSubDivider()
                    PresetGroupItemRow(
                        item = item,
                        checked = group.isItemSelected(item),
                        groupEnabled = group.enabled,
                        onCheckedChange = { checked ->
                            onGroupItemEnabledChange(presetId, group.id, item.id, checked)
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun PresetGroupItemRow(
    item: PresetGroupItem,
    checked: Boolean,
    groupEnabled: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    val textColor = if (groupEnabled && checked) {
        MaterialTheme.colorScheme.onSurface
    } else {
        MaterialTheme.colorScheme.onSurfaceVariant
    }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(start = 12.dp, top = 6.dp, bottom = 6.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = item.title,
                style = MaterialTheme.typography.titleSmall,
                color = textColor,
                fontWeight = FontWeight.SemiBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Text(
                text = "${item.metaLabel()}\n${item.content.ifBlank { "空词条" }}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
        }
        Spacer(modifier = Modifier.width(12.dp))
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            colors = presetSwitchColors()
        )
    }
}

@Composable
private fun PresetSectionSurface(
    title: String,
    description: String,
    content: @Composable () -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.22f),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.16f))
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleSmall,
                    color = MaterialTheme.colorScheme.onSurface,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = description,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            Spacer(modifier = Modifier.height(10.dp))
            content()
        }
    }
}

@Composable
private fun PresetToggleRow(
    title: String,
    description: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 6.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.onSurface,
                fontWeight = FontWeight.SemiBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Text(
                text = description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
        }
        Spacer(modifier = Modifier.width(12.dp))
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            colors = presetSwitchColors()
        )
    }
}

@Composable
private fun PresetDivider() {
    HorizontalDivider(
        modifier = Modifier.padding(vertical = 6.dp),
        color = MaterialTheme.colorScheme.outline.copy(alpha = 0.14f)
    )
}

@Composable
private fun PresetSubDivider() {
    HorizontalDivider(
        modifier = Modifier.padding(start = 12.dp, top = 2.dp, bottom = 2.dp),
        color = MaterialTheme.colorScheme.outline.copy(alpha = 0.08f)
    )
}

@Composable
private fun PresetIndexBadge(index: Int, isActive: Boolean) {
    val color = if (isActive) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
    Box(
        modifier = Modifier
            .size(30.dp)
            .clip(CircleShape)
            .background(color.copy(alpha = if (isActive) 0.18f else 0.10f)),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = index.toString().padStart(2, '0'),
            style = MaterialTheme.typography.labelSmall,
            color = color,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
private fun PresetStateChip(text: String, isActive: Boolean) {
    val color = if (isActive) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
    Surface(
        shape = RoundedCornerShape(999.dp),
        color = color.copy(alpha = if (isActive) 0.14f else 0.08f),
        border = BorderStroke(1.dp, color.copy(alpha = if (isActive) 0.34f else 0.16f))
    ) {
        Text(
            text = text,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
            style = MaterialTheme.typography.labelMedium,
            color = color,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
private fun presetSwitchColors() = SwitchDefaults.colors(
    checkedThumbColor = MaterialTheme.colorScheme.onPrimary,
    checkedTrackColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.70f),
    uncheckedThumbColor = MaterialTheme.colorScheme.onSurfaceVariant,
    uncheckedTrackColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.70f)
)
