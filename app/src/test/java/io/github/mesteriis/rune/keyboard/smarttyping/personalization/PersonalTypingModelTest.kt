package io.github.mesteriis.rune.keyboard.smarttyping.personalization

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.*
import org.junit.Test

class PersonalTypingModelTest {
    private val en = KeyboardLanguage.ENGLISH
    private val ru = KeyboardLanguage.RUSSIAN
    private val dictionary = setOf("see", "you", "soon", "very", "well", "hello", "world")
    private fun model() = PersonalTypingModel { word, language -> language == en && word in dictionary }

    @Test fun `rejection permanently overrides stronger positive feedback without certifying original`() {
        val model = model()
        model.recordRejected("Yuo", "you", en)
        repeat(1000) { model.recordAccepted("yuo", "you", en) }
        assertTrue(model.rejects("YUO", "YOU", en))
        assertFalse(model.protectsOriginal("yuo", en))
        assertEquals(-PersonalTypingModel.MAX_COUNT, model.preference("yuo", "you", en))
        assertEquals(PersonalTypingModel.MAX_COUNT, model.snapshot().feedback.single().accepted)
        assertFalse(model.rejects("yuo", "you", ru))
        model.reset()
        assertFalse(model.rejects("yuo", "you", en))
    }

    @Test fun `accepted and manual retyped pairs supply manual ordering only`() {
        val model = model()
        model.recordAccepted("helo", "hello", en)
        model.recordManualRetype("helo", "hello", en)
        assertEquals(2, model.preference("helo", "hello", en))
        assertTrue(model.protectsOriginal("hello", en))
        assertFalse(model.protectsOriginal("helo", en))
        assertEquals(0, model.preference("helo", "world", en))
    }

    @Test fun `phrases require repeated validated support without certifying raw spelling`() {
        val model = model()
        repeat(2) { model.recordPhrase("see", "you soon", en) }
        assertTrue(model.suggestions("see ", en).isEmpty())
        model.recordPhrase("see", "you soon", en)
        assertEquals(listOf("you soon"), model.suggestions("see ", en).map { it.text })
        repeat(1000) { model.recordPhrase("see", "yuo", en) }
        assertFalse(model.protectsOriginal("see", en))
        assertFalse(model.protectsOriginal("yuo", en))
        assertEquals(listOf("you soon"), model.suggestions("see ", en).map { it.text })
        model.recordConfirmedWord("yuo", en)
        repeat(3) { model.recordPhrase("see", "yuo", en) }
        assertTrue(model.suggestions("see ", en).any { it.text == "yuo" })
    }

    @Test fun `sentence message and invalid continuation boundaries do not bridge`() {
        val model = model()
        repeat(3) {
            model.recordPhrase("see you.", "soon", en)
            model.recordPhrase("see you\n", "soon", en)
            model.recordPhrase("see you", "very well soon", en)
            model.recordPhrase("see you", "soon.world", en)
        }
        assertTrue(model.snapshot().phrases.isEmpty())
        repeat(3) { model.recordPhrase("hello. see you", "soon", en) }
        assertEquals(listOf("soon"), model.suggestions("world see you ", en).map { it.text })
        assertTrue(model.suggestions("see you. ", en).isEmpty())
        assertTrue(model.suggestions("see you\n", en).isEmpty())
        assertTrue(model.suggestions("see you ", ru).isEmpty())
        assertTrue(model.suggestions("x".repeat(513), en).isEmpty())
    }

    @Test fun `memory tables word sizes and counts stay bounded`() {
        val model = PersonalTypingModel { _, _ -> true }
        for (index in 0..1500) {
            val word = "word" + alphabetic(index)
            model.recordAccepted(word, "replacement", en)
            model.recordConfirmedWord(word, en)
            repeat(3) { model.recordPhrase("hello", word, en) }
        }
        val snapshot = model.snapshot()
        assertEquals(PersonalTypingModel.MAX_FEEDBACK, snapshot.feedback.size)
        assertEquals(PersonalTypingModel.MAX_CONFIRMED, snapshot.confirmed.size)
        assertEquals(PersonalTypingModel.MAX_PHRASES, snapshot.phrases.size)
        model.recordRejected("newword", "replacement", en)
        assertTrue(model.rejects("newword", "replacement", en))
        model.recordConfirmedWord("z".repeat(49), en)
        assertFalse(model.protectsOriginal("z".repeat(49), en))
    }

    @Test fun `full rejection table fails closed for new pairs until reset`() {
        val model = model()
        repeat(PersonalTypingModel.MAX_FEEDBACK + 1) {
            model.recordRejected("word" + alphabetic(it), "replacement", en)
        }
        assertEquals(PersonalTypingModel.MAX_FEEDBACK, model.snapshot().feedback.size)
        assertTrue(model.rejects("newword", "replacement", en))
        val restored = model()
        restored.restore(PersonalTypingCodec.decode(PersonalTypingCodec.encode(model.snapshot())))
        assertTrue(restored.rejects("newword", "replacement", en))
        model.reset()
        assertFalse(model.rejects("newword", "replacement", en))
    }

    @Test fun `dictionary-only import cannot manufacture explicit spelling approval`() {
        val model = model()
        assertEquals(1, model.importPhrases(listOf(
            PersonalPhrase(en, "see", "you", 255), PersonalPhrase(en, "see", "yuo", 255))))
        assertEquals(listOf("you"), model.suggestions("see", en).map { it.text })
        assertTrue(model.snapshot().feedback.isEmpty())
        assertTrue(model.snapshot().confirmed.isEmpty())
        model.recordConfirmedWord("yuo", en)
        assertEquals(0, model.importPhrases(listOf(PersonalPhrase(en, "see", "yuo", 255))))
    }

    private fun alphabetic(index: Int): String = if (index < 26) ('a' + index).toString()
        else alphabetic(index / 26 - 1) + ('a' + index % 26)
}
