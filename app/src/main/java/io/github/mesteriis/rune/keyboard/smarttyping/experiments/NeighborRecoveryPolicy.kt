package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.RecoveryQualification
import io.github.mesteriis.rune.keyboard.smarttyping.correction.RecoveryThresholds
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate

/** Separate RET2 ranking; the original participates as an explicit abstention option. */
internal object NeighborRecoveryPolicy {
    fun select(models: ExperimentModels, context: String, generation: CandidateGeneration,
        language: KeyboardLanguage, thresholds: RecoveryThresholds? = RecoveryQualification.local): GeneratedCandidate? {
        thresholds ?: return null
        val original = generation.original ?: return null
        val pool = generation.neighborRecovery
        if (language != KeyboardLanguage.RUSSIAN || generation.isValidWord || generation.protectedReason != null ||
            !pool.isComplete || pool.alternatives.isEmpty() || pool.alternatives.size > 64 ||
            !models.recoveryReady || !models.contextReady) return null
        val scores = listOf(models.recoveryOriginalScore(context, original)) +
            pool.alternatives.map { models.recoveryScore(context, original, it) }
        val winner = thresholds.winner(scores) ?: return null
        return pool.alternatives.getOrNull(winner - 1)
    }
}
