package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LanguageRouter
import java.util.Locale
import org.junit.Assert.*
import org.junit.Test

class OrthographyPoliciesTest {
    @Test
    fun `technical and non-word forms are protected without context`() {
        val tokens = listOf(
            "https://example.org", "example.org", "name@example.org", "/usr/bin", "C:\\temp", "a/b", "a\\b",
            "snake_case", "camelCase", "PascalCase", "iPhone", "kebab-case", "ALLCAPS", "ЁЛКА", "NIÑO",
            "hello2", "2слова", "b１２", "550e8400-e29b-41d4-a716-446655440000", "127.0.0.1", "::1",
            "1.2.3", "v1.2.3-rc.1", "foo()", "x=y", "--help", "$" + "PATH", "echo hi", "a|b", "`pwd`",
            "foo😀", "word\u200D", "ab\u202E", "foo\n", "50%", "\u0301", "'quoted'", "", "123",
        )
        for (token in tokens) assertTrue("Expected protected token", ProtectedTokenPolicy.isProtected(token))
    }

    @Test
    fun `ordinary words title case and internal apostrophes remain eligible`() {
        for (token in listOf("hello", "Hello", "I", "Я", "привет", "ёлка", "всё", "niño", "está", "pingüino",
            "don't", "l’amour", "e\u0301", "q\u0301", "сло́во")) {
            assertFalse("Ordinary word unexpectedly protected", ProtectedTokenPolicy.isProtected(token))
        }
    }

    @Test
    fun `mixed scripts and unsupported scripts fail closed`() {
        for (token in listOf("pаypal", "aб", "testЯ", "аα", "a\u093E", "a\u05B0")) {
            assertEquals(ProtectedTokenReason.MIXED_SCRIPT, ProtectedTokenPolicy.reason(token))
        }
        for (token in listOf("中文", "مرحبا", "αβ")) {
            assertEquals(ProtectedTokenReason.UNSUPPORTED_SCRIPT, ProtectedTokenPolicy.reason(token))
        }
    }

    @Test
    fun `protection uses code points and rejects malformed Unicode and expansion overflow`() {
        assertFalse(ProtectedTokenPolicy.isProtected("a".repeat(32)))
        assertEquals(ProtectedTokenReason.TOO_LONG, ProtectedTokenPolicy.reason("a".repeat(33)))
        assertEquals(ProtectedTokenReason.TOO_LONG, ProtectedTokenPolicy.reason("😀".repeat(33)))
        assertEquals(ProtectedTokenReason.MALFORMED_UNICODE, ProtectedTokenPolicy.reason("a\uD800"))
        assertEquals(ProtectedTokenReason.MALFORMED_UNICODE, ProtectedTokenPolicy.reason("\uDC00a"))
        assertEquals(ProtectedTokenReason.TOO_LONG, ProtectedTokenPolicy.reason("a" + "\u0344".repeat(31)))
        assertEquals(ProtectedTokenReason.TOO_LONG, ProtectedTokenPolicy.reason("İ" + "a".repeat(31)))
    }

    @Test
    fun `Cyrillic and Spanish markers override active layout`() {
        for (active in KeyboardLanguage.entries) {
            for (token in listOf("привет", "ёлка", "все")) {
                val route = LanguageRouter.route(token, active)
                assertEquals(KeyboardLanguage.RUSSIAN, route.primary)
                assertNull(route.fallback)
            }
            for (token in listOf("niño", "á", "é", "í", "ó", "ú", "ü", "Á", "n\u0303", "e\u0301")) {
                val route = LanguageRouter.route(token, active)
                assertEquals(KeyboardLanguage.SPANISH, route.primary)
                assertNull(route.fallback)
            }
        }
    }

    @Test
    fun `plain Latin has strong active EN ES prior and bounded opposite fallback`() {
        for (active in listOf(KeyboardLanguage.ENGLISH, KeyboardLanguage.SPANISH)) {
            val route = LanguageRouter.route("casa", active)
            assertEquals(active, route.primary)
            assertNotEquals(active, route.fallback)
            assertEquals(4, route.primaryPrior)
            assertEquals(1, route.fallbackPrior)
            assertEquals(2, route.fallbackCandidateLimit)
        }
        val fromRu = LanguageRouter.route("hello", KeyboardLanguage.RUSSIAN)
        assertEquals(KeyboardLanguage.ENGLISH, fromRu.primary)
        assertEquals(KeyboardLanguage.SPANISH, fromRu.fallback)
    }

    @Test
    fun `technical mixed and oversized tokens have no language search route`() {
        for (token in listOf("someIdentifier", "aб", "a_b", "a".repeat(33), "")) {
            val route = LanguageRouter.route(token, KeyboardLanguage.ENGLISH)
            assertNull(route.primary)
            assertNull(route.fallback)
            assertEquals(0, route.fallbackCandidateLimit)
            assertNotNull(route.protectedReason)
        }
    }

    @Test
    fun `case patterns distinguish title caps mixed and uncased`() {
        for (token in listOf("hello", "ñandú", "ёлка", "e\u0301")) assertEquals(CasePattern.LOWER, CasePattern.analyze(token))
        for (token in listOf("Hello", "Ñandú", "Ёлка", "ǅungla")) assertEquals(CasePattern.TITLE, CasePattern.analyze(token))
        for (token in listOf("HELLO", "I", "ЁЛКА")) assertEquals(CasePattern.UPPER, CasePattern.analyze(token))
        for (token in listOf("camelCase", "iPhone", "HeLLo")) assertEquals(CasePattern.MIXED, CasePattern.analyze(token))
        assertEquals(CasePattern.UNCASED, CasePattern.analyze("123😀"))
        assertEquals(CasePattern.UNCASED, CasePattern.analyze(""))
    }

    @Test
    fun `case restoration preserves accents handles titlecase and declines mixed`() {
        assertEquals("ёлка", CasePattern.LOWER.preserve("ЁЛКА"))
        assertEquals("Niño", CasePattern.TITLE.preserve("NIÑO"))
        assertEquals("Ésta", CasePattern.TITLE.preserve("e\u0301sta"))
        assertEquals("ǲungla", CasePattern.TITLE.preserve("ǳUNGLA"))
        assertEquals("Ss", CasePattern.TITLE.preserve("ß"))
        assertEquals("ESTÁ", CasePattern.UPPER.preserve("está"))
        assertNull(CasePattern.MIXED.preserve("candidate"))
        assertNull(CasePattern.UNCASED.preserve("candidate"))
        assertNull(CasePattern.UPPER.preserve("ß".repeat(32)))
    }

    @Test
    fun `default locale never changes normalization casing or routing`() {
        val previous = Locale.getDefault()
        try {
            Locale.setDefault(Locale.forLanguageTag("tr-TR"))
            assertEquals("i", CasePattern.LOWER.preserve("I"))
            assertEquals("I", CasePattern.UPPER.preserve("i"))
            assertEquals(KeyboardLanguage.SPANISH, LanguageRouter.route("NIño", KeyboardLanguage.ENGLISH).let {
                // Mixed case remains protected even in Turkish; a normal title token routes ES.
                assertNotNull(it.protectedReason)
                LanguageRouter.route("Niño", KeyboardLanguage.ENGLISH).primary
            })
            assertEquals(0.0, WeightedDamerauLevenshtein().features("I", "i", KeyboardLanguage.ENGLISH).editCost, 0.0)
        } finally {
            Locale.setDefault(previous)
        }
    }
}
