package io.github.mesteriis.rune.keyboard.qa

import android.os.Build
import android.os.SystemClock
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiObject2
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingResources
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test

/** Full real-IME synthetic flow, never run against an owner's phone. */
class CaseRejectionImeInstrumentedTest {
    @Test fun learnedCaseRejectionSurvivesSymbolsAndColon() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        assumeTrue(Build.HARDWARE in setOf("ranchu", "goldfish") &&
            InstrumentationRegistry.getArguments().getString("runeSyntheticProfileFixture") == "true")
        val context = instrumentation.targetContext
        val driver = ImeTestDriver()
        val store = PersonalTypingResources.get(context).personal
        var setup = false
        var original: io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingSnapshot? = null
        fun await(condition: () -> Boolean) {
            val deadline = SystemClock.uptimeMillis() + 15_000
            while (!condition()) { check(SystemClock.uptimeMillis() < deadline) { "Personal fixture timeout" }; SystemClock.sleep(25) }
        }
        try {
            driver.setUp(); setup = true
            await { store.isReady }
            original = store.model.snapshot()
            check(store.update { it.reset(); it.recordRejected("москва", "Москва", KeyboardLanguage.RUSSIAN) })
            await { store.lastWriteSucceeded == true && store.model.rejects("москва", "Москва", KeyboardLanguage.RUSSIAN) }
            driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true, mechanical = false, doubleSpace = false)
            KeyboardPreferences(context).writePersonalLearning(true)
            instrumentation.waitForIdleSync()
            driver.launchComposingQa(language = KeyboardLanguage.RUSSIAN)
            driver.tapKey("Я", "я")
            driver.tapKeyByDescription(context.getString(R.string.key_space))
            "москва".forEach { driver.tapKey(it.toString()) }
            driver.awaitFieldText("qa_composing_text", "я москва")
            val candidate = checkNotNull(driver.device.wait(Until.findObject(By.desc(
                context.getString(R.string.candidate_correction, "Москва"))), 10_000))
            assertFalse(candidate.isSelected)
            driver.tapKeyByDescription(context.getString(R.string.key_symbols))
            driver.tapKey(":")
            driver.awaitFieldText("qa_composing_text", "я москва:")
        } finally {
            original?.let { snapshot ->
                check(store.update { it.restore(snapshot) })
                await { store.lastWriteSucceeded == true }
            }
            if (setup) driver.tearDown()
        }
    }

    @Test fun undoLearnsAndLaterManualCaseChoiceStillWorks() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        assumeTrue(Build.HARDWARE in setOf("ranchu", "goldfish") &&
            InstrumentationRegistry.getArguments().getString("runeSyntheticProfileFixture") == "true")
        val context = instrumentation.targetContext
        val driver = ImeTestDriver()
        val store = PersonalTypingResources.get(context).personal
        var setup = false
        var original: io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingSnapshot? = null
        fun await(condition: () -> Boolean) {
            val deadline = SystemClock.uptimeMillis() + 15_000
            while (!condition()) { check(SystemClock.uptimeMillis() < deadline) { "Personal fixture timeout" }; SystemClock.sleep(25) }
        }
        fun space() = driver.tapKeyByDescription(context.getString(R.string.key_space))
        fun waitCandidate(canonical: String): UiObject2 {
            val description = context.getString(R.string.candidate_correction, canonical)
            return checkNotNull(driver.device.wait(Until.findObject(By.desc(description)), 10_000)) {
                "Canonical candidate unavailable"
            }
        }
        try {
            driver.setUp(); setup = true
            await { store.isReady }
            original = store.model.snapshot()
            driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true, mechanical = false, doubleSpace = false)
            KeyboardPreferences(context).writePersonalLearning(true)
            instrumentation.waitForIdleSync()
            for ((word, title) in listOf("москва" to "Москва", "клавы" to "Клавы",
                "читы" to "Читы", "моника" to "Моника")) {
                check(store.update { it.reset() })
                await { store.lastWriteSucceeded == true }
                driver.launchComposingQa(language = KeyboardLanguage.RUSSIAN)
                driver.tapKey("Я", "я"); space()
                word.dropLast(1).forEach { driver.tapKey(it.toString()) }
                val deadline = SystemClock.uptimeMillis() + 120_000
                var candidate: UiObject2? = null
                do {
                    driver.tapKey(word.last().toString())
                    driver.awaitFieldText("qa_composing_text", "я $word")
                    candidate = driver.device.wait(Until.findObject(By.desc(
                        context.getString(R.string.candidate_correction, title))), 2_000)
                    if (candidate == null) {
                        driver.tapDelete(); driver.awaitFieldText("qa_composing_text", "я ${word.dropLast(1)}")
                    }
                } while (candidate == null && SystemClock.uptimeMillis() < deadline)
                assertTrue("Initial canonical correction was not selected", checkNotNull(candidate).isSelected)
                space(); driver.awaitFieldText("qa_composing_text", "я $title ")
                driver.tapDelete(); driver.awaitFieldText("qa_composing_text", "я $word")
                await { store.model.rejects(word, title, KeyboardLanguage.RUSSIAN) && store.lastWriteSucceeded == true }
                space(); driver.awaitFieldText("qa_composing_text", "я $word ")
                word.forEach { driver.tapKey(it.toString()) }
                driver.awaitFieldText("qa_composing_text", "я $word $word")
                assertFalse("Rejected capitalization was still selected automatically", waitCandidate(title).isSelected)
                space(); driver.awaitFieldText("qa_composing_text", "я $word $word ")
                word.forEach { driver.tapKey(it.toString()) }
                driver.awaitFieldText("qa_composing_text", "я $word $word $word")
                waitCandidate(title).click()
                driver.awaitFieldText("qa_composing_text", "я $word $word $title")
            }
        } finally {
            original?.let { snapshot ->
                check(store.update { it.restore(snapshot) })
                await { store.lastWriteSucceeded == true }
            }
            if (setup) driver.tearDown()
        }
    }
}
