package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.PunctuationAction
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.UnchangedPunctuationReason
import org.junit.Assert.*
import org.junit.Test

class MechanicalRefusalDiagnosticsTest {
    @Test fun onlySelectedReasonsAtSingleBoundaryActionsAreEligible() {
        val expected = mapOf(
            UnchangedPunctuationReason.PROTECTED_TOKEN to DiagnosticReason.PROTECTED_TOKEN,
            UnchangedPunctuationReason.PROTECTED_PUNCTUATION to DiagnosticReason.PROTECTED_PUNCTUATION,
            UnchangedPunctuationReason.PROTECTED_LINE to DiagnosticReason.PROTECTED_LINE,
            UnchangedPunctuationReason.AMBIGUOUS_DOT to DiagnosticReason.AMBIGUOUS_DOT,
            UnchangedPunctuationReason.AMBIGUOUS_COLON to DiagnosticReason.AMBIGUOUS_COLON,
            UnchangedPunctuationReason.DOUBLE_SPACE_INELIGIBLE to DiagnosticReason.DOUBLE_SPACE_INELIGIBLE,
            UnchangedPunctuationReason.TRUNCATED_CONTEXT to DiagnosticReason.TRUNCATED_CONTEXT,
            UnchangedPunctuationReason.OWNERSHIP_MISMATCH to DiagnosticReason.OWNERSHIP_MISMATCH,
        )
        val boundaries = " ,.;:!?".map { PunctuationAction.Text(it.toString()) } + PunctuationAction.DoubleSpaceGesture
        for (action in boundaries) for (refusal in UnchangedPunctuationReason.entries) {
            assertEquals(expected[refusal], MechanicalRefusalDiagnostics.reason(action, refusal))
        }
    }

    @Test fun lettersPastedFragmentsAndNonTextCommandsNeverEmitRefusalMetadata() {
        val actions = listOf("a", "я", "ñ", "word", "word.", ", ", "  ", "\n", "\t", "", "😀")
            .map { PunctuationAction.Text(it) } + listOf(PunctuationAction.Send, PunctuationAction.Other)
        for (action in actions) for (refusal in UnchangedPunctuationReason.entries) {
            assertNull(MechanicalRefusalDiagnostics.reason(action, refusal))
        }
    }
}
