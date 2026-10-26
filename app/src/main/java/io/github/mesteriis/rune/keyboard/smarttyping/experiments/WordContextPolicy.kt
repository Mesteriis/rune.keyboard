package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import java.util.Locale

/** Reviewed finite contextual exception; no statistical prior or confidence claim. */
internal object WordContextPolicy {
    const val VERSION = 4
    val RULE_IDENTITY: String get() = "ru:" + rules.entries.joinToString(";") {
        "${it.key.first}|${it.key.second}|${it.value}"
    } + ":lowercase:whole-whitespace-suffix:v3"

    /** Null leaves legacy admission in charge; a null-candidate choice explicitly vetoes it. */
    fun maySupplement(primary: JointCorrectionChoice?, baselineWord: String?): Boolean =
        primary?.candidate == null && (baselineWord == null || primary != null)

    private val rules = mapOf(("нужен" to "новй") to "новый", ("встретимся" to "завтро") to "завтра",
        ("я уже" to "ддмой") to "домой")
    fun isReviewedPair(original: String, candidate: String): Boolean =
        rules.any { (key, target) -> key.second == original && target == candidate }

    fun evaluate(context: String, generation: CandidateGeneration,
        language: KeyboardLanguage): JointCorrectionEvaluation {
        fun refused(reason: JointCorrectionRefusal) = JointCorrectionEvaluation(refusal = reason)
        if (language != KeyboardLanguage.RUSSIAN || rules.keys.none { it.second == generation.original })
            return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        if (generation.isValidWord) return refused(JointCorrectionRefusal.ORIGINAL_VALID)
        if (generation.protectedReason != null) return refused(JointCorrectionRefusal.PROTECTED_FORM)
        if (!generation.jointEvaluated) return refused(JointCorrectionRefusal.RESULT_NOT_READY)
        if (!generation.jointSearch.isComplete) return refused(JointCorrectionRefusal.SEARCH_INCOMPLETE)
        // Keep the complete final token: punctuation, identifiers and mixed scripts cannot match.
        val previous = context.trimEnd().lowercase(Locale.ROOT)
            .split(Regex("[\\p{javaWhitespace}\\p{Zs}]+"))
            .filter { it.isNotEmpty() }.joinToString(" ")
        val expected = rules.entries.singleOrNull { (key, _) ->
            key.second == generation.original && (previous == key.first || previous.endsWith(" " + key.first))
        }?.value ?: return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        val pool = generation.jointSearch.alternatives
        if (pool.isEmpty()) return refused(JointCorrectionRefusal.NO_CANDIDATES)
        if (pool.size > 64 || pool.any { it.language != language || it.unitDistance !in 1..3 })
            return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        val target = pool.singleOrNull { it.text == expected && it.terminalKey == expected && it.unitDistance == 1 &&
            it.frequencyRank in 1..50_000 && it.editFeatures.editCost.isFinite() && it.editFeatures.editCost >= 0 }
            ?: return refused(JointCorrectionRefusal.NOT_QUALIFIED)
        return JointCorrectionEvaluation(choice = JointCorrectionChoice(target, wordContext = true))
    }
}
