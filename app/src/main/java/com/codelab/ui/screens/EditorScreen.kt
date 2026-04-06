package com.codelab.ui.screens

import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.FolderOpen
import androidx.compose.material.icons.filled.LightMode
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Save
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.codelab.ui.theme.CodeBackground
import com.codelab.ui.theme.CodeForeground
import com.codelab.ui.theme.HtmlGreen
import com.codelab.ui.theme.LineNumber
import com.codelab.ui.theme.PythonOrange
import com.codelab.viewmodel.EditorViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EditorScreen(viewModel: EditorViewModel) {
    val code by remember { viewModel.code }
    val fileName by remember { viewModel.fileName }
    val language by remember { viewModel.fileLanguage }
    val isDark by remember { viewModel.isDarkEditor }
    val pythonOutput by remember { viewModel.pythonOutput }
    val fontSize by remember { viewModel.fontSize }
    val storageUsed by remember { viewModel.storageManager.usedSpace }

    var selectedTab by remember { mutableIntStateOf(0) }
    val lineCount = code.count { it == '\n' } + 1
    val lineNumbers = (1..lineCount).joinToString("\n")

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = fileName,
                        maxLines = 1
                    )
                },
                actions = {
                    IconButton(onClick = { viewModel.openNewFileDialog() }) {
                        Icon(Icons.Default.Add, contentDescription = "New")
                    }
                    IconButton(onClick = { viewModel.openFileList() }) {
                        Icon(Icons.Default.FolderOpen, contentDescription = "Files")
                    }
                    IconButton(onClick = { viewModel.saveFile() }) {
                        Icon(Icons.Default.Save, contentDescription = "Save")
                    }
                    IconButton(onClick = { viewModel.toggleDarkEditor() }) {
                        Icon(
                            if (isDark) Icons.Default.LightMode else Icons.Default.DarkMode,
                            contentDescription = "Toggle theme"
                        )
                    }
                    IconButton(onClick = { viewModel.openSettings() }) {
                        Icon(Icons.Default.Settings, contentDescription = "Settings")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF1A73E8),
                    titleContentColor = Color.White,
                    actionIconContentColor = Color.White
                )
            )
        },
        bottomBar = {
            BottomBar(language, storageUsed, viewModel)
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            val tabs = if (language == "html") {
                listOf("Code", "Preview")
            } else {
                listOf("Code", "Output")
            }

            TabRow(
                selectedTabIndex = selectedTab,
                modifier = Modifier.fillMaxWidth()
            ) {
                tabs.forEachIndexed { index, title ->
                    Tab(
                        selected = selectedTab == index,
                        onClick = { selectedTab = index },
                        text = { Text(title) }
                    )
                }
            }

            when (selectedTab) {
                0 -> CodeEditor(
                    code = code,
                    lineNumbers = lineNumbers,
                    isDark = isDark,
                    fontSize = fontSize,
                    onCodeChange = { viewModel.updateCode(it) }
                )
                1 -> {
                    if (language == "html") {
                        HtmlPreview(code = code)
                    } else {
                        PythonOutput(output = pythonOutput, isDark = isDark)
                    }
                }
            }
        }
    }
}

@Composable
fun CodeEditor(
    code: String,
    lineNumbers: String,
    isDark: Boolean,
    fontSize: Int,
    onCodeChange: (String) -> Unit
) {
    val bgColor = if (isDark) CodeBackground else Color(0xFFF5F5F5)
    val textColor = if (isDark) CodeForeground else Color(0xFF1E1E1E)
    val lineNumberColor = if (isDark) LineNumber else Color(0xFF9E9E9E)

    Row(
        modifier = Modifier
            .fillMaxSize()
            .background(bgColor)
    ) {
        Text(
            text = lineNumbers,
            color = lineNumberColor,
            fontFamily = FontFamily.Monospace,
            fontSize = fontSize.sp,
            modifier = Modifier
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 12.dp, vertical = 16.dp)
                .alignBy { it.measuredHeight }
        )

        Box(
            modifier = Modifier
                .weight(1f)
                .background(textColor.copy(alpha = 0.03f))
        ) {
            var localCode by remember(code) { mutableIntStateOf(0); androidx.compose.runtime.mutableStateOf(code) }

            androidx.compose.foundation.text.BasicTextField(
                value = code,
                onValueChange = onCodeChange,
                modifier = Modifier
                    .fillMaxSize()
                    .padding(16.dp)
                    .verticalScroll(rememberScrollState())
                    .horizontalScroll(rememberScrollState()),
                textStyle = androidx.compose.ui.text.TextStyle(
                    color = textColor,
                    fontFamily = FontFamily.Monospace,
                    fontSize = fontSize.sp,
                    lineHeight = (fontSize + 6).sp
                ),
                cursorBrush = androidx.compose.ui.graphics.SolidColor(Color(0xFF1A73E8))
            )
        }
    }
}

@Composable
fun HtmlPreview(code: String) {
    AndroidView(
        factory = { context ->
            WebView(context).apply {
                webViewClient = WebViewClient()
                settings.javaScriptEnabled = true
                settings.domStorageEnabled = true
                settings.loadWithOverviewMode = true
                settings.useWideViewPort = true
            }
        },
        update = { webView ->
            webView.loadDataWithBaseURL(null, code, "text/html", "UTF-8", null)
        },
        modifier = Modifier.fillMaxSize()
    )
}

@Composable
fun PythonOutput(output: String, isDark: Boolean) {
    val bgColor = if (isDark) CodeBackground else Color(0xFFF5F5F5)
    val textColor = if (isDark) Color(0xFF4CAF50) else Color(0xFF2E7D32)

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(bgColor)
            .verticalScroll(rememberScrollState())
            .padding(16.dp)
    ) {
        Text(
            text = output.ifEmpty { "Click Run to execute Python code" },
            color = textColor,
            fontFamily = FontFamily.Monospace,
            fontSize = 13.sp,
            lineHeight = 20.sp
        )
    }
}

@Composable
fun BottomBar(language: String, storageUsed: Long, viewModel: EditorViewModel) {
    val langColor = if (language == "html") HtmlGreen else PythonOrange
    val langLabel = if (language == "html") "HTML" else "PYTHON"

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xFFF1F3F4))
            .padding(horizontal = 16.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = " $langLabel ",
            color = Color.White,
            fontFamily = FontFamily.Monospace,
            fontSize = 11.sp,
            modifier = Modifier
                .background(langColor, androidx.compose.foundation.shape.RoundedCornerShape(4.dp))
                .padding(horizontal = 8.dp, vertical = 2.dp)
        )

        if (language == "python") {
            IconButton(
                onClick = { viewModel.runPython() },
                modifier = Modifier.padding(start = 8.dp)
            ) {
                Icon(
                    Icons.Default.PlayArrow,
                    contentDescription = "Run",
                    tint = PythonOrange,
                    modifier = Modifier.size(20.dp)
                )
            }
        }

        androidx.compose.foundation.layout.Spacer(modifier = Modifier.weight(1f))

        Text(
            text = formatStorageBytes(storageUsed),
            color = Color(0xFF5F6368),
            fontSize = 12.sp
        )
        Text(
            text = " / 250 GB",
            color = Color(0xFF9AA0A6),
            fontSize = 12.sp
        )
    }
}

private fun formatStorageBytes(bytes: Long): String {
    val gb = bytes.toDouble() / (1024.0 * 1024.0 * 1024.0)
    if (gb >= 1.0) return String.format("%.1f GB", gb)
    val mb = bytes.toDouble() / (1024.0 * 1024.0)
    if (mb >= 1.0) return String.format("%.1f MB", mb)
    val kb = bytes.toDouble() / 1024.0
    if (kb >= 1.0) return String.format("%.1f KB", kb)
    return "$bytes B"
}
