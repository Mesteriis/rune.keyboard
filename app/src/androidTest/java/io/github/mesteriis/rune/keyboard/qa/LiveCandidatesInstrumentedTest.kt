package io.github.mesteriis.rune.keyboard.qa

import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiObject2
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/** Public fixture only; observations cross the existing :qa_editor Binder connection. */
@RunWith(AndroidJUnit4::class)
class LiveCandidatesInstrumentedTest : ImeTestBase() {
    @Test fun languageSwitchFailureReportsDisabledTarget() {
        driver.configureEnglishStartingLanguage()
        driver.launchComposingQa()
        val failure = runCatching { driver.switchToRussian() }.exceptionOrNull()
        assertTrue("Expected language switch failure", failure is IllegalStateException)
        val message = failure?.message.orEmpty()
        assertTrue(message, message.contains("enabled=[ENGLISH]"))
        assertTrue(message, message.contains("visible=[EN]"))
        assertTrue(message, message.contains("swipesSent=5"))
    }

    @Test fun englishIIsManualSuggestionAndSpaceKeepsOriginal() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa()
        driver.tapKey("Y", "y"); driver.tapKey("e"); driver.tapKey("s"); space(); driver.tapKey("i")
        driver.awaitFieldText(FIELD, "yes i")
        assertEquals("I", awaitCandidate(R.string.candidate_correction, "I").text)
        space(); driver.awaitFieldText(FIELD, "yes i ")
        driver.tapKey("i")
        driver.awaitFieldText(FIELD, "yes i i")
        awaitCandidate(R.string.candidate_correction, "I").click()
        driver.awaitFieldText(FIELD, "yes i I")
        noReadback()
    }

    @Test fun spanishIHasNoEnglishPronounSuggestion() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa(language =
            io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.SPANISH)
        driver.tapKey("I", "i")
        driver.awaitFieldText(FIELD, "i")
        assertTrue(!driver.device.wait(Until.hasObject(By.desc(description(R.string.candidate_correction, "I"))), 3_000))
        space(); driver.awaitFieldText(FIELD, "i ")
        noReadback()
    }

    @Test fun russianKuaOffersKudaManuallyInStandardStrip() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        KeyboardPreferences(context).writeManualCandidateExpansion(false)
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa(language = KeyboardLanguage.RUSSIAN)

        "куа".forEach { driver.tapKey(it.toString()) }
        driver.awaitFieldText(FIELD, "куа")
        assertEquals("куда", awaitCandidate(R.string.candidate_correction, "куда").text)
        space()
        driver.awaitFieldText(FIELD, "куа ")

        "куа".forEach { driver.tapKey(it.toString()) }
        driver.awaitFieldText(FIELD, "куа куа")
        awaitCandidate(R.string.candidate_correction, "куда").click()
        driver.awaitFieldText(FIELD, "куа куда")
        noReadback()
    }

    @Test fun englishIAfterInternalApostropheIsNotSuggested() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        KeyboardPreferences(instrumentation.targetContext).writeKeyFlicks(true)
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa()
        "baha".forEach { driver.tapKey(it.toString(), it.uppercase()) }
        val bounds = driver.characterKey("k", "K").visibleBounds
        assertTrue(driver.device.swipe(bounds.centerX(), bounds.centerY(), bounds.centerX(),
            bounds.centerY() + (bounds.height() * .8f).toInt(), 10))
        driver.awaitFieldText(FIELD, "baha'")
        driver.tapKey("i", "I")
        driver.awaitFieldText(FIELD, "baha'i")
        val correction = By.desc(description(R.string.candidate_correction, "I"))
        assertTrue(!driver.device.wait(Until.hasObject(correction), 3_000))
        space()
        driver.awaitFieldText(FIELD, "baha'i ")
        driver.tapKey("i", "I")
        driver.awaitFieldText(FIELD, "baha'i i")
        assertEquals("I", awaitCandidate(R.string.candidate_correction, "I").text)
        noReadback()
    }

    @Test fun shortRussianCorrectionPreviewAndUndoPreserveTheNextWord() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        assertTrue(context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, android.content.Context.MODE_PRIVATE)
            .edit().putBoolean(io.github.mesteriis.rune.keyboard.settings.SettingsCodec.KEY_VISIBLE_UNDO, true).commit())
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa(language =
            io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN)
        "зочу".forEach { driver.tapKey(it.toString()) }
        val preview = awaitCandidate(R.string.candidate_correction, "хочу")
        assertEquals(InstrumentationRegistry.getInstrumentation().targetContext
            .getString(R.string.candidate_auto_preview_label, "хочу"), preview.text)
        space()
        driver.awaitFieldText(FIELD, "хочу ")
        "до".forEach { driver.tapKey(it.toString()) }
        driver.awaitFieldText(FIELD, "хочу до")
        awaitCandidate(R.string.candidate_undo, "зочу").click()
        driver.awaitFieldText(FIELD, "зочу до")
        noReadback()
    }

    @Test fun immediateBackspaceUndoThenSpaceKeepsOriginalDuringFollowingWord() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa(language =
            io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN)
        "зочу".forEach { driver.tapKey(it.toString()) }
        awaitCandidate(R.string.candidate_correction, "хочу")
        space(); driver.awaitFieldText(FIELD, "хочу ")
        driver.tapDelete(); driver.awaitFieldText(FIELD, "зочу")
        space(); driver.awaitFieldText(FIELD, "зочу ")
        "домой".forEach { driver.tapKey(it.toString()) }
        driver.awaitFieldText(FIELD, "зочу домой")
        space(); driver.awaitFieldText(FIELD, "зочу домой ")
        noReadback()
    }

    @Test fun jointShortWordCorrectionPreviewAndUndoPreserveTheNextWord() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        assertTrue(context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, android.content.Context.MODE_PRIVATE)
            .edit().putBoolean(io.github.mesteriis.rune.keyboard.settings.SettingsCodec.KEY_VISIBLE_UNDO, true).commit())
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa(language =
            io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN)
        "ссын".forEach { driver.tapKey(it.toString()) }
        val preview = awaitCandidate(R.string.candidate_correction, "сын")
        assertEquals(InstrumentationRegistry.getInstrumentation().targetContext
            .getString(R.string.candidate_auto_preview_label, "сын"), preview.text)
        space()
        driver.awaitFieldText(FIELD, "сын ")
        "до".forEach { driver.tapKey(it.toString()) }
        driver.awaitFieldText(FIELD, "сын до")
        awaitCandidate(R.string.candidate_undo, "ссын").click()
        driver.awaitFieldText(FIELD, "ссын до")
        noReadback()
    }

    @Test fun reportedRussianMisspellingsCorrectOnSpaceWhileAmbiguousFragmentStaysUntouched() = withCiFailureMetadata(driver) {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa(language =
            io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN)

        fun type(word: String) {
            word.forEach { driver.tapKey(it.toString()) }
            space()
        }

        type("смотруть")
        driver.awaitFieldText(FIELD, "смотреть ")
        type("ощющениям")
        driver.awaitFieldText(FIELD, "смотреть ощущениям ")
        type("заберай")
        driver.awaitFieldText(FIELD, "смотреть ощущениям забирай ")
        type("пвременить")
        driver.awaitFieldText(FIELD, "смотреть ощущениям забирай повременить ")
        type("ерминатор")
        driver.awaitFieldText(FIELD, "смотреть ощущениям забирай повременить терминатор ")
        type("спаателей")
        driver.awaitFieldText(FIELD,
            "смотреть ощущениям забирай повременить терминатор спасателей ")
        type("ность")
        driver.awaitFieldText(FIELD,
            "смотреть ощущениям забирай повременить терминатор спасателей ность ")
        noReadback()
    }

    @Test fun canonicalCaseAutoReplacesOnBoundaryAndBackspaceRestoresOriginal() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa()
        driver.switchToRussian()
        driver.tapKey("Я", "я")
        space()
        for (key in listOf("м", "о", "с", "к", "в")) driver.tapKey(key)
        val deadline = SystemClock.uptimeMillis() + 120_000L
        var canonical: UiObject2? = null
        do {
            driver.tapKey("а")
            driver.awaitFieldText(FIELD, "я москва")
            canonical = driver.device.wait(Until.findObject(By.desc(
                description(R.string.candidate_correction, "Москва"))), 2_000L)
            if (canonical == null) {
                driver.tapDelete()
                driver.awaitFieldText(FIELD, "я москв")
            }
        } while (canonical == null && SystemClock.uptimeMillis() < deadline)
        assertTrue("Canonical case candidate unavailable", checkNotNull(canonical).isSelected)

        space()
        driver.awaitFieldText(FIELD, "я Москва ")
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "я москва")
        assertTrue(awaitCandidate(R.string.candidate_original, "москва").isSelected)
        val restored = stats()
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "я москв")
        awaitStats { it.getValue("compose") == restored.getValue("compose") + 1 }
        val deleted = stats()
        for (counter in listOf("commit", "region", "finish")) {
            assertEquals(restored.getValue(counter), deleted.getValue(counter))
        }
        assertEquals(restored.getValue("start"), deleted.getValue("start"))
        assertEquals(7, deleted.getValue("end"))
        assertEquals(7, deleted.getValue("selectionStart"))
        assertEquals(7, deleted.getValue("selectionEnd"))
        noReadback()
    }

    @Test fun russianAlpAbbreviationStaysLowercaseAtAllBoundaries() {
        assertRussianOriginalAtAllBoundaries("альп", "Альп")
    }

    @Test fun russianDomainLabelStaysExactAtAllBoundaries() {
        assertRussianOriginalAtAllBoundaries("яокб", "якоб")
    }

    private fun assertRussianOriginalAtAllBoundaries(original: String, suggestion: String) {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        for (boundary in listOf(" ", ".", ":")) {
            driver.launchComposingQa(language = KeyboardLanguage.RUSSIAN)
            for (character in original) driver.tapKey(character.toString(), character.uppercase())
            driver.awaitFieldText(FIELD, original)
            awaitCandidate(R.string.candidate_correction, suggestion)
            when (boundary) {
                " " -> space()
                ":" -> {
                    val context = InstrumentationRegistry.getInstrumentation().targetContext
                    driver.tapKeyByDescription(context.getString(R.string.key_symbols))
                    driver.tapKey(boundary)
                }
                else -> driver.tapKey(boundary)
            }
            driver.awaitFieldText(FIELD, "$original$boundary")
            driver.tapDelete()
            driver.awaitFieldText(FIELD, original)
            noReadback()
        }
    }

    @Test fun russianSentencePeriodCorrectsReadyWordAndBackspaceRestoresExactSource() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa(language =
            io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN)
        for (key in listOf("с", "м", "о", "т", "р", "у", "т", "ь")) driver.tapKey(key)

        val deadline = SystemClock.uptimeMillis() + 120_000L
        var correction: UiObject2? = null
        do {
            correction = driver.device.wait(Until.findObject(By.desc(
                description(R.string.candidate_correction, "смотреть"))), 2_000L)
            if (correction == null) {
                driver.tapDelete()
                driver.awaitFieldText(FIELD, "смотрут")
                driver.tapKey("ь")
                driver.awaitFieldText(FIELD, "смотруть")
            }
        } while (correction == null && SystemClock.uptimeMillis() < deadline)
        assertTrue("Russian correction unavailable", correction != null)

        driver.tapKey(".")
        driver.awaitFieldText(FIELD, "смотреть.")
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "смотруть")
        assertTrue(awaitCandidate(R.string.candidate_original, "смотруть").isSelected)
        noReadback()
    }

    @Test fun ambiguousInnStaysLowercaseBeforePeriod() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa(language =
            io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN)
        driver.tapKey("И", "и")
        driver.tapKey("н"); driver.tapKey("н")
        driver.awaitFieldText(FIELD, "инн")
        awaitCandidate(R.string.candidate_correction, "Инн")
        driver.tapKey(".")
        driver.awaitFieldText(FIELD, "инн.")
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "инн")
        noReadback()
    }

    @Test fun ambiguousInnTitleCaseRemainsManuallySelectable() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa(language =
            io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN)
        driver.tapKey("И", "и")
        driver.tapKey("н"); driver.tapKey("н")
        driver.awaitFieldText(FIELD, "инн")
        awaitCandidate(R.string.candidate_correction, "Инн").click()
        driver.awaitFieldText(FIELD, "Инн")
        noReadback()
    }

    @Test fun ambiguousInnStaysLowercaseBeforeColon() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa(language =
            io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN)
        driver.tapKey("И", "и")
        driver.tapKey("н"); driver.tapKey("н")
        driver.awaitFieldText(FIELD, "инн")
        awaitCandidate(R.string.candidate_correction, "Инн")
        driver.tapKeyByDescription(InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.key_symbols))
        driver.tapKey(":")
        driver.awaitFieldText(FIELD, "инн:")
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "инн")
        noReadback()
    }

    @Test fun russianColonCorrectsReadyWordAndBackspaceRestoresExactSource() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa(language =
            io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN)
        for (key in listOf("с", "м", "о", "т", "р", "у", "т", "ь")) driver.tapKey(key)
        driver.awaitFieldText(FIELD, "смотруть")
        awaitCandidate(R.string.candidate_correction, "смотреть")
        driver.tapKeyByDescription(InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.key_symbols))
        driver.tapKey(":")
        driver.awaitFieldText(FIELD, "смотреть:")
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "смотруть")
        noReadback()
    }

    @Test fun otherSymbolAfterLayerChangeKeepsOriginalWord() {
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false)
        driver.launchComposingQa(language =
            io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN)
        for (key in listOf("с", "м", "о", "т", "р", "у", "т", "ь")) driver.tapKey(key)
        driver.awaitFieldText(FIELD, "смотруть")
        awaitCandidate(R.string.candidate_correction, "смотреть")
        driver.tapKeyByDescription(InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.key_symbols))
        driver.tapKey("1")
        driver.awaitFieldText(FIELD, "смотруть1")
        noReadback()
    }

    @Test fun retainedSymbolsCandidateDoesNotCrossEditorBoundary() {
        for (mode in listOf("private", "no_suggestions")) {
            driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
                mechanical = false, doubleSpace = false)
            driver.launchComposingQa(language =
                io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN)
            for (key in listOf("с", "м", "о", "т", "р", "у", "т", "ь")) driver.tapKey(key)
            driver.awaitFieldText(FIELD, "смотруть")
            awaitCandidate(R.string.candidate_correction, "смотреть")
            driver.tapKeyByDescription(InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.key_symbols))
            driver.launchComposingQa(mode, io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN)
            assertTrue(!driver.device.hasObject(By.desc(description(R.string.candidate_correction, "смотреть"))))
            driver.tapKeyByDescription(InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.key_symbols))
            driver.tapKey(":")
            driver.awaitFieldText(FIELD, ":")
            noReadback()
        }
    }

    @Test fun correctionAndOriginalTapsReplaceOnlyOwnedWordWithNoReadback() {
        val correction = prepareCorrection()
        val before = stats()
        correction.click()
        driver.awaitFieldText(FIELD, "a hello")
        awaitStats { it.getValue("compose") == before.getValue("compose") + 1 }
        assertEquals(before.getValue("commit"), stats().getValue("commit"))
        val original = awaitCandidate(R.string.candidate_original, "helllo")
        val corrected = stats()
        original.click()
        driver.awaitFieldText(FIELD, "a helllo")
        awaitStats { it.getValue("compose") == corrected.getValue("compose") + 1 }
        assertTrue(awaitCandidate(R.string.candidate_original, "helllo").isSelected)
        assertEquals(corrected.getValue("commit"), stats().getValue("commit"))
        noReadback()
    }

    @Test fun boundaryKeepsTypedOriginalAndDropsPreviousSuggestions() {
        prepareCorrection()
        space()
        driver.awaitFieldText(FIELD, "a helllo ")
        driver.device.waitForIdle()
        assertTrue(!driver.device.hasObject(By.desc(description(R.string.candidate_correction, "hello"))))
        assertTrue(!driver.device.hasObject(By.desc(description(R.string.candidate_original, "helllo"))))
        noReadback()
    }

    @Test fun incognitoEditorTransitionClearsLoadedSuggestionsAndAllowsOwnedTyping() {
        prepareCorrection()
        driver.launchComposingQa("private")
        assertTrue(!driver.device.hasObject(By.desc(description(R.string.candidate_correction, "hello"))))
        assertTrue(!driver.device.hasObject(By.desc(description(R.string.candidate_original, "helllo"))))
        driver.tapKey("a")
        driver.awaitFieldText(FIELD, "a")
        assertEquals(1, stats().getValue("compose"))
        awaitCandidate(R.string.candidate_original, "a")
        assertTrue(!driver.device.hasObject(By.desc(description(R.string.candidate_correction, "hello"))))
        noReadback()
    }

    private fun prepareCorrection(): UiObject2 = driver.prepareLiveCorrection()

    private fun noReadback() {
        for (key in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot")) {
            assertEquals("Unexpected editor readback counter", 0, stats().getValue(key))
        }
    }

    private fun space() = driver.tapKeyByDescription(
        InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.key_space),
    )

    private fun description(resource: Int, word: String): String =
        InstrumentationRegistry.getInstrumentation().targetContext.getString(resource, word)

    private fun awaitCandidate(resource: Int, word: String): UiObject2 = checkNotNull(
        driver.device.wait(Until.findObject(By.desc(description(resource, word))), ImeTestDriver.WAIT_MILLIS),
    ) { "Expected current candidate unavailable" }

    private fun stats(): Map<String, Int> = checkNotNull(
        driver.device.findObject(By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats")),
    ).text.orEmpty().split(' ').associate { value ->
        val (key, number) = value.split('=')
        key to number.toInt()
    }

    private fun awaitStats(predicate: (Map<String, Int>) -> Boolean) {
        val deadline = SystemClock.uptimeMillis() + ImeTestDriver.WAIT_MILLIS
        while (!predicate(stats()) && SystemClock.uptimeMillis() < deadline) SystemClock.sleep(25)
        assertTrue("Editor command counters did not settle", predicate(stats()))
    }

    private companion object {
        const val FIELD = "qa_composing_text"
    }
}
