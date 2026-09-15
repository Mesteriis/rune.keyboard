package io.github.mesteriis.rune.keyboard.smarttyping.controls

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.DataInputStream
import java.io.DataOutputStream

object TypingControlCodec {
    const val MAX_BYTES = 512 * 1024
    private const val MAGIC = 0x52544331
    fun encode(snapshot: TypingControlSnapshot): ByteArray {
        TypingControlModel.validate(snapshot)
        val buffer = ByteArrayOutputStream()
        DataOutputStream(buffer).use { output ->
            output.writeInt(MAGIC)
            output.writeInt(snapshot.words.size)
            snapshot.words.forEach { output.writeUTF(it.language.name); output.writeUTF(it.word) }
            output.writeInt(snapshot.apps.size)
            snapshot.apps.forEach { output.writeUTF(it.packageName); output.writeInt(it.profile.code) }
        }
        return buffer.toByteArray().also { require(it.size <= MAX_BYTES) }
    }
    fun decode(bytes: ByteArray): TypingControlSnapshot {
        require(bytes.size <= MAX_BYTES)
        return DataInputStream(ByteArrayInputStream(bytes)).use { input ->
            require(input.readInt() == MAGIC)
            val wordCount = input.readInt().also { require(it in 0..TypingControlModel.MAX_WORDS) }
            val words = List(wordCount) { ProtectedWord(KeyboardLanguage.valueOf(input.readUTF()), input.readUTF()) }
            val appCount = input.readInt().also { require(it in 0..TypingControlModel.MAX_APPS) }
            val apps = List(appCount) {
                val name = input.readUTF()
                val code = input.readInt()
                AppProfileBinding(name, TypingProfile.entries.single { it.code == code })
            }
            require(input.read() == -1)
            TypingControlSnapshot(words, apps).also(TypingControlModel::validate)
        }
    }
}
