package io.github.mesteriis.rune.keyboard.smarttyping.correction

/** Independent release gates. Missing evidence never inherits a baseline qualification. */
internal object RecoveryQualification {
    // Populated only from a frozen calibration plus a passing independent product holdout.
    const val LOCAL_QUALIFIED = true // Frozen public holdout, ambiguous controls and device gates passed.
    const val RANKER_BYTES = 22036
    const val RANKER_SHA256 = "15117d34f9c3257143b1b761482b9adc22340fe23f72b15ffeddce7acf106e20"
    const val POLICY_SHA256 = "9014d85e15e530fcdf112561fda4ddd456f9b5ea3c869414e44cfed5547e3cce"
    fun fingerprint(): RecoveryQualificationFingerprint {
        val current = QualificationArtifacts.compactPublic()
        return RecoveryQualificationFingerprint(
            io.github.mesteriis.rune.keyboard.smarttyping.lexicon.NeighborRecoverySearch.VERSION,
            RANKER_SHA256, POLICY_SHA256, local, current.contextSha256, current.morphologySha256,
            current.rareWordsSha256, current.lexicons[io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage.RUSSIAN].orEmpty())
    }
    fun allows(fingerprint: RecoveryQualificationFingerprint): Boolean = LOCAL_QUALIFIED &&
        fingerprint == RecoveryQualificationFingerprint(1,
            "15117d34f9c3257143b1b761482b9adc22340fe23f72b15ffeddce7acf106e20",
            "9014d85e15e530fcdf112561fda4ddd456f9b5ea3c869414e44cfed5547e3cce",
            RecoveryThresholds(0.5337506772948372, 0.317066726012393),
            "accd46a39e111999994d95c148d0cff6f9892ab8ad5176ffd4c64aa800372a50",
            "c1707864a8fbc805aa98bc8307be99f2c9904eec5cc27d26a5220e001d88d28b",
            "434b462d4edb0165946568dfdf2a6729ff8b2590fead1fe815d3912817837b6e",
            "f08c2cccb75aeb1b7c80e0a06b5fc6befa8ed46e344004ed7bb1f63fc62ef632")
    val local: RecoveryThresholds? = RecoveryThresholds(0.5337506772948372, 0.317066726012393)
    const val MODEL_QUALIFIED = false // Holdout: 5 improvements, 6 correct-to-wrong regressions.
    val refinement: RecoveryThresholds? = RecoveryThresholds(-7.6423018735874235, 2.1959238658551015)
}

internal data class RecoveryThresholds(val minimumScore: Double, val minimumMargin: Double) {
    init { require(minimumScore.isFinite() && minimumMargin.isFinite() && minimumMargin > 0) }

    fun winner(scores: List<Double>): Int? {
        if (scores.size !in 2..65 || scores.any { !it.isFinite() }) return null
        val order = scores.indices.sortedWith(compareByDescending<Int> { scores[it] }.thenBy { it })
        val winner = order[0]
        return winner.takeIf { scores[it] >= minimumScore && scores[it] - scores[order[1]] >= minimumMargin }
    }
}

internal data class RecoveryQualificationFingerprint(val searchVersion: Int, val rankerSha256: String,
    val policySha256: String, val thresholds: RecoveryThresholds?, val contextSha256: String, val morphologySha256: String,
    val rareWordsSha256: String, val lexiconSha256: String)
