package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

data class TrustedCanonicalCaseAsset(val path: String, val bytes: Long, val sha256: String)

/** Generated from canonical-case-manifest.json and the already licensed frozen surface forms. */
object FrozenCanonicalCaseLexicons {
    private val EN = TrustedCanonicalCaseAsset("smarttyping/lexicon/case/en.case", 457335L,
        "ad1bcca401600e247e060f2bbf4aed99acd9d49458f1d0227babe4ecfd2cc658")
    private val ES = TrustedCanonicalCaseAsset("smarttyping/lexicon/case/es.case", 26696L,
        "02885e6cf10d85e75482d27bd38d0f7f3d66a3eb182aff86246ff392f47ea290")
    private val RU = TrustedCanonicalCaseAsset("smarttyping/lexicon/case/ru.case", 672062L,
        "845144afb06ae7881f0db2f577f340694b8c7dfa5fee9685563ec4852939c81b")

    fun forLanguage(language: KeyboardLanguage): TrustedCanonicalCaseAsset = when (language) {
        KeyboardLanguage.ENGLISH -> EN
        KeyboardLanguage.SPANISH -> ES
        KeyboardLanguage.RUSSIAN -> RU
    }
}
