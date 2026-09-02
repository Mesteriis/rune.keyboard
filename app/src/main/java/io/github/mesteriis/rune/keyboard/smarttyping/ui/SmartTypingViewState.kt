package io.github.mesteriis.rune.keyboard.smarttyping.ui

import java.util.Collections

/**
 * The owner has already applied editor/privacy/settings policy and selected the visible items.
 * An enabled empty strip retains its height between words; HIDDEN retains no candidate text.
 */
class SmartTypingViewState(
    val enabled: Boolean,
    candidates: List<CandidateUiItem> = emptyList(),
    val selectedCandidateId: String? = candidates.firstOrNull()?.id,
) {
    val candidates: List<CandidateUiItem>

    init {
        require(candidates.size <= MAX_VISIBLE_CANDIDATES) { "Too many visible candidates" }
        val snapshot = candidates.toList()
        require(enabled || snapshot.isEmpty()) { "Hidden state must not retain candidate text" }
        require(snapshot.map { it.id }.distinct().size == snapshot.size) { "Duplicate candidate ID" }
        require(snapshot.isEmpty() || snapshot.count { it is CandidateUiItem.Original } == 1) {
            "Visible candidates must contain exactly one original"
        }
        require(
            if (snapshot.isEmpty()) selectedCandidateId == null
            else snapshot.any { it.id == selectedCandidateId },
        ) { "Selection must refer to a visible candidate" }
        this.candidates = Collections.unmodifiableList(snapshot)
    }

    override fun toString(): String =
        "SmartTypingViewState(enabled=$enabled, candidateCount=${candidates.size})"

    companion object {
        const val MAX_VISIBLE_CANDIDATES = 3
        val HIDDEN = SmartTypingViewState(enabled = false)
        val EMPTY = SmartTypingViewState(enabled = true)
    }
}
