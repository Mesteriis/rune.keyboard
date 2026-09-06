package io.github.mesteriis.rune.keyboard.qa

import android.content.ComponentName
import android.content.Context
import android.content.ContextWrapper
import android.inputmethodservice.InputMethodService
import android.os.SystemClock
import android.text.InputType
import android.view.inputmethod.InputConnection
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import io.github.mesteriis.rune.keyboard.ime.editor.EditorCommandExecutor
import io.github.mesteriis.rune.keyboard.ime.model.EditorCommand
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.intelligence.ipc.NumericScore
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringCode
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringInput
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCompletion
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalCandidateReply
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingEdit
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingSessionController
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingTextResult
import io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem
import java.util.concurrent.Callable
import java.util.concurrent.FutureTask
import java.util.concurrent.TimeUnit
import org.junit.Assert.*
import org.junit.Test

/**
 * Production controller/executor -> live IME InputConnection -> :qa_editor protocol coverage.
 * Valid-word membership and numerical scores are synthetic; no model or strip tap is exercised.
 * The test forwards the remote fixture's numeric selection observations to its own controller.
 */
class ContextualPunctuationEditorInstrumentedTest : ImeTestBase() {
    @Test fun explicitSelectionChangesOnlyOwnedBoundaryAndOptionalFirstLetterAcrossBinder() {
        for (example in listOf(
            Example("hello", "world", KeyboardLanguage.ENGLISH, 1, ", world"),
            Example("ayer", "árbol", KeyboardLanguage.SPANISH, 4, ". Árbol"),
        )) Fixture(example.left, example.word, example.language).use { f ->
            val input = f.beginRanking()
            val before = f.settledStats()
            val originalId = onMain { f.controller.originalCandidateId }
            assertTrue(onMain { f.controller.acceptContextualRanking(reply(input, example.winner)) })
            val candidateId = f.punctuationId()
            assertEquals(originalId, onMain { f.controller.candidateViewState.selectedCandidateId })
            f.assertUnchanged(before, "${example.left} ${example.word}")

            assertEquals(TypingTextResult.HANDLED, onMain {
                f.controller.selectCandidate(candidateId, f::execute)
            })
            f.observe("${example.left}${example.continuation}", example.left.length)
            val after = stats()
            assertEquals(before.getValue("compose") + 1, after.getValue("compose"))
            for (counter in listOf("commit", "region", "finish")) {
                assertEquals("Punctuation must only replace the current composition", before[counter], after[counter])
            }
            f.noReadback()
        }
    }

    @Test fun obsoleteReplyAndCandidateCannotReplaceNewWordOrConsumeItsCurrentRequest() {
        Fixture("hello", "world", KeyboardLanguage.ENGLISH).use { f ->
            val obsolete = f.beginRanking()
            assertTrue(onMain { f.controller.acceptContextualRanking(reply(obsolete, 4)) })
            val staleCandidate = f.punctuationId()
            f.type("s", "hello worlds", 5)
            val current = f.beginRanking()
            assertTrue(current.token.revision > obsolete.token.revision)
            assertTrue(current.token.requestId > obsolete.token.requestId)
            val before = f.settledStats()

            assertFalse(onMain { f.controller.acceptContextualRanking(reply(obsolete, 4)) })
            assertEquals(TypingTextResult.REJECTED, onMain {
                f.controller.selectCandidate(staleCandidate, f::execute)
            })
            assertTrue(onMain { f.controller.isCurrentContextualRanking(current.token) })
            assertTrue(onMain { f.controller.candidateViewState.candidates.none { it is CandidateUiItem.Punctuation } })
            f.assertUnchanged(before, "hello worlds")

            // A current reply and explicit selection must still work on that same remote editor.
            assertTrue(onMain { f.controller.acceptContextualRanking(reply(current, 1)) })
            val currentCandidate = f.punctuationId()
            assertEquals(TypingTextResult.HANDLED, onMain {
                f.controller.selectCandidate(currentCandidate, f::execute)
            })
            f.observe("hello, worlds", 5)
            f.noReadback()
        }
    }

    @Test fun remoteCursorMovementInvalidatesPendingReplyAndHeldPunctuationSelection() {
        // Exercise both a reply still in flight and a suggestion already held for selection.
        for (replyBeforeCursor in listOf(false, true)) {
            Fixture("hello", "world", KeyboardLanguage.ENGLISH).use { f ->
                val input = f.beginRanking()
                val heldCandidate = if (replyBeforeCursor) {
                    assertTrue(onMain { f.controller.acceptContextualRanking(reply(input, 4)) })
                    f.punctuationId()
                } else null
                val connections = stats().getValue("connections")
                driver.tapQaControl("qa_composing_cursor")
                val moved = awaitStats { it["selectionStart"] == 0 && it["selectionEnd"] == 0 }
                assertEquals("Cursor control must retain the same editor connection", connections, moved["connections"])
                assertTrue(onMain {
                    f.controller.updateSelection(moved.getValue("selectionStart"), moved.getValue("selectionEnd"),
                        moved.getValue("start"), moved.getValue("end"), f::execute)
                })
                awaitStats { it["start"] == -1 && it["end"] == -1 }
                val before = f.settledStats()

                assertFalse(onMain { f.controller.acceptContextualRanking(reply(input, 4)) })
                if (heldCandidate != null) assertEquals(TypingTextResult.REJECTED, onMain {
                    f.controller.selectCandidate(heldCandidate, f::execute)
                })
                assertTrue(onMain { f.controller.candidateViewState.candidates.none { it is CandidateUiItem.Punctuation } })
                f.assertUnchanged(before, "hello world")
                f.noReadback()
            }
        }
    }

    private inner class Fixture(left: String, word: String, private val language: KeyboardLanguage) : AutoCloseable {
        val controller = onMain { TypingSessionController() }
        private val connection: InputConnection
        private var requestId = 0L

        init {
            // Keep the resident IME's independent consumers idle; the controller under test owns
            // this protocol's edits and uses no readiness override or production test hook.
            driver.configureSmartTyping(AutocorrectionMode.OFF, true, mechanical = false,
                doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
            driver.launchComposingQa()
            val keyboard = keyboardSnapshot().keyboard
            val target = InstrumentationRegistry.getInstrumentation().targetContext
            @Suppress("DEPRECATION")
            val editorInfo = target.packageManager.getActivityInfo(
                ComponentName(target, ImeQaActivity::class.java), 0)
            assertEquals("${target.packageName}:qa_editor", editorInfo.processName)
            connection = onMain {
                var context: Context = keyboard.context
                while (context !is InputMethodService && context is ContextWrapper) context = context.baseContext
                checkNotNull((context as? InputMethodService)?.currentInputConnection) { "Live editor connection unavailable" }
            }
            onMain { controller.startSession(EditorContext.from(InputType.TYPE_CLASS_TEXT, 0), 0, 0) }
            type(left, left, 0)
            type(" ", "$left ", left.length)
            type(word, "$left $word", left.length)
            noReadback()
        }

        fun type(text: String, expected: String, start: Int) {
            assertEquals(TypingTextResult.HANDLED, onMain { controller.typeText(text, ::execute) })
            observe(expected, start)
        }

        fun observe(expected: String, start: Int) {
            driver.awaitFieldText(FIELD, expected)
            val observed = awaitStats {
                it["start"] == start && it["end"] == expected.length &&
                    it["selectionStart"] == expected.length && it["selectionEnd"] == expected.length
            }
            assertFalse("Owned remote acknowledgement must preserve the typing session", onMain {
                controller.updateSelection(observed.getValue("selectionStart"), observed.getValue("selectionEnd"),
                    observed.getValue("start"), observed.getValue("end"), ::execute)
            })
        }

        fun beginRanking(): ScoringInput = onMain {
            val local = checkNotNull(controller.beginCandidateRequest(++requestId, language))
            assertTrue(controller.acceptCandidates(LocalCandidateReply(local.sessionId, local.revision, local.requestId,
                CandidateGeneration(local.token, emptyList(), CandidateCompletion.COMPLETE, true, null, 1, 1))))
            checkNotNull(controller.beginContextualRanking(requestId)).also {
                assertEquals((0..6).toList(), it.token.candidateIds)
                assertEquals(7, it.continuations.size)
            }
        }

        fun punctuationId(): String = onMain {
            controller.candidateViewState.candidates.single { it is CandidateUiItem.Punctuation }.id
        }

        fun execute(edit: TypingEdit): Boolean =
            EditorCommandExecutor.execute(command(edit), connection, false, false).handled

        fun assertUnchanged(before: Map<String, Int>, expected: String) {
            InstrumentationRegistry.getInstrumentation().waitForIdleSync()
            driver.device.waitForIdle()
            driver.awaitFieldText(FIELD, expected)
            val after = stats()
            for (counter in listOf("compose", "region", "finish", "commit", "length", "selectionStart", "selectionEnd",
                "before", "after", "selected", "extracted", "caps", "surrounding", "snapshot")) {
                assertEquals("Unselected or obsolete punctuation changed the remote editor", before[counter], after[counter])
            }
        }

        fun settledStats(): Map<String, Int> {
            InstrumentationRegistry.getInstrumentation().waitForIdleSync()
            driver.device.waitForIdle()
            return stats()
        }

        fun noReadback() {
            val observed = stats()
            // The resident IME retains its pre-existing NORMAL getCursorCapsMode lookup on
            // editor callbacks. This independent controller has no composing state in that IME.
            // Payload reads must stay zero; score-only actions must not add even caps lookups
            // (assertUnchanged checks all counters after the preceding callbacks settle).
            for (counter in listOf("before", "after", "selected", "extracted", "surrounding", "snapshot")) {
                assertEquals("Unexpected editor readback: $counter", 0, observed.getValue(counter))
            }
        }

        override fun close() = onMain {
            controller.finishComposition(::execute)
            controller.endSession()
        }
    }

    private fun command(edit: TypingEdit): EditorCommand = when (edit) {
        is TypingEdit.SetComposingText -> EditorCommand.SetComposingText(edit.value)
        is TypingEdit.CommitText -> EditorCommand.CommitText(edit.value)
        TypingEdit.FinishComposingText -> EditorCommand.FinishComposingText
        is TypingEdit.SetComposingRegion -> EditorCommand.SetComposingRegion(edit.start, edit.end)
        is TypingEdit.Batch -> EditorCommand.Batch(edit.edits.map(::command), edit.isCurrent)
    }

    private fun reply(input: ScoringInput, winner: Int) = ScoringReply(input.token, ScoringCode.OK, 1,
        input.token.candidateIds.map { NumericScore(it, if (it == winner) -1.0 else -7.0, 1) })

    private fun stats(): Map<String, Int> = checkNotNull(driver.device.findObject(
        By.res(ImeTestDriver.PACKAGE_NAME, "qa_composing_stats"))).text.orEmpty().split(' ').associate {
        val (key, value) = it.split('='); key to value.toInt()
    }

    private fun awaitStats(predicate: (Map<String, Int>) -> Boolean): Map<String, Int> {
        val deadline = SystemClock.uptimeMillis() + ImeTestDriver.WAIT_MILLIS
        do {
            val observed = stats()
            if (predicate(observed)) return observed
            SystemClock.sleep(25)
        } while (SystemClock.uptimeMillis() < deadline)
        throw AssertionError("Remote composing state did not settle")
    }

    private fun <T> onMain(action: () -> T): T {
        val task = FutureTask(Callable(action))
        InstrumentationRegistry.getInstrumentation().runOnMainSync(task)
        return task.get(5, TimeUnit.SECONDS)
    }

    private data class Example(val left: String, val word: String, val language: KeyboardLanguage,
        val winner: Int, val continuation: String)

    private companion object { const val FIELD = "qa_composing_text" }
}
