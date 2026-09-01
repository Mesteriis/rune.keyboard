package io.github.mesteriis.rune.keyboard.intelligence.delivery

import io.github.mesteriis.rune.keyboard.intelligence.model.ModelDescriptor
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.file.Files
import java.security.MessageDigest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class CandidateInstallerTest {
    @Test
    fun publishesVerifiedCandidateWithoutTouchingActivePointer() {
        val root = Files.createTempDirectory("candidate-installer").toFile()
        val active = File(root, "active-model.json").apply { writeText("old-active") }
        val bytes = gguf()
        val descriptor = descriptor(bytes)

        val candidate = CandidateInstaller(root).install(ByteArrayInputStream(bytes), descriptor)

        assertTrue(File(root, "candidates/${candidate.directoryName}/${descriptor.fileName}").isFile)
        assertTrue(File(root, "candidates/${candidate.directoryName}/${CandidateInstaller.MODEL_MANIFEST_NAME}").isFile)
        assertEquals("old-active", active.readText())
        assertFalse(File(root, ".installing").exists())
    }

    @Test
    fun hashMismatchRemovesPrivatePartialAndPreservesExistingCandidate() {
        val root = Files.createTempDirectory("candidate-installer").toFile()
        val bytes = gguf()
        val descriptor = descriptor(bytes).copy(sha256 = "0".repeat(64))
        val previous = File(root, "candidates/${descriptor.id}-${descriptor.version}/keep").apply {
            parentFile?.mkdirs(); writeText("previous")
        }

        assertThrows(CandidateInstallException::class.java) {
            CandidateInstaller(root).install(ByteArrayInputStream(bytes), descriptor)
        }

        assertEquals("previous", previous.readText())
        assertFalse(File(root, ".installing").exists())
    }

    private fun descriptor(bytes: ByteArray) = ModelDescriptor(
        id = "rune-text-v1",
        version = "0.1.0",
        displayName = "Rune Text 0.1",
        fileName = "rune-text-v1-0.1.0-q4_k_m.gguf",
        downloadUrl = "https://github.com/Mesteriis/rune.keyboard/releases/download/model-rune-text-v0.1.0/rune-text-v1-0.1.0-q4_k_m.gguf",
        sha256 = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) },
        sizeBytes = bytes.size.toLong(),
        runtimeApi = 1,
        minimumRuneVersionCode = 2,
        ggufVersion = 3,
        architecture = "qwen3",
        fileType = 15,
    )

    private fun gguf(): ByteArray {
        val out = ByteArrayOutputStream()
        out.write("GGUF".toByteArray()); out.write(leInt(3)); out.write(leLong(0)); out.write(leLong(2))
        string(out, "general.architecture"); out.write(leInt(8)); string(out, "qwen3")
        string(out, "general.file_type"); out.write(leInt(4)); out.write(leInt(15))
        return out.toByteArray()
    }

    private fun string(out: ByteArrayOutputStream, value: String) {
        val bytes = value.toByteArray(); out.write(leLong(bytes.size.toLong())); out.write(bytes)
    }
    private fun leInt(value: Int) = ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(value).array()
    private fun leLong(value: Long) = ByteBuffer.allocate(8).order(ByteOrder.LITTLE_ENDIAN).putLong(value).array()
}
