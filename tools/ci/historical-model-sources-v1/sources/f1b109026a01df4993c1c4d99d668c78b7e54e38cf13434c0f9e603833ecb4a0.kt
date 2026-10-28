package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration

/** One immediate automatic edit of a Rune-owned span; never an editor-wide undo stack. */
class UndoableTextEdit internal constructor(
    val original: String,
    val applied: String,
    val sessionId: Long,
    val revision: Long,
    val restoreComposition: ComposingSegment,
    internal val contextBefore: String,
    /** Non-null only when some of applied has already been committed by the boundary action. */
    internal val committedStart: Int? = null,
    internal val composingAfter: ComposingSegment? = null,
    internal val correction: UndoCorrectionCandidates? = null,
) {
    override fun toString(): String =
        "UndoableTextEdit(sessionId=$sessionId, revision=$revision, redacted)"
}

internal class UndoCorrectionCandidates(val generation: CandidateGeneration, val language: KeyboardLanguage,
    val requestId: Long) {
    override fun toString(): String = "UndoCorrectionCandidates(redacted)"
}
