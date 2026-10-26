package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

internal enum class SpellingSource { COMMON_CONFUSION, GENERAL_LOCAL, COMPACT_PUBLIC, MODEL, NEIGHBOR_RECOVERY, MODEL_REFINEMENT, JOINT_SHORT, JOINT_LONG, JOINT_RESCUE, WORD_CONTEXT, CONTEXTUAL_PUBLIC }

/** Quality admission is separate for the finite local source, general ranking, and model ranking. */
internal fun interface SpellingQualification {
    fun allows(language: KeyboardLanguage, source: SpellingSource): Boolean

    fun allowsCommonConfusion(language: KeyboardLanguage) = allows(language, SpellingSource.COMMON_CONFUSION)
    fun allowsGeneralLocal(language: KeyboardLanguage) = allows(language, SpellingSource.GENERAL_LOCAL)
    fun allowsCompactPublic(language: KeyboardLanguage) = allows(language, SpellingSource.COMPACT_PUBLIC)
    fun allowsModel(language: KeyboardLanguage) = allows(language, SpellingSource.MODEL)

    companion object {
        /**
         * V7 common confusions are explicit reviewed exceptions. General local V1/search V1 with
         * morphology admission V1 is independently qualified for RU/ES at 99% point precision. The existing model
         * qualification remains the frozen 95% policy, independent of local qualification.
         */
        val CURRENT = SpellingQualification { language, source -> when (source) {
            SpellingSource.CONTEXTUAL_PUBLIC -> ContextualQualification.enabled(language, 3) && ContextualQualification.enabled(language, 5)
            SpellingSource.WORD_CONTEXT -> WordContextQualification.enabled(language)
            SpellingSource.JOINT_RESCUE -> JointRescueQualification.enabled(language)
            SpellingSource.JOINT_SHORT -> JointQualification.enabled(language, 3)
            SpellingSource.JOINT_LONG -> JointQualification.enabled(language, 5)
            SpellingSource.COMMON_CONFUSION -> QualificationArtifacts.allowsLocal(language, QualificationArtifacts.local())
            SpellingSource.GENERAL_LOCAL -> QualificationArtifacts.allowsGeneralLocal(
                language, QualificationArtifacts.generalLocal())
            SpellingSource.COMPACT_PUBLIC -> QualificationArtifacts.allowsCompactPublic(
                language, QualificationArtifacts.compactPublic())
            SpellingSource.NEIGHBOR_RECOVERY -> language == KeyboardLanguage.RUSSIAN && RecoveryQualification.allows(RecoveryQualification.fingerprint())
            SpellingSource.MODEL_REFINEMENT -> language == KeyboardLanguage.RUSSIAN && RecoveryQualification.MODEL_QUALIFIED && RecoveryQualification.refinement != null && ModelRuntimeQualification.CURRENT
            SpellingSource.MODEL -> ModelRuntimeQualification.CURRENT
        } }
    }
}
