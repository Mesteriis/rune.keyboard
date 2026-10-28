package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.content.ContextWrapper
import android.inputmethodservice.InputMethodService
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.editor.EditorCallbackTrace
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Callable
import java.util.concurrent.FutureTask
import java.util.concurrent.TimeUnit
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TestName

/** Real IME/Binder callback receipt; fixed public input and bounded flag-only RAM trace. */
class EditorCallbackProfilesInstrumentedTest {
    private val driver = ImeTestDriver()
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private var prepared = false
    private var tracing = false
    private var stores = emptyMap<String, Map<String, String>>()
    private var storesCaptured = false
    @get:Rule val name = TestName()

    @Before fun prepare() {
        val physical = Build.HARDWARE !in setOf("ranchu", "goldfish")
        if (physical) check(Build.MODEL.startsWith("SM-F") &&
            InstrumentationRegistry.getArguments().getString("allowPhysicalDevice") == "true" &&
            InstrumentationRegistry.getArguments().getString("runeFailureArtifacts") == "false")
        prepared = true
        driver.setUp(privateQa = true)
        val edit = context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE).edit()
        for (key in listOf(SettingsCodec.KEY_PERSONAL_LEARNING, SettingsCodec.KEY_TOUCH_PERSONALIZATION,
            SettingsCodec.KEY_COLLECT_EXAMPLES, SettingsCodec.KEY_TYPO_PATTERNS, SettingsCodec.KEY_DYNAMIC_TOUCH,
            SettingsCodec.KEY_DYNAMIC_TOUCH_APPLY, SettingsCodec.KEY_QUALITY_METRICS,
            SettingsCodec.KEY_SHADOW_COMPARISON, SettingsCodec.KEY_APP_PROFILES)) edit.putBoolean(key, false)
        check(edit.commit())
        driver.prepareLiveCorrection(mode = "private")
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
        flushDiagnostics()
        stores = personalStoreSnapshot(context)
        storesCaptured = true
    }

    @After fun restore() {
        try {
            if (tracing) {
                val captured = onMain { EditorCallbackTrace.end() }; tracing = false
                instrumentation.sendStatus(2, Bundle().apply {
                    putString("callback_case", name.methodName)
                    putInt("callback_total", captured.total); putInt("callback_dropped", captured.dropped)
                    putString("callback_flags", captured.events.joinToString(","))
                })
            }
            flushDiagnostics()
            if (storesCaptured) assertEquals("Synthetic QA must preserve personal stores", stores, personalStoreSnapshot(context))
        } finally { if (prepared) driver.tearDown() }
    }

    private fun begin() { assertTrue(onMain { EditorCallbackTrace.begin() }); tracing = true }
    private fun type(value: String) = value.forEach {
        assertEquals(context.packageName, driver.device.currentPackageName)
        driver.tapKey(it.toString())
    }
    private fun flushDiagnostics() {
        val recorder = io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.TypingDiagnosticsProvider
            .create(context) as io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticsRecorder
        val done = CountDownLatch(1)
        var success = false
        recorder.barrier { success = it; done.countDown() }
        assertTrue("Diagnostics queue fence timed out", done.await(5, TimeUnit.SECONDS))
        assertTrue("Diagnostics queue fence failed", success)
    }
    private fun space() {
        assertEquals(context.packageName, driver.device.currentPackageName)
        driver.tapKeyByDescription(context.getString(R.string.key_space))
    }
    private fun stats(web: Boolean = false): Map<String, Int> = checkNotNull(driver.device.findObject(
        By.res(context.packageName, if (web) "qa_webview_stats" else "qa_composing_stats")))
        .text.orEmpty().split(' ').associate { val (key, value) = it.split('='); key to value.toInt() }
    private fun noReads(web: Boolean = false) {
        for (key in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Unexpected payload read: $key", 0, stats(web).getValue(key))
    }
    private fun await(condition: () -> Boolean) {
        val deadline = SystemClock.uptimeMillis() + 5000
        while (!condition()) { if (SystemClock.uptimeMillis() >= deadline) fail("Bounded QA condition timed out"); SystemClock.sleep(25) }
    }
    private fun trace() = onMain { EditorCallbackTrace.snapshot() }
    private fun <T> onMain(action: () -> T): T {
        val task = FutureTask(Callable(action)); instrumentation.runOnMainSync(task)
        return task.get(5, TimeUnit.SECONDS)
    }

    @Test fun noOpRegionCallbackCalibrationPreservesCorrectionAndUndo() {
        driver.launchComposingQa(mode = "callback_trace"); begin(); type("teh")
        driver.awaitFieldText("qa_composing_text", "teh")
        val before = stats(); val callbacks = trace().total
        val keyboard = keyboardSnapshot()
        onMain {
            var owner: Context = keyboard.keyboard.rootView.context
            while (owner !is InputMethodService && owner is ContextWrapper) owner = owner.baseContext
            val service = checkNotNull(owner as? InputMethodService)
            assertEquals(context.packageName, service.currentInputEditorInfo?.packageName)
            assertEquals(R.id.qa_composing_text, service.currentInputEditorInfo?.fieldId)
            val connection = checkNotNull(service.currentInputConnection)
            assertTrue(connection.setComposingRegion(before.getValue("start"), before.getValue("end")))
        }
        await { stats().getValue("region") > before.getValue("region") }
        SystemClock.sleep(150)
        instrumentation.sendStatus(2, Bundle().apply { putInt("noop_callbacks_observed", trace().total - callbacks) })
        space(); driver.awaitFieldText("qa_composing_text", "the ")
        driver.tapDelete(); driver.awaitFieldText("qa_composing_text", "teh")
        assertFalse(trace().events.any { it and EditorCallbackTrace.SESSION_DISABLED_EXTERNALLY != 0 })
        noReads()
    }

    @Test fun splitSelectionThenCompositionPreservesEveryTypedLetter() {
        driver.launchComposingQa(mode = "selection_then_composition"); begin()
        type("t"); driver.awaitFieldText("qa_composing_text", "t")
        await { stats().getValue("twoPhaseReleased") == 1 }
        SystemClock.sleep(150)
        val disabled = trace().events.any { it and EditorCallbackTrace.SESSION_DISABLED_EXTERNALLY != 0 }
        type("eh"); space()
        driver.awaitFieldText("qa_composing_text", if (disabled) "teh " else "the ")
        assertEquals(1, stats().getValue("twoPhaseRequested"))
        instrumentation.sendStatus(2, Bundle().apply { putBoolean("split_disabled", disabled) })
        noReads()
    }

    @Test fun shiftedPrefixCallbackPreservesWordAndFollowingLiteralInput() {
        driver.launchComposingQa(mode = "callback_trace"); begin(); type("hello")
        driver.awaitFieldText("qa_composing_text", "hello")
        val before = stats(); driver.tapQaControl("qa_composing_prefix")
        driver.awaitFieldText("qa_composing_text", "X hello")
        await { stats().getValue("finish") > before.getValue("finish") }
        assertEquals(before.getValue("connections"), stats().getValue("connections"))
        type("x"); driver.awaitFieldText("qa_composing_text", "X hellox")
        assertTrue(trace().events.any { it and EditorCallbackTrace.SESSION_DISABLED_EXTERNALLY != 0 })
        noReads()
    }

    @Test fun offlineWebViewRecordsAvailabilityAcrossFiveWordsWithoutLosingInput() {
        driver.launchWebViewQa(privateInput = true); begin()
        repeat(5) { type("teh"); space() }
        await { stats(true).getValue("length") >= 20 }
        val value = checkNotNull(driver.device.findObject(By.pkg(context.packageName).clazz("android.widget.EditText"))).text.orEmpty()
        val words = value.trim().split(' ')
        assertEquals(5, words.size)
        assertTrue(words.all { it in setOf("teh", "the") })
        instrumentation.sendStatus(2, Bundle().apply {
            putInt("web_words", words.size); putInt("web_corrections", words.count { it == "the" })
            putBoolean("web_last_corrected", words.last() == "the")
        })
        assertTrue(trace().total > 0)
        noReads(true)
    }
}
