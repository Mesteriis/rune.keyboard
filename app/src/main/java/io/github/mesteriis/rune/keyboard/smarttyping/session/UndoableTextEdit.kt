package io.github.mesteriis.rune.keyboard.smarttyping.session

/** One immediate automatic edit of a Rune-owned span; never an editor-wide undo stack. */
class UndoableTextEdit internal constructor(
    val original: String,
    val applied: String,
    val sessionId: Long,
    val revision: Long,
    val restoreComposition: ComposingSegment,
    internal val contextBefore: String,
) {
    override fun toString(): String =
        "UndoableTextEdit(sessionId=$sessionId, revision=$revision, redacted)"
}
