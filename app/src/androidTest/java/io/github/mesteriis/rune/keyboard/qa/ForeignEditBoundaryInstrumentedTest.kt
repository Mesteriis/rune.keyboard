package io.github.mesteriis.rune.keyboard.qa

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.ContextWrapper
import android.os.SystemClock
import android.view.inputmethod.InputConnection
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.RuneInputMethodService
import io.github.mesteriis.rune.keyboard.ime.editor.EditorCommandExecutor
import io.github.mesteriis.rune.keyboard.ime.model.EditorCommand
import io.github.mesteriis.rune.keyboard.ime.model.EditorContextAction
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingEdit
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingSessionController
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/** Test-only caller of the new guard; production editing actions are not wired yet. */
class ForeignEditBoundaryInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private val driver = ImeTestDriver()
    private var prepared = false
    private var clipboardTouched = false
    private lateinit var service: RuneInputMethodService
    private lateinit var controller: TypingSessionController
    private lateinit var connection: InputConnection

    @Before fun prepareDisposableEditor() {
        check(android.os.Build.HARDWARE in setOf("ranchu", "goldfish")) { "Disposable emulator required" }
        prepared = true
        driver.setUp()
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
        driver.launchComposingQa()
        val keyboard = keyboardSnapshot().keyboard
        instrumentation.runOnMainSync {
            var owner: Context = keyboard.rootView.context
            while (owner is ContextWrapper && owner !is RuneInputMethodService) owner = owner.baseContext
            service = checkNotNull(owner as? RuneInputMethodService)
            assertEquals(context.packageName, service.currentInputEditorInfo.packageName)
            controller = RuneInputMethodService::class.java.getDeclaredField("typingSession").apply {
                isAccessible = true
            }.get(service) as TypingSessionController
            connection = checkNotNull(service.currentInputConnection)
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

    @Test fun pastedSuffixStaysLiteralAndOwnWhitespaceRestoresQualifiedCorrection() {
        type("old")
        var session = 0L
        instrumentation.runOnMainSync {
            session = controller.state.sessionId
            prepareExternal(await = true)
            clipboardTouched = true
            context.getSystemService(ClipboardManager::class.java).setPrimaryClip(ClipData.newPlainText("Rune QA", "foreign"))
            assertTrue(EditorCommandExecutor.execute(EditorCommand.ContextMenu(EditorContextAction.PASTE), connection, false, false).handled)
        }
        awaitField("oldforeign")
        type("teh")
        awaitField("oldforeignteh")
        instrumentation.runOnMainSync {
            assertEquals(session, controller.state.sessionId)
            assertNull(controller.state.composing)
            assertEquals("", controller.state.contextText)
            assertNull(controller.originalCandidateId)
        }
        space()
        awaitField("oldforeignteh ")
        instrumentation.runOnMainSync { assertEquals(" ", controller.state.contextText) }
        type("teh")
        assertNotNull(driver.device.wait(Until.findObject(By.desc(context.getString(R.string.candidate_correction, "the"))), 5_000))
        space()
        awaitField("oldforeignteh the ")
        noPayloadReads()
    }

    @Test fun cuttingBetweenForeignFragmentsCannotCorrectTheNewAdjacentSuffix() {
        type("abxcd")
        instrumentation.runOnMainSync {
            prepareExternal(await = true)
            assertTrue(connection.setSelection(2, 3)) // Numeric bounds of this fixed public fixture only.
        }
        awaitSelection(2, 3)
        instrumentation.runOnMainSync {
            prepareExternal(await = true)
            clipboardTouched = true
            assertTrue(EditorCommandExecutor.execute(EditorCommand.ContextMenu(EditorContextAction.CUT), connection, true, false).handled)
        }
        awaitField("abcd")
        awaitSelection(2, 2)
        type("teh"); space()
        awaitField("abteh cd")
        instrumentation.runOnMainSync {
            assertEquals(" ", controller.state.contextText)
            assertNull(controller.state.lastAutoEdit)
        }
        noPayloadReads()
    }

    private fun prepareExternal(await: Boolean) {
        val method = RuneInputMethodService::class.java.getDeclaredMethod("executeTypingEdit", TypingEdit::class.java).apply {
            isAccessible = true
        }
        assertTrue(controller.prepareExternalEdit(await) { edit -> method.invoke(service, edit) as Boolean })
    }

    private fun type(value: String) = value.forEach { driver.tapKey(it.toString()) }
    private fun space() = driver.tapKeyByDescription(context.getString(R.string.key_space))

    private fun awaitField(expected: String) = driver.awaitFieldText("qa_composing_text", expected)

    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(
        By.res(context.packageName, "qa_composing_stats"))).text.orEmpty().split(' ').associate {
        val (name, value) = it.split('='); name to value.toInt()
    }

    private fun awaitSelection(start: Int, end: Int) {
        val deadline = SystemClock.uptimeMillis() + 3_000
        do {
            val counts = stats()
            if (counts["selectionStart"] == start && counts["selectionEnd"] == end) return
            SystemClock.sleep(40)
        } while (SystemClock.uptimeMillis() < deadline)
        fail("Fixed public selection did not reach $start,$end")
    }

    private fun noPayloadReads() {
        val counts = stats()
        for (name in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot"))
            assertEquals("Unexpected payload read: $name", 0, counts.getValue(name))
    }
}
