package com.frischar.fantareal.ui.memory

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.frischar.fantareal.domain.memory.LongTermMemory
import com.frischar.fantareal.ui.common.FantarealTopBar
import com.frischar.fantareal.ui.common.GlassPanel
import com.frischar.fantareal.ui.viewmodel.MemoryUiState
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MemoryScreen(
    uiState: MemoryUiState,
    onImportBytes: (ByteArray) -> Unit,
    onExportJson: ((String) -> Unit) -> Unit,
    onDeleteEntry: (String) -> Unit,
    onOpenDrawer: () -> Unit
) {
    val context = LocalContext.current
    val importLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let { val bytes = context.contentResolver.openInputStream(it)?.readBytes(); if (bytes != null) onImportBytes(bytes) }
    }
    val exportLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        uri?.let { destUri -> onExportJson { jsonString -> context.contentResolver.openOutputStream(destUri)?.use { out -> out.write(jsonString.toByteArray(Charsets.UTF_8)) } } }
    }

    Scaffold(containerColor = androidx.compose.ui.graphics.Color.Transparent, 
        topBar = {
            FantarealTopBar(title = "记忆（动态信息）", onOpenDrawer = onOpenDrawer)
        }
    ) { paddingValues ->
        Column(modifier = Modifier.fillMaxSize().padding(paddingValues)) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(16.dp),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                OutlinedButton(onClick = { importLauncher.launch("*/*") }) {
                    Text("导入并覆盖记忆集")
                }
                OutlinedButton(onClick = { exportLauncher.launch("memories_export.json") }) {
                    Text("导出记忆集")
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
                if (uiState.memories.isEmpty()) {
                    item {
                        Text("当前没有任何记忆记录。", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                } else {
                    items(uiState.memories, key = { it.id }) { entry ->
                        MemoryCard(entry = entry, onDelete = { onDeleteEntry(entry.id) })
                    }
                }
            }
        }
    }
}

@Composable
fun MemoryCard(entry: LongTermMemory, onDelete: () -> Unit) {
    val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault())
    val dateText = sdf.format(Date(entry.createdAt))

    GlassPanel(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text("记忆记录: ${entry.id.takeLast(4)}", style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.primary)
                IconButton(onClick = onDelete) {
                    Icon(Icons.Default.Delete, contentDescription = "删除记录", tint = MaterialTheme.colorScheme.error)
                }
            }
            Text("时间: $dateText", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Spacer(modifier = Modifier.height(8.dp))
            Text(entry.text, style = MaterialTheme.typography.bodyMedium, maxLines = 10, overflow = TextOverflow.Ellipsis)
        }
    }
}
