package io.github.mesteriis.rune.keyboard.qa

import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences
import io.github.mesteriis.rune.keyboard.smarttyping.controls.TypingControlStore
import io.github.mesteriis.rune.keyboard.smarttyping.controls.TypingProfile
import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

class TypingProfilesImeInstrumentedTest : ImeTestBase() {
    @Test fun assignedConversationProfileAppliesInRealEditorAndDisableAllRestoresMainSettings() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        val prefs = KeyboardPreferences(context)
        val store = TypingControlStore.get(context)
        prefs.disableAdditionalTyping()
        driver.configureSmartTyping(AutocorrectionMode.OFF, true, mechanical = true, doubleSpace = true,
            contextual = ContextualPunctuationMode.OFF)
        awaitResult { store.reset(it) }
        store.observePackage(context.packageName)
        awaitResult { store.assign(context.packageName, TypingProfile.CONVERSATION, it) }
        prefs.writeAppProfiles(true)
        prefs.notifyTypingControlsChanged()
        instrumentation.waitForIdleSync()
        fun typeExample() {
            driver.launchComposingQa()
            for (key in listOf("h", "e", "l", "l", "o")) driver.tapKey(key)
            driver.tapKeyByDescription(context.getString(R.string.key_space))
            driver.tapKey(","); driver.tapKey("w")
        }
        fun typeDoubleSpaceExample() {
            driver.launchComposingQa()
            for (key in listOf("h", "e", "l", "l", "o")) driver.tapKey(key)
            driver.doubleTap(checkNotNull(driver.device.findObject(By.desc(context.getString(R.string.key_space)))))
        }
        try {
            typeExample()
            driver.awaitFieldText("qa_composing_text", "hello ,w")
            assertTrue(prefs.readSettings().mechanicalPunctuation)
            assertTrue(prefs.readSettings().doubleSpacePeriod)
            typeDoubleSpaceExample()
            driver.awaitFieldText("qa_composing_text", "hello  ")
            prefs.disableAdditionalTyping()
            instrumentation.waitForIdleSync()
            typeExample()
            driver.awaitFieldText("qa_composing_text", "hello, w")
            typeDoubleSpaceExample()
            driver.awaitFieldText("qa_composing_text", "hello. ")
            assertTrue(prefs.readSettings().doubleSpacePeriod)
            assertEquals(TypingProfile.CONVERSATION, store.snapshot.profile(context.packageName))
        } finally { awaitResult { store.reset(it) } }
    }
    private fun awaitResult(start: ((TypingControlStore.Result) -> Unit) -> Unit) {
        val done = CountDownLatch(1); var result: TypingControlStore.Result? = null
        start { result = it; done.countDown() }
        assertTrue(done.await(10, TimeUnit.SECONDS)); assertEquals(TypingControlStore.Result.SAVED, result)
    }
}
