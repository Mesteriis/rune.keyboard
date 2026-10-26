package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringInput

/** One Rune-owned previous word. Request identity is independent of current-word candidate stamps. */
internal class PreviousWordRefinementTicket(
    val id: Long,
    val root: UndoableTextEdit,
    var appliedWord: String,
    val spaceStartedAtNanos: Long,
    var revision: Long,
    val qualityRevision: Long?,
) {
    var request: ScoringInput? = null
    var completed = false
    var nextWordStarted = false
    val language get() = root.correction!!.language
    val generation get() = root.correction!!.generation
    val start get() = root.committedStart!!
    val previous get() = root.restoreComposition.copy(typedWord = appliedWord)
    fun withinWindow(now: Long) = now - spaceStartedAtNanos in 0 until WINDOW_NANOS
    override fun toString(): String = "PreviousWordRefinementTicket(id=$id, redacted)"

    companion object { const val WINDOW_NANOS = 1_000_000_000L }
}
