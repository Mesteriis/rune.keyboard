package io.github.mesteriis.rune.keyboard.smarttyping.personalization

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.InputStream
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction

/** Private device snapshot and deliberately narrower, phrase-only portable profile. */
object PersonalTypingCodec {
    const val MAX_FILE_BYTES = 1024 * 1024
    const val PROFILE_HEADER = "RUNE_PERSONAL_PHRASES_V1"
    private const val MAGIC = 0x52505431

    fun encode(snapshot: PersonalTypingSnapshot): ByteArray {
        validate(snapshot)
        val bytes = ByteArrayOutputStream()
        DataOutputStream(bytes).use { out ->
            out.writeInt(MAGIC)
            out.writeInt(snapshot.confirmed.size)
            snapshot.confirmed.forEach { out.writeUTF(it.language.name); out.writeUTF(it.word) }
            out.writeInt(snapshot.feedback.size)
            snapshot.feedback.forEach {
                out.writeUTF(it.language.name); out.writeUTF(it.original); out.writeUTF(it.replacement)
                out.writeInt(it.accepted); out.writeBoolean(it.rejected)
            }
            out.writeInt(snapshot.phrases.size)
            snapshot.phrases.forEach {
                out.writeUTF(it.language.name); out.writeUTF(it.prefix); out.writeUTF(it.continuation); out.writeInt(it.support)
            }
        }
        return bytes.toByteArray().also { require(it.size <= MAX_FILE_BYTES) { "Invalid personal snapshot" } }
    }

    fun decode(bytes: ByteArray): PersonalTypingSnapshot {
        require(bytes.size <= MAX_FILE_BYTES) { "Invalid personal snapshot" }
        val source = DataInputStream(ByteArrayInputStream(bytes))
        require(source.readInt() == MAGIC) { "Invalid personal snapshot" }
        val confirmed = List(readSize(source, PersonalTypingModel.MAX_CONFIRMED)) {
            PersonalWord(language(source.readUTF()), source.readUTF())
        }
        val feedback = List(readSize(source, PersonalTypingModel.MAX_FEEDBACK)) {
            val lang = language(source.readUTF())
            val original = source.readUTF()
            val replacement = source.readUTF()
            val accepted = source.readInt()
            val rejected = source.readUnsignedByte()
            require(rejected in 0..1) { "Invalid personal snapshot" }
            PersonalFeedback(lang, original, replacement, accepted, rejected == 1)
        }
        val phrases = List(readSize(source, PersonalTypingModel.MAX_PHRASES)) {
            PersonalPhrase(language(source.readUTF()), source.readUTF(), source.readUTF(), source.readInt())
        }
        require(source.read() == -1) { "Invalid personal snapshot" }
        return PersonalTypingSnapshot(feedback, confirmed, phrases).also(::validate)
    }

    /** Never permits imported confirmations or correction pairs, regardless of supplied counts. */
    fun decodeProfile(input: InputStream): List<PersonalPhrase> {
        val decoder = Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT)
        val text = decoder.decode(ByteBuffer.wrap(readBounded(input))).toString()
        val lines = text.split('\n').let { if (it.lastOrNull() == "") it.dropLast(1) else it }
        require(lines.firstOrNull() == PROFILE_HEADER && lines.size <= PersonalTypingModel.MAX_PHRASES + 1) {
            "Invalid personal profile"
        }
        val phrases = lines.drop(1).map { line ->
            val fields = line.split('\t')
            require(fields.size == 4) { "Invalid personal profile" }
            val count = fields[3].toIntOrNull() ?: throw IllegalArgumentException("Invalid personal profile")
            val phrase = PersonalPhrase(language(fields[0]), fields[1], fields[2], count)
            require(validPhrase(phrase) && count >= PersonalTypingModel.MIN_PHRASE_SUPPORT) { "Invalid personal profile" }
            phrase
        }
        require(phrases.map { Triple(it.language, it.prefix, it.continuation) }.distinct().size == phrases.size) {
            "Invalid personal profile"
        }
        return phrases
    }

    fun readBounded(input: InputStream): ByteArray {
        val result = ByteArrayOutputStream()
        val buffer = ByteArray(8192)
        while (true) {
            val count = input.read(buffer, 0, minOf(buffer.size, MAX_FILE_BYTES + 1 - result.size()))
            if (count < 0) break
            require(count > 0) { "Invalid personal file" }
            result.write(buffer, 0, count)
            require(result.size() <= MAX_FILE_BYTES) { "Invalid personal file" }
        }
        return result.toByteArray()
    }

    internal fun validate(snapshot: PersonalTypingSnapshot) {
        require(snapshot.feedback.size <= PersonalTypingModel.MAX_FEEDBACK &&
            snapshot.confirmed.size <= PersonalTypingModel.MAX_CONFIRMED &&
            snapshot.phrases.size <= PersonalTypingModel.MAX_PHRASES) { "Invalid personal snapshot" }
        require(snapshot.confirmed.all { canonicalWord(it.word) } && snapshot.confirmed.distinct().size == snapshot.confirmed.size) {
            "Invalid personal snapshot"
        }
        require(snapshot.feedback.all { canonicalWord(it.original) && canonicalWord(it.replacement) &&
            it.original != it.replacement && it.accepted in 0..PersonalTypingModel.MAX_COUNT && (it.rejected || it.accepted > 0) } &&
            snapshot.feedback.map { Triple(it.language, it.original, it.replacement) }.distinct().size == snapshot.feedback.size) {
            "Invalid personal snapshot"
        }
        require(snapshot.phrases.all(::validPhrase) &&
            snapshot.phrases.map { Triple(it.language, it.prefix, it.continuation) }.distinct().size == snapshot.phrases.size) {
            "Invalid personal snapshot"
        }
    }

    internal fun validPhrase(phrase: PersonalPhrase): Boolean =
        canonicalPhrase(phrase.prefix) && canonicalPhrase(phrase.continuation) && phrase.support in 1..PersonalTypingModel.MAX_COUNT

    private fun canonicalWord(word: String) = PersonalTypingModel.normalizeWord(word) == word
    private fun canonicalPhrase(words: String) = PersonalTypingModel.phraseWords(words)?.joinToString(" ") == words
    private fun language(value: String) = KeyboardLanguage.entries.firstOrNull { it.name == value }
        ?: throw IllegalArgumentException("Invalid personal language")
    private fun readSize(input: DataInputStream, max: Int): Int = input.readInt().also {
        require(it in 0..max) { "Invalid personal snapshot" }
    }
}
