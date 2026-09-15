package io.github.mesteriis.rune.keyboard.smarttyping.personalization

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.ByteArrayInputStream
import org.junit.Assert.*
import org.junit.Test

class PersonalTypingCodecTest {
    private val en = KeyboardLanguage.ENGLISH

    @Test fun `snapshot round trip preserves explicit rejection and bounded phrase evidence`() {
        val original = PersonalTypingModel { _, _ -> true }
        original.recordAccepted("helo", "hello", en)
        original.recordRejected("world", "word", en)
        repeat(3) { original.recordPhrase("hello", "world", en) }
        val bytes = PersonalTypingCodec.encode(original.snapshot())
        val restored = PersonalTypingModel { _, _ -> true }
        restored.restore(PersonalTypingCodec.decode(bytes))
        assertEquals(original.snapshot(), restored.snapshot())
        assertTrue(restored.rejects("world", "word", en))
        assertEquals(listOf("world"), restored.suggestions("hello", en).map { it.text })
    }

    @Test fun `restoring while dictionary loads retains phrases but waits to suggest`() {
        var ready = false
        val model = PersonalTypingModel { _, _ -> ready }
        model.restore(PersonalTypingSnapshot(phrases = listOf(PersonalPhrase(en, "see", "you", 3))))
        assertEquals(1, model.snapshot().phrases.size)
        assertTrue(model.suggestions("see", en).isEmpty())
        ready = true
        assertEquals(listOf("you"), model.suggestions("see", en).map { it.text })
    }

    @Test fun `corrupt truncated oversized and trailing snapshot data is rejected`() {
        val bytes = PersonalTypingCodec.encode(PersonalTypingSnapshot())
        invalid { PersonalTypingCodec.decode(bytes.copyOf(bytes.size - 1)) }
        invalid { PersonalTypingCodec.decode(bytes + byteArrayOf(1)) }
        invalid { PersonalTypingCodec.decode(ByteArray(PersonalTypingCodec.MAX_FILE_BYTES + 1)) }
        invalid { PersonalTypingCodec.decode(bytes.clone().apply { this[0] = 0 }) }
        invalid { PersonalTypingCodec.readBounded(ByteArrayInputStream(ByteArray(PersonalTypingCodec.MAX_FILE_BYTES + 1))) }
    }

    @Test fun `invalid snapshot leaves live model unchanged`() {
        val model = PersonalTypingModel { _, _ -> true }
        model.recordConfirmedWord("hello", en)
        val before = model.snapshot()
        invalid { model.restore(PersonalTypingSnapshot(confirmed = listOf(PersonalWord(en, "Hello")))) }
        assertEquals(before, model.snapshot())
        invalid { PersonalTypingCodec.encode(PersonalTypingSnapshot(confirmed = before.confirmed + before.confirmed)) }
    }

    @Test fun `portable importer validates schema support language duplicates and word boundaries`() {
        val header = PersonalTypingCodec.PROFILE_HEADER + "\n"
        assertEquals(listOf(PersonalPhrase(en, "see you", "soon", 3)), profile(header + "ENGLISH\tsee you\tsoon\t3\n"))
        listOf(
            "BAD\n", header + "ENGLISH\tsee\tyou\t2\n", header + "ENGLISH\tsee\tyou\t256\n",
            header + "ENGLISH\tsee\tyou\tthree\n", header + "OTHER\tsee\tyou\t3\n",
            header + "ENGLISH\tsee. you\tsoon\t3\n", header + "ENGLISH\tsee\tyou soon world\t3\n",
            header + "ENGLISH\tsee\tYou\t3\n", header + "C\tENGLISH\tyuo\t255\n",
            header + "ENGLISH\tsee\tyou\t3\nENGLISH\tsee\tyou\t3\n",
        ).forEach { text -> invalid { profile(text) } }
        invalid { PersonalTypingCodec.decodeProfile(ByteArrayInputStream(byteArrayOf(0xC3.toByte(), 0x28))) }
    }

    @Test fun `all maximum capacity tables fit byte budget with multibyte words`() {
        fun word(index: Int): String = "界".repeat(45) + ('a' + index / 676) + ('a' + index / 26 % 26) + ('a' + index % 26)
        val snapshot = PersonalTypingSnapshot(
            feedback = List(PersonalTypingModel.MAX_FEEDBACK) { PersonalFeedback(en, word(it), word(it + 2000), 255, true) },
            confirmed = List(PersonalTypingModel.MAX_CONFIRMED) { PersonalWord(en, word(it)) },
            phrases = List(PersonalTypingModel.MAX_PHRASES) { PersonalPhrase(en, word(it) + " " + word(it),
                word(it + 2000) + " " + word(it + 2000), 255) },
        )
        val bytes = PersonalTypingCodec.encode(snapshot)
        assertTrue(bytes.size <= PersonalTypingCodec.MAX_FILE_BYTES)
        assertEquals(snapshot, PersonalTypingCodec.decode(bytes))
    }

    @Test fun `private records do not disclose words in diagnostic strings`() {
        val snapshot = PersonalTypingSnapshot(listOf(PersonalFeedback(en, "secret", "private", 1, true)),
            listOf(PersonalWord(en, "secret")), listOf(PersonalPhrase(en, "secret", "private", 3)))
        assertFalse(snapshot.toString().contains("secret"))
        assertFalse(snapshot.feedback.single().toString().contains("private"))
        assertFalse(snapshot.confirmed.single().toString().contains("secret"))
        assertFalse(snapshot.phrases.single().toString().contains("private"))
    }

    private fun profile(value: String) = PersonalTypingCodec.decodeProfile(ByteArrayInputStream(value.toByteArray(Charsets.UTF_8)))
    private fun invalid(block: () -> Unit) {
        try { block(); fail("Expected invalid data rejection") } catch (_: IllegalArgumentException) {
        } catch (_: java.io.IOException) { }
    }
}
