package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.PunctuationAction
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.UnchangedPunctuationReason

/** Only selected refusal metadata at explicit boundary actions; ordinary keys never fill the journal. */
internal object MechanicalRefusalDiagnostics {
    fun reason(action: PunctuationAction, refusal: UnchangedPunctuationReason): DiagnosticReason? {
        val boundary = when (action) {
            PunctuationAction.DoubleSpaceGesture -> true
            is PunctuationAction.Text -> action.value.length == 1 && action.value[0] in " ,.;:!?"
            else -> false
        }
        if (!boundary) return null
        return when (refusal) {
            UnchangedPunctuationReason.PROTECTED_TOKEN -> DiagnosticReason.PROTECTED_TOKEN
            UnchangedPunctuationReason.PROTECTED_PUNCTUATION -> DiagnosticReason.PROTECTED_PUNCTUATION
            UnchangedPunctuationReason.PROTECTED_LINE -> DiagnosticReason.PROTECTED_LINE
            UnchangedPunctuationReason.AMBIGUOUS_DOT -> DiagnosticReason.AMBIGUOUS_DOT
            UnchangedPunctuationReason.AMBIGUOUS_COLON -> DiagnosticReason.AMBIGUOUS_COLON
            UnchangedPunctuationReason.DOUBLE_SPACE_INELIGIBLE -> DiagnosticReason.DOUBLE_SPACE_INELIGIBLE
            UnchangedPunctuationReason.TRUNCATED_CONTEXT -> DiagnosticReason.TRUNCATED_CONTEXT
            UnchangedPunctuationReason.OWNERSHIP_MISMATCH -> DiagnosticReason.OWNERSHIP_MISMATCH
            else -> null
        }
    }
}
