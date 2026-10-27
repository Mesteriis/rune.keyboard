package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.content.ContextWrapper
import android.os.SystemClock
import android.view.KeyCharacterMap
import android.view.KeyEvent
import android.view.inputmethod.InputConnection
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.ime.RuneInputMethodService
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/** Prototype only: actual Binder connection to :qa_editor, no product editing API yet. */
class EditingSelectionPrototypeInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private val driver = ImeTestDriver()
    private var prepared = false

    @Before fun prepareDisposableEditor() {
        // Guard before ImeTestDriver can change any device setting or capture a screen.
        check(android.os.Build.HARDWARE in setOf("ranchu", "goldfish")) { "Disposable emulator required" }
        prepared = true
        driver.setUp()
        driver.configureMechanicalPunctuation(mechanical = false, doubleSpace = false)
        driver.launchComposingQa()
    }

    @After fun restoreFixture() {
        if (prepared) driver.tearDown()
    }

    @Test fun shiftMetaAloneMovesWithoutExtendingInTextView() {
        seed("abcd", 4)
        val connection = connection()
        arrow(connection, KeyEvent.KEYCODE_DPAD_LEFT, KeyEvent.META_SHIFT_ON)
        arrow(connection, KeyEvent.KEYCODE_DPAD_LEFT, KeyEvent.META_SHIFT_ON)
        // Regression control: Android TextView ignores this arrow-only selection protocol.
        awaitSelection(2, 2)
        arrow(connection, KeyEvent.KEYCODE_DPAD_RIGHT, 0)
        awaitSelection(3, 3)
        assertNoPayloadReads("meta-only-negative-control", 3)
    }

    @Test fun explicitShiftKeyPairSelectsWithZeroArrowMetaAndReleases() {
        seed("abcd", 4)
        val connection = connection()
        key(connection, KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_SHIFT_LEFT, 0)
        try {
            arrow(connection, KeyEvent.KEYCODE_DPAD_LEFT, 0)
            arrow(connection, KeyEvent.KEYCODE_DPAD_LEFT, 0)
            awaitSelection(4, 2)
        } finally {
            key(connection, KeyEvent.ACTION_UP, KeyEvent.KEYCODE_SHIFT_LEFT, 0)
        }
        arrow(connection, KeyEvent.KEYCODE_DPAD_RIGHT, 0)
        awaitSelection(4, 4)
        assertNoPayloadReads("explicit-shift-zero-meta")
    }

    @Test fun explicitShiftAndArrowMetaRespectEmojiBoundaryAndRelease() {
        seed("a😀b", 4)
        val connection = connection()
        key(connection, KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_SHIFT_LEFT, KeyEvent.META_SHIFT_ON)
        try {
            arrow(connection, KeyEvent.KEYCODE_DPAD_LEFT, KeyEvent.META_SHIFT_ON)
            awaitSelection(4, 3)
            arrow(connection, KeyEvent.KEYCODE_DPAD_LEFT, KeyEvent.META_SHIFT_ON)
            awaitSelection(4, 1)
        } finally {
            key(connection, KeyEvent.ACTION_UP, KeyEvent.KEYCODE_SHIFT_LEFT, 0)
        }
        arrow(connection, KeyEvent.KEYCODE_DPAD_RIGHT, 0)
        awaitSelection(4, 4)
        assertNoPayloadReads("explicit-shift-with-meta-emoji")
    }

    private fun seed(value: String, caret: Int) {
        // Seed fixed public text through the same Binder connection. Accessibility SET_TEXT
        // invalidates the framework connection and can itself request an editor snapshot.
        val connection = connection()
        instrumentation.runOnMainSync { assertTrue(connection.commitText(value, 1)) }
        awaitSelection(caret, caret)
        assertEquals(caret, stats().getValue("length"))
        assertPayloadReadsZero("before-editing-commands")
    }

    private fun connection(): InputConnection {
        var result: InputConnection? = null
        val keyboard = keyboardSnapshot().keyboard
        instrumentation.runOnMainSync {
            var owner: Context = keyboard.rootView.context
            while (owner is ContextWrapper && owner !is RuneInputMethodService) owner = owner.baseContext
            val service = checkNotNull(owner as? RuneInputMethodService)
            assertEquals(context.packageName, service.currentInputEditorInfo.packageName)
            result = service.currentInputConnection
        }
        return checkNotNull(result)
    }

    private fun arrow(connection: InputConnection, code: Int, meta: Int) {
        key(connection, KeyEvent.ACTION_DOWN, code, meta)
        key(connection, KeyEvent.ACTION_UP, code, meta)
    }

    private fun key(connection: InputConnection, action: Int, code: Int, meta: Int) {
        instrumentation.runOnMainSync {
            val time = SystemClock.uptimeMillis()
            assertTrue(connection.sendKeyEvent(KeyEvent(time, time, action, code, 0, meta,
                KeyCharacterMap.VIRTUAL_KEYBOARD, 0, KeyEvent.FLAG_SOFT_KEYBOARD)))
        }
    }

    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(
        By.res(context.packageName, "qa_composing_stats"))).text.orEmpty().split(' ').associate {
        val (name, value) = it.split('=')
        name to value.toInt()
    }

    private fun awaitSelection(start: Int, end: Int) {
        val deadline = SystemClock.uptimeMillis() + 3_000
        var observed: Map<String, Int>
        do {
            observed = stats()
            if (observed["selectionStart"] == start && observed["selectionEnd"] == end) return
            SystemClock.sleep(40)
        } while (SystemClock.uptimeMillis() < deadline)
        fail("Numeric selection differs: expected=$start,$end actual=${observed["selectionStart"]},${observed["selectionEnd"]}")
    }

    private fun assertPayloadReadsZero(phase: String) {
        val counts = stats()
        for (name in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot")) {
            assertEquals("$phase unexpectedly read $name", 0, counts.getValue(name))
        }
    }

    private fun assertNoPayloadReads(protocol: String, caret: Int = 4) {
        assertPayloadReadsZero(protocol)
        val counts = stats()
        assertEquals(4, counts.getValue("length"))
        instrumentation.sendStatus(2, android.os.Bundle().apply {
            putString("stream", "EDIT_SELECTION_PROTOTYPE protocol=$protocol keyDown=${counts.getValue("keyDown")} keyUp=${counts.getValue("keyUp")} payloadReads=0 finalSelection=$caret,$caret length=4\n")
        })
    }
}
