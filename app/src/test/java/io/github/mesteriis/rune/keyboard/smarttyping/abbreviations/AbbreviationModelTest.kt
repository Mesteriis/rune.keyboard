package io.github.mesteriis.rune.keyboard.smarttyping.abbreviations

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.*
import org.junit.Test
import java.util.Locale

class AbbreviationModelTest {
    private val ru = KeyboardLanguage.RUSSIAN
    private val en = KeyboardLanguage.ENGLISH
    private val es = KeyboardLanguage.SPANISH

    @Test fun `new model has no seeds and only explicitly saved expansions`() {
        val model = AbbreviationModel()
        assertNull(model.expansion("щб", ru))
        assertEquals(AbbreviationResult.SAVED, model.save(ru, "щб", "щас буду"))
        assertEquals("щас буду", model.expansion("щб", ru))
        assertNull(model.expansion("щб", en))
        assertNull(model.expansion("щб ", ru))
        assertNull(model.expansion("щ", ru))
    }

    @Test fun `unicode keys fold and normalize while expansion preserves user casing`() {
        val model = AbbreviationModel()
        model.save(ru, "ЩБ", "Щас буду!")
        assertEquals("Щас буду!", model.expansion("Щб", ru))
        model.save(es, "MAÑ", "Mañana, a las 8.")
        assertEquals("Mañana, a las 8.", model.expansion("man\u0303", es))
        assertEquals(AbbreviationResult.DUPLICATE, model.save(es, "man\u0303", "mañana"))
    }

    @Test fun `key casing is independent of device locale`() {
        val previous = Locale.getDefault()
        try {
            Locale.setDefault(Locale.forLanguageTag("tr"))
            val model = AbbreviationModel()
            model.save(en, "IDK", "I do not know")
            assertEquals("I do not know", model.expansion("idk", en))
        } finally { Locale.setDefault(previous) }
    }

    @Test fun `duplicate requires explicit edit and other languages remain independent`() {
        val model = AbbreviationModel()
        model.save(en, "brb", "be right back")
        assertEquals(AbbreviationResult.DUPLICATE, model.save(en, "BRB", "back soon"))
        assertEquals("be right back", model.expansion("brb", en))
        assertEquals(AbbreviationResult.SAVED, model.save(es, "brb", "vuelvo pronto"))
        val original = model.snapshot().first()
        assertEquals(AbbreviationResult.SAVED, model.save(en, "bbl", "back later", original))
        assertNull(model.expansion("brb", en))
        assertEquals("back later", model.expansion("bbl", en))
        assertEquals(AbbreviationResult.NOT_FOUND, model.delete(original))
        val edited = model.snapshot().first()
        assertEquals(AbbreviationResult.SAVED, model.delete(edited))
        assertNull(model.expansion("bbl", en))
        assertEquals("vuelvo pronto", model.expansion("brb", es))
    }

    @Test fun `editing cannot silently overwrite another entry`() {
        val model = AbbreviationModel()
        model.save(en, "brb", "be right back")
        model.save(en, "bbl", "back later")
        val before = model.snapshot()
        assertEquals(AbbreviationResult.DUPLICATE, model.save(en, "bbl", "soon", before.first()))
        assertEquals(before, model.snapshot())
        assertEquals(AbbreviationResult.SAVED, model.save(en, "brb", "Back soon.", before.first()))
        assertEquals(AbbreviationResult.NOT_FOUND, model.save(en, "brb", "old edit", before.first()))
    }

    @Test fun `capacity rejects new records but permits replacement and reuse after deletion`() {
        val model = AbbreviationModel()
        repeat(AbbreviationModel.MAX_ENTRIES) { index ->
            val key = "k" + ('a' + index / 26) + ('a' + index % 26)
            assertEquals(AbbreviationResult.SAVED, model.save(en, key, "expansion"))
        }
        assertEquals(AbbreviationResult.LIMIT, model.save(en, "new", "expansion"))
        assertEquals(AbbreviationResult.SAVED, model.save(en, "new", "replacement", model.snapshot().first()))
        model.delete(model.snapshot().first())
        assertEquals(AbbreviationResult.SAVED, model.save(en, "added", "expansion"))
        assertEquals(AbbreviationModel.MAX_ENTRIES, model.snapshot().size)
    }

    @Test fun `length limits measure Unicode code points and reject unsafe characters`() {
        val model = AbbreviationModel()
        val astralLetter = String(Character.toChars(0x10428))
        assertEquals(AbbreviationResult.SAVED, model.save(en, astralLetter.repeat(32), astralLetter.repeat(128)))
        assertEquals(AbbreviationResult.INVALID, model.save(en, astralLetter.repeat(33), "valid"))
        assertEquals(AbbreviationResult.INVALID, model.save(en, "valid", astralLetter.repeat(129)))
        listOf("", "a b", " brb", "brb ", "brb1", "a\n", "a\u0000", "a\u202E", "\u0301a", "\uD800").forEach {
            assertEquals(AbbreviationResult.INVALID, model.save(en, it, "valid"))
        }
        listOf("", " leading", "trailing ", "line\nbreak", "tab\ttext", "hidden\u200B", "bidi\u202E", "\uD800", "😊").forEach {
            assertEquals(AbbreviationResult.INVALID, model.save(en, "valid", it))
        }
    }

    @Test fun `invalid restore is all or nothing and snapshots do not leak mutable ownership`() {
        val model = AbbreviationModel()
        val input = mutableListOf(Abbreviation(ru, "щб", "щас буду"))
        model.restore(input)
        input.clear()
        assertEquals("щас буду", model.expansion("щб", ru))
        try {
            model.restore(listOf(Abbreviation(ru, "ЩБ", "invalid canonical key")))
            fail("Expected validation failure")
        } catch (_: IllegalArgumentException) { }
        assertEquals("щас буду", model.expansion("щб", ru))
        assertFalse(model.snapshot().toString().contains("щас буду"))
    }
}
