package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.intelligence.ipc.QualifiedModelArtifact
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.FrozenPackedLexicons

internal data class LocalQualificationFingerprint(val policyVersion: Int,
    val lexicons: Map<KeyboardLanguage, String>)
internal data class ModelQualificationFingerprint(val modelSha256: String, val runtimeApi: Int,
    val runtimeBuildId: String, val spellingPolicyVersion: Int, val lexicons: Map<KeyboardLanguage, String>)

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
    fun model() = ModelQualificationFingerprint(QualifiedModelArtifact.MODEL_SHA256,
        QualifiedModelArtifact.RUNTIME_API, QualifiedModelArtifact.RUNTIME_BUILD_ID,
        CalibratedSpellingPolicy.VERSION, currentLexicons)
    fun allowsLocal(language: KeyboardLanguage, fingerprint: LocalQualificationFingerprint) =
        fingerprint.policyVersion == 1 && fingerprint.lexicons[language] == qualifiedLexicons[language]
}
