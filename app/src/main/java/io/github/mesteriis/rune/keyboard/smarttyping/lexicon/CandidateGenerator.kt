package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import io.github.mesteriis.rune.keyboard.smarttyping.correction.EditCostProfile
import io.github.mesteriis.rune.keyboard.smarttyping.correction.EditFeatures
import io.github.mesteriis.rune.keyboard.smarttyping.correction.ProtectedTokenPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.correction.ProtectedTokenReason
import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode
import io.github.mesteriis.rune.keyboard.smarttyping.correction.WeightedDamerauLevenshtein

enum class CandidateCompletion {
    COMPLETE, PROTECTED, VALID_WORD, STATES_EXHAUSTED, VERIFIED_EXHAUSTED,
    CANCELLED, UNAVAILABLE, READER_FAILURE,
}

data class GeneratedCandidate(
    val text: String,
    /** Folded display after case preservation; used for duplicate and original suppression. */
    val canonicalKey: String,
    /** Canonical lexicon terminal before display-case expansion; final deterministic identity tie. */
    val terminalKey: String,
    val language: KeyboardLanguage,
    val isFallback: Boolean,
    val languagePrior: Int,
    val frequencyRank: Int,
    val unitDistance: Int,
    val editFeatures: EditFeatures,
    val lengthDifference: Int,
    val casePattern: CasePattern,
) {
    override fun toString(): String = "GeneratedCandidate(redacted)"
}

data class CandidateGeneration(
    /** Caller owns this output snapshot; cancelled requests return no text references. */
    val original: String?,
    val alternatives: List<GeneratedCandidate>,
    val completion: CandidateCompletion,
    val isValidWord: Boolean,
    val protectedReason: ProtectedTokenReason?,
    val inspectedStates: Int,
    val verifiedTerminals: Int,
) {
    val isComplete: Boolean
        get() = completion == CandidateCompletion.COMPLETE

    /** False clears only a retrieval veto. It NEVER authorizes AutoReplace or supplies confidence. */
    val prohibitsAutoReplace: Boolean
        get() = completion != CandidateCompletion.COMPLETE || isValidWord || protectedReason != null

    override fun toString(): String =
        "CandidateGeneration(completion=$completion, candidateCount=${alternatives.size}, redacted)"
}

/**
 * Worker-confined suggestion foundation, with no editor, model, logging or persistence dependency.
 * Packed selection requires an exact global requested-width certificate; generic readers exhaust the
 * neighborhood before display-case/dedup/quota/top-N selection. INITIAL
 * edit cost, descending route prior, frequency rank, Unicode scalar lexical order, then language
 * ordinal and original terminal identity define a deterministic proposal comparator, NOT a
 * calibrated CandidateRanker. The last tie resolves equal-ranked display expansion collisions.
 * Repetition and length features are retained without inventing further ranking coefficients.
 */
class CandidateGenerator(
    private val lexicon: CandidateLexicon,
    private val maximumAlternatives: Int = MAX_ALTERNATIVES,
) {
    init { require(maximumAlternatives in 1..MAX_ALTERNATIVES) { "CANDIDATE_WIDTH" } }
    private val unit = WeightedDamerauLevenshtein(EditCostProfile.UNIT)
    private val weighted = WeightedDamerauLevenshtein()
    private val candidates = arrayOfNulls<GeneratedCandidate>(CandidateSearchControl.MAX_VERIFIED)

    fun generate(
        token: String,
        activeLanguage: KeyboardLanguage,
        cancellation: CandidateCancellation = CandidateCancellation { false },
    ): CandidateGeneration {
        val control = CandidateSearchControl(cancellation)
        var candidateCount = 0
        var validWord = false
        var protectedReason: ProtectedTokenReason? = null
        fun result(completion: CandidateCompletion, alternatives: List<GeneratedCandidate> = emptyList()) =
            CandidateGeneration(
                original = if (completion == CandidateCompletion.CANCELLED) null else token,
                alternatives = alternatives,
                completion = completion,
                isValidWord = validWord,
                protectedReason = protectedReason,
                inspectedStates = control.inspectedStates,
                verifiedTerminals = control.verifiedTerminals,
            )
        try {
            if (!control.checkpoint()) return result(control.stop!!)
            protectedReason = ProtectedTokenPolicy.reason(token)
            if (protectedReason != null) return result(CandidateCompletion.PROTECTED)
            val key = TokenUnicode.folded(token)
            val pattern = CasePattern.analyze(token)
            val route = LanguageRouter.route(token, activeLanguage)
            val primary = route.primary ?: return result(CandidateCompletion.PROTECTED)
            val languages = listOfNotNull(primary, route.fallback)
            for (language in languages) {
                val membership = lexicon.exact(language, key, control)
                if (!control.checkpoint()) return result(control.stop!!)
                when (membership) {
                    ExactMembership.PRESENT -> {
                        validWord = true
                        return result(CandidateCompletion.VALID_WORD)
                    }
                    ExactMembership.UNAVAILABLE -> return result(CandidateCompletion.UNAVAILABLE)
                    ExactMembership.ABSENT -> Unit
                }
            }
            val length = key.codePointCount(0, key.length)
            val radius = if (length < 5) 1 else 2
            val top = lexicon.selectTop(key, route, pattern, control, maximumAlternatives)
            if (top != null) {
                if (!control.cancellationCheckpoint()) return result(CandidateCompletion.CANCELLED)
                check(top.maximumAlternatives == maximumAlternatives) { "TOP_SELECTION_WIDTH" }
                check(control.stop == null || control.stop == top.completion) { "TOP_SELECTION_STOP" }
                check(top.alternatives.size <= control.verifiedTerminals) { "TOP_SELECTION_VERIFICATION" }
                return result(top.completion, top.alternatives)
            }
            var completion = CandidateCompletion.COMPLETE
            for (language in languages) {
                val fallback = language != primary
                val status = lexicon.scan(language, key, radius, control) { terminal, frequency ->
                    if (!control.verifyTerminal()) return@scan false
                    // Fail closed on malformed reader output; never normalize or silently truncate it.
                    if (terminal.isEmpty() || !TokenUnicode.bounded(terminal) || frequency <= 0 ||
                        TokenUnicode.folded(terminal) != terminal || terminal == key) {
                        control.rejectReader()
                        return@scan false
                    }
                    // Reader supplies full unit-radius enumeration; independent verification bounds
                    // feature work to 64 and catches out-of-radius emission.
                    val unitDistance = unit.features(key, terminal, language).editCost.toInt()
                    if (!control.checkpoint()) return@scan false
                    if (unitDistance !in 1..radius) {
                        control.rejectReader()
                        return@scan false
                    }
                    val features = weighted.features(key, terminal, language)
                    if (!control.checkpoint()) return@scan false
                    val display = pattern.preserve(terminal) ?: return@scan true
                    val displayKey = TokenUnicode.folded(display)
                    if (displayKey == key) return@scan true
                    candidates[candidateCount++] = GeneratedCandidate(
                        display, displayKey, terminal, language, fallback,
                        if (fallback) route.fallbackPrior else route.primaryPrior,
                        frequency, unitDistance, features,
                        kotlin.math.abs(length - terminal.codePointCount(0, terminal.length)), pattern,
                    )
                    true
                }
                if (!control.checkpoint()) {
                    when (control.stop) {
                        CandidateCompletion.STATES_EXHAUSTED, CandidateCompletion.VERIFIED_EXHAUSTED -> {
                            completion = control.stop!!
                            break
                        }
                        else -> return result(control.stop!!)
                    }
                }
                if (status != LexiconScanStatus.COMPLETE) return result(CandidateCompletion.UNAVAILABLE)
            }
            // Budget exhaustion stops retrieval, not bounded selection of verified partial suggestions.
            // Their status remains incomplete: no claim that an unseen candidate cannot rank better.
            if (!control.cancellationCheckpoint()) return result(CandidateCompletion.CANCELLED)
            // Bounded <=64 object collection. No per-index-state candidate objects or rank pruning.
            val sorted = (0 until candidateCount).map { candidates[it]!! }.sortedWith(COMPARATOR)
            val seen = HashSet<String>()
            val selected = ArrayList<GeneratedCandidate>(maximumAlternatives)
            var fallbackCount = 0
            for (candidate in sorted) {
                if (!control.cancellationCheckpoint()) return result(CandidateCompletion.CANCELLED)
                // Dedup selects the best representation before applying its fallback quota.
                if (!seen.add(candidate.canonicalKey)) continue
                if (candidate.isFallback && fallbackCount == route.fallbackCandidateLimit) continue
                selected.add(candidate)
                if (candidate.isFallback) fallbackCount++
                if (selected.size == maximumAlternatives) break
            }
            if (!control.cancellationCheckpoint()) return result(CandidateCompletion.CANCELLED)
            return result(completion, selected.toList())
        } catch (_: InterruptedException) {
            // Preserve the worker's interrupt signal and treat interrupted reader work as cancellation.
            Thread.currentThread().interrupt()
            return result(CandidateCompletion.CANCELLED)
        } catch (_: Exception) {
            // Reader errors must not escape into logs with a query-bearing message.
            // Deliberately exclude fatal Error types; finally still releases owned scratch.
            return result(if (control.cancellationCheckpoint()) CandidateCompletion.READER_FAILURE else CandidateCompletion.CANCELLED)
        } finally {
            candidates.fill(null)
            // Both distance engines clear their primitive arrays in their own finally blocks.
            // Query Strings are method locals: this frame must return before a worker waits idle.
        }
    }

    companion object {
        const val MAX_ALTERNATIVES = 7

        internal val COMPARATOR = Comparator<GeneratedCandidate> { left, right ->
            var order = left.editFeatures.editCost.compareTo(right.editFeatures.editCost)
            if (order == 0) order = right.languagePrior.compareTo(left.languagePrior)
            if (order == 0) order = left.frequencyRank.compareTo(right.frequencyRank)
            if (order == 0) order = compareScalars(left.canonicalKey, right.canonicalKey)
            if (order == 0) order = left.language.ordinal.compareTo(right.language.ordinal)
            if (order == 0) order = compareScalars(left.terminalKey, right.terminalKey)
            order
        }

        private fun compareScalars(left: String, right: String): Int {
            var i = 0
            var j = 0
            while (i < left.length && j < right.length) {
                val a = left.codePointAt(i)
                val b = right.codePointAt(j)
                if (a != b) return a.compareTo(b)
                i += Character.charCount(a)
                j += Character.charCount(b)
            }
            return (left.length - i).compareTo(right.length - j)
        }
    }
}
