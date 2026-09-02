package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.editor.DoubleSpacePeriod
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import io.github.mesteriis.rune.keyboard.smarttyping.correction.ProtectedTokenPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.correction.ProtectedTokenReason
import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCompletion
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGenerator
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateSearchControl
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalCandidateReply
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalCandidateRequest
import io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem
import io.github.mesteriis.rune.keyboard.smarttyping.ui.SmartTypingViewState
import java.util.ArrayDeque

/**
 * Main-thread session owner. The execution callback returns the editor's actual result; all
 * acknowledgements and failure cleanup happen here. It must not independently replay edits.
 */
class TypingSessionController internal constructor(
    private val graphemes: GraphemeSegmenter,
) {
    constructor() : this(IcuGraphemeSegmenter)

    var state = TypingSessionState()
        private set

    private var context: SessionTextContext? = null
    private var selectionStart = -1
    private var selectionEnd = -1
    private var composingStart = -1
    private val expectedSelections = ArrayDeque<EditorSelection>()
    private var expectedEditorSelection: EditorSelection? = null
    private var lastAcknowledgedSelection: EditorSelection? = null
    private var awaitingEditorSelection = false
    private var plainWordUntilBoundary = false
    private var editorEditDepth = 0
    private var candidateEpoch = 0L
    private var lastCandidateRequestId = -1L
    private var pendingCandidate: CandidateStamp? = null
    private var candidateSelection: CandidateSelection? = null

    /** Owner must additionally check the active view, editor policy, layer, language and readiness. */
    val ownsCandidateComposition: Boolean
        get() {
            val composing = state.composing ?: return false
            return state.enabled && !awaitingEditorSelection && editorEditDepth == 0 &&
                composing.typedWord.isNotEmpty() && composingStart >= 0 &&
                selectionStart == selectionEnd &&
                selectionStart.toLong() == composingStart.toLong() + composing.text.length &&
                context?.text?.endsWith(composing.text) == true
        }

    val canRequestCandidates: Boolean
        get() = ownsCandidateComposition && !state.originalSelected &&
            candidateSelection?.manual != true &&
            !ProtectedTokenPolicy.isProtected(state.composing!!.typedWord)

    /** Only the numeric stamp is retained. Caller admits this request after live service checks. */
    fun beginCandidateRequest(requestId: Long, activeLanguage: KeyboardLanguage): LocalCandidateRequest? {
        if (!canRequestCandidates || requestId < 0 || requestId <= lastCandidateRequestId) return null
        clearCandidates()
        lastCandidateRequestId = requestId
        pendingCandidate = CandidateStamp(state.sessionId, state.revision, requestId)
        return LocalCandidateRequest(state.sessionId, state.revision, requestId,
            state.composing!!.typedWord, activeLanguage, eligible = true)
    }

    /** Service rechecks its policy/language/lifetime first; this owner checks the exact live word. */
    fun acceptCandidates(reply: LocalCandidateReply): Boolean {
        val stamp = pendingCandidate ?: return false
        if (stamp != CandidateStamp(reply.sessionId, reply.revision, reply.requestId)) return false
        pendingCandidate = null
        val generation = reply.generation
        if (state.sessionId != stamp.sessionId || state.revision != stamp.revision ||
            !canRequestCandidates || generation.original != state.composing?.typedWord ||
            generation.completion == CandidateCompletion.CANCELLED ||
            generation.alternatives.size > CandidateGenerator.MAX_ALTERNATIVES ||
            generation.inspectedStates !in 0..CandidateSearchControl.MAX_STATES ||
            generation.verifiedTerminals !in 0..CandidateSearchControl.MAX_VERIFIED
        ) return false

        val suggests = generation.completion == CandidateCompletion.COMPLETE ||
            generation.completion == CandidateCompletion.STATES_EXHAUSTED ||
            generation.completion == CandidateCompletion.VERIFIED_EXHAUSTED
        if ((!suggests || generation.isValidWord || generation.protectedReason != null) &&
            generation.alternatives.isNotEmpty()) return false
        val original = generation.original!!
        val originalCase = CasePattern.analyze(original)
        val seen = hashSetOf(TokenUnicode.folded(original))
        for (candidate in generation.alternatives) {
            val reason = ProtectedTokenPolicy.reason(candidate.text)
            // Eligible one-letter uppercase input can expand to a multi-letter uppercase display.
            // Source admission stays protected; only its preserved ALL_CAPS output is allowed.
            if ((reason != null && !(reason == ProtectedTokenReason.ALL_CAPS && originalCase == CasePattern.UPPER)) ||
                !seen.add(TokenUnicode.folded(candidate.text))) return false
        }
        val alternatives = generation.alternatives.take(SmartTypingViewState.MAX_VISIBLE_CANDIDATES - 1)
            .map { it.text }
        candidateSelection = CandidateSelection(original, alternatives, stamp.requestId,
            generation.completion, selectedIndex = if (alternatives.isEmpty()) -1 else 0)
        return true
    }

    /** No editor mutation or veto reset. Service calls this when its own policy/route invalidates. */
    fun clearCandidates() {
        candidateEpoch++
        pendingCandidate = null
        candidateSelection = null
    }

    /** Diagnostic completion only: this controller never authorizes automatic replacement. */
    val candidateCompletion: CandidateCompletion?
        get() = candidateSelection?.completion

    /** Pure projection. Service applies its additional HIDDEN policy before displaying it. */
    val candidateViewState: SmartTypingViewState
        get() {
            if (!state.enabled) return SmartTypingViewState.HIDDEN
            val originalId = originalCandidateId ?: return SmartTypingViewState.EMPTY
            val selection = candidateSelection
            val items = buildList {
                add(CandidateUiItem.Original(originalId, selection?.original ?: state.composing!!.typedWord))
                selection?.alternatives?.forEachIndexed { index, word ->
                    add(CandidateUiItem.Correction(correctionId(selection.requestId, index), word))
                }
            }
            val selectedId = if (selection != null && selection.selectedIndex >= 0 &&
                (!state.originalSelected || selection.manual)) {
                correctionId(selection.requestId, selection.selectedIndex)
            } else originalId
            return SmartTypingViewState(true, items, selectedId)
        }

    val originalCandidateId: String?
        get() = if (ownsCandidateComposition)
            "original:${state.sessionId}:${state.revision}:$candidateEpoch" else null

    /** A stale strip tap cannot select a different word or resurrect an earlier session. */
    fun selectOriginal(candidateId: String): Boolean {
        if (candidateId != originalCandidateId) return false
        val selection = candidateSelection
        // The old no-editor API cannot restore a manually replaced word. Use selectCandidate.
        if (selection != null && selection.original != state.composing?.typedWord) return false
        discardUndo()
        clearCandidates()
        state = state.copy(originalSelected = true, revision = state.revision + 1)
        candidateSelection = selection?.copy(selectedIndex = -1, manual = true)
        return true
    }

    /** Explicit user choice only. Unknown/stale IDs are REJECTED and must never fall back/replay. */
    fun selectCandidate(candidateId: String, execute: (TypingEdit) -> Boolean): TypingTextResult {
        if (!ownsCandidateComposition) return TypingTextResult.REJECTED
        val selection = candidateSelection
        val index = if (candidateId == originalCandidateId) -1 else {
            selection?.alternatives?.indices?.firstOrNull {
                candidateId == correctionId(selection.requestId, it)
            } ?: return TypingTextResult.REJECTED
        }
        if (index == -1 && (selection == null || selection.original == state.composing!!.typedWord)) {
            return if (selectOriginal(candidateId)) TypingTextResult.HANDLED else TypingTextResult.REJECTED
        }
        if (selection == null) return TypingTextResult.REJECTED
        val previous = state.composing!!
        val word = if (index == -1) selection.original else selection.alternatives[index]
        val next = previous.copy(typedWord = word)
        val caret = composingStart.toLong() + next.text.length
        if (caret > Int.MAX_VALUE || next.text.length > MAX_COMPOSING_UTF16) return TypingTextResult.REJECTED
        discardUndo()
        val expected = EditorSelection(caret.toInt(), caret.toInt(), composingStart, caret.toInt())
        return applyEdit(TypingEdit.SetComposingText(next.text), expected, execute) {
            check(context?.replaceSuffix(previous.text, next.text) == true) { "Candidate context mismatch" }
            state = state.copy(composing = next, originalSelected = state.originalSelected || index == -1)
            candidateSelection = selection.copy(selectedIndex = index, manual = true)
            publish()
        }
    }

    private fun correctionId(requestId: Long, index: Int): String =
        "correction:${state.sessionId}:${state.revision}:$requestId:$index"

    fun startSession(editor: EditorContext, selectionStart: Int, selectionEnd: Int) {
        endSession()
        val enabled = editor.supportsSmartTyping &&
            selectionStart >= 0 && selectionEnd >= 0
        this.selectionStart = selectionStart
        this.selectionEnd = selectionEnd
        context = if (enabled) SessionTextContext(graphemes) else null
        state = TypingSessionState(
            sessionId = state.sessionId + 1,
            revision = state.revision + 1,
            enabled = enabled,
        )
    }

    fun typeText(text: String, execute: (TypingEdit) -> Boolean): TypingTextResult {
        if (text.isNotEmpty()) discardUndo()
        if (!state.enabled || awaitingEditorSelection || text.isEmpty()) return TypingTextResult.BYPASS
        if (text == " ") {
            if (!finishComposition(execute)) return TypingTextResult.REJECTED
            return compose(ComposingSegment(leadingBoundary = " "), text, execute)
        }
        if (text.codePoints().allMatch(::isWordCodePoint)) {
            if (plainWordUntilBoundary) return commitPlain(text, execute)
            val previous = state.composing ?: ComposingSegment()
            val next = previous.copy(typedWord = previous.typedWord + text)
            if (next.text.length > MAX_COMPOSING_UTF16) {
                if (!finishComposition(execute)) return TypingTextResult.REJECTED
                plainWordUntilBoundary = true
                return commitPlain(text, execute)
            }
            return compose(next, text, execute)
        }
        if (!finishComposition(execute)) return TypingTextResult.REJECTED
        return commitPlain(text, execute)
    }

    private fun commitPlain(text: String, execute: (TypingEdit) -> Boolean): TypingTextResult {
        val caret = minOf(selectionStart, selectionEnd) + text.length
        val expected = EditorSelection(caret, caret, -1, -1)
        return applyEdit(TypingEdit.CommitText(text), expected, execute) {
            context?.append(text)
            publish()
        }
    }

    fun deletePrevious(execute: (TypingEdit) -> Boolean): TypingTextResult {
        clearCandidates()
        if (!state.enabled || awaitingEditorSelection) return TypingTextResult.BYPASS
        state.lastAutoEdit?.let { edit ->
            discardUndo()
            if (edit.sessionId == state.sessionId && edit.revision == state.revision &&
                state.composing?.text == edit.applied && composingStart >= 0 &&
                selectionStart == selectionEnd &&
                selectionStart.toLong() == composingStart.toLong() + edit.applied.length
            ) {
                val caret = composingStart + edit.original.length
                val expected = EditorSelection(caret, caret, composingStart, caret)
                return applyEdit(TypingEdit.SetComposingText(edit.original), expected, execute) {
                    state = state.copy(
                        composing = edit.restoreComposition,
                        originalSelected = edit.restoreComposition.typedWord.isNotEmpty(),
                    )
                    context?.restore(edit.contextBefore)
                    publish()
                }
            }
        }
        val previous = state.composing ?: run {
            awaitEditorSelection(execute)
            return TypingTextResult.BYPASS
        }
        val end = graphemes.boundaries(previous.text).dropLast(1).last()
        val shortened = previous.text.substring(0, end)
        val next = if (shortened.isEmpty()) null else ComposingSegment(
            leadingBoundary = previous.leadingBoundary.take(shortened.length),
            typedWord = shortened.drop(previous.leadingBoundary.length),
        )
        val caret = composingStart + shortened.length
        val expected = EditorSelection(caret, caret, composingStart, caret)
        if (next == null) {
            // Android editors may report either a zero-width composing span or no span for the
            // empty set. Both are own acknowledgements; explicitly finish after the accepted set.
            remember(EditorSelection(caret, caret, -1, -1))
        }
        val result = applyEdit(TypingEdit.SetComposingText(shortened), expected, execute) {
            context?.removeLastGrapheme()
            state = state.copy(
                composing = next ?: ComposingSegment(),
                originalSelected = state.originalSelected && !next?.typedWord.isNullOrEmpty(),
            )
            publish()
        }
        if (result != TypingTextResult.HANDLED || next != null) return result
        return if (finishComposition(execute)) TypingTextResult.HANDLED else TypingTextResult.REJECTED
    }

    /** Finishes only Rune's owned span; invalidates revisions even when already idle. */
    fun finishComposition(execute: (TypingEdit) -> Boolean): Boolean {
        clearCandidates()
        discardUndo()
        plainWordUntilBoundary = false
        state = state.copy(revision = state.revision + 1, originalSelected = false)
        if (state.composing == null) return true
        val expected = EditorSelection(selectionStart, selectionEnd, -1, -1)
        return applyEdit(TypingEdit.FinishComposingText, expected, execute) {
            composingStart = -1
            state = state.copy(composing = null)
        } == TypingTextResult.HANDLED
    }

    /** Cursor/layer/language boundaries can explicitly discard context without editor reads. */
    fun invalidate(execute: (TypingEdit) -> Boolean): Boolean {
        val session = state.sessionId
        val finished = finishComposition(execute)
        if (state.sessionId != session) return false
        context?.clear()
        publish()
        return finished
    }

    /** Before a legacy mutation whose resulting caret is unknown, wait for its actual callback. */
    fun awaitEditorSelection(execute: (TypingEdit) -> Boolean): Boolean {
        val finished = invalidate(execute)
        awaitingEditorSelection = state.enabled && finished
        return finished
    }

    /** Converts only the pending space and preceding suffix accepted from Rune commands. */
    fun doubleSpace(executeTypingEdit: (TypingEdit) -> Boolean): TypingTextResult {
        discardUndo()
        val previous = state.composing
        val before = context?.text ?: return TypingTextResult.BYPASS
        if (!state.enabled || awaitingEditorSelection || previous?.leadingBoundary != " " ||
            previous.typedWord.isNotEmpty() || composingStart < 0 ||
            selectionStart != selectionEnd || selectionStart == Int.MAX_VALUE ||
            selectionStart.toLong() != composingStart.toLong() + previous.text.length ||
            !DoubleSpacePeriod.canConvert(before)
        ) return TypingTextResult.BYPASS

        val next = ComposingSegment(leadingBoundary = ". ")
        val caret = selectionStart + 1
        val expected = EditorSelection(caret, caret, composingStart, caret)
        return applyEdit(TypingEdit.SetComposingText(next.text), expected, executeTypingEdit) {
            check(context?.replaceSuffix(previous.text, next.text) == true)
            state = state.copy(
                composing = next,
                lastAutoEdit = UndoableTextEdit(
                    original = previous.text,
                    applied = next.text,
                    sessionId = state.sessionId,
                    revision = state.revision,
                    restoreComposition = previous,
                    contextBefore = before,
                ),
            )
            publish()
        }
    }

    /** Settings and non-text boundaries can close Undo without making an editor call. */
    fun discardUndo() {
        if (state.lastAutoEdit != null) state = state.copy(lastAutoEdit = null)
    }

    /** Returns true when the callback cannot be attributed to a recent Rune edit. */
    fun updateSelection(
        newStart: Int,
        newEnd: Int,
        candidatesStart: Int,
        candidatesEnd: Int,
        execute: (TypingEdit) -> Boolean,
    ): Boolean {
        if (!state.enabled) return false
        val incoming = EditorSelection(newStart, newEnd, candidatesStart, candidatesEnd)
        if (expectedSelections.contains(incoming)) {
            // Framework callbacks are ordered but may coalesce several edits. Retire that prefix;
            // an acknowledged historical span must never authorize a later editor replacement.
            while (expectedSelections.removeFirst() != incoming) Unit
            lastAcknowledgedSelection = incoming
            return false
        }
        if (incoming == lastAcknowledgedSelection && incoming == expectedEditorSelection) return false
        // A duplicate initial callback is harmless, but losing a live composing region is not.
        if (state.composing == null && newStart == selectionStart && newEnd == selectionEnd &&
            candidatesStart == -1 && candidatesEnd == -1
        ) return false

        val hadComposition = state.composing != null ||
            (expectedEditorSelection?.composingStart ?: -1) >= 0
        val stillOwnsSpan = state.composing != null && candidatesStart == composingStart &&
            candidatesEnd == composingStart + state.composing!!.text.length
        clearCandidates()
        context?.clear()
        expectedSelections.clear()
        expectedEditorSelection = null
        lastAcknowledgedSelection = null
        awaitingEditorSelection = false
        plainWordUntilBoundary = false
        state = state.copy(
            composing = null, lastAutoEdit = null, originalSelected = false,
            revision = state.revision + 1,
        )
        composingStart = -1
        selectionStart = newStart
        selectionEnd = newEnd
        publish()
        // Never finish an unknown replacement span and never reapply a stale Rune buffer.
        if (stillOwnsSpan) {
            val expected = EditorSelection(newStart, newEnd, -1, -1)
            applyEdit(TypingEdit.FinishComposingText, expected, execute) {}
        }
        if ((hadComposition && !stillOwnsSpan) || (!stillOwnsSpan && candidatesStart >= 0) ||
            newStart < 0 || newEnd < 0
        ) disableSession()
        return true
    }

    fun endSession() {
        clearCandidates()
        context?.clear()
        context = null
        expectedSelections.clear()
        expectedEditorSelection = null
        lastAcknowledgedSelection = null
        awaitingEditorSelection = false
        plainWordUntilBoundary = false
        selectionStart = -1
        selectionEnd = -1
        composingStart = -1
        state = TypingSessionState(sessionId = state.sessionId, revision = state.revision + 1)
    }

    private fun compose(
        next: ComposingSegment,
        addedText: String,
        execute: (TypingEdit) -> Boolean,
    ): TypingTextResult {
        val start = if (state.composing == null) minOf(selectionStart, selectionEnd) else composingStart
        val caret = start + next.text.length
        val expected = EditorSelection(caret, caret, start, caret)
        return applyEdit(TypingEdit.SetComposingText(next.text), expected, execute) {
            composingStart = start
            state = state.copy(composing = next)
            context?.append(addedText)
            publish()
        }
    }

    private fun applyEdit(
        edit: TypingEdit,
        expected: EditorSelection,
        execute: (TypingEdit) -> Boolean,
        accepted: () -> Unit,
    ): TypingTextResult = acknowledgeEdit(
        expected = expected,
        execute = { execute(edit) },
        accepted = accepted,
        rejected = {
            // Freeze any span the editor retained, including an ambiguously applied false result.
            // This never resends text. Subsequent plain commits must not replace an old Rune word.
            if (edit is TypingEdit.SetComposingText) execute(TypingEdit.FinishComposingText)
        },
    )

    private fun acknowledgeEdit(
        expected: EditorSelection,
        execute: () -> Boolean,
        accepted: () -> Unit = {},
        rejected: () -> Unit = {},
    ): TypingTextResult {
        val session = state.sessionId
        val revision = state.revision + 1
        clearCandidates()
        val expectedCandidateEpoch = candidateEpoch
        state = state.copy(revision = revision)
        remember(expected)
        editorEditDepth++
        val handled = try { execute() } finally { editorEditDepth-- }
        if (state.sessionId != session || state.revision != revision) {
            // A reentrant external/lifecycle callback already invalidated this operation.
            // Abort a multi-command action even if this individual editor call succeeded.
            return TypingTextResult.REJECTED
        }
        if (!handled || candidateEpoch != expectedCandidateEpoch) {
            // Owner policy may invalidate candidates reentrantly without changing the editor
            // session. Freeze an ambiguously applied span; never publish its old allowlist.
            disableSession()
            rejected()
            return TypingTextResult.REJECTED
        }
        selectionStart = expected.start
        selectionEnd = expected.end
        accepted()
        return TypingTextResult.HANDLED
    }

    private fun remember(selection: EditorSelection) {
        expectedEditorSelection = selection
        if (expectedSelections.peekLast() == selection) return
        if (expectedSelections.size == MAX_EXPECTED_SELECTIONS) expectedSelections.removeFirst()
        expectedSelections.addLast(selection)
    }

    private fun publish() {
        state = state.copy(contextText = context?.text.orEmpty())
    }

    private fun disableSession() {
        clearCandidates()
        context?.clear()
        context = null
        expectedSelections.clear()
        expectedEditorSelection = null
        lastAcknowledgedSelection = null
        awaitingEditorSelection = false
        plainWordUntilBoundary = false
        composingStart = -1
        state = state.copy(
            composing = null,
            lastAutoEdit = null,
            originalSelected = false,
            contextText = "",
            enabled = false,
            revision = state.revision + 1,
        )
    }

    private data class EditorSelection(val start: Int, val end: Int, val composingStart: Int, val composingEnd: Int)

    private data class CandidateStamp(val sessionId: Long, val revision: Long, val requestId: Long)

    private data class CandidateSelection(
        val original: String,
        val alternatives: List<String>,
        val requestId: Long,
        val completion: CandidateCompletion,
        val selectedIndex: Int,
        val manual: Boolean = false,
    ) {
        override fun toString(): String = "CandidateSelection(redacted)"
    }

    private companion object {
        const val MAX_COMPOSING_UTF16 = 256
        const val MAX_EXPECTED_SELECTIONS = 512

        fun isWordCodePoint(codePoint: Int): Boolean {
            val type = Character.getType(codePoint)
            return Character.isLetter(codePoint) || type == Character.NON_SPACING_MARK.toInt() ||
                type == Character.COMBINING_SPACING_MARK.toInt() ||
                type == Character.ENCLOSING_MARK.toInt()
        }
    }
}
