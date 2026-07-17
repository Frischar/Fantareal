package com.frischar.fantareal.ui.rolecard

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
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.HorizontalDivider
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.frischar.fantareal.domain.rolecard.RoleCard
import com.frischar.fantareal.domain.statejournal.StateJournalConfig
import com.frischar.fantareal.domain.statejournal.StateJournalRuntime
import com.frischar.fantareal.ui.common.FantarealTopBar
import com.frischar.fantareal.ui.common.GlassPanel
import com.frischar.fantareal.ui.viewmodel.RoleCardUiState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RoleCardScreen(
    uiState: RoleCardUiState,
    onImportBytes: (String, ByteArray) -> Unit,
    onExportJson: ((String) -> Unit) -> Unit,
    onOpenDrawer: () -> Unit
) {
    val card = uiState.roleCard
    val context = androidx.compose.ui.platform.LocalContext.current

    val exportLauncher = androidx.activity.compose.rememberLauncherForActivityResult(
        androidx.activity.result.contract.ActivityResultContracts.CreateDocument("application/json")
    ) { uri ->
        uri?.let { destUri ->
            onExportJson { jsonString ->
                context.contentResolver.openOutputStream(destUri)?.use { out ->
                    out.write(jsonString.toByteArray(Charsets.UTF_8))
                }
                android.widget.Toast.makeText(context, "导出成功", android.widget.Toast.LENGTH_SHORT).show()
            }
        }
    }

    Scaffold(containerColor = androidx.compose.ui.graphics.Color.Transparent, 
        topBar = {
            FantarealTopBar(title = "角色卡（主人物）", onOpenDrawer = onOpenDrawer)
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
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    val launcher = androidx.activity.compose.rememberLauncherForActivityResult(
                        androidx.activity.result.contract.ActivityResultContracts.GetContent()
                    ) { uri ->
                        if (uri != null) {
                            try {
                                val inputStream = context.contentResolver.openInputStream(uri)
                                val bytes = inputStream?.readBytes()
                                if (bytes != null) {
                                    onImportBytes("imported_card", bytes)
                                }
                            } catch (e: Exception) {
                                android.widget.Toast.makeText(context, "读取失败", android.widget.Toast.LENGTH_SHORT).show()
                            }
                        }
                    }

                    OutlinedButton(onClick = { launcher.launch("*/*") }) {
                        Text("导入并覆盖角色卡")
                    }
                    OutlinedButton(onClick = { exportLauncher.launch("rolecard_export.json") }) {
                        Text("导出当前卡")
                    }
                }
            }

            if (!uiState.statusMessage.isNullOrBlank()) {
                item {
                    Text(uiState.statusMessage, color = MaterialTheme.colorScheme.primary)
                }
            }

            if (!uiState.error.isNullOrBlank()) {
                item {
                    Text(uiState.error, color = MaterialTheme.colorScheme.error)
                }
            }

            if (card == null) {
                item {
                    Text("当前没有载入角色卡。请导入一个角色卡来开始。", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            } else {
                item {
                    RoleCardDetails(card)
                }
                if (uiState.stateJournalConfig.enabled && !uiState.stateJournalRuntime?.roles.isNullOrEmpty()) {
                    item {
                        StateJournalPanel(
                            config = uiState.stateJournalConfig,
                            runtime = requireNotNull(uiState.stateJournalRuntime)
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun StateJournalPanel(config: StateJournalConfig, runtime: StateJournalRuntime) {
    val roleDefinitions = config.roles.associateBy { it.roleId }
    GlassPanel(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("幕笺 · StateJournal", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
            if (runtime.displayTitle.isNotBlank()) {
                Spacer(modifier = Modifier.height(6.dp))
                Text(runtime.displayTitle, style = MaterialTheme.typography.titleMedium)
            }
            if (runtime.displaySummary.isNotBlank()) {
                Text(runtime.displaySummary, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }

            runtime.roles.forEachIndexed { index, role ->
                if (index > 0) {
                    Spacer(modifier = Modifier.height(14.dp))
                    HorizontalDivider()
                    Spacer(modifier = Modifier.height(14.dp))
                } else {
                    Spacer(modifier = Modifier.height(14.dp))
                }
                Text(
                    "${role.roleName} · ${role.activeStageName.ifBlank { role.activeStageKey }}",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.secondary
                )
                if (role.stageChanged && role.previousStageName.isNotBlank()) {
                    Text(
                        "阶段变化：${role.previousStageName} → ${role.activeStageName}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary
                    )
                }

                val visibleVariables = role.variables.filter { it.display }
                if (visibleVariables.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("变量", style = MaterialTheme.typography.titleSmall)
                    visibleVariables.forEach { variable ->
                        val deltaText = when {
                            variable.delta > 0.000001 -> "  +${formatJournalNumber(variable.delta)}"
                            variable.delta < -0.000001 -> "  ${formatJournalNumber(variable.delta)}"
                            else -> ""
                        }
                        Text(
                            "${variable.name}：${formatJournalNumber(variable.value)} / ${formatJournalNumber(variable.maximum)}$deltaText",
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                }

                val labels = roleDefinitions[role.roleId]?.snapshotFields.orEmpty().associate { it.key to it.label }
                val visibleSnapshots = role.snapshots.filterValues { it.isNotBlank() }
                if (visibleSnapshots.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text("本轮幕笺", style = MaterialTheme.typography.titleSmall)
                    visibleSnapshots.forEach { (key, value) ->
                        Text(
                            "${labels[key] ?: key}：$value",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
    }
}

private fun formatJournalNumber(value: Double): String {
    val whole = value.toLong()
    return if (kotlin.math.abs(value - whole.toDouble()) < 0.000001) whole.toString()
    else "%.2f".format(value).trimEnd('0').trimEnd('.')
}

@Composable
fun RoleCardDetails(card: RoleCard) {
    GlassPanel(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(card.name.ifBlank { "未命名" }, style = MaterialTheme.typography.headlineSmall, color = MaterialTheme.colorScheme.primary)
            Spacer(modifier = Modifier.height(8.dp))
            Text("描述", style = MaterialTheme.typography.titleSmall)
            Text(card.description.ifBlank { "无" }, style = MaterialTheme.typography.bodyMedium, maxLines = 5, overflow = TextOverflow.Ellipsis)
            
            Spacer(modifier = Modifier.height(12.dp))
            Text("性格", style = MaterialTheme.typography.titleSmall)
            Text(card.personality.ifBlank { "无" }, style = MaterialTheme.typography.bodyMedium, maxLines = 3, overflow = TextOverflow.Ellipsis)

            Spacer(modifier = Modifier.height(12.dp))
            Text("设定/剧情前情", style = MaterialTheme.typography.titleSmall)
            Text(card.scenario.ifBlank { "无" }, style = MaterialTheme.typography.bodyMedium, maxLines = 3, overflow = TextOverflow.Ellipsis)

            Spacer(modifier = Modifier.height(12.dp))
            Text("初次问候", style = MaterialTheme.typography.titleSmall)
            Text(card.firstMes.ifBlank { "无" }, style = MaterialTheme.typography.bodyMedium, maxLines = 3, overflow = TextOverflow.Ellipsis)
        }
    }
}
