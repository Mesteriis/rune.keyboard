package io.github.mesteriis.rune.keyboard.qa

import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Public fixtures over the real :qa_editor Binder connection; no model or lexicon readiness. */
@RunWith(AndroidJUnit4::class)
class MechanicalPunctuationInstrumentedTest : ImeTestBase() {
    @Test fun commaPopupPunctuationCapsAndImmediateUndoNeverReplayOldWord() {
        prepare()
        word("hello"); space()
        driver.selectFirstAlternate(",") {
            // A failed popup would use performLongClick and commit early. Require release ownership.
            assertEquals("hello ", driver.fieldText(FIELD))
        }
        driver.awaitFieldText(FIELD, "hello?")
        val before = stats()
        driver.tapKey("w")
        driver.awaitFieldText(FIELD, "hello? W")
        awaitStats { it.getValue("compose") == before.getValue("compose") + 1 }
        assertEquals(before.getValue("compose") + 1, stats().getValue("compose"))
        assertEquals(before.getValue("commit"), stats().getValue("commit"))
        driver.tapDelete(); driver.awaitFieldText(FIELD, "hello?w")
        driver.tapDelete(); driver.awaitFieldText(FIELD, "hello?")
        noReadback()
    }

    @Test fun pairOfDotsWaitsForWhitespaceAndNewWordThenUndoesCapsTogether() {
        prepare()
        word("hello"); driver.tapKey("."); driver.tapKey(".")
        driver.awaitFieldText(FIELD, "hello..")
        space(); space(); driver.awaitFieldText(FIELD, "hello..  ")
        driver.tapKey("w")
        driver.awaitFieldText(FIELD, "hello. W")
        driver.tapDelete(); driver.awaitFieldText(FIELD, "hello..  w")
        driver.tapDelete(); driver.awaitFieldText(FIELD, "hello..  ")
        driver.tapKey("."); driver.awaitFieldText(FIELD, "hello..  .")
        noReadback()
    }

    @Test fun cachedMechanicalTogglePreservesHeldKeyInstancesAndNextInputUndo() {
        prepare(mechanical = false)
        word("hello"); space(); driver.tapKey(",")
        driver.awaitFieldText(FIELD, "hello ,")
        val key = driver.keyByText("w")
        val before = keyboardSnapshot()
        val touch = driver.touchDown(key)
        var released = false
        try {
            driver.configureMechanicalPunctuation(mechanical = true, doubleSpace = false)
            assertEquals("hello ,", driver.fieldText(FIELD))
            assertSameKeys(before, keyboardSnapshot())
            driver.releaseTouch(touch)
            released = true
        } finally {
            if (!released) driver.cancelTouch(touch)
        }
        driver.awaitFieldText(FIELD, "hello, w")
        // Drain ACTION_UP's deferred key render and posted caps refresh before comparing again.
        driver.device.waitForIdle()
        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
        assertSameKeys(before, keyboardSnapshot())
        driver.tapDelete(); driver.awaitFieldText(FIELD, "hello ,w")
        noReadback()
    }

    @Test fun decimalVersionAndHostnameKeepOwnedBoundariesWithoutLayerChanges() {
        // Set this before the tested sessions: switching to symbols mid-token would discard
        // Rune's context and could make a broken protected-token rule appear to pass.
        driver.setNumberRowThroughSettings(enabled = true)
        for (token in listOf("3.14", "1.2.3", "example.com")) {
            prepare()
            driver.assertKeyVisible("1")
            driver.assertKeyVisible("w")
            awaitStats { it.getValue("connections") > 0 }
            val connections = stats().getValue("connections")
            val keys = keyboardSnapshot()
            val typed = StringBuilder()
            for (character in token) {
                driver.tapKey(character.toString())
                typed.append(character)
                driver.awaitFieldText(FIELD, typed.toString())
            }

            // A real punctuation/letter boundary must still exclude a numeric or dotted left
            // token. The live comma span proves this is an owned composing path in a text field.
            driver.tapKey(",")
            driver.awaitFieldText(FIELD, "$token,")
            awaitStats { it.getValue("start") == token.length && it.getValue("end") == token.length + 1 }
            val beforeLetter = stats()
            driver.tapKey("w")
            driver.awaitFieldText(FIELD, "$token,w")
            awaitStats { it.getValue("compose") == beforeLetter.getValue("compose") + 1 }
            assertEquals(beforeLetter.getValue("commit"), stats().getValue("commit"))
            assertEquals(token.length, stats().getValue("start"))
            assertEquals(token.length + 2, stats().getValue("end"))
            driver.tapDelete(); driver.awaitFieldText(FIELD, "$token,")
            driver.tapDelete(); driver.awaitFieldText(FIELD, token)

            // Positive control in the same session: mechanical cleanup remains active and the
            // next ordinary word receives one space, with immediate Undo restoring raw input.
            space(); word("hello"); driver.tapKey(",")
            driver.awaitFieldText(FIELD, "$token hello,")
            driver.tapKey("w"); driver.awaitFieldText(FIELD, "$token hello, w")
            driver.tapDelete(); driver.awaitFieldText(FIELD, "$token hello,w")
            assertEquals(connections, stats().getValue("connections"))
            assertSameKeys(keys, keyboardSnapshot())
            noReadback()
        }
    }

    @Test fun commandDotKeepsItsSeparatorAcrossBoundaryAndOrdinaryBackspace() {
        prepare()
        word("find"); space(); driver.tapKey(".")
        driver.awaitFieldText(FIELD, "find .")
        space(); driver.tapKey("w")
        driver.awaitFieldText(FIELD, "find . w")
        driver.tapDelete(); driver.awaitFieldText(FIELD, "find . ")
        driver.tapDelete(); driver.awaitFieldText(FIELD, "find .")
        noReadback()
    }

    @Test fun russianEraAbbreviationKeepsLowercaseInSentenceCapsEditor() {
        driver.configureMechanicalPunctuation(mechanical = true, doubleSpace = false)
        driver.setNumberRowThroughSettings(enabled = true)
        driver.launchComposingQa(mode = "sentence_caps", language = KeyboardLanguage.RUSSIAN)
        word("До"); space(); word("н"); driver.tapKey("."); space()
        driver.awaitFieldText(FIELD, "До н. ")
        driver.tapKey("э"); driver.tapKey(".")
        driver.awaitFieldText(FIELD, "До н. э.")
        driver.tapDelete(); driver.awaitFieldText(FIELD, "До н. э")
        noReadback()

        driver.launchComposingQa(mode = "sentence_caps", language = KeyboardLanguage.RUSSIAN)
        word("В"); space(); word("536"); space(); word("году"); space(); word("н"); driver.tapKey("."); space()
        driver.awaitFieldText(FIELD, "В 536 году н. ")
        driver.tapKey("э"); driver.tapKey(".")
        driver.awaitFieldText(FIELD, "В 536 году н. э.")
        driver.tapDelete(); driver.awaitFieldText(FIELD, "В 536 году н. э")
        noReadback()

        driver.launchComposingQa(mode = "sentence_caps", language = KeyboardLanguage.RUSSIAN)
        word("Это"); space(); word("я"); driver.tapKey("."); space()
        driver.tapKey("Э")
        driver.awaitFieldText(FIELD, "Это я. Э")
        noReadback()
    }

    @Test fun russianPeriodContinuationCapitalizesNextSentence() {
        driver.configureMechanicalPunctuation(mechanical = true, doubleSpace = false)
        driver.launchComposingQa(mode = "sentence_caps", language = KeyboardLanguage.RUSSIAN)
        word("Сейчас"); space(); word("проверю"); driver.tapKey(".")
        driver.awaitFieldText(FIELD, "Сейчас проверю.")
        space()
        word("Потом")
        driver.awaitFieldText(FIELD, "Сейчас проверю. Потом")
        repeat(5) { driver.tapDelete() }
        driver.awaitFieldText(FIELD, "Сейчас проверю. ")
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "Сейчас проверю.")
        noReadback()
    }

    @Test fun russianColonContinuationAddsSpaceWithoutCapitalization() {
        driver.configureMechanicalPunctuation(mechanical = true, doubleSpace = false)
        typeRussianColonAndReturnToLetters()
        driver.tapKey("д")
        driver.awaitFieldText(FIELD, "Сначала уточню: д")
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "Сначала уточню:д")
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "Сначала уточню:")
        noReadback()

        driver.configureMechanicalPunctuation(mechanical = false, doubleSpace = false)
        typeRussianColonAndReturnToLetters()
        driver.tapKey("д")
        driver.awaitFieldText(FIELD, "Сначала уточню:д")
        driver.tapDelete()
        driver.awaitFieldText(FIELD, "Сначала уточню:")
        noReadback()
    }

    private fun typeRussianColonAndReturnToLetters() {
        driver.launchComposingQa(mode = "sentence_caps", language = KeyboardLanguage.RUSSIAN)
        word("Сначала"); space(); word("уточню")
        val resources = InstrumentationRegistry.getInstrumentation().targetContext
        driver.tapKeyByDescription(resources.getString(R.string.key_symbols))
        driver.tapKey(":")
        driver.awaitFieldText(FIELD, "Сначала уточню:")
        driver.tapKeyByDescription(resources.getString(R.string.key_letters))
    }

    private fun prepare(mechanical: Boolean = true) {
        driver.configureMechanicalPunctuation(mechanical, doubleSpace = false)
        driver.launchComposingQa()
    }

    private fun word(value: String) { value.forEach { driver.tapKey(it.toString()) } }
    private fun space() = driver.tapKeyByDescription(
        InstrumentationRegistry.getInstrumentation().targetContext.getString(R.string.key_space))
    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(
        By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats"))).text.orEmpty().split(' ').associate {
        val (key, value) = it.split('='); key to value.toInt()
    }
    private fun awaitStats(predicate: (Map<String, Int>) -> Boolean) {
        val deadline = SystemClock.uptimeMillis() + ImeTestDriver.WAIT_MILLIS
        while (!predicate(stats()) && SystemClock.uptimeMillis() < deadline) SystemClock.sleep(25)
        assertTrue("Editor command counters did not settle", predicate(stats()))
    }
    private fun noReadback() {
        for (key in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot")) {
            assertEquals("Unexpected editor readback counter", 0, stats().getValue(key))
        }
    }
    private companion object { const val FIELD = "qa_composing_text" }
}
