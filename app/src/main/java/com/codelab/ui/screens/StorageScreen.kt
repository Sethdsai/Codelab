package com.codelab.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.background
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.SdStorage
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.codelab.ui.theme.HtmlGreen
import com.codelab.ui.theme.PythonOrange
import com.codelab.ui.theme.StorageBar
import com.codelab.viewmodel.EditorViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StorageScreen(viewModel: EditorViewModel, onBack: () -> Unit) {
    val files by viewModel.savedFiles.collectAsState()
    val usedFormatted = viewModel.storageManager.getUsedSpaceFormatted()
    val freeFormatted = viewModel.storageManager.getFreeSpaceFormatted()
    val usagePercent = viewModel.storageManager.getUsagePercentage()
    var deleteTarget by remember { mutableStateOf<String?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Storage") },
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
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(containerColor = Color.White)
                ) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                Icons.Default.SdStorage,
                                contentDescription = null,
                                tint = Color(0xFF1A73E8),
                                modifier = Modifier.size(32.dp)
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Column {
                                Text("Total Storage", style = androidx.compose.material3.MaterialTheme.typography.bodyMedium, color = Color(0xFF5F6368))
                                Text("250 GB", style = androidx.compose.material3.MaterialTheme.typography.headlineMedium)
                            }
                        }

                        Spacer(modifier = Modifier.height(20.dp))

                        LinearProgressIndicator(
                            progress = usagePercent / 100f,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(10.dp),
                            color = StorageBar,
                            trackColor = Color(0xFFE8EAED),
                        )

                        Spacer(modifier = Modifier.height(12.dp))

                        Row(modifier = Modifier.fillMaxWidth()) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text("Used", color = Color(0xFF5F6368), fontSize = 12.sp)
                                Text(usedFormatted, style = androidx.compose.material3.MaterialTheme.typography.titleMedium)
                            }
                            Column(modifier = Modifier.weight(1f), horizontalAlignment = Alignment.End) {
                                Text("Free", color = Color(0xFF5F6368), fontSize = 12.sp)
                                Text(freeFormatted, style = androidx.compose.material3.MaterialTheme.typography.titleMedium)
                            }
                        }
                    }
                }
            }

            item {
                Spacer(modifier = Modifier.height(8.dp))
                Text("Files", style = androidx.compose.material3.MaterialTheme.typography.titleMedium, color = Color(0xFF1A73E8))
                Spacer(modifier = Modifier.height(4.dp))
            }

            if (files.isEmpty()) {
                item {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(32.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text("No files stored", color = Color(0xFF9AA0A6))
                    }
                }
            } else {
                items(files) { fileName ->
                    val isHtml = fileName.endsWith(".html") || fileName.endsWith(".htm")
                    val badgeColor = if (isHtml) HtmlGreen else PythonOrange
                    val ext = if (isHtml) ".html" else ".py"
                    val size = viewModel.storageManager.getFileSize(fileName)
                    val sizeFormatted = formatFileSize(size)

                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(containerColor = Color.White)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(fileName, style = androidx.compose.material3.MaterialTheme.typography.bodyLarge)
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(
                                        ext,
                                        color = Color.White,
                                        fontFamily = FontFamily.Monospace,
                                        fontSize = 10.sp,
                                        modifier = Modifier
                                            .background(badgeColor, RoundedCornerShape(3.dp))
                                            .padding(horizontal = 6.dp, vertical = 1.dp)
                                    )
                                    Spacer(modifier = Modifier.width(8.dp))
                                    Text(sizeFormatted, color = Color(0xFF9AA0A6), fontSize = 12.sp)
                                }
                            }
                            IconButton(onClick = { deleteTarget = fileName }) {
                                Icon(
                                    Icons.Default.Delete,
                                    contentDescription = "Delete",
                                    tint = Color(0xFFD93025),
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    deleteTarget?.let { target ->
        AlertDialog(
            onDismissRequest = { deleteTarget = null },
            title = { Text("Delete file") },
            text = { Text("Delete $target? This cannot be undone.") },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.deleteFile(target)
                    deleteTarget = null
                }) {
                    Text("Delete", color = Color(0xFFD93025))
                }
            },
            dismissButton = {
                TextButton(onClick = { deleteTarget = null }) {
                    Text("Cancel")
                }
            }
        )
    }
}

private fun formatFileSize(bytes: Long): String {
    if (bytes < 1024) return "$bytes B"
    val kb = bytes / 1024.0
    if (kb < 1024) return String.format("%.1f KB", kb)
    val mb = kb / 1024.0
    return String.format("%.1f MB", mb)
}
