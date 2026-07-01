package com.frischar.fantareal.ui.workshop

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
import androidx.compose.material3.AssistChip
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.frischar.fantareal.ui.common.FantarealTopBar
import com.frischar.fantareal.ui.common.GlassPanel
import com.frischar.fantareal.ui.viewmodel.WorkshopUiState

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WorkshopScreen(
    uiState: WorkshopUiState,
    onOpenDrawer: () -> Unit
) {
    val state = uiState.state
    Scaffold(
        topBar = {
            FantarealTopBar(title = "创意工坊（阶段剧本）", onOpenDrawer = onOpenDrawer)
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
                GlassPanel(modifier = Modifier.fillMaxWidth(), color = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f)) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("当前剧情进度", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
                        Text("阶段 ${state.stage}: ${state.stageName}", style = MaterialTheme.typography.titleLarge)
                        Text("好感/状态: ${state.affinity} / 100", style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
            item {
                Text("阶段提示", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
            }
            item {
                WorkshopEventCard("当前注入", "Prompt Builder", state.stagePrompt)
            }
        }
    }
}

@Composable
fun WorkshopEventCard(title: String, condition: String, action: String) {
    val context = androidx.compose.ui.platform.LocalContext.current
    GlassPanel(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Spacer(modifier = Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                AssistChip(onClick = { android.widget.Toast.makeText(context, "提示词来源", android.widget.Toast.LENGTH_SHORT).show() }, label = { Text("来源: $condition") })
                AssistChip(onClick = { android.widget.Toast.makeText(context, "提示词动作", android.widget.Toast.LENGTH_SHORT).show() }, label = { Text("动作: 注入提示") })
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(action, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
