package io.github.mesteriis.rune.keyboard.smarttyping.abbreviations

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.InputStream

/** Versioned private snapshot, intentionally unrelated to portable personalization profiles. */
object AbbreviationCodec {
    const val MAX_FILE_BYTES = 128 * 1024
    private const val MAGIC = 0x52414231

    fun encode(entries: List<Abbreviation>): ByteArray {
        AbbreviationModel.validate(entries)
        val bytes = ByteArrayOutputStream()
        DataOutputStream(bytes).use { output ->
            output.writeInt(MAGIC)
            output.writeInt(entries.size)
            entries.forEach { output.writeUTF(it.language.name); output.writeUTF(it.key); output.writeUTF(it.expansion) }
        }
        return bytes.toByteArray().also { require(it.size <= MAX_FILE_BYTES) { "Invalid abbreviations" } }
    }

    fun decode(bytes: ByteArray): List<Abbreviation> {
        require(bytes.size <= MAX_FILE_BYTES) { "Invalid abbreviations" }
        return DataInputStream(ByteArrayInputStream(bytes)).use { input ->
            require(input.readInt() == MAGIC) { "Invalid abbreviations" }
            val count = input.readInt()
            require(count in 0..AbbreviationModel.MAX_ENTRIES) { "Invalid abbreviations" }
            val entries = List(count) {
                val name = input.readUTF()
                val language = KeyboardLanguage.entries.firstOrNull { it.name == name }
                    ?: throw IllegalArgumentException("Invalid abbreviation language")
                Abbreviation(language, input.readUTF(), input.readUTF())
            }
            require(input.read() == -1) { "Invalid abbreviations" }
            entries.also { AbbreviationModel.validate(it) }
        }
    }

    fun readBounded(input: InputStream): ByteArray {
        val output = ByteArrayOutputStream()
        val buffer = ByteArray(4096)
        while (true) {
            val count = input.read(buffer, 0, minOf(buffer.size, MAX_FILE_BYTES + 1 - output.size()))
            if (count < 0) return output.toByteArray()
            require(count > 0) { "Invalid abbreviations" }
            output.write(buffer, 0, count)
            require(output.size() <= MAX_FILE_BYTES) { "Invalid abbreviations" }
        }
    }
}
