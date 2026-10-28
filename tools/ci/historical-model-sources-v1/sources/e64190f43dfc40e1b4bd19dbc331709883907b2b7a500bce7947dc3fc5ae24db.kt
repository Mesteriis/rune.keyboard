package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern

/**
 * Synchronous, read-only contract for a validated index. Implementations must not retain query,
 * control or visitor after return; their query/path/DP scratch must be cleared in finally.
 * Keys are nonempty NFC / ROOT lowercase, at most 32 Unicode scalar values. Ranks are positive;
 * Int.MAX_VALUE means unranked. No text-bearing errors or diagnostics belong in this API.
 *
 * Before inspecting each index edge/record (including pruned ones), call inspectState(). Exact
 * and scan use the SAME control. Check checkpoint() between DP rows and before returning.
 * A false callback/check ends work immediately. Root/header reads do not consume a state.
 *
 * scan emits every nonoriginal terminal within unrestricted UNIT edit radius, once per language.
 * No rank-dependent pruning or local top-N is allowed. COMPLETE certifies full enumeration;
 * stopping for any other reader reason returns UNAVAILABLE. Reader correctness, state accounting
 * and completeness require separate reader tests; the generator cannot detect an omitted branch.
 */
interface CandidateLexicon {
    fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl): ExactMembership

    fun scan(
        language: KeyboardLanguage,
        key: String,
        unitRadius: Int,
        control: CandidateSearchControl,
        visitor: CandidateVisitor,
    ): LexiconScanStatus

    /**
     * Optional exact global requested-width selection after shared membership/protection checks.
     * Null selects the exhaustive scan path. COMPLETE requires a full-comparator certificate,
     * including display-case dedup BEFORE fallback quota. The SAME control charges all routes;
     * budget exhaustion retains its veto. Never reinterpret scan COMPLETE as a top-N result.
     */
    fun selectTop(key: String, route: LanguageRoute, pattern: CasePattern,
        control: CandidateSearchControl, maximumAlternatives: Int): TopCandidateSelection? = null
}

enum class ExactMembership { PRESENT, ABSENT, UNAVAILABLE }
enum class LexiconScanStatus { COMPLETE, UNAVAILABLE }

fun interface CandidateVisitor {
    /** False means stop. The generator charges verification before evaluating this terminal. */
    fun visit(canonicalKey: String, frequencyRank: Int): Boolean
}

fun interface CandidateCancellation {
    /** Thread-safe, nonthrowing flag read; callers must not capture query text here. */
    fun isCancelled(): Boolean
}

/** Request-local numeric budget; contains no query or candidate payload. */
class CandidateSearchControl internal constructor(private val cancellation: CandidateCancellation) {
    var inspectedStates: Int = 0
        private set
    var verifiedTerminals: Int = 0
        private set
    internal var stop: CandidateCompletion? = null
        private set

    fun checkpoint(): Boolean {
        return cancellationCheckpoint() && stop == null
    }

    /** Selection may retain verified suggestions after exhaustion, but must still observe cancellation. */
    internal fun cancellationCheckpoint(): Boolean {
        // Cancellation overrides exhaustion so a cancelled request never returns text for publication.
        if (Thread.currentThread().isInterrupted || cancellation.isCancelled()) stop = CandidateCompletion.CANCELLED
        return stop != CandidateCompletion.CANCELLED
    }

    fun inspectState(): Boolean {
        if (!checkpoint()) return false
        if (inspectedStates == MAX_STATES) {
            stop = CandidateCompletion.STATES_EXHAUSTED
            return false
        }
        inspectedStates++
        return true
    }

    internal fun verifyTerminal(): Boolean {
        if (!checkpoint()) return false
        if (verifiedTerminals == MAX_VERIFIED) {
            stop = CandidateCompletion.VERIFIED_EXHAUSTED
            return false
        }
        verifiedTerminals++
        return true
    }

    internal fun rejectReader() {
        if (checkpoint()) stop = CandidateCompletion.READER_FAILURE
    }

    companion object {
        const val MAX_STATES = 8_192
        const val MAX_VERIFIED = 64
    }
}
