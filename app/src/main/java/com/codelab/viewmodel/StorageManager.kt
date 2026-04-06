package com.codelab.viewmodel

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.io.File

class StorageManager(private val context: Context) {

    companion object {
        val TOTAL_STORAGE = 250L * 1024 * 1024 * 1024
    }

    private val filesDir = File(context.filesDir, "codelab_projects")

    init {
        if (!filesDir.exists()) filesDir.mkdirs()
    }

    private val _usedSpace = MutableStateFlow(0L)
    val usedSpace: StateFlow<Long> = _usedSpace.asStateFlow()

    init {
        calculateUsedSpace()
    }

    fun getUsedSpaceFormatted(): String {
        return formatBytes(_usedSpace.value)
    }

    fun getTotalSpaceFormatted(): String {
        return "250 GB"
    }

    fun getFreeSpaceFormatted(): String {
        return formatBytes(TOTAL_STORAGE - _usedSpace.value)
    }

    fun getUsagePercentage(): Float {
        return if (TOTAL_STORAGE > 0) {
            (_usedSpace.value.toFloat() / TOTAL_STORAGE) * 100f
        } else 0f
    }

    fun addFile(name: String, content: String): Boolean {
        return try {
            val file = File(filesDir, name)
            file.writeText(content)
            calculateUsedSpace()
            true
        } catch (e: Exception) {
            false
        }
    }

    fun getFileContent(name: String): String? {
        return try {
            val file = File(filesDir, name)
            if (file.exists()) file.readText() else null
        } catch (e: Exception) {
            null
        }
    }

    fun deleteFile(name: String): Boolean {
        return try {
            val file = File(filesDir, name)
            if (file.exists()) {
                file.delete()
                calculateUsedSpace()
                true
            } else false
        } catch (e: Exception) {
            false
        }
    }

    fun renameFile(oldName: String, newName: String): Boolean {
        return try {
            val oldFile = File(filesDir, oldName)
            val newFile = File(filesDir, newName)
            if (oldFile.exists()) {
                oldFile.renameTo(newFile)
                calculateUsedSpace()
                true
            } else false
        } catch (e: Exception) {
            false
        }
    }

    fun getFileNames(): List<String> {
        return filesDir.listFiles()?.map { it.name }?.sorted() ?: emptyList()
    }

    fun getFileSize(name: String): Long {
        val file = File(filesDir, name)
        return if (file.exists()) file.length() else 0L
    }

    fun calculateUsedSpace() {
        var total = 0L
        filesDir.listFiles()?.forEach { file ->
            total += file.length()
        }
        _usedSpace.value = total
    }

    private fun formatBytes(bytes: Long): String {
        val gb = bytes.toDouble() / (1024.0 * 1024.0 * 1024.0)
        if (gb >= 1.0) {
            return String.format("%.1f GB", gb)
        }
        val mb = bytes.toDouble() / (1024.0 * 1024.0)
        if (mb >= 1.0) {
            return String.format("%.1f MB", mb)
        }
        val kb = bytes.toDouble() / 1024.0
        if (kb >= 1.0) {
            return String.format("%.1f KB", kb)
        }
        return "$bytes B"
    }
}
