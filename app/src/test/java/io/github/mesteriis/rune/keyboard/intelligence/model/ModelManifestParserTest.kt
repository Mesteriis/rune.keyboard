package io.github.mesteriis.rune.keyboard.intelligence.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class ModelManifestParserTest {
    private val valid = """
        {
          "schemaVersion": 1,
          "modelId": "rune-text-v1",
          "version": "0.1.0",
          "displayName": "Rune Text 0.1",
          "fileName": "rune-text-v1-0.1.0-q4_k_m.gguf",
          "url": "https://github.com/Mesteriis/rune.keyboard/releases/download/model-rune-text-v0.1.0/rune-text-v1-0.1.0-q4_k_m.gguf",
          "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "sizeBytes": 420000000,
          "runtimeApi": 1,
          "minimumRuneVersionCode": 2,
          "ggufVersion": 3,
          "architecture": "qwen3",
          "fileType": 15
        }
    """.trimIndent()

    @Test
    fun parsesStrictSchemaV1() {
        val descriptor = ModelManifestParser.parse(valid)

        assertEquals("rune-text-v1", descriptor.id)
        assertEquals("0.1.0", descriptor.version)
        assertEquals(420000000L, descriptor.sizeBytes)
        assertEquals(15, descriptor.fileType)
        assertEquals(descriptor, ModelManifestParser.parse(ModelManifestParser.encode(descriptor)))
    }

    @Test
    fun parsesImmutableHuggingFaceCommitUrl() {
        val commit = "0123456789abcdef0123456789abcdef01234567"
        val huggingFace = valid.replace(
            "https://github.com/Mesteriis/rune.keyboard/releases/download/model-rune-text-v0.1.0/rune-text-v1-0.1.0-q4_k_m.gguf",
            "https://huggingface.co/Mesteriis/rune-text-0.3-gguf/resolve/$commit/rune-text-v1-0.1.0-q4_k_m.gguf",
        )

        assertEquals(
            "https://huggingface.co/Mesteriis/rune-text-0.3-gguf/resolve/$commit/rune-text-v1-0.1.0-q4_k_m.gguf",
            ModelManifestParser.parse(huggingFace).downloadUrl,
        )
    }

    @Test
    fun rejectsUnknownDuplicateAndUnsafeFields() {
        assertThrows(ManifestValidationException::class.java) {
            ModelManifestParser.parse(valid.replace("\"schemaVersion\": 1,", "\"schemaVersion\": 1, \"extra\": true,"))
        }
        assertThrows(ManifestValidationException::class.java) {
            ModelManifestParser.parse(valid.replace("\"modelId\": \"rune-text-v1\",", "\"modelId\": \"rune-text-v1\", \"modelId\": \"other\","))
        }
        assertThrows(ManifestValidationException::class.java) {
            ModelManifestParser.parse(valid.replace("rune-text-v1-0.1.0-q4_k_m.gguf", "../model.gguf"))
        }
    }

    @Test
    fun rejectsWrongRuntimeHashSizeAndHost() {
        assertThrows(ManifestValidationException::class.java) {
            ModelManifestParser.parse(valid.replace("\"runtimeApi\": 1", "\"runtimeApi\": 2"))
        }
        assertThrows(ManifestValidationException::class.java) {
            ModelManifestParser.parse(valid.replace(Regex("a{64}"), "abc"))
        }
        assertThrows(ManifestValidationException::class.java) {
            ModelManifestParser.parse(valid.replace("420000000", "0"))
        }
        assertThrows(ManifestValidationException::class.java) {
            ModelManifestParser.parse(valid.replace("https://github.com/", "https://example.com/"))
        }
    }

    @Test
    fun rejectsMovingOrIndirectHuggingFaceUrls() {
        val releaseUrl = "https://github.com/Mesteriis/rune.keyboard/releases/download/model-rune-text-v0.1.0/rune-text-v1-0.1.0-q4_k_m.gguf"
        val artifact = "rune-text-v1-0.1.0-q4_k_m.gguf"
        val immutable = "https://huggingface.co/Mesteriis/rune-text-0.3-gguf/resolve/0123456789abcdef0123456789abcdef01234567/$artifact"
        listOf(
            "https://huggingface.co/Mesteriis/rune-text-0.3-gguf/resolve/main/$artifact",
            "https://huggingface.co/Mesteriis/rune-text-0.3-gguf/resolve/v0.3.0/$artifact",
            "$immutable?download=true",
            immutable.replace("huggingface.co", "hf.co"),
            immutable.replace("/$artifact", "/other.gguf"),
        ).forEach { url ->
            assertThrows(ManifestValidationException::class.java) {
                ModelManifestParser.parse(valid.replace(releaseUrl, url))
            }
        }
    }
}
