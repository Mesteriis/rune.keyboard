package io.github.mesteriis.rune.keyboard.smarttyping.learning

import android.content.res.AssetManager
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.AndroidCanonicalCaseLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.AndroidPackedLexiconLoader
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCancellation
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGenerator
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.FrozenPackedLexicons
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.PackedCandidateLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.PackedLexiconLoad

/** APK assets only, loaded and queried on the evaluation worker; no model or private archive. */
object AndroidLearningEvaluation {
    fun run(assets: AssetManager, snapshot: LearningSnapshot, cancelled: () -> Boolean): LearningEvaluation {
        return runWithGenerator(assets, snapshot, cancelled) { generate ->
            LearningEvaluator.evaluate(snapshot, generate, cancelled)
        }
    }

    fun runRollback(assets: AssetManager, snapshot: LearningSnapshot,
        cancelled: () -> Boolean): LearningEvaluation? {
        if (snapshot.rollbackPolicy == null) return null
        return runWithGenerator(assets, snapshot, cancelled) { generate ->
            LearningEvaluator.evaluateRollback(snapshot, generate, cancelled)
        }
    }

    private fun <T> runWithGenerator(assets: AssetManager, snapshot: LearningSnapshot,
        cancelled: () -> Boolean,
        evaluate: ((String, KeyboardLanguage) -> CandidateGeneration) -> T): T {
        if (snapshot.examples.none { it.holdout }) return evaluate { _, _ -> error("NO_EXAMPLES") }
        val handles = listOf(FrozenPackedLexicons.ENGLISH, FrozenPackedLexicons.RUSSIAN, FrozenPackedLexicons.SPANISH).mapNotNull {
            if (cancelled()) return@mapNotNull null
            (AndroidPackedLexiconLoader.load(assets, it) as? PackedLexiconLoad.Ready)?.lexicon
        }
        val generator = CandidateGenerator(PackedCandidateLexicon(handles), canonicalCaseLexicon = AndroidCanonicalCaseLexicon(assets))
        return evaluate { word, language -> generator.generate(word, language, CandidateCancellation(cancelled)) }
    }
}
