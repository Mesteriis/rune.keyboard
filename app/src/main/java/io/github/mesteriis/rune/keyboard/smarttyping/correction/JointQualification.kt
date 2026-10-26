package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionThresholds
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.JointCorrectionPolicy

/** Short and long sources have independent product evidence; no inherited admission. */
internal object JointQualification {
    // Separate frozen evaluation for known words whose morphology has no unique lemma.
    fun uniqueAmbiguousWinnerEnabled(language: KeyboardLanguage, length: Int): Boolean =
        length in 5..32 && enabled(language, length)
    const val RANKER_BYTES = 22036
    const val RANKER_SHA256 = "a917f63010b23cbb3ff06f8069460398b366bce389f70d61f77ad5c156783dcb"
    const val POLICY_SHA256 = "36fbdfd7c7c96e580b3d68b7fd6abaec58c0a62aa8302351606acbff15c5f722"
    const val LONG_POLICY_SHA256 = "ba3d9f20cdf7d5dabe8ff306df59fc76016dd6c1d0a2bdb6019c6164442dd82c"
    private val short = RecoveryThresholds(-0.1159913845255558, 0.24699818316768785)
    val thresholds = JointCorrectionThresholds(short, RecoveryThresholds(0.5526915271546093, 0.4475581943461431),
        RecoveryThresholds(0.47757815371058715, 0.10336967059629464))
    fun fingerprint(): RecoveryQualificationFingerprint {
        val current = QualificationArtifacts.compactPublic()
        return RecoveryQualificationFingerprint(JointCorrectionPolicy.VERSION, RANKER_SHA256, POLICY_SHA256,
            short, current.contextSha256, current.morphologySha256, current.rareWordsSha256,
            current.lexicons[KeyboardLanguage.RUSSIAN].orEmpty())
    }
    fun allows(fingerprint: RecoveryQualificationFingerprint): Boolean = fingerprint ==
        RecoveryQualificationFingerprint(1,
            "a917f63010b23cbb3ff06f8069460398b366bce389f70d61f77ad5c156783dcb",
            "36fbdfd7c7c96e580b3d68b7fd6abaec58c0a62aa8302351606acbff15c5f722",
            RecoveryThresholds(-0.1159913845255558, 0.24699818316768785),
            "accd46a39e111999994d95c148d0cff6f9892ab8ad5176ffd4c64aa800372a50",
            "c1707864a8fbc805aa98bc8307be99f2c9904eec5cc27d26a5220e001d88d28b",
            "434b462d4edb0165946568dfdf2a6729ff8b2590fead1fe815d3912817837b6e",
            "f08c2cccb75aeb1b7c80e0a06b5fc6befa8ed46e344004ed7bb1f63fc62ef632")
    fun longFingerprint(): RecoveryQualificationFingerprint = fingerprint().copy(
        policySha256 = LONG_POLICY_SHA256, thresholds = thresholds.long)
    fun allowsLong(fingerprint: RecoveryQualificationFingerprint, retention: RecoveryThresholds): Boolean =
        fingerprint == RecoveryQualificationFingerprint(1,
            "a917f63010b23cbb3ff06f8069460398b366bce389f70d61f77ad5c156783dcb",
            "ba3d9f20cdf7d5dabe8ff306df59fc76016dd6c1d0a2bdb6019c6164442dd82c",
            RecoveryThresholds(0.5526915271546093, 0.4475581943461431),
            "accd46a39e111999994d95c148d0cff6f9892ab8ad5176ffd4c64aa800372a50",
            "c1707864a8fbc805aa98bc8307be99f2c9904eec5cc27d26a5220e001d88d28b",
            "434b462d4edb0165946568dfdf2a6729ff8b2590fead1fe815d3912817837b6e",
            "f08c2cccb75aeb1b7c80e0a06b5fc6befa8ed46e344004ed7bb1f63fc62ef632") &&
            retention == RecoveryThresholds(0.47757815371058715, 0.10336967059629464)
    fun enabled(language: KeyboardLanguage, length: Int): Boolean = language == KeyboardLanguage.RUSSIAN && when (length) {
        in 3..4 -> allows(fingerprint())
        in 5..32 -> allowsLong(longFingerprint(), thresholds.retention)
        else -> false
    }
}
