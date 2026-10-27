package io.github.mesteriis.rune.keyboard.smarttyping.personalization

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal

/** Shared veto explanations for ordinary, refinement and compact admission; never grants admission. */
internal object PersonalAdmissionPolicy {
    inline fun protectedOriginalRefusal(enabled: Boolean, controlsReady: Boolean,
        contains: () -> Boolean): AutomaticAdmissionRefusal? = when {
        !enabled -> null
        !controlsReady -> AutomaticAdmissionRefusal.RESOURCE_UNAVAILABLE
        contains() -> AutomaticAdmissionRefusal.PROTECTED_WORD
        else -> null
    }

    fun personalRefusal(ready: Boolean, model: PersonalTypingModel, original: String,
        replacement: String, language: KeyboardLanguage): AutomaticAdmissionRefusal? =
        if (ready && (model.protectsOriginal(original, language) || model.rejects(original, replacement, language)))
            AutomaticAdmissionRefusal.PERSONAL_VETO else null
}
