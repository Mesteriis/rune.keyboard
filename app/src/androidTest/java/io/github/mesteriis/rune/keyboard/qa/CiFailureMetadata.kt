package io.github.mesteriis.rune.keyboard.qa

import android.util.Log
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticStream
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticsRecorder
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.TypingDiagnosticsProvider
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

/** Only a disposable, explicitly opted-in CI emulator may own synthetic diagnostics. */
internal fun withCiFailureMetadata(driver: ImeTestDriver, action: () -> Unit) {
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
