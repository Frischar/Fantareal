package com.frischar.fantareal.ui.worldbook

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
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.frischar.fantareal.domain.worldbook.WorldbookEntry
import com.frischar.fantareal.ui.common.FantarealTopBar
import com.frischar.fantareal.ui.common.GlassPanel
import com.frischar.fantareal.ui.viewmodel.WorldbookUiState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WorldbookScreen(
    uiState: WorldbookUiState,
    onImportBytes: (ByteArray) -> Unit,
    onExportJson: ((String) -> Unit) -> Unit,
    onOpenDrawer: () -> Unit
) {
    Scaffold(containerColor = androidx.compose.ui.graphics.Color.Transparent, 
        topBar = {
            FantarealTopBar(title = "世界书（设定集）", onOpenDrawer = onOpenDrawer)
        }
    ) { paddingValues ->
        Column(modifier = Modifier.fillMaxSize().padding(paddingValues)) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(16.dp),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                val context = androidx.compose.ui.platform.LocalContext.current
                val exportLauncher = androidx.activity.compose.rememberLauncherForActivityResult(androidx.activity.result.contract.ActivityResultContracts.CreateDocument("application/json")) { uri -> uri?.let { destUri -> onExportJson { jsonString -> context.contentResolver.openOutputStream(destUri)?.use { out -> out.write(jsonString.toByteArray(Charsets.UTF_8)) }; android.widget.Toast.makeText(context, "导出成功", android.widget.Toast.LENGTH_SHORT).show() } } }
                val launcher = androidx.activity.compose.rememberLauncherForActivityResult(
                    androidx.activity.result.contract.ActivityResultContracts.GetContent()
                ) { uri ->
                    if (uri != null) {
                        try {
                            val inputStream = context.contentResolver.openInputStream(uri)
                            val bytes = inputStream?.readBytes()
                            if (bytes != null) {
                                onImportBytes(bytes)
                            }
                        } catch (e: Exception) {
                            android.widget.Toast.makeText(context, "读取失败", android.widget.Toast.LENGTH_SHORT).show()
                        }
                    }
                }

                OutlinedButton(onClick = { launcher.launch("*/*") }) {
                    Text("导入并覆盖世界书")
                }
                OutlinedButton(onClick = {
                    exportLauncher.launch("worldbook_export.json")
                }) {
                    Text("导出世界书")
                }
            }

            if (!uiState.statusMessage.isNullOrBlank()) {
                Text(
                    text = uiState.statusMessage,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.padding(horizontal = 16.dp)
                )
            }

            if (!uiState.error.isNullOrBlank()) {
                Text(
                    text = uiState.error,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(horizontal = 16.dp)
                )
            }

            LazyColumn(
                modifier = Modifier.fillMaxWidth().weight(1f),
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                if (uiState.entries.isEmpty()) {
                    item {
                        Text("当前没有任何世界书条目。", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                } else {
                    items(uiState.entries, key = { it.id }) { entry ->
                        WorldbookEntryCard(entry)
                    }
                }
            }
        }
    }
}

@Composable
fun WorldbookEntryCard(entry: WorldbookEntry) {
    GlassPanel(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("触发词: ${entry.primaryTriggers.joinToString(", ")}", style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
            if (entry.secondaryTriggers.isNotEmpty()) {
                Text("次要触发词: ${entry.secondaryTriggers.joinToString(", ")}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.secondary)
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(entry.content, style = MaterialTheme.typography.bodyMedium, maxLines = 5, overflow = TextOverflow.Ellipsis)
        }
    }
}
