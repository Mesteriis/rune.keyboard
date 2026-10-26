package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import io.github.mesteriis.rune.keyboard.smarttyping.correction.EditCostProfile
import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode
import io.github.mesteriis.rune.keyboard.smarttyping.correction.WeightedDamerauLevenshtein
import java.util.TreeSet

/** Complete bounded unit-edit retrieval over two exact public dictionaries. */
internal class PublicCandidateAugmenter(
    private val morphology: MorphologyLexicon,
    private val rareWords: RareWordLexicon,
) {
    private val weighted = WeightedDamerauLevenshtein()

    fun augment(source: String, existing: List<GeneratedCandidate>, language: KeyboardLanguage,
        languagePrior: Int, pattern: CasePattern, cancellation: CandidateCancellation,
        allowKnownOriginalForManual: Boolean = false): List<GeneratedCandidate>? {
        if (language != KeyboardLanguage.RUSSIAN || source.length !in 3..MAX_LENGTH ||
            source.any { it !in ALPHABET }) return existing
        val originalMorphology = morphology.lookup(language, source)
        val originalRare = rareWords.lookup(source)
        if (!originalMorphology.available || !originalRare.available || cancellation.isCancelled()) return null
        if (!allowKnownOriginalForManual && (originalMorphology.present || originalRare.present)) return null

        val variants = TreeSet<String>()
        for (index in source.indices) {
            variants += source.removeRange(index, index + 1)
            for (letter in ALPHABET) if (letter != source[index]) {
                variants += source.replaceRange(index, index + 1, letter.toString())
            }
            if (index + 1 < source.length && source[index] != source[index + 1]) {
                variants += source.substring(0, index) + source[index + 1] + source[index] +
                    source.substring(index + 2)
            }
        }
        for (index in 0..source.length) for (letter in ALPHABET) {
            variants += source.substring(0, index) + letter + source.substring(index)
        }
        variants.remove(source)
        val present = existing.mapTo(HashSet()) { it.canonicalKey }
        val additions = ArrayList<GeneratedCandidate>()
        for (value in variants) {
            if (cancellation.isCancelled()) return null
            val morph = morphology.lookup(language, value)
            val rare = rareWords.lookup(value)
            if (!morph.available || !rare.available) return null
            if ((!morph.present && !rare.present) || !present.add(value)) continue
            val display = pattern.preserve(value) ?: continue
            val features = weighted.features(source, value, language)
            additions += GeneratedCandidate(
                text = display,
                canonicalKey = TokenUnicode.folded(display),
                terminalKey = value,
                language = language,
                isFallback = false,
                languagePrior = languagePrior,
                frequencyRank = 50_000 + (rare.rank ?: 1_000_000),
                unitDistance = 1,
                editFeatures = features,
                lengthDifference = kotlin.math.abs(source.length - value.length),
                casePattern = pattern,
                kind = GeneratedCandidateKind.PUBLIC_AUGMENTED,
            )
        }
        additions.sortWith(compareBy<GeneratedCandidate>({ it.editFeatures.editCost },
            { it.frequencyRank }, { it.canonicalKey }))
        if (existing.size + additions.size > MAX_ALTERNATIVES) return null
        return existing + additions
    }

    companion object {
        const val MAX_ALTERNATIVES = 64
        private const val MAX_LENGTH = 32
        private const val ALPHABET = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    }
}
