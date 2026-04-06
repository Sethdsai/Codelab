package com.codelab

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.compose.runtime.collectAsState
import com.codelab.ui.screens.EditorScreen
import com.codelab.ui.screens.FileListScreen
import com.codelab.ui.screens.NewFileDialog
import com.codelab.ui.screens.RickRollScreen
import com.codelab.ui.screens.SettingsScreen
import com.codelab.ui.screens.StorageScreen
import com.codelab.ui.theme.CodelabTheme
import com.codelab.viewmodel.EditorViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            CodelabTheme {
                val vm: EditorViewModel = viewModel()
                CodelabApp(vm)
            }
        }
    }
}

@Composable
fun CodelabApp(viewModel: EditorViewModel) {
    val showRickRoll by viewModel.showRickRoll.collectAsState()
    val showSettings by viewModel.showSettings.collectAsState()
    val showFileList by viewModel.showFileList.collectAsState()
    val showStorageInfo by viewModel.showStorageInfo.collectAsState()
    val showNewFileDialog by viewModel.showNewFileDialog.collectAsState()

    when {
        showRickRoll -> RickRollScreen(
            onBack = { viewModel.closeRickRoll() }
        )
        showSettings -> SettingsScreen(
            viewModel = viewModel,
            onBack = { viewModel.closeSettings() }
        )
        showFileList -> FileListScreen(
            viewModel = viewModel,
            onBack = { viewModel.closeFileList() }
        )
        showStorageInfo -> StorageScreen(
            viewModel = viewModel,
            onBack = { viewModel.closeStorageInfo() }
        )
        else -> EditorScreen(viewModel = viewModel)
    }

    if (showNewFileDialog) {
        NewFileDialog(viewModel = viewModel)
    }
}
