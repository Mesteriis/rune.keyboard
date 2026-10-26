package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.ContextualRanker
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.FrozenContextualAssets
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.FrozenInfinitiveRevisionAssets
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.InfinitiveRevisionPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.InfinitiveRevisionScope
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.FrozenMorphologyLexicon

internal data class InfinitiveRevisionFingerprint(val version: Int, val scope: Int, val features: Int,
    val model: String, val policy: String, val referenceModel: String, val referencePolicy: String,
    val wiki: String, val conversation: String, val grammar: String, val morphology: String,
    val minimumScore: Double, val minimumMargin: Double)

/** Additional changes to the installed result were qualified separately, not pooled with old gains. */
internal object InfinitiveRevisionQualification {
    const val MINIMUM_SCORE = 0.41741117881683354
    const val MINIMUM_MARGIN = 0.004802324582884099
    fun fingerprint() = InfinitiveRevisionFingerprint(InfinitiveRevisionPolicy.VERSION, InfinitiveRevisionScope.VERSION,
        ContextualRanker.FEATURES, FrozenInfinitiveRevisionAssets.MODEL_SHA256, FrozenInfinitiveRevisionAssets.POLICY_SHA256,
        FrozenContextualAssets.MODEL_SHA256, FrozenContextualAssets.POLICY_SHA256, FrozenContextualAssets.WIKI_SHA256,
        FrozenContextualAssets.CONVERSATION_SHA256, FrozenContextualAssets.GRAMMAR_SHA256,
        FrozenMorphologyLexicon.ASSET_SHA256, MINIMUM_SCORE, MINIMUM_MARGIN)
    fun allows(f: InfinitiveRevisionFingerprint): Boolean = f == InfinitiveRevisionFingerprint(1, 1, 146,
        "20409f7407fea7381d223351570b784adaed46357c5cd1643a28d285961b23cd",
        "67fc726f75afcc627997ec1968eefe6f3b513898958e9088e39c3f97d054e595",
        "4d7bf2a9477b588046a1187c11e206bd1ca6f73180e8abf3b21c84f024a783f0",
        "f4df5f9d5498ced72472a0c4e15f4e96627126d72faab15d50f165dbfe7fd3c6",
        "e16f45a1c97c58d900efbffab498441389d7d0823f1d9ab4512b6085daae812b",
        "2fb480d5264ab5e6120695822bf4c7b6ddc839582a3bac7dd1b83299e27f77e6",
        "2e58a4d702f415de6579434247e3256909dc7546cfd77d64f878a4695a6d3a2b",
        "c1707864a8fbc805aa98bc8307be99f2c9904eec5cc27d26a5220e001d88d28b",
        0.41741117881683354, 0.004802324582884099)
    fun enabled(language: KeyboardLanguage, length: Int): Boolean =
        ContextualQualification.enabled(language, length) && allows(fingerprint())
}
