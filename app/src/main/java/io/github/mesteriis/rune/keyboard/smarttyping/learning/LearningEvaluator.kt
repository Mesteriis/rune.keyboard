package io.github.mesteriis.rune.keyboard.smarttyping.learning

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.LocalCorrectionPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCompletion
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate

data class LearningEvaluation(
    val heldOut: Int, val evaluated: Int, val unavailable: Int, val missingCandidates: Int,
    val baselineTop: Int, val learnedTop: Int, val identities: Int, val baselinePreserved: Int,
    val learnedPreserved: Int, val policyMatches: Int, val cancelled: Boolean,
)

/** Local top-suggestion replay only. Frozen training evidence never includes held-out expected words. */
object LearningEvaluator {
    /** Stable ties preserve the local generator order, matching the live preference ordering. */
    fun rerank(snapshot: LearningSnapshot, original: String, language: KeyboardLanguage,
        alternatives: List<GeneratedCandidate>): List<GeneratedCandidate> = alternatives.sortedByDescending {
        LearningModel.preference(snapshot, original, it.text, language)
    }

    fun evaluate(snapshot: LearningSnapshot,
        generate: (String, KeyboardLanguage) -> CandidateGeneration,
        cancelled: () -> Boolean = { false }): LearningEvaluation {
        val conflict = snapshot.evidence.groupBy { it.language to it.originalHash }.filterValues { rows ->
            rows.any { it.source == FeedbackSource.REJECTED || it.conflicted } || rows.map { it.expectedHash }.distinct().size > 1
        }.keys
        val rows = snapshot.examples.filter { it.holdout && it.source != FeedbackSource.REJECTED && (it.language to it.originalHash) !in conflict }
        var evaluated = 0; var unavailable = 0; var missing = 0; var baseline = 0; var learned = 0
        var identities = 0; var preserved = 0; var learnedPreserved = 0; var policy = 0; var stopped = false
        for (row in rows) {
            if (cancelled()) { stopped = true; break }
            val original = checkNotNull(row.original); val expected = checkNotNull(row.expected)
            val generation = generate(original, row.language)
            if (cancelled() || generation.completion == CandidateCompletion.CANCELLED) { stopped = true; break }
            if (generation.completion !in setOf(CandidateCompletion.COMPLETE, CandidateCompletion.VALID_WORD, CandidateCompletion.PROTECTED)) { unavailable++; continue }
            evaluated++
            val alternatives = generation.alternatives
            val base = alternatives.firstOrNull()?.text ?: original
            val reordered = rerank(snapshot, original, row.language, alternatives)
            val personalized = reordered.firstOrNull()?.text ?: original
            fun same(value: String) = LearningModel.normalize(value) == expected
            if (same(base)) baseline++
            if (same(personalized)) learned++
            if (expected != original && alternatives.none { same(it.text) }) missing++
            if (expected == original) { identities++; if (same(base)) preserved++; if (same(personalized)) learnedPreserved++ }
            val policyWord = LocalCorrectionPolicy.decide(generation, row.language)?.canonicalKey ?: original
            if (same(policyWord)) policy++
        }
        return LearningEvaluation(rows.size, evaluated, unavailable, missing, baseline, learned, identities, preserved, learnedPreserved, policy, stopped)
    }
}
