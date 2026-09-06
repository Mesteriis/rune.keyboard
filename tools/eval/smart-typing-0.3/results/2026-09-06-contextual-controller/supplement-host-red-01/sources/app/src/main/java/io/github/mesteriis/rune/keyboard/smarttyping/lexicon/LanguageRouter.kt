package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.ProtectedTokenPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.correction.ProtectedTokenReason
import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode

data class LanguageRoute(
    val primary: KeyboardLanguage?,
    val fallback: KeyboardLanguage?,
    val primaryPrior: Int,
    val fallbackPrior: Int,
    val fallbackCandidateLimit: Int,
    val protectedReason: ProtectedTokenReason? = null,
)

/** Shape evidence wins over layout; Latin uses a 4:1 layout prior and at most two fallback candidates. */
object LanguageRouter {
    fun route(token: String, active: KeyboardLanguage): LanguageRoute {
        ProtectedTokenPolicy.reason(token)?.let { return LanguageRoute(null, null, 0, 0, 0, it) }
        val folded = TokenUnicode.folded(token)
        var offset = 0
        var cyrillic = false
        var spanish = false
        while (offset < folded.length) {
            val cp = folded.codePointAt(offset)
            cyrillic = cyrillic || Character.UnicodeScript.of(cp) == Character.UnicodeScript.CYRILLIC
            spanish = spanish || cp in SPANISH_MARKERS
            offset += Character.charCount(cp)
        }
        if (cyrillic) return single(KeyboardLanguage.RUSSIAN)
        if (spanish) return single(KeyboardLanguage.SPANISH)
        // RU is not evidence that a Latin token is Russian; use deterministic EN then ES.
        val primary = if (active == KeyboardLanguage.SPANISH) active else KeyboardLanguage.ENGLISH
        val fallback = if (primary == KeyboardLanguage.ENGLISH) KeyboardLanguage.SPANISH else KeyboardLanguage.ENGLISH
        return LanguageRoute(primary, fallback, 4, 1, 2)
    }

    private fun single(language: KeyboardLanguage) = LanguageRoute(language, null, 4, 0, 0)
    private val SPANISH_MARKERS = intArrayOf('ñ'.code, 'á'.code, 'é'.code, 'í'.code, 'ó'.code, 'ú'.code, 'ü'.code)
}
