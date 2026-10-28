package io.github.mesteriis.rune.keyboard.smarttyping.punctuation

import io.github.mesteriis.rune.keyboard.ime.model.EditorMode
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy

/**
 * Only text accepted from Rune commands, ending at the current caret. [composingText]
 * is the exact live owned span, not an arbitrary suffix the caller wishes to edit.
 * Null means no existing composing span; a plan may then only insert at the caret.
 * Caller must verify collapsed selection and session/revision again before execution.
 */
class OwnedPunctuationSuffix(
    val text: String,
    val composingText: String?,
    val startsAtTokenBoundary: Boolean,
    val sessionId: Long,
    val revision: Long,
) {
    override fun toString() = "OwnedPunctuationSuffix(sessionId=$sessionId, revision=$revision, redacted)"
}

data class MechanicalPunctuationPolicy(
    val inputPolicy: InputPolicy,
    val mode: EditorMode,
    val requiresRawKeyEvents: Boolean,
    val enabled: Boolean,
    val doubleSpaceEnabled: Boolean,
)

sealed interface PunctuationAction {
    class Text(val value: String) : PunctuationAction {
        override fun toString() = "Text(redacted)"
    }
    /** The existing reducer recognized the timed gesture; the planner does not infer timing. */
    data object DoubleSpaceGesture : PunctuationAction
    data object Send : PunctuationAction
    /** Enter, selection/lifecycle changes, Backspace and other non-text commands. */
    data object Other : PunctuationAction
}

enum class MechanicalEditKind { DOUBLE_SPACE_PERIOD, SPACE_BEFORE, SPACE_AFTER, REPEATED_SPACE, DUPLICATE_PUNCTUATION, SENTENCE_CASE }

enum class UnchangedPunctuationReason {
    INPUT_POLICY, NON_TEXT_MODE, RAW_EDITOR, DISABLED, SEND, NON_TEXT_ACTION,
    INVALID_BOUNDS, OWNERSHIP_MISMATCH, OUTSIDE_COMPOSING_SPAN, TRUNCATED_CONTEXT,
    PROTECTED_TOKEN, PROTECTED_PUNCTUATION, AMBIGUOUS_DOT, AMBIGUOUS_COLON,
    DOUBLE_SPACE_INELIGIBLE, UNSUPPORTED_ACTION, NO_CHANGE,
}

sealed interface MechanicalPunctuationPlan {
    data class Unchanged(val reason: UnchangedPunctuationReason) : MechanicalPunctuationPlan

    /**
     * One setComposingText transaction, consuming the incoming text/gesture exactly once.
     * Never commit [replacementComposing] after executing the raw action separately.
     * [undoOriginal] feeds the existing single UndoableTextEdit; it is not another undo store.
     */
    class Replace(
        val sessionId: Long,
        val revision: Long,
        val expectedComposing: String?,
        val replacementComposing: String,
        val undoOriginal: String,
        val kind: MechanicalEditKind,
        /** Apply existing caps state to only the new action text starting at this UTF-16 offset. */
        val sentenceCapsForNewTextAt: Int?,
    ) : MechanicalPunctuationPlan {
        /** A gesture primes the next key; a non-null offset applies only to this action's new text. */
        val requestsSentenceCaps: Boolean
            get() = kind == MechanicalEditKind.DOUBLE_SPACE_PERIOD || sentenceCapsForNewTextAt != null

        override fun toString() = "Replace(sessionId=$sessionId, revision=$revision, kind=$kind, redacted)"
    }
}
