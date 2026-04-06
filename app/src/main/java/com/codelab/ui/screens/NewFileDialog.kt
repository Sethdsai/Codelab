package com.codelab.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import com.codelab.ui.theme.HtmlGreen
import com.codelab.ui.theme.PythonOrange

@Composable
fun NewFileDialog(viewModel: com.codelab.viewmodel.EditorViewModel) {
    val show by viewModel.showNewFileDialog.collectAsState()
    val fileName by viewModel.newFileName.collectAsState()
    val language by viewModel.newFileLanguage.collectAsState()

    if (show) {
        AlertDialog(
            onDismissRequest = { viewModel.closeNewFileDialog() },
            title = { Text("New File") },
            text = {
                Column {
                    TextField(
                        value = fileName,
                        onValueChange = { viewModel.updateNewFileName(it) },
                        label = { Text("File name") },
                        singleLine = true,
                        colors = TextFieldDefaults.colors(
                            focusedIndicatorColor = Color(0xFF1A73E8),
                            focusedContainerColor = Color.White,
                            unfocusedContainerColor = Color.White
                        ),
                        modifier = Modifier.fillMaxWidth()
                    )

                    Spacer(modifier = Modifier.height(16.dp))

                    Text("Language", style = MaterialTheme.typography.bodyMedium, color = Color(0xFF5F6368))

                    Spacer(modifier = Modifier.height(8.dp))

                    Row(modifier = Modifier.fillMaxWidth()) {
                        val htmlSelected = language == "html"
                        val pySelected = language == "python"

                        OutlinedButton(
                            onClick = { viewModel.setNewFileLanguage("html") },
                            shape = RoundedCornerShape(8.dp),
                            colors = ButtonDefaults.outlinedButtonColors(
                                containerColor = if (htmlSelected) HtmlGreen.copy(alpha = 0.1f) else Color.Transparent,
                                contentColor = if (htmlSelected) HtmlGreen else Color(0xFF5F6368)
                            ),
                            border = ButtonDefaults.outlinedButtonBorder.copy(
                                brush = androidx.compose.ui.graphics.SolidColor(
                                    if (htmlSelected) HtmlGreen else Color(0xFFDADCE0)
                                )
                            ),
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("HTML", fontFamily = FontFamily.Monospace)
                        }

                        Spacer(modifier = Modifier.width(8.dp))

                        OutlinedButton(
                            onClick = { viewModel.setNewFileLanguage("python") },
                            shape = RoundedCornerShape(8.dp),
                            colors = ButtonDefaults.outlinedButtonColors(
                                containerColor = if (pySelected) PythonOrange.copy(alpha = 0.1f) else Color.Transparent,
                                contentColor = if (pySelected) PythonOrange else Color(0xFF5F6368)
                            ),
                            border = ButtonDefaults.outlinedButtonBorder.copy(
                                brush = androidx.compose.ui.graphics.SolidColor(
                                    if (pySelected) PythonOrange else Color(0xFFDADCE0)
                                )
                            ),
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Python", fontFamily = FontFamily.Monospace)
                        }
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = { viewModel.createNewFile() },
                    enabled = fileName.isNotBlank(),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF1A73E8))
                ) {
                    Text("Create")
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { viewModel.closeNewFileDialog() }) {
                    Text("Cancel")
                }
            }
        )
    }
}
