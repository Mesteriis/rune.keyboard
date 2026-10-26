package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import java.text.Normalizer
import java.util.Locale

/** Experimental following-word evidence, separate from the installed scorer and editor admission. */
internal class RightContextGrammarFeatures(private val lookup: (String) -> List<GrammarAnalysis>) {
    constructor(dictionary: GrammarFeatureDictionary) : this({ dictionary.analyses(it).analyses })

    fun extract(rightContext: String, candidate: String): DoubleArray {
        val word = if (candidate.length <= 64) normalize(candidate) else ""
        val analyses = if (WORD.matches(word)) lookup(word) else emptyList()
        val predicates = analyses.filter { it.pos in PREDICATES }
        val words = completedFollowingWords(rightContext)
        val first = words.firstOrNull()?.let(lookup) ?: emptyList()
        val copula = if (words.firstOrNull() in COPULAS) first.filter { it.pos == "VERB" } else emptyList()
        val subjectTags = if (copula.isNotEmpty()) words.getOrNull(1)?.let(lookup) ?: emptyList() else first
        val subject = subjectTags.filter { it.pos in SUBJECTS && it.case == "nomn" }
        val result = DoubleArray(COUNT)
        var position = 0
        fun add(value: Boolean) { result[position++] = if (value) 1.0 else 0.0 }
        fun agreement(cues: List<GrammarAnalysis>) {
            val number = predicates.any { a -> cues.any { a.number != null && a.number == it.number } }
            val numberKnown = predicates.isNotEmpty() && cues.isNotEmpty() && (predicates + cues).all { it.number != null }
            val gender = predicates.any { a -> cues.any {
                a.number == "sing" && it.number == "sing" && a.gender != null && a.gender == it.gender
            } }
            val genderKnown = predicates.isNotEmpty() && cues.isNotEmpty() &&
                (predicates + cues).all { it.number == "sing" && it.gender != null }
            add(number); add(numberKnown && !number); add(gender); add(genderKnown && !gender)
        }
        add(analyses.isNotEmpty()); add(predicates.isNotEmpty())
        result[position++] = words.size / 8.0
        add(first.isNotEmpty()); add(copula.isNotEmpty())
        agreement(copula)
        add(subject.isNotEmpty()); agreement(subject)
        add(ambiguous(copula) || ambiguous(subject)); add(ambiguous(predicates))
        check(position == COUNT)
        return result
    }

    companion object {
        const val VERSION = 1
        const val COUNT = 16
        private val WORD = Regex("[а-яё]{1,32}")
        private val COPULAS = setOf("буду", "будешь", "будет", "будем", "будете", "будут", "был", "была", "было", "были")
        private val PREDICATES = setOf("ADJS", "PRTS")
        private val SUBJECTS = setOf("NOUN", "NPRO")
        private fun normalize(value: String) = Normalizer.normalize(value, Normalizer.Form.NFC).lowercase(Locale.ROOT)
        private fun ambiguous(variants: List<GrammarAnalysis>) = variants.map { it.number to it.gender }.distinct().size > 1

        /** Exact typed suffix. An unfinished token, identifier or later clause supplies no cue. */
        internal fun completedFollowingWords(rightContext: String): List<String> {
            val text = normalize(rightContext.take(128))
            if (text.isEmpty() || text[0] !in " \t") return emptyList()
            val words = mutableListOf<String>()
            var position = 0
            while (position < text.length && words.size < 8) {
                while (position < text.length && text[position] in " \t") position++
                val start = position
                while (position < text.length && (text[position] in 'а'..'я' || text[position] == 'ё')) position++
                val word = text.substring(start, position)
                if (!WORD.matches(word) || position == text.length) break
                val boundary = text[position]
                if (boundary !in " \t.,!?;:\n\r") break
                words.add(word)
                if (boundary !in " \t") break
            }
            return words
        }
    }
}
