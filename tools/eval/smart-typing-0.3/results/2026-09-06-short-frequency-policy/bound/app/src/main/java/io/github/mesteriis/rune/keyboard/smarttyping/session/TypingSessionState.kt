package io.github.mesteriis.rune.keyboard.smarttyping.session

/** Composing snapshot; bounded candidate ownership lives in TypingSessionController. No model state. */
data class TypingSessionState(
    val sessionId: Long = 0,
    val revision: Long = 0,
    val composing: ComposingSegment? = null,
    val contextText: String = "",
    val enabled: Boolean = false,
    val lastAutoEdit: UndoableTextEdit? = null,
    val originalSelected: Boolean = false,
) {
    override fun toString(): String =
        "TypingSessionState(sessionId=$sessionId, revision=$revision, enabled=$enabled)"
}

sealed interface TypingEdit {
    data class SetComposingText(val value: String) : TypingEdit {
        override fun toString(): String = "SetComposingText(redacted)"
    }

    data class CommitText(val value: String) : TypingEdit {
        override fun toString(): String = "CommitText(redacted)"
    }

    data object FinishComposingText : TypingEdit

    data class SetComposingRegion(val start: Int, val end: Int) : TypingEdit {
        init { require(start >= 0 && end > start && end.toLong() - start <= 256) }
    }

    /** Guard is checked between editor calls; a reentrant ownership loss stops the batch. */
    class Batch(edits: List<TypingEdit>, val isCurrent: () -> Boolean) : TypingEdit {
        val edits = edits.toList()
        init {
            require(edits.size in 1..3 && edits.all {
                it is SetComposingText || it is CommitText || it is SetComposingRegion
            })
        }
        override fun toString(): String = "TypingBatch(redacted)"
    }
}

enum class TypingTextResult {
    HANDLED,
    BYPASS,
    /** The editor rejected a command. Do not replay the old buffer or the current input. */
    REJECTED,
}
