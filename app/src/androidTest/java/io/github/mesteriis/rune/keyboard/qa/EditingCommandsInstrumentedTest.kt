package io.github.mesteriis.rune.keyboard.qa

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.ContextWrapper
import android.os.SystemClock
import android.view.KeyEvent
import android.view.inputmethod.InputConnection
import android.view.inputmethod.InputConnectionWrapper
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import io.github.mesteriis.rune.keyboard.ime.RuneInputMethodService
import io.github.mesteriis.rune.keyboard.ime.editor.EditorCommandExecutor
import io.github.mesteriis.rune.keyboard.ime.model.CursorDirection
import io.github.mesteriis.rune.keyboard.ime.model.EditorCommand
import io.github.mesteriis.rune.keyboard.ime.model.EditorContextAction
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/** The public seed/clipboard belongs only to this disposable cross-process QA fixture. */
class EditingCommandsInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private val driver = ImeTestDriver()
    private var prepared = false
    private var clipboardTouched = false
    private val events = mutableListOf<Triple<Int, Int, Int>>()
    private val menuActions = mutableListOf<Int>()
    private lateinit var connection: InputConnection

    @Before fun prepareDisposableEditor() {
        check(android.os.Build.HARDWARE in setOf("ranchu", "goldfish")) { "Disposable emulator required" }
        prepared = true
        driver.setUp()
        driver.configureMechanicalPunctuation(mechanical = false, doubleSpace = false)
        driver.launchComposingQa()
        val keyboard = keyboardSnapshot().keyboard
        instrumentation.runOnMainSync {
            var owner: Context = keyboard.rootView.context
            while (owner is ContextWrapper && owner !is RuneInputMethodService) owner = owner.baseContext
            val service = checkNotNull(owner as? RuneInputMethodService)
            assertEquals(context.packageName, service.currentInputEditorInfo.packageName)
            connection = object : InputConnectionWrapper(checkNotNull(service.currentInputConnection), false) {
                override fun sendKeyEvent(event: KeyEvent): Boolean {
                    events += Triple(event.action, event.keyCode, event.metaState)
                    return super.sendKeyEvent(event)
                }
                override fun performContextMenuAction(id: Int): Boolean {
                    menuActions += id
                    return super.performContextMenuAction(id)
                }
            }
        }
    }

    @After fun restoreFixture() {
        if (clipboardTouched) instrumentation.runOnMainSync {
            val clipboard = context.getSystemService(ClipboardManager::class.java)
            if (android.os.Build.VERSION.SDK_INT >= 28) clipboard.clearPrimaryClip()
            else clipboard.setPrimaryClip(ClipData.newPlainText("Rune QA", ""))
        }
        if (prepared) driver.tearDown()
    }

    @Test fun executorExtendsAcrossEmojiAndReleasesShiftBeforeOrdinaryMovement() {
        seed("a😀b")
        execute(EditorCommand.NavigateCursor(CursorDirection.LEFT, true))
        awaitEditor(4, 3, 4)
        execute(EditorCommand.NavigateCursor(CursorDirection.LEFT, true))
        awaitEditor(4, 1, 4)
        execute(EditorCommand.NavigateCursor(CursorDirection.RIGHT))
        awaitEditor(4, 4, 4)
        val extended = listOf(Triple(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_SHIFT_LEFT, KeyEvent.META_SHIFT_ON),
            Triple(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_DPAD_LEFT, KeyEvent.META_SHIFT_ON),
            Triple(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_DPAD_LEFT, KeyEvent.META_SHIFT_ON),
            Triple(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_SHIFT_LEFT, 0))
        assertEquals(extended + extended + listOf(Triple(KeyEvent.ACTION_DOWN, KeyEvent.KEYCODE_DPAD_RIGHT, 0),
            Triple(KeyEvent.ACTION_UP, KeyEvent.KEYCODE_DPAD_RIGHT, 0)), events)
        noPayloadReads()
    }

    @Test fun homeEndAndHorizontalCommandsUseTheEditorCaretWithoutReadback() {
        seed("abcd")
        execute(EditorCommand.NavigateCursor(CursorDirection.HOME))
        awaitEditor(0, 0, 4)
        execute(EditorCommand.NavigateCursor(CursorDirection.RIGHT))
        awaitEditor(1, 1, 4)
        execute(EditorCommand.NavigateCursor(CursorDirection.END))
        awaitEditor(4, 4, 4)
        assertEquals(listOf(KeyEvent.KEYCODE_MOVE_HOME, KeyEvent.KEYCODE_DPAD_RIGHT, KeyEvent.KEYCODE_MOVE_END),
            events.filter { it.first == KeyEvent.ACTION_DOWN }.map { it.second })
        assertTrue(events.all { it.third == 0 })
        noPayloadReads()
    }

    @Test fun contextMenuDelegatesClipboardToEditorAndKeepsSelectionMetadataUnclaimed() {
        seed("abcd")
        clipboardTouched = true
        putClipboard("fixture-sentinel") // Never inspect a clipboard value left by somebody else.
        execute(EditorCommand.ContextMenu(EditorContextAction.SELECT_ALL))
        awaitEditor(0, 4, 4)
        execute(EditorCommand.ContextMenu(EditorContextAction.COPY), hasSelection = true)
        awaitCopiedPublicSeed()
        // COPY may end the editor's selection mode; request SELECT_ALL again before CUT.
        execute(EditorCommand.ContextMenu(EditorContextAction.SELECT_ALL))
        awaitEditor(0, 4, 4)
        execute(EditorCommand.ContextMenu(EditorContextAction.CUT), hasSelection = true)
        awaitEditor(0, 0, 0)
        putClipboard("foreign ")
        execute(EditorCommand.ContextMenu(EditorContextAction.PASTE))
        awaitEditor(8, 8, 8)
        // The observer reads only this public QA view; Rune never reads clipboard/selection text.
        assertEquals("foreign ", checkNotNull(driver.device.findObject(By.res(context.packageName, "qa_composing_text"))).text)
        assertEquals(listOf(android.R.id.selectAll, android.R.id.copy, android.R.id.selectAll, android.R.id.cut, android.R.id.paste), menuActions)
        assertTrue(events.isEmpty())
        noPayloadReads()
    }

    private fun putClipboard(value: String) = instrumentation.runOnMainSync {
        context.getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText("Rune QA", value))
    }

    private fun awaitCopiedPublicSeed() {
        val deadline = SystemClock.uptimeMillis() + 3_000
        do {
            var copied = false
            instrumentation.runOnMainSync {
                // Test observer only, after overwriting with our own public sentinel. No product read.
                val clip = context.getSystemService(ClipboardManager::class.java).primaryClip
                copied = clip != null && clip.itemCount == 1 && clip.getItemAt(0).text?.toString() == "abcd"
            }
            if (copied) return
            SystemClock.sleep(40)
        } while (SystemClock.uptimeMillis() < deadline)
        fail("Controlled public COPY did not reach the fixture clipboard")
    }

    private fun seed(value: String) {
        instrumentation.runOnMainSync { assertTrue(connection.commitText(value, 1)) }
        awaitEditor(value.length, value.length, value.length)
        noPayloadReads()
    }

    private fun execute(command: EditorCommand, hasSelection: Boolean = false) {
        instrumentation.runOnMainSync {
            val result = EditorCommandExecutor.execute(command, connection, hasSelection, false)
            assertTrue("Dispatch refused", result.handled)
            assertFalse("Dispatch must not fabricate an observed caret", result.clearsSelection)
        }
    }

    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(
        By.res(context.packageName, "qa_composing_stats"))).text.orEmpty().split(' ').associate {
        val (name, value) = it.split('='); name to value.toInt()
    }

    private fun awaitEditor(start: Int, end: Int, length: Int) {
        val deadline = SystemClock.uptimeMillis() + 3_000
        do {
            val observed = stats()
            if (observed["selectionStart"] == start && observed["selectionEnd"] == end && observed["length"] == length) return
            SystemClock.sleep(40)
        } while (SystemClock.uptimeMillis() < deadline)
        fail("Public fixture numeric selection/length did not reach $start,$end/$length")
    }

    private fun noPayloadReads() {
        val counts = stats()
        for (name in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Unexpected input-connection payload read: $name", 0, counts.getValue(name))
    }
}
