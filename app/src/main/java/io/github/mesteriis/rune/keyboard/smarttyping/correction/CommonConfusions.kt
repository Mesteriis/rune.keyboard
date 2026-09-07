package io.github.mesteriis.rune.keyboard.smarttyping.correction

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidateKind

/** Reviewed finite exceptions, independent of statistical spelling calibration. */
object CommonConfusions {
    const val VERSION = 1
    private val targets = mapOf(
        KeyboardLanguage.RUSSIAN to mapOf(
            "автокрекция" to "автокоррекция", "арфография" to "орфография",
            "сообшение" to "сообщение", "реалбно" to "реально",
            "мододец" to "молодец", "шоржусь" to "горжусь",
        ),
        KeyboardLanguage.ENGLISH to mapOf("teh" to "the", "recieve" to "receive", "adress" to "address"),
        KeyboardLanguage.SPANISH to mapOf("mensage" to "mensaje", "correcion" to "corrección"),
    )

    fun target(language: KeyboardLanguage, foldedToken: String): String? = targets[language]?.get(foldedToken)

    /** Generation marks only targets with exact lexicon membership. Incomplete retrieval still vetoes. */
    fun preferredId(generation: CandidateGeneration, language: KeyboardLanguage): Int {
        if (generation.prohibitsAutoReplace) return 0
        val original = generation.original ?: return 0
        val target = target(language, TokenUnicode.folded(original)) ?: return 0
        val display = CasePattern.analyze(original).preserve(target) ?: return 0
        return generation.alternatives.indexOfFirst {
            it.kind == GeneratedCandidateKind.COMMON_CONFUSION && it.language == language &&
                it.terminalKey == target && it.text == display
        } + 1
    }
}
