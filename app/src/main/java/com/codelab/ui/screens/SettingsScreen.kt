package com.codelab.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.SdStorage
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import com.codelab.ui.theme.HtmlGreen
import com.codelab.ui.theme.StorageBar
import com.codelab.viewmodel.EditorViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(viewModel: EditorViewModel, onBack: () -> Unit) {
    val storageUsed by remember { viewModel.storageManager.usedSpace }
    val usagePercent by remember { mutableStateOf(viewModel.storageManager.getUsagePercentage()) }
    val usedFormatted = viewModel.storageManager.getUsedSpaceFormatted()
    val freeFormatted = viewModel.storageManager.getFreeSpaceFormatted()

    var hardwareToggle by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF1A73E8),
                    titleContentColor = Color.White,
                    navigationIconContentColor = Color.White
                )
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .verticalScroll(rememberScrollState())
                .padding(16.dp)
        ) {
            Text(
                text = "Editor",
                style = MaterialTheme.typography.titleMedium,
                color = Color(0xFF1A73E8)
            )

            Spacer(modifier = Modifier.height(8.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color.White)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { }
                        .padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Default Language", style = MaterialTheme.typography.bodyLarge)
                        Text(
                            "HTML",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color(0xFF5F6368)
                        )
                    }
                    Icon(Icons.Default.ChevronRight, contentDescription = null, tint = Color(0xFF9AA0A6))
                }
            }

            Spacer(modifier = Modifier.height(4.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color.White)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Font Size", style = MaterialTheme.typography.bodyLarge)
                        Text(
                            "14px",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color(0xFF5F6368)
                        )
                    }
                    Icon(Icons.Default.ChevronRight, contentDescription = null, tint = Color(0xFF9AA0A6))
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Text(
                text = "Advanced",
                style = MaterialTheme.typography.titleMedium,
                color = Color(0xFF1A73E8)
            )

            Spacer(modifier = Modifier.height(8.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color.White)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Hardware Free Use", style = MaterialTheme.typography.bodyLarge)
                        Text(
                            "Enable hardware acceleration",
                            style = MaterialTheme.typography.bodySmall,
                            color = Color(0xFF5F6368)
                        )
                    }
                    Switch(
                        checked = hardwareToggle,
                        onCheckedChange = {
                            hardwareToggle = it
                            if (it) viewModel.openRickRoll()
                        }
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Text(
                text = "Storage",
                style = MaterialTheme.typography.titleMedium,
                color = Color(0xFF1A73E8)
            )

            Spacer(modifier = Modifier.height(8.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color.White)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.SdStorage, contentDescription = null, tint = Color(0xFF1A73E8))
                        Spacer(modifier = Modifier.width(12.dp))
                        Text("250 GB Virtual Storage", style = MaterialTheme.typography.bodyLarge)
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    LinearProgressIndicator(
                        progress = { usagePercent / 100f },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(8.dp),
                        color = StorageBar,
                        trackColor = Color(0xFFE8EAED)
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    Row(modifier = Modifier.fillMaxWidth()) {
                        Text("Used: $usedFormatted", color = Color(0xFF5F6368), fontSize = androidx.compose.ui.unit.sp(13))
                        Spacer(modifier = Modifier.weight(1f))
                        Text("Free: $freeFormatted", color = Color(0xFF5F6368), fontSize = androidx.compose.ui.unit.sp(13))
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { viewModel.openStorageInfo() }
                            .padding(vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            "Manage Files",
                            color = Color(0xFF1A73E8),
                            style = MaterialTheme.typography.bodyMedium
                        )
                        Icon(Icons.Default.ChevronRight, contentDescription = null, tint = Color(0xFF1A73E8))
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            Text(
                text = "About",
                style = MaterialTheme.typography.titleMedium,
                color = Color(0xFF1A73E8)
            )

            Spacer(modifier = Modifier.height(8.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = Color.White)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Codelab v1.0", style = MaterialTheme.typography.titleMedium)
                    Text("html and python ide", style = MaterialTheme.typography.bodyMedium, color = Color(0xFF5F6368))

                    Spacer(modifier = Modifier.height(12.dp))

                    Text("Platforms", style = MaterialTheme.typography.bodyMedium, color = Color(0xFF5F6368))
                    Spacer(modifier = Modifier.height(4.dp))

                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("\u2022 ", color = HtmlGreen)
                        Text("Android", color = HtmlGreen, fontFamily = FontFamily.Monospace)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("active", color = HtmlGreen, fontSize = androidx.compose.ui.unit.sp(12))
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("\u2022 ", color = Color(0xFF9AA0A6))
                        Text("iOS", color = Color(0xFF9AA0A6))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("wip", color = Color(0xFF9AA0A6), fontSize = androidx.compose.ui.unit.sp(12))
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("\u2022 ", color = Color(0xFF9AA0A6))
                        Text("macOS", color = Color(0xFF9AA0A6))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("wip", color = Color(0xFF9AA0A6), fontSize = androidx.compose.ui.unit.sp(12))
                    }
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("\u2022 ", color = Color(0xFF9AA0A6))
                        Text("Windows", color = Color(0xFF9AA0A6))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("wip", color = Color(0xFF9AA0A6), fontSize = androidx.compose.ui.unit.sp(12))
                    }
                }
            }
        }
    }
}
