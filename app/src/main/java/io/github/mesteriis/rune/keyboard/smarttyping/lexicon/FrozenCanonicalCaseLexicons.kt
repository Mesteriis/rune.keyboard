package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

data class TrustedCanonicalCaseAsset(val path: String, val bytes: Long, val sha256: String)

/** Generated from canonical-case-manifest.json and the already licensed frozen surface forms. */
object FrozenCanonicalCaseLexicons {
    private val EN = TrustedCanonicalCaseAsset("smarttyping/lexicon/case/en.case", 457101L,
        "2d5ba3c807ef8c66be5222b01c3cd0f98645a891c12b6356827ea58544725a34")
    private val ES = TrustedCanonicalCaseAsset("smarttyping/lexicon/case/es.case", 26687L,
        "52614678597416daf63763bb1f34015097d97ab974d9aa951b0221a67105a6fa")
    private val RU = TrustedCanonicalCaseAsset("smarttyping/lexicon/case/ru.case", 672062L,
        "845144afb06ae7881f0db2f577f340694b8c7dfa5fee9685563ec4852939c81b")

    fun forLanguage(language: KeyboardLanguage): TrustedCanonicalCaseAsset = when (language) {
        KeyboardLanguage.ENGLISH -> EN
        KeyboardLanguage.SPANISH -> ES
        KeyboardLanguage.RUSSIAN -> RU
    }
}
