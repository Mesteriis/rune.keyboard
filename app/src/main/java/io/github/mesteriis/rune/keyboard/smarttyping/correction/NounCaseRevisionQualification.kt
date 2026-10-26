package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.ContextualRanker
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.FrozenContextualAssets
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.FrozenExperimentAssets
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.FrozenInfinitiveRevisionAssets
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.FrozenNounCaseAssets
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.NounCaseRevisionPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.NounCaseRevisionScope
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.FrozenMorphologyLexicon

internal data class NounCaseRevisionFingerprint(val version: Int, val scope: Int, val features: Int,
    val model: String, val policy: String, val referenceModel: String, val referencePolicy: String,
    val referenceInfinitiveModel: String, val referenceInfinitivePolicy: String, val character: String,
    val wiki: String, val conversation: String, val grammar: String, val morphology: String,
    val minimumScore: Double, val minimumMargin: Double)

/** Incremental noun changes are measured against the complete preceding controller. */
internal object NounCaseRevisionQualification {
    const val MINIMUM_SCORE = 0.6485549857424353
    const val MINIMUM_MARGIN = 0.05342739426456289
    fun fingerprint() = NounCaseRevisionFingerprint(NounCaseRevisionPolicy.VERSION, NounCaseRevisionScope.VERSION,
        ContextualRanker.FEATURES, FrozenNounCaseAssets.MODEL_SHA256, FrozenNounCaseAssets.POLICY_SHA256,
        FrozenContextualAssets.MODEL_SHA256, FrozenContextualAssets.POLICY_SHA256,
        FrozenInfinitiveRevisionAssets.MODEL_SHA256, FrozenInfinitiveRevisionAssets.POLICY_SHA256,
        FrozenExperimentAssets.RANKING_CONTEXT_SHA256, FrozenContextualAssets.WIKI_SHA256,
        FrozenContextualAssets.CONVERSATION_SHA256, FrozenContextualAssets.GRAMMAR_SHA256,
        FrozenMorphologyLexicon.ASSET_SHA256, MINIMUM_SCORE, MINIMUM_MARGIN)
    fun allows(f: NounCaseRevisionFingerprint): Boolean = f == NounCaseRevisionFingerprint(1, 1, 146,
        "c848b1cac54515382287325343a863e4e8713ca7a628e3336806b74ccd64de42",
        "ed6589ff9a16a7c7375258def2b1c9fc214afc1ca9a20a57e4c6d9448a244d1d",
        "4d7bf2a9477b588046a1187c11e206bd1ca6f73180e8abf3b21c84f024a783f0",
        "f4df5f9d5498ced72472a0c4e15f4e96627126d72faab15d50f165dbfe7fd3c6",
        "20409f7407fea7381d223351570b784adaed46357c5cd1643a28d285961b23cd",
        "67fc726f75afcc627997ec1968eefe6f3b513898958e9088e39c3f97d054e595",
        "accd46a39e111999994d95c148d0cff6f9892ab8ad5176ffd4c64aa800372a50",
        "e16f45a1c97c58d900efbffab498441389d7d0823f1d9ab4512b6085daae812b",
        "2fb480d5264ab5e6120695822bf4c7b6ddc839582a3bac7dd1b83299e27f77e6",
        "2e58a4d702f415de6579434247e3256909dc7546cfd77d64f878a4695a6d3a2b",
        "c1707864a8fbc805aa98bc8307be99f2c9904eec5cc27d26a5220e001d88d28b",
        0.6485549857424353, 0.05342739426456289)
    fun enabled(language: KeyboardLanguage, length: Int): Boolean =
        InfinitiveRevisionQualification.enabled(language, length) && allows(fingerprint())
}
