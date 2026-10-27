package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import java.security.MessageDigest

/** Synthetic QA only: include absence and sidecars so creation/deletion cannot pass as unchanged. */
internal fun personalStoreSnapshot(context: Context): Map<String, Map<String, String>> = listOf(
    "personal-typing", "personal-touch-v1.tsv", "learning-lab", "typing-controls-v1.bin",
    "typing-quality-v1.txt", "typing-diagnostics",
).associateWith { name ->
    val root = java.io.File(context.noBackupFilesDir, name)
    val directory = name in setOf("personal-typing", "learning-lab", "typing-diagnostics")
    val files = if (directory) {
        if (root.isDirectory) root.walkTopDown().filter { it.isFile }.toList() else emptyList()
    } else root.parentFile?.listFiles().orEmpty().filter {
        it.isFile && (it.name == name || it.name.startsWith("$name."))
    }
    files.associate { file ->
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { stream ->
            val bytes = ByteArray(8192)
            while (true) { val count = stream.read(bytes); if (count < 0) break; digest.update(bytes, 0, count) }
        }
        file.relativeTo(context.noBackupFilesDir).path to digest.digest().joinToString("") { "%02x".format(it) }
    }.ifEmpty { mapOf("state" to if (root.exists()) "EMPTY_DIRECTORY" else "ABSENT") }
}
