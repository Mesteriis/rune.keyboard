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
}
