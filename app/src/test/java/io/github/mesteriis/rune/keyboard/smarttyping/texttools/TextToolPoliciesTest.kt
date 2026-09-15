package io.github.mesteriis.rune.keyboard.smarttyping.texttools

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.*
import org.junit.Test

class TextToolPoliciesTest {
    private val ru = KeyboardLanguage.RUSSIAN
    private val words = setOf("не", "знаю", "потому", "что", "привет", "при", "дом", "работа", "домработа")
    private fun boundary(text: String, dictionary: Set<String> = words) =
        WordBoundaryPolicy.suggest(text, ru, dictionary::contains)

    @Test fun `curated missing boundaries preserve exact case and trailing space`() {
        assertEquals(TextToolSuggestion("Незнаю ", "Не знаю ", TextToolKind.WORD_SPLIT), boundary("Я. Незнаю "))
        assertEquals("потому что", boundary("потомучто")?.replacementSuffix)
        assertNull(boundary("потомучто", emptySet()))
        assertNull(boundary("незнаю", words + "незнаю"))
    }

    @Test fun `unique dictionary split has minimum parts and does not split valid words`() {
        assertEquals("hello world", WordBoundaryPolicy.suggest("helloworld", KeyboardLanguage.ENGLISH,
            setOf("hello", "world")::contains)?.replacementSuffix)
        assertNull(WordBoundaryPolicy.suggest("helloworld", KeyboardLanguage.ENGLISH,
            setOf("hello", "world", "hell", "oworld")::contains))
        assertNull(WordBoundaryPolicy.suggest("say helloworld", KeyboardLanguage.ENGLISH,
            setOf("sayhelloworld", "hello", "world", "hell", "oworld")::contains))
        assertNull(WordBoundaryPolicy.suggest("say helloworld", KeyboardLanguage.ENGLISH,
            setOf("sayhelloworld", "hello", "world")::contains))
        assertNull(boundary("домработа"))
        assertNull(boundary("ядома", setOf("я", "дома")))
    }

    @Test fun `join requires dictionary word and at least one invalid fragment`() {
        assertEquals(TextToolSuggestion("При вет", "Привет", TextToolKind.WORD_JOIN), boundary("О! При вет"))
        assertEquals("привет ", boundary("при вет ")?.replacementSuffix)
        assertNull(boundary("при вет", words + "вет"))
        assertNull(boundary("при Вет"))
        assertNull(boundary("при. вет"))
        assertNull(boundary("при\nвет"))
        assertNull(boundary("при  вет"))
    }

    @Test fun `protected tokens and wrong language stay untouched`() {
        for (text in listOf("@незнаю", "site/незнаю", "незнаю.ru", "НезНаю", "НЕЗНАЮ", "не3знаю", "неzнаю",
            "при @вет", "user@при вет", "при\tвет", "\uD800незнаю", "незнаю  ")) {
            assertNull(text, boundary(text))
        }
        assertNull(WordBoundaryPolicy.suggest("незнаю", KeyboardLanguage.ENGLISH, words::contains))
        assertEquals("café solo", WordBoundaryPolicy.suggest("cafésolo", KeyboardLanguage.SPANISH,
            setOf("café", "solo")::contains)?.replacementSuffix)
    }

    @Test fun `bounded policy stops before dictionary work and contains failures`() {
        var calls = 0
        assertNull(WordBoundaryPolicy.suggest("а".repeat(257), ru) { calls++; true })
        assertEquals(0, calls)
        WordBoundaryPolicy.suggest("а".repeat(32), ru) { calls++; false }
        assertTrue(calls <= 64)
        assertNull(WordBoundaryPolicy.suggest("незнаю", ru) { error("unavailable") })
    }

    @Test fun `finished phrase agreement is an actual finite grammatical rule`() {
        assertEquals(TextToolSuggestion("Я идет домой.", "Я иду домой.", TextToolKind.PHRASE_REVIEW),
            PhraseReviewPolicy.suggest("Я идет домой.", ru))
        assertEquals("Ты не знаешь? ", PhraseReviewPolicy.suggest("Ты не знаю? ", ru)?.replacementSuffix)
        assertEquals("Мы думаем!", PhraseReviewPolicy.suggest("Мы думает!", ru)?.replacementSuffix)
        assertEquals("Я иду.", PhraseReviewPolicy.suggest("Я идёшь.", ru)?.replacementSuffix)
        assertNull(PhraseReviewPolicy.suggest("Я иду домой.", ru))
        assertNull(PhraseReviewPolicy.suggest("Я идет домой", ru))
        assertNull(PhraseReviewPolicy.suggest("I goes home.", KeyboardLanguage.ENGLISH))
    }

    @Test fun `clear subordinate clauses receive necessary commas`() {
        assertEquals("Я думаю, что ты знаешь.", PhraseReviewPolicy.suggest("Я думаю что ты знаешь.", ru)?.replacementSuffix)
        assertEquals("Я иду домой, потому что я хочу спать.",
            PhraseReviewPolicy.suggest("Я идет домой потому что я хочу спать.", ru)?.replacementSuffix)
        assertNull(PhraseReviewPolicy.suggest("Я думаю, что ты знаешь.", ru))
        assertNull(PhraseReviewPolicy.suggest("Я иду домой не потому что я хочу спать.", ru))
        assertNull(PhraseReviewPolicy.suggest("Я не иду домой потому что я хочу спать.", ru))
        assertNull(PhraseReviewPolicy.suggest("Я знаю что-то.", ru))
        assertNull(PhraseReviewPolicy.suggest("Я знаю что делать.", ru))
    }

    @Test fun `phrase only returns last completed sentence and preserves spacing`() {
        assertEquals(TextToolSuggestion("Я  идет домой! ", "Я  иду домой! ", TextToolKind.PHRASE_REVIEW),
            PhraseReviewPolicy.suggest("Ты знаешь. Я  идет домой! ", ru))
        for (text in listOf("Я идет site.ru.", "Я идет @домой.", "Я идет /домой.", "Я идет домой...",
            "Я идет домой?!", "Я ИДЕТ домой.", "Я ИдЕт домой.", "Я идет \uD800.", "а".repeat(257))) {
            assertNull(text, PhraseReviewPolicy.suggest(text, ru))
        }
        assertNull(PhraseReviewPolicy.suggest("Я идет домой. Следующая", ru))
        assertNull(PhraseReviewPolicy.suggest("Он говорит, я идет домой.", ru))
    }

    @Test fun `suggestions cannot accidentally expose owned text through diagnostics`() {
        val suggestion = boundary("незнаю")!!
        assertFalse(suggestion.toString().contains("незнаю"))
        assertFalse(suggestion.toString().contains("не знаю"))
    }
}
