package io.github.mesteriis.rune.keyboard.smarttyping.correction

/**
 * Exact shipped Rune Text / source-normalized CPU backend requalified on Fold, 2026-10-27:
 * release 4-candidate sample p95 EN58/RU249/ES136 ms; production service 8.08 CPU-s/60 s,
 * with 105/120 requests denied and idle model pages released. Real model self-test/scoring
 * also pass API 26 and API 37/16 KiB. See the native-preparation runtime acceptance receipt.
 * This is not unplugged battery or full release acceptance. Requalify model/backend changes.
 */
internal object ModelRuntimeQualification {
    val CURRENT: Boolean get() = allows(QualificationArtifacts.model())
    fun allows(fingerprint: ModelQualificationFingerprint) =
        fingerprint.modelSha256 == "7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4" &&
        fingerprint.runtimeApi == 1 && fingerprint.runtimeBuildId == "d48f6df2ed03cd11d3182abe453fb3a5bd126aea92f2bc06ab747b201f84565f" &&
        fingerprint.spellingPolicyVersion == 1 && fingerprint.lexicons == QualificationArtifacts.qualifiedLexicons
}
