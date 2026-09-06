package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import java.io.File
import java.io.ByteArrayOutputStream

internal class DiagnosticsStorage(
    private val directory: () -> File,
    private val readPreferences: () -> Map<String, *>,
    private val writePreferences: (DiagnosticsPreferences) -> Boolean,
) : DiagnosticsBackend {
    override fun loadPreferences() = readPreferences()
    override fun savePreferences(value: DiagnosticsPreferences) = writePreferences(value)
    override fun append(stream: DiagnosticStream, bytes: ByteArray) {
        require(bytes.size <= DiagnosticsRecorder.RECORD_BYTES)
        val root = directory()
        check(root.isDirectory || root.mkdirs())
        val active = file(stream, 0)
        val partCap = stream.cap / PARTS
        if (active.length() + bytes.size > partCap) {
            val oldest = file(stream, PARTS - 1)
            check(!oldest.exists() || oldest.delete())
            for (index in PARTS - 2 downTo 0) {
                val source = file(stream, index)
                if (source.exists()) check(source.renameTo(file(stream, index + 1)))
            }
        }
        java.io.FileOutputStream(active, true).use { it.write(bytes) }
    }

    override fun snapshot(stream: DiagnosticStream): ByteArray {
        val output = ByteArrayOutputStream()
        for (index in PARTS - 1 downTo 0) {
            val source = file(stream, index)
            if (!source.exists()) continue
            check(source.isFile && source.length() <= stream.cap / PARTS)
            source.inputStream().use { input ->
                val buffer = ByteArray(DiagnosticsRecorder.RECORD_BYTES)
                while (true) {
                    val count = input.read(buffer)
                    if (count < 0) break
                    check(count <= stream.cap - output.size())
                    output.write(buffer, 0, count)
                }
            }
        }
        return output.toByteArray()
    }

    override fun delete() {
        for (stream in DiagnosticStream.entries) for (index in 0 until PARTS) {
            val managed = file(stream, index)
            check(!managed.exists() || managed.delete())
        }
    }
    private fun file(stream: DiagnosticStream, index: Int) =
        File(directory(), "${stream.name.lowercase(java.util.Locale.ROOT)}.$index.jsonl")

    companion object {
        private const val PARTS = 4
        fun forAppDirectory(root: () -> File, read: () -> Map<String, *>,
            write: (DiagnosticsPreferences) -> Boolean) =
            DiagnosticsStorage({ File(root(), "typing-diagnostics") }, read, write)
    }
}
