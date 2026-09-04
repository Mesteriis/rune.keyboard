package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/** Independent of user preference and provisional calibration. Owner-injected in qualification tests. */
internal fun interface SpellingQualification {
    fun allows(language: KeyboardLanguage, modelAssisted: Boolean): Boolean

    companion object {
        /**
         * The frozen product holdout passes the user-selected 95% point-precision gate only for
         * the model-assisted branch in every supported language. Deterministic ranking remains a
         * suggestion fallback and cannot write automatically.
         */
        val CURRENT = SpellingQualification { _, modelAssisted -> modelAssisted }
    }
}
