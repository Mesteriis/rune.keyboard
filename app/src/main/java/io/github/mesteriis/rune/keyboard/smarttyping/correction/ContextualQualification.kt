package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.ContextualCorrectionPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.ContextualRanker
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.FrozenContextualAssets

internal data class ContextualFingerprint(val version: Int, val features: Int, val model: String,
    val policy: String, val wiki: String, val conversation: String, val grammar: String,
    val minimumScore: Double, val minimumMargin: Double)

/** Separate 95% candidate policy; source certificates remain independently required. */
internal object ContextualQualification {
    const val MINIMUM_SCORE = -0.10238100540254857
    const val MINIMUM_MARGIN = 0.038424043936311734
    fun fingerprint() = ContextualFingerprint(ContextualCorrectionPolicy.VERSION, ContextualRanker.FEATURES,
        FrozenContextualAssets.MODEL_SHA256, FrozenContextualAssets.POLICY_SHA256, FrozenContextualAssets.WIKI_SHA256,
        FrozenContextualAssets.CONVERSATION_SHA256, FrozenContextualAssets.GRAMMAR_SHA256, MINIMUM_SCORE, MINIMUM_MARGIN)
    fun allows(f: ContextualFingerprint): Boolean = f == ContextualFingerprint(1, 146,
        "4d7bf2a9477b588046a1187c11e206bd1ca6f73180e8abf3b21c84f024a783f0",
        "f4df5f9d5498ced72472a0c4e15f4e96627126d72faab15d50f165dbfe7fd3c6",
        "e16f45a1c97c58d900efbffab498441389d7d0823f1d9ab4512b6085daae812b",
        "2fb480d5264ab5e6120695822bf4c7b6ddc839582a3bac7dd1b83299e27f77e6",
        "2e58a4d702f415de6579434247e3256909dc7546cfd77d64f878a4695a6d3a2b",
        -0.10238100540254857, 0.038424043936311734)
    fun enabled(language: KeyboardLanguage, length: Int): Boolean =
        JointQualification.enabled(language, length) && allows(fingerprint())
}
