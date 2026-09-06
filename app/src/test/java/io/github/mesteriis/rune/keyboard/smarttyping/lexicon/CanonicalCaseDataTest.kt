package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import java.io.ByteArrayOutputStream
import java.io.DataOutputStream
import java.nio.file.Files
import java.nio.file.Path
import org.junit.Assert.*
import org.junit.Test

class CanonicalCaseDataTest {
    @Test
    fun `packaged canonical case assets validate and contain public references`() {
        val root = listOf(Path.of("src/main/assets"), Path.of("app/src/main/assets"))
            .first { Files.isDirectory(it) }
        for ((language, key, expected) in listOf(
            Triple("en", "london", CanonicalCase("London", true)),
            Triple("es", "juan", CanonicalCase("Juan", false)),
            Triple("ru", "москва", CanonicalCase("Москва", true)),
        )) {
            val data = CanonicalCaseData.validate(Files.readAllBytes(
                root.resolve("smarttyping/lexicon/case/$language.case")))
            assertEquals(expected, data.lookup(key))
        }
    }

    @Test
    fun `validated index finds countries cities and names without retaining query identity`() {
        val data = CanonicalCaseData.validate(asset(listOf(
            Triple("juan", "Juan", false),
            Triple("madrid", "Madrid", true),
            Triple("москва", "Москва", true),
        )))
        assertEquals(CanonicalCase("Juan", false), data.lookup("juan"))
        assertEquals(CanonicalCase("Madrid", true), data.lookup("madrid"))
        assertEquals(CanonicalCase("Москва", true), data.lookup("москва"))
        assertNull(data.lookup("unknown"))
        assertEquals("CanonicalCase(redacted)", data.lookup("москва").toString())
    }

    @Test
    fun `malformed ordering utf8 and canonical case fail closed`() {
        assertThrows(IllegalArgumentException::class.java) {
            CanonicalCaseData.validate(asset(listOf(
                Triple("z", "Z", true), Triple("a", "A", true),
            )))
        }
        val malformed = asset(listOf(Triple("a", "A", true))).also { it[it.size - 1] = 0x80.toByte() }
        assertThrows(Exception::class.java) { CanonicalCaseData.validate(malformed) }
        assertThrows(IllegalArgumentException::class.java) {
            CanonicalCaseData.validate(asset(listOf(Triple("london", "london", true))))
        }
    }

    private fun asset(rows: List<Triple<String, String, Boolean>>): ByteArray {
        val records = ByteArrayOutputStream()
        val offsets = mutableListOf(0)
        for ((key, canonical, safe) in rows) {
            val keyBytes = key.toByteArray()
            val valueBytes = canonical.toByteArray()
            records.write(if (safe) 1 else 0)
            records.write(keyBytes.size)
            records.write(valueBytes.size)
            records.write(keyBytes)
            records.write(valueBytes)
            offsets += records.size()
        }
        return ByteArrayOutputStream().also { output ->
            DataOutputStream(output).use { stream ->
                stream.writeBytes("RNC1")
                stream.writeInt(rows.size)
                offsets.forEach(stream::writeInt)
                stream.write(records.toByteArray())
            }
        }.toByteArray()
    }
}
