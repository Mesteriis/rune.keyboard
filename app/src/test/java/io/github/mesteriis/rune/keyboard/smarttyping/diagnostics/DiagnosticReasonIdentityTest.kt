package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal
import org.junit.Assert.*
import org.junit.Test

class DiagnosticReasonIdentityTest {
    @Test fun existingNumericReasonCodesStayAppendOnly() {
        val frozen = listOf(
            "START",
            "NONE",
            "ACCEPTED",
            "STALE",
            "INVALID",
            "MODEL_ERROR",
            "ABSTAINED",
            "INELIGIBLE",
            "PROTECTED_FORM",
            "NO_CANDIDATES",
            "NO_RANKING",
            "POLICY_REJECTED",
            "OWNERSHIP_REJECTED",
            "LIMIT",
            "AUTO_REPLACE",
            "ORIGINAL",
            "CORRECTION",
            "CONTEXTUAL",
            "EDITOR_ACCEPTED",
            "EDITOR_REJECTED",
            "SCHEDULED",
            "SUBMITTED",
            "CANCELLED",
            "RESULT_NOT_READY",
            "SERVICE_REFUSED",
            "VALID_WORD",
            "SCORING_FAILED",
            "TOOL",
            "TOUCH_UNCHANGED",
            "TOUCH_SHADOW",
            "TOUCH_REMAPPED",
            "TARGET_NOT_IN_DICTIONARY",
            "SEARCH_INCOMPLETE",
            "TARGET_NOT_FOUND",
            "TOP_K_EXCLUDED",
            "MANUAL_ONLY",
            "TOO_SHORT",
            "ORIGINAL_VALID",
            "MORPHOLOGY_UNAVAILABLE",
            "WINNER_AMBIGUOUS",
            "RIVAL_OTHER_LEMMA",
            "INSUFFICIENT_MARGIN",
            "NOT_QUALIFIED",
            "DEADLINE_MISSED",
            "STALE_REVISION",
            "MODEL_REFINED",
            "RARE_ORIGINAL",
            "RESOURCE_UNAVAILABLE",
            "SCORE_TOO_LOW",
            "ORIGINAL_PREFERRED",
            "REPLACEMENT_VETOED",
            "UNCHANGED",
            "PREVIOUS_NOT_UNAMBIGUOUS_FINITE",
            "PROPOSAL_NOT_UNAMBIGUOUS_INFINITIVE",
            "LEMMA_UNAVAILABLE",
            "DIFFERENT_LEMMA",
            "NO_INFINITIVE_CUE",
            "PREVIOUS_NOT_UNAMBIGUOUS_INSTRUMENTAL",
            "PROPOSAL_NOT_UNAMBIGUOUS_ACCUSATIVE",
            "NO_ACCUSATIVE_CUE",
            "EDITOR_SUGGESTIONS_DISABLED"
        )
        assertEquals(frozen, DiagnosticReason.entries.take(frozen.size).map { it.name })
        assertEquals(listOf("TARGET_UNKNOWN", "RIVAL_UNKNOWN", "LOCAL_SEARCH_EMPTY", "PERSONAL_VETO", "PROTECTED_WORD"),
            DiagnosticReason.entries.drop(frozen.size).map { it.name })
    }

    @Test fun admissionReasonPrefixKeepsItsOriginalOrdinals() {
        assertEquals(listOf("MORPHOLOGY_UNAVAILABLE", "ORIGINAL_VALID", "WINNER_AMBIGUOUS",
            "RIVAL_OTHER_LEMMA", "NOT_QUALIFIED"), AutomaticAdmissionRefusal.entries.take(5).map { it.name })
        assertEquals(listOf("TARGET_UNKNOWN", "RIVAL_UNKNOWN", "RESOURCE_UNAVAILABLE", "PERSONAL_VETO", "PROTECTED_WORD"),
            AutomaticAdmissionRefusal.entries.drop(5).map { it.name })
    }
}
