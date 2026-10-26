package io.github.mesteriis.rune.keyboard.smarttyping.session

import android.text.InputType
import android.text.Selection
import android.view.inputmethod.BaseInputConnection
import android.view.inputmethod.EditorInfo
import android.widget.EditText
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.ime.editor.EditorCommandExecutor
import io.github.mesteriis.rune.keyboard.ime.model.*
import io.github.mesteriis.rune.keyboard.intelligence.ipc.*
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.smarttyping.correction.*
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticFeature
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.*
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem
import org.junit.Assert.*
import org.junit.Test

/** Synthetic scores qualify mechanics only. The actual framework Editable owns text and spans. */
class PreviousWordRefinementInstrumentedTest {
    @Test fun previousWordReplacementAndRootUndoPreserveFrameworkComposition() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        instrumentation.runOnMainSync {
            for (winner in listOf("проверки", "проверочка", "слово", "рроверка")) {
                val field = EditText(instrumentation.targetContext)
                field.inputType = InputType.TYPE_CLASS_TEXT
                val reads = IntArray(6)
                val target = field.onCreateInputConnection(EditorInfo())!!
                val connection = when {
                    android.os.Build.VERSION.SDK_INT >= 33 -> SnapshotConnection(target, reads)
                    android.os.Build.VERSION.SDK_INT >= 31 -> SurroundingConnection(target, reads)
                    else -> ObservedConnection(target, reads)
                }
                var now = 0L
                val controller = TypingSessionController(IcuGraphemeSegmenter, SpellingQualification { _, _ -> true },
                    nanoTime = { now }, refinementThresholds = RecoveryThresholds(-3.0, .5))
                controller.startSession(EditorContext.from(InputType.TYPE_CLASS_TEXT, 0), 0, 0)
                controller.configureFeatures(DiagnosticFeature.VISIBLE_UNDO.bit, DiagnosticFeature.VISIBLE_UNDO.bit)
                fun command(edit: TypingEdit): EditorCommand = when (edit) {
                    is TypingEdit.SetComposingText -> EditorCommand.SetComposingText(edit.value)
                    is TypingEdit.CommitText -> EditorCommand.CommitText(edit.value)
                    is TypingEdit.SetComposingRegion -> EditorCommand.SetComposingRegion(edit.start, edit.end)
                    TypingEdit.FinishComposingText -> EditorCommand.FinishComposingText
                    is TypingEdit.Batch -> EditorCommand.Batch(edit.edits.map(::command), edit.isCurrent)
                }
                val execute: (TypingEdit) -> Boolean = { EditorCommandExecutor.execute(command(it), connection, false, false).handled }
                fun type(text: String) = controller.typeText(text,
                    MechanicalPunctuationPolicy(InputPolicy.NORMAL, EditorMode.TEXT, false, false, false),
                    KeyboardState(KeyboardLanguage.RUSSIAN), autocorrectionMode = AutocorrectionMode.HIGH_CONFIDENCE,
                    execute = execute)
                assertEquals(TypingTextResult.HANDLED, type("рроверка"))
                val request = controller.beginCandidateRequest(1, KeyboardLanguage.RUSSIAN)!!
                fun candidate(word: String) = GeneratedCandidate(word, word, word, KeyboardLanguage.RUSSIAN,
                    false, 2, 1, 1, EditFeatures(.75, 1, .0), 0, CasePattern.LOWER)
                val local = candidate("проверка")
                assertTrue(controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId,
                    CandidateGeneration(request.token, listOf(local), CandidateCompletion.COMPLETE, false, null, 1, 1,
                        LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(local), 1, 1),
                        neighborRecovery = LocalSearchEvidence(CandidateCompletion.COMPLETE, listOf(candidate(winner)), 1, 1)))))
                assertEquals(TypingTextResult.HANDLED, type(" "))
                assertEquals("проверка ", field.text.toString())
                val input = controller.beginPreviousWordRefinement(1)!!
                type("сл"); type("ед")
                now = 999_000_000
                val id = input.continuations.indexOf(winner)
                assertTrue(controller.acceptPreviousWordRefinement(ScoringReply(input.token, 0, 1,
                    input.token.candidateIds.map { NumericScore(it, if (it == id) -1.0 else -8.0, 1) }), execute))
                assertEquals("$winner след", field.text.toString())
                assertEquals(field.length(), Selection.getSelectionStart(field.text))
                assertEquals(winner.length, BaseInputConnection.getComposingSpanStart(field.text))
                assertEquals(field.length(), BaseInputConnection.getComposingSpanEnd(field.text))
                val undo = controller.candidateViewState.candidates.filterIsInstance<CandidateUiItem.Undo>().single()
                assertEquals(TypingTextResult.HANDLED, controller.selectCandidate(undo.id, execute))
                assertEquals("рроверка след", field.text.toString())
                assertEquals(field.length(), Selection.getSelectionStart(field.text))
                assertEquals(8, BaseInputConnection.getComposingSpanStart(field.text))
                assertArrayEquals("No editor text readback", IntArray(6), reads)
                controller.endSession()
                connection.closeConnection()
            }
        }
    }
    private open class ObservedConnection(target: android.view.inputmethod.InputConnection, protected val reads: IntArray) :
        android.view.inputmethod.InputConnectionWrapper(target, false) {
        override fun getTextBeforeCursor(length: Int, flags: Int): CharSequence? { reads[0]++; return null }
        override fun getTextAfterCursor(length: Int, flags: Int): CharSequence? { reads[1]++; return null }
        override fun getSelectedText(flags: Int): CharSequence? { reads[2]++; return null }
        override fun getExtractedText(request: android.view.inputmethod.ExtractedTextRequest?, flags: Int):
            android.view.inputmethod.ExtractedText? { reads[3]++; return null }
    }
    private open class SurroundingConnection(target: android.view.inputmethod.InputConnection, reads: IntArray) :
        ObservedConnection(target, reads) {
        override fun getSurroundingText(beforeLength: Int, afterLength: Int, flags: Int):
            android.view.inputmethod.SurroundingText? { reads[4]++; return null }
    }
    private class SnapshotConnection(target: android.view.inputmethod.InputConnection, reads: IntArray) :
        SurroundingConnection(target, reads) {
        override fun takeSnapshot(): android.view.inputmethod.TextSnapshot? { reads[5]++; return null }
    }

}
