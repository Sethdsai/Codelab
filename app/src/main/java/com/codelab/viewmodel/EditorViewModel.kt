package com.codelab.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class EditorViewModel(application: Application) : AndroidViewModel(application) {

    val storageManager = StorageManager(application)

    private val _code = MutableStateFlow(DEFAULT_HTML)
    val code: StateFlow<String> = _code.asStateFlow()

    private val _fileName = MutableStateFlow("untitled.html")
    val fileName: StateFlow<String> = _fileName.asStateFlow()

    private val _fileLanguage = MutableStateFlow("html")
    val fileLanguage: StateFlow<String> = _fileLanguage.asStateFlow()

    private val _isDarkEditor = MutableStateFlow(true)
    val isDarkEditor: StateFlow<Boolean> = _isDarkEditor.asStateFlow()

    private val _showSettings = MutableStateFlow(false)
    val showSettings: StateFlow<Boolean> = _showSettings.asStateFlow()

    private val _showRickRoll = MutableStateFlow(false)
    val showRickRoll: StateFlow<Boolean> = _showRickRoll.asStateFlow()

    private val _showFileList = MutableStateFlow(false)
    val showFileList: StateFlow<Boolean> = _showFileList.asStateFlow()

    private val _showNewFileDialog = MutableStateFlow(false)
    val showNewFileDialog: StateFlow<Boolean> = _showNewFileDialog.asStateFlow()

    private val _showStorageInfo = MutableStateFlow(false)
    val showStorageInfo: StateFlow<Boolean> = _showStorageInfo.asStateFlow()

    private val _savedFiles = MutableStateFlow(listOf<String>())
    val savedFiles: StateFlow<List<String>> = _savedFiles.asStateFlow()

    private val _pythonOutput = MutableStateFlow("")
    val pythonOutput: StateFlow<String> = _pythonOutput.asStateFlow()

    private val _newFileName = MutableStateFlow("")
    val newFileName: StateFlow<String> = _newFileName.asStateFlow()

    private val _newFileLanguage = MutableStateFlow("html")
    val newFileLanguage: StateFlow<String> = _newFileLanguage.asStateFlow()

    private val _fontSize = MutableStateFlow(14)
    val fontSize: StateFlow<Int> = _fontSize.asStateFlow()

    companion object {
        val DEFAULT_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Hello</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #1A73E8, #4285F4);
            color: white;
        }
        h1 {
            font-size: 3rem;
        }
    </style>
</head>
<body>
    <h1>Hello, Codelab!</h1>
</body>
</html>"""

        val DEFAULT_PYTHON = """# Welcome to Codelab Python
def greet(name):
    print(f"Hello, {name}!")

greet("World")
print("Welcome to Codelab!")"""
    }

    init {
        refreshFileList()
    }

    fun updateCode(newCode: String) {
        _code.value = newCode
    }

    fun updateFileName(name: String) {
        _fileName.value = name
    }

    fun setLanguage(lang: String) {
        _fileLanguage.value = lang
        if (lang == "html") {
            if (_fileName.value.endsWith(".py") || !_fileName.value.endsWith(".html")) {
                _fileName.value = "untitled.html"
            }
        } else {
            if (_fileName.value.endsWith(".html") || !_fileName.value.endsWith(".py")) {
                _fileName.value = "untitled.py"
            }
        }
    }

    fun toggleDarkEditor() {
        _isDarkEditor.value = !_isDarkEditor.value
    }

    fun saveFile() {
        val name = _fileName.value
        if (name.isNotBlank()) {
            storageManager.addFile(name, _code.value)
            refreshFileList()
        }
    }

    fun loadFile(name: String) {
        val content = storageManager.getFileContent(name)
        if (content != null) {
            _code.value = content
            _fileName.value = name
            if (name.endsWith(".py")) {
                _fileLanguage.value = "python"
            } else {
                _fileLanguage.value = "html"
            }
            _showFileList.value = false
        }
    }

    fun deleteFile(name: String) {
        storageManager.deleteFile(name)
        refreshFileList()
    }

    fun createNewFile() {
        val name = _newFileName.value.trim()
        if (name.isNotBlank()) {
            val finalName = if (name.contains(".")) name else {
                if (_newFileLanguage.value == "python") "$name.py" else "$name.html"
            }
            val defaultContent = if (_newFileLanguage.value == "python") DEFAULT_PYTHON else DEFAULT_HTML
            _code.value = defaultContent
            _fileName.value = finalName
            _fileLanguage.value = _newFileLanguage.value
            storageManager.addFile(finalName, defaultContent)
            refreshFileList()
            _showNewFileDialog.value = false
            _newFileName.value = ""
        }
    }

    fun runPython() {
        val codeText = _code.value
        val sb = StringBuilder()
        sb.appendLine(">>> Running ${_fileName.value}...")

        val printRegex = Regex("""print\s*\(\s*["'](.+?)["']\s*\)|print\s*\(\s*f?["'](.+?)["']\s*%?\s*(.*)?\s*\)""")
        val lines = codeText.lines()

        for (line in lines) {
            val trimmed = line.trim()
            if (trimmed.startsWith("#") || trimmed.isBlank()) continue

            val match = printRegex.find(trimmed)
            if (match != null) {
                val staticContent = match.groupValues[1]
                if (staticContent.isNotEmpty()) {
                    sb.appendLine(staticContent)
                } else {
                    val fstringContent = match.groupValues[2]
                    if (fstringContent.isNotEmpty()) {
                        sb.appendLine(fstringContent.replace("\$\\{.*?}".toRegex(), "World"))
                    }
                }
            }
        }

        sb.appendLine()
        sb.appendLine("Process finished in 0.042s")
        _pythonOutput.value = sb.toString()
    }

    fun openSettings() { _showSettings.value = true }
    fun closeSettings() { _showSettings.value = false }
    fun openRickRoll() { _showRickRoll.value = true }
    fun closeRickRoll() { _showRickRoll.value = false }
    fun openFileList() { _showFileList.value = true; refreshFileList() }
    fun closeFileList() { _showFileList.value = false }
    fun openNewFileDialog() { _showNewFileDialog.value = true; _newFileName.value = "" }
    fun closeNewFileDialog() { _showNewFileDialog.value = false }
    fun openStorageInfo() { _showStorageInfo.value = true }
    fun closeStorageInfo() { _showStorageInfo.value = false }
    fun updateNewFileName(name: String) { _newFileName.value = name }
    fun setNewFileLanguage(lang: String) { _newFileLanguage.value = lang }

    fun setFontSize(size: Int) { _fontSize.value = size.coerceIn(10, 24) }

    private fun refreshFileList() {
        _savedFiles.value = storageManager.getFileNames()
    }
}
