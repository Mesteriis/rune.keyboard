package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.intelligence.ipc.QualifiedModelArtifact
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.FrozenPackedLexicons
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGenerator
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.FrozenMorphologyLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.FrozenRareWordLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.CompactAutoCorrectionPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.FrozenExperimentAssets

internal data class LocalQualificationFingerprint(val policyVersion: Int,
    val lexicons: Map<KeyboardLanguage, String>)
internal data class GeneralLocalQualificationFingerprint(val policyVersion: Int, val searchVersion: Int,
    val admissionVersion: Int,
    val lexicons: Map<KeyboardLanguage, String>)
internal data class ModelQualificationFingerprint(val modelSha256: String, val runtimeApi: Int,
    val runtimeBuildId: String, val spellingPolicyVersion: Int, val lexicons: Map<KeyboardLanguage, String>)
internal data class CompactPublicQualificationFingerprint(val policyVersion: Int,
    val policySha256: String, val rankerSha256: String, val legacyRankerSha256: String,
    val contextSha256: String,
    val morphologySha256: String, val rareWordsSha256: String,
    val lexicons: Map<KeyboardLanguage, String>)

/** Separate frozen evidence from current release metadata: changing either requires requalification. */
internal object QualificationArtifacts {
    val qualifiedLexicons: Map<KeyboardLanguage, String> = mapOf(
        KeyboardLanguage.ENGLISH to "596255698ec63d1e88917d2b0e2e28a2be37131a5f0692f8399f7a63cea2d181",
        KeyboardLanguage.RUSSIAN to "f08c2cccb75aeb1b7c80e0a06b5fc6befa8ed46e344004ed7bb1f63fc62ef632",
        KeyboardLanguage.SPANISH to "152675e27e900c2bd968e7b320500ab6c195213c1c8276cafc701c6d2f3e0d1c",
    )
    private val currentLexicons = listOf(FrozenPackedLexicons.ENGLISH, FrozenPackedLexicons.RUSSIAN,
        FrozenPackedLexicons.SPANISH).associate { it.language to it.manifest.identity() }
    fun local() = LocalQualificationFingerprint(CommonConfusions.VERSION, currentLexicons)
    fun generalLocal() = GeneralLocalQualificationFingerprint(LocalCorrectionPolicy.VERSION,
        CandidateGenerator.SEARCH_VERSION, AutoCorrectionAdmissionGuard.VERSION, currentLexicons)
    fun model() = ModelQualificationFingerprint(QualifiedModelArtifact.MODEL_SHA256,
        QualifiedModelArtifact.RUNTIME_API, QualifiedModelArtifact.RUNTIME_BUILD_ID,
        CalibratedSpellingPolicy.VERSION, currentLexicons)
    fun compactPublic() = CompactPublicQualificationFingerprint(CompactAutoCorrectionPolicy.VERSION,
        CompactAutoCorrectionPolicy.POLICY_SHA256, FrozenExperimentAssets.RANK_SHA256,
        FrozenExperimentAssets.LEGACY_AUTOMATIC_RANK_SHA256,
        FrozenExperimentAssets.RANKING_CONTEXT_SHA256, FrozenMorphologyLexicon.ASSET_SHA256,
        FrozenRareWordLexicon.ASSET_SHA256, currentLexicons)
    fun allowsLocal(language: KeyboardLanguage, fingerprint: LocalQualificationFingerprint) =
        fingerprint.policyVersion == 7 && fingerprint.lexicons[language] == qualifiedLexicons[language]
    fun allowsGeneralLocal(language: KeyboardLanguage, fingerprint: GeneralLocalQualificationFingerprint) =
        language in setOf(KeyboardLanguage.RUSSIAN, KeyboardLanguage.SPANISH) &&
            fingerprint.policyVersion == 1 && fingerprint.searchVersion == 1 &&
            fingerprint.admissionVersion == 1 &&
            fingerprint.lexicons[language] == qualifiedLexicons[language]
    fun allowsCompactPublic(language: KeyboardLanguage, fingerprint: CompactPublicQualificationFingerprint) =
        language == KeyboardLanguage.RUSSIAN && fingerprint.policyVersion == 4 &&
            fingerprint.policySha256 == "5057e9e955fafdc507e06b4b1e88307b4dd2201d6864a9620b39e23358a33acd" &&
            fingerprint.rankerSha256 == "f4b0737515abc6855b7354ddaf0d1b349be98b5d7b80587cc94f1c0c1bc576ec" &&
            fingerprint.legacyRankerSha256 == "eb466bcabc4ea1cfac493422fa814386bdff02dc9c04c48bd66a9d8a25a11bcd" &&
            fingerprint.contextSha256 == "accd46a39e111999994d95c148d0cff6f9892ab8ad5176ffd4c64aa800372a50" &&
            fingerprint.morphologySha256 == "c1707864a8fbc805aa98bc8307be99f2c9904eec5cc27d26a5220e001d88d28b" &&
            fingerprint.rareWordsSha256 == "434b462d4edb0165946568dfdf2a6729ff8b2590fead1fe815d3912817837b6e" &&
            fingerprint.lexicons[language] == qualifiedLexicons[language]
}
