package io.github.mesteriis.rune.keyboard.smarttyping.controls

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.*
import org.junit.Assert.*
import org.junit.Test

class TypingControlModelTest {
    private val ru = KeyboardLanguage.RUSSIAN
    private fun allSettings() = KeyboardSettings.DEFAULT.copy(personalLearning = true, touchPersonalization = true,
        phraseSuggestions = true, qualityMetrics = true, shadowComparison = true, wordBoundarySuggestions = true,
        abbreviations = true, phraseReview = true, visibleUndo = true, protectedWords = true,
        appProfiles = true, collectExamples = true, typoPatterns = true, doubleSpacePeriod = true,
        contextualPunctuationMode = ContextualPunctuationMode.SUGGESTIONS)

    @Test fun normalizedProtectionIsLanguageScopedAndBounded() {
        val data = checkNotNull(TypingControlModel.addWord(TypingControlSnapshot(), "ИмЯ", ru))
        assertTrue(data.contains("имя", ru)); assertTrue(data.contains("ИМЯ", ru))
        assertFalse(data.contains("имя", KeyboardLanguage.ENGLISH))
        assertEquals(data, TypingControlModel.addWord(data, "ИМЯ", ru))
        assertEquals("café", TypingControlModel.normalize("cafe\u0301"))
        for (invalid in listOf("", "two words", "https://example.org", "@name", "1234", "a\nb", "a".repeat(49)))
            assertNull(TypingControlModel.normalize(invalid))
        assertFalse(data.toString().contains("имя")); assertFalse(data.words[0].toString().contains("имя"))
    }

    @Test fun appObservationDoesNotEvictAssignedProfilesOrAcceptUnknownBindings() {
        val filled = TypingControlSnapshot(apps = (0 until TypingControlModel.MAX_APPS).map {
            AppProfileBinding("org.example.app$it", TypingProfile.FORMAL)
        })
        assertNull(TypingControlModel.observePackage(filled, "org.example.extra"))
        assertNull(TypingControlModel.assign(filled, "org.example.unknown", TypingProfile.CONVERSATION))
        val withDefault = filled.copy(apps = filled.apps.dropLast(1) + AppProfileBinding("org.example.default", TypingProfile.DEFAULT))
        val updated = checkNotNull(TypingControlModel.observePackage(withDefault, "org.example.extra"))
        assertEquals(TypingControlModel.MAX_APPS, updated.apps.size)
        assertEquals(TypingProfile.FORMAL, updated.profile("org.example.app0"))
        assertFalse(updated.apps.any { it.packageName == "org.example.default" })
        for (name in listOf("", "../private", "org app", "org.example.\napp", "a".repeat(256)))
            assertNull(TypingControlModel.observePackage(TypingControlSnapshot(), name))
    }

    @Test fun presetsRestrictFeaturesAndPreserveGlobalConsentAndOff() {
        for (base in listOf(allSettings(), KeyboardSettings.DEFAULT.copy(autocorrectionMode = AutocorrectionMode.OFF))) {
            for (profile in TypingProfile.entries) {
                val result = profile.apply(base)
                assertEquals(base.protectedWords, result.protectedWords)
                assertEquals(base.personalLearning, result.personalLearning)
                assertEquals(base.collectExamples, result.collectExamples)
                assertEquals(base.typoPatterns, result.typoPatterns)
                assertEquals(base.touchPersonalization, result.touchPersonalization)
                if (base.autocorrectionMode == AutocorrectionMode.OFF) assertEquals(AutocorrectionMode.OFF, result.autocorrectionMode)
            }
        }
        val chat = TypingProfile.CONVERSATION.apply(allSettings())
        assertEquals(AutocorrectionMode.SUGGESTIONS, chat.autocorrectionMode)
        assertFalse(chat.mechanicalPunctuation); assertFalse(chat.phraseReview); assertFalse(chat.doubleSpacePeriod)
        assertEquals(ContextualPunctuationMode.OFF, chat.contextualPunctuationMode)
        val formal = TypingProfile.FORMAL.apply(allSettings())
        assertFalse(formal.phraseSuggestions); assertFalse(formal.abbreviations)
    }

    @Test fun resolutionUsesCurrentAppAndMissingStorageFailsClosed() {
        val base = allSettings()
        assertTrue(base.doubleSpacePeriod)
        val data = TypingControlSnapshot(apps = listOf(AppProfileBinding("org.example.chat", TypingProfile.CONVERSATION),
            AppProfileBinding("org.example.mail", TypingProfile.FORMAL)))
        assertEquals(TypingProfile.CONVERSATION, TypingProfileResolver.resolve(base, "org.example.chat", data).first)
        assertEquals(TypingProfile.FORMAL, TypingProfileResolver.resolve(base, "org.example.mail", data).first)
        assertEquals(base, TypingProfileResolver.resolve(base, "org.example.other", data).second)
        assertEquals(base.copy(appProfiles = false), TypingProfileResolver.resolve(base.copy(appProfiles = false), "org.example.chat", null).second)
        val loading = TypingProfileResolver.resolve(base, "org.example.chat", null).second
        assertEquals(AutocorrectionMode.OFF, loading.autocorrectionMode)
        assertFalse(loading.phraseSuggestions); assertFalse(loading.mechanicalPunctuation)
        assertFalse(loading.doubleSpacePeriod)
        val disabled = TypingProfileResolver.resolve(base.copy(appProfiles = false), "org.example.chat", data).second
        assertTrue(disabled.doubleSpacePeriod)
        assertTrue(base.doubleSpacePeriod)
    }

    @Test fun maximalUnicodeSnapshotFitsPersistentBudget() {
        val words = (0 until TypingControlModel.MAX_WORDS).map { index ->
            val prefix = listOf(index % 26, index / 26 % 26, index / 676).map { ('a'.code + it).toChar() }.joinToString("")
            ProtectedWord(ru, checkNotNull(TypingControlModel.normalize(prefix + String(Character.toChars(0x10428)).repeat(45))))
        }
        val snapshot = TypingControlSnapshot(words, (0 until TypingControlModel.MAX_APPS).map {
            AppProfileBinding("org." + "a".repeat(245) + it.toString().padStart(3, 'a'), TypingProfile.FORMAL)
        })
        assertEquals(snapshot, TypingControlCodec.decode(TypingControlCodec.encode(snapshot)))
    }

    @Test fun codecRoundTripsAndRejectsCorruptionDuplicatesAndOversize() {
        val value = TypingControlSnapshot(listOf(ProtectedWord(ru, "имя")), listOf(AppProfileBinding("org.example.chat", TypingProfile.CONVERSATION)))
        val encoded = TypingControlCodec.encode(value)
        assertEquals(value, TypingControlCodec.decode(encoded))
        for (bytes in listOf(byteArrayOf(), encoded.dropLast(1).toByteArray(), encoded + byteArrayOf(0),
            encoded.copyOf().apply { this[0] = 0 }, ByteArray(TypingControlCodec.MAX_BYTES + 1))) {
            try { TypingControlCodec.decode(bytes); fail("Corrupt data accepted") } catch (_: Exception) { }
        }
        for (data in listOf(value.copy(words = value.words + value.words), value.copy(apps = value.apps + value.apps),
            value.copy(words = listOf(ProtectedWord(ru, "Имя"))))) {
            try { TypingControlCodec.encode(data); fail("Invalid data accepted") } catch (_: IllegalArgumentException) { }
        }
    }
}
