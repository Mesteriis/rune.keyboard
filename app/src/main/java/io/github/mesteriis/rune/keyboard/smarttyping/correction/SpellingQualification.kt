package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

internal enum class SpellingSource { COMMON_CONFUSION, GENERAL_LOCAL, MODEL }

/** Quality admission is separate for the finite local source, general ranking, and model ranking. */
internal fun interface SpellingQualification {
    fun allows(language: KeyboardLanguage, source: SpellingSource): Boolean

    fun allowsCommonConfusion(language: KeyboardLanguage) = allows(language, SpellingSource.COMMON_CONFUSION)
    fun allowsGeneralLocal(language: KeyboardLanguage) = allows(language, SpellingSource.GENERAL_LOCAL)
    fun allowsModel(language: KeyboardLanguage) = allows(language, SpellingSource.MODEL)

    companion object {
        /**
         * V2 common confusions are explicit reviewed exceptions. General local V1/search V1 is
         * independently qualified for RU/ES at 99% point precision. The existing model
         * qualification remains the frozen 95% policy, independent of local qualification.
         */
        val CURRENT = SpellingQualification { language, source -> when (source) {
            SpellingSource.COMMON_CONFUSION -> QualificationArtifacts.allowsLocal(language, QualificationArtifacts.local())
            SpellingSource.GENERAL_LOCAL -> QualificationArtifacts.allowsGeneralLocal(
                language, QualificationArtifacts.generalLocal())
            SpellingSource.MODEL -> ModelRuntimeQualification.CURRENT
        } }
    }
}
