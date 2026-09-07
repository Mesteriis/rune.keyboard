package io.github.mesteriis.rune.keyboard.smarttyping.correction

/**
 * Exact shipped Rune Text / optimized CPU backend qualified on Fold, 2026-09-05:
 * release 4-candidate p95 EN75/RU260/ES173 ms; production service 7.85 CPU-s/60 s,
 * with 107/120 requests denied and idle model pages released. This is not an
 * unplugged battery or full release acceptance. Requalify when model/backend changes.
 */
internal object ModelRuntimeQualification {
    val CURRENT: Boolean get() = allows(QualificationArtifacts.model())
    fun allows(fingerprint: ModelQualificationFingerprint) =
        fingerprint.modelSha256 == "7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4" &&
        fingerprint.runtimeApi == 1 && fingerprint.runtimeBuildId == "356dc78ec8b156462d8384ca14f0e20ff831c66b83c38831f40edfd6bd645613" &&
        fingerprint.spellingPolicyVersion == 1 && fingerprint.lexicons == QualificationArtifacts.qualifiedLexicons
}
