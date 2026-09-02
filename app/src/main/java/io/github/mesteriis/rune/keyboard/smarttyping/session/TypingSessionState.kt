package io.github.mesteriis.rune.keyboard.smarttyping.session

/** No model/request/candidate state exists until a consumer is implemented. */
data class TypingSessionState(
    val sessionId: Long = 0,
    val revision: Long = 0,
    val composing: ComposingSegment? = null,
    val contextText: String = "",
    val enabled: Boolean = false,
    val lastAutoEdit: UndoableTextEdit? = null,
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
}

enum class TypingTextResult {
    HANDLED,
    BYPASS,
    /** The editor rejected a command. Do not replay the old buffer or the current input. */
    REJECTED,
}
