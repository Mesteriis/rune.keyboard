package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.content.ContextWrapper
import android.inputmethodservice.InputMethodService
import android.os.SystemClock
import android.view.inputmethod.InputConnection
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import io.github.mesteriis.rune.keyboard.ime.editor.EditorCommandExecutor
import io.github.mesteriis.rune.keyboard.ime.model.EditorCommand
import java.util.concurrent.Callable
import java.util.concurrent.FutureTask
import java.util.concurrent.TimeUnit
import org.junit.Assert.*
import org.junit.Test

/** Editor protocol over the real IME -> :qa_editor Binder connection; no quality-gate override. */
class OwnedBatchInstrumentedTest : ImeTestBase() {
    @Test fun commitBoundaryAndRestoreOwnedRegionPreserveTextAndDoNotReadEditor() {
        driver.launchComposingQa()
        val keyboard = keyboardSnapshot()
        val connection = onMain {
            var context: Context = keyboard.keyboard.context
            while (context !is InputMethodService && context is ContextWrapper) context = context.baseContext
            checkNotNull((context as? InputMethodService)?.currentInputConnection)
        }
        run(connection, EditorCommand.SetComposingText("helllo"))
        driver.awaitFieldText(FIELD, "helllo")
        awaitSpan(0, 6)
        val before = stats()
        run(connection, EditorCommand.Batch(listOf(EditorCommand.CommitText("hello "),
            EditorCommand.SetComposingRegion(5, 6))) { true })
        driver.awaitFieldText(FIELD, "hello ")
        awaitSpan(5, 6)
        assertEquals(before.getValue("commit") + 1, stats().getValue("commit"))
        assertEquals(before.getValue("region") + 1, stats().getValue("region"))
        run(connection, EditorCommand.Batch(listOf(EditorCommand.SetComposingRegion(0, 6),
            EditorCommand.SetComposingText("helllo"))) { true })
        driver.awaitFieldText(FIELD, "helllo")
        awaitSpan(0, 6)
        assertEquals(before.getValue("region") + 2, stats().getValue("region"))
        assertEquals(before.getValue("compose") + 1, stats().getValue("compose"))
        for (counter in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot")) {
            assertEquals("Unexpected readback: $counter", 0, stats().getValue(counter))
        }
        assertSameKeys(keyboard, keyboardSnapshot())
    }

    private fun run(connection: InputConnection, command: EditorCommand) = onMain {
        assertTrue(EditorCommandExecutor.execute(command, connection, false, false).handled)
    }

    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(
        By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats"))).text.orEmpty().split(' ').associate {
        val (key, value) = it.split('='); key to value.toInt()
    }

    private fun awaitSpan(start: Int, end: Int) {
        val deadline = SystemClock.uptimeMillis() + ImeTestDriver.WAIT_MILLIS
        do {
            val current = stats()
            if (current["start"] == start && current["end"] == end) return
            SystemClock.sleep(25)
        } while (SystemClock.uptimeMillis() < deadline)
        throw AssertionError("Expected composing region did not arrive")
    }

    private fun <T> onMain(action: () -> T): T {
        val task = FutureTask(Callable(action))
        InstrumentationRegistry.getInstrumentation().runOnMainSync(task)
        return task.get(5, TimeUnit.SECONDS)
    }

    private companion object { const val FIELD = "qa_composing_text" }
}
