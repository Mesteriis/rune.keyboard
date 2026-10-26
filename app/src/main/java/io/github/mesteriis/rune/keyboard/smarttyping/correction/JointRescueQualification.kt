package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/** Independent acquisition source; it cannot inherit the primary joint model's qualification. */
internal object JointRescueQualification {
    const val QUALIFIED = true
    const val RANKER_BYTES = 39444
    const val RANKER_SHA256 = "16c1a81a86ce5e71a23d4dbd2b22297abe30529a3c3d75560d6163a12685d168"
    const val POLICY_SHA256 = "ebdb0e83f3c4ed3476f5b317e31619415ca020d9703cd3d6900b9e8ac5c4701d"
    val thresholds = RecoveryThresholds(0.46357352954758124, 0.632436045368692)
    fun fingerprint(): RecoveryQualificationFingerprint = JointQualification.fingerprint().copy(
        searchVersion = 1, rankerSha256 = RANKER_SHA256, policySha256 = POLICY_SHA256, thresholds = thresholds)
    fun allows(fingerprint: RecoveryQualificationFingerprint): Boolean = QUALIFIED && fingerprint ==
        RecoveryQualificationFingerprint(1,
            "16c1a81a86ce5e71a23d4dbd2b22297abe30529a3c3d75560d6163a12685d168",
            "ebdb0e83f3c4ed3476f5b317e31619415ca020d9703cd3d6900b9e8ac5c4701d",
            RecoveryThresholds(0.46357352954758124, 0.632436045368692),
            "accd46a39e111999994d95c148d0cff6f9892ab8ad5176ffd4c64aa800372a50",
            "c1707864a8fbc805aa98bc8307be99f2c9904eec5cc27d26a5220e001d88d28b",
            "434b462d4edb0165946568dfdf2a6729ff8b2590fead1fe815d3912817837b6e",
            "f08c2cccb75aeb1b7c80e0a06b5fc6befa8ed46e344004ed7bb1f63fc62ef632")
    fun enabled(language: KeyboardLanguage): Boolean = language == KeyboardLanguage.RUSSIAN &&
        JointQualification.enabled(language, 5) && allows(fingerprint())
}
