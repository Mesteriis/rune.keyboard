package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.os.SystemClock
import android.util.Log
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticStream
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticsRecorder
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.TypingDiagnosticsProvider
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import org.junit.Assert.*
import org.junit.Test

/** Fixed public words; the real IME, packed ranker, worker and remote editor own this flow. */
class NeighborRecoveryLiveInstrumentedTest : ImeTestBase() {
    @Test fun twoNeighborErrorsCorrectAndUndoKeepsTheNextWord() = withCiFailureMetadata {
        exercise("палецшего", true)
    }
    @Test fun threeNeighborErrorsCorrectWithHiddenStripAndBackspaceRestoresSource() = exercise("машефшегш", false)

    /** Only a disposable, explicitly opted-in CI emulator may own synthetic diagnostics. */
    private fun withCiFailureMetadata(action: () -> Unit) {
        val args = InstrumentationRegistry.getArguments()
        if (args.getString("runeCiFailureCapture") != "true" ||
            driver.shell("getprop ro.kernel.qemu") != "1" ||
            driver.shell("getprop ro.hardware") !in setOf("ranchu", "goldfish")) return action()
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val recorder = TypingDiagnosticsProvider.create(context) as DiagnosticsRecorder
        fun operation(start: ((Boolean) -> Unit) -> Unit) {
            val done = CountDownLatch(1)
            val success = AtomicBoolean(false)
            start { success.set(it); done.countDown() }
            check(done.await(10, TimeUnit.SECONDS) && success.get()) { "Diagnostic fixture operation failed" }
        }
        operation(recorder::barrier)
        val managed = File(context.noBackupFilesDir, "typing-diagnostics")
        val existing = if (managed.exists()) managed.listFiles() ?: return action() else emptyArray()
        if (recorder.preferences.metadata || recorder.preferences.text ||
            existing.any { it.length() > 0 }) return action()
        try {
            operation { done -> recorder.setMetadata(true, done) }
        } catch (error: Throwable) {
            try { operation(recorder::delete) } catch (cleanupError: Throwable) { error.addSuppressed(cleanupError) }
            throw error
        }
        var failure: Throwable? = null
        try {
            action()
        } catch (error: Throwable) {
            failure = error
            try {
                val bytes = ByteArrayOutputStream()
                operation { done -> recorder.export(recorder.newExport(), DiagnosticStream.METADATA, { bytes }, done) }
                bytes.toString(Charsets.UTF_8.name()).lineSequence().filter { it.isNotBlank() }
                    .forEach { Log.i("RuneRecoveryFailure", it) }
            } catch (captureError: Throwable) {
                error.addSuppressed(captureError)
            }
            throw error
        } finally {
            try {
                operation(recorder::delete)
            } catch (cleanupError: Throwable) {
                if (failure != null) failure.addSuppressed(cleanupError) else throw cleanupError
            }
        }
    }

    private fun exercise(typed: String, strip: Boolean) {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        assertTrue(context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE).edit()
            .putBoolean(SettingsCodec.KEY_VISIBLE_UNDO, true)
            .putBoolean(SettingsCodec.KEY_PERSONAL_LEARNING, false)
            .putBoolean(SettingsCodec.KEY_TOUCH_PERSONALIZATION, false)
            .putBoolean(SettingsCodec.KEY_COLLECT_EXAMPLES, false).commit())
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, strip,
            mechanical = false, doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
        driver.launchComposingQa(language = KeyboardLanguage.RUSSIAN)
        fun space() = driver.tapKeyByDescription(context.getString(R.string.key_space))
        for (character in "он не дает ни $typed") {
            if (character == ' ') space() else driver.tapKey(character.toString())
        }
        // A ready correction is measured separately from the 15 ms rapid-touch delivery fixture.
        SystemClock.sleep(350)
        space()
        driver.awaitFieldText("qa_composing_text", "он не дает ни малейшего ")
        if (strip) {
            "след".forEach { driver.tapKey(it.toString()) }
            driver.tapDelete()
            driver.awaitFieldText("qa_composing_text", "он не дает ни малейшего сле")
            val undo = driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_undo, typed))), 5000)
            assertNotNull(undo); undo!!.click()
            driver.awaitFieldText("qa_composing_text", "он не дает ни $typed сле")
        } else {
            driver.tapDelete()
            driver.awaitFieldText("qa_composing_text", "он не дает ни $typed")
        }
        val stats = driver.device.findObject(By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats"))
            .text.split(' ').associate { val (key, value) = it.split('='); key to value.toInt() }
        for (name in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Unexpected editor readback", 0, stats.getValue(name))
        assertEquals(stats.getValue("selectionStart"), stats.getValue("selectionEnd"))
    }
}
