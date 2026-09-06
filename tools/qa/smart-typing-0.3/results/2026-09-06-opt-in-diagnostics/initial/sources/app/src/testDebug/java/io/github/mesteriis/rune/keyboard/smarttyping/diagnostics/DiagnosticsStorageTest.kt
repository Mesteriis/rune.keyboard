package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

class DiagnosticsStorageTest {
    @Test fun rotatesWithinEachStreamCapAndKeepsOtherFilesUntouched() {
        val directory = Files.createTempDirectory("rune-diagnostics-test").toFile()
        try {
            val unrelated = directory.resolve("unrelated.txt").apply { writeText("untouched") }
            val storage = DiagnosticsStorage({ directory }, { emptyMap<String, Any>() }, { true })
            for (stream in DiagnosticStream.entries) {
                val line = ("x".repeat(8_191) + "\n").toByteArray()
                repeat(stream.cap / line.size + 20) { storage.append(stream, line) }
                val files = directory.listFiles()!!.filter { it.name.startsWith(stream.name.lowercase() + ".") }
                assertEquals(4, files.size)
                assertTrue(files.sumOf { it.length() } <= stream.cap)
                assertTrue(files.all { it.length() <= stream.cap / 4 })
                val snapshot = storage.snapshot(stream)
                assertTrue(snapshot.isNotEmpty() && snapshot.size <= stream.cap)
            }
            storage.delete()
            assertEquals(listOf("unrelated.txt"), directory.listFiles()!!.map { it.name })
            assertEquals("untouched", unrelated.readText())
        } finally { directory.deleteRecursively() }
    }

    @Test fun rejectsOversizeAppendAndNeverReadsAnOversizeManagedFile() {
        val directory = Files.createTempDirectory("rune-diagnostics-test").toFile()
        try {
            val storage = DiagnosticsStorage({ directory }, { emptyMap<String, Any>() }, { true })
            var rejected = false
            try { storage.append(DiagnosticStream.METADATA, ByteArray(8_193)) }
            catch (_: IllegalArgumentException) { rejected = true }
            assertTrue(rejected)
            directory.resolve("text.0.jsonl").writeBytes(ByteArray(DiagnosticStream.TEXT.cap + 1))
            rejected = false
            try { storage.snapshot(DiagnosticStream.TEXT) }
            catch (_: IllegalStateException) { rejected = true }
            assertTrue(rejected)
        } finally { directory.deleteRecursively() }
    }
}
