package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/** Independent of user preference and provisional calibration. Owner-injected in qualification tests. */
internal fun interface SpellingQualification {
    fun allows(language: KeyboardLanguage, modelAssisted: Boolean): Boolean

    companion object {
        /** No final product holdout has passed yet. No setting or model Ready state overrides this. */
        val CURRENT = SpellingQualification { _, _ -> false }
    }
}
