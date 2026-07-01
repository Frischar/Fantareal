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
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.frischar.fantareal.domain.rolecard.RoleCard
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
            }
        }
    }
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
