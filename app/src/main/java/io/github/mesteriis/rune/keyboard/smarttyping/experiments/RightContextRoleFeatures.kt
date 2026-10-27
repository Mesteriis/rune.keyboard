package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import java.text.Normalizer
import java.util.Locale

/** Experimental v1 role features; never source admission or editor authority.
 * Past analyses require a separately bound dictionary: the main asset omits tense.
 */
internal class RightContextRoleFeatures(
    private val lookup: (String) -> List<GrammarAnalysis>,
    private val pastFiniteLookup: (String) -> List<GrammarAnalysis>,
) {
    constructor(dictionary: GrammarFeatureDictionary, pastDictionary: GrammarFeatureDictionary) :
        this({ dictionary.analyses(it).analyses }, { pastDictionary.analyses(it).analyses })

    fun extract(leftContext: String, rightContext: String, candidate: String): DoubleArray {
        val words = RightContextGrammarFeatures.completedFollowingWords(rightContext)
        val first = words.firstOrNull()?.let(lookup) ?: emptyList()
        val copula = if (words.firstOrNull() in COPULAS) first.filter { it.pos == "VERB" } else emptyList()
        val subjectTags = if (copula.isNotEmpty()) words.getOrNull(1)?.let(lookup) ?: emptyList() else first
        val nominal = subjectTags.filter { it.pos in NOMINAL }
        val nominative = nominal.filter { it.case == "nomn" }
        val alternative = nominal.any { it.case != "nomn" }
        val rightGenders = genders(copula + nominative)
        val candidateGenders = genders(lookup(candidate).filter { it.pos in PREDICATES })
        var past = emptyList<GrammarAnalysis>()
        for (word in precedingClauseWords(leftContext).asReversed()) {
            val variants = pastFiniteLookup(word).filter { it.pos == "VERB" }
            if (variants.isNotEmpty()) { past = variants; break }
        }
        val pastGenders = genders(past)
        val result = DoubleArray(COUNT)
        var position = 0
        fun add(value: Boolean) { result[position++] = if (value) 1.0 else 0.0 }
        add(nominative.isNotEmpty() && alternative)
        add(nominative.isNotEmpty() && !alternative && nominal.size == subjectTags.size)
        add(nominal.mapNotNull { it.number }.distinct().size > 1)
        add(nominative.isNotEmpty() && nominal.size != subjectTags.size)
        add(nominative.any { it.pos == "NOUN" }); add(nominative.any { it.pos == "NPRO" })
        add(rightGenders.isNotEmpty()); add(rightGenders.size > 1)
        for (gender in listOf("masc", "femn", "neut")) add(gender in candidateGenders)
        add(pastGenders.isNotEmpty())
        add(pastGenders.any { it in candidateGenders })
        add(pastGenders.isNotEmpty() && candidateGenders.isNotEmpty() && pastGenders.none { it in candidateGenders })
        add(pastGenders.size > 1)
        check(position == COUNT)
        return result
    }

    companion object {
        const val VERSION = 1
        const val COUNT = 15
        private val WORD = Regex("[а-яё]{1,32}")
        private val COPULAS = setOf("буду", "будешь", "будет", "будем", "будете", "будут", "был", "была", "было", "были")
        private val NOMINAL = setOf("NOUN", "NPRO")
        private val PREDICATES = setOf("ADJS", "PRTS")
        private val GENDERS = setOf("masc", "femn", "neut")
        private fun genders(tags: List<GrammarAnalysis>) = tags.filter { it.number == "sing" }
            .mapNotNull { it.gender }.filter { it in GENDERS }.toSet()
        private fun alphanumeric(codePoint: Int) = Character.isLetterOrDigit(codePoint) ||
            Character.getType(codePoint) in setOf(Character.LETTER_NUMBER.toInt(), Character.OTHER_NUMBER.toInt())

        internal fun precedingClauseWords(context: String): List<String> {
            val count = context.codePointCount(0, context.length)
            val windowStart = context.offsetByCodePoints(0, maxOf(0, count - 128))
            val text = Normalizer.normalize(context.substring(windowStart), Normalizer.Form.NFC).lowercase(Locale.ROOT)
            if (text.isEmpty() || text.last() !in " \t,") return emptyList()
            var end = text.length
            val result = mutableListOf<String>()
            while (end > 0 && result.size < 8) {
                while (end > 0 && text[end - 1] in " \t,") end--
                var start = end
                while (start > 0 && (text[start - 1] in 'а'..'я' || text[start - 1] == 'ё')) start--
                val word = text.substring(start, end)
                if (!WORD.matches(word)) break
                if (start > 0 && text[start - 1] !in " \t,.:;!?\n\r") break
                if (start == 0 && count > 128 && alphanumeric(context.codePointBefore(windowStart))) break
                result.add(word)
                if (start == 0 || text[start - 1] !in " \t,") break
                end = start
            }
            return result.asReversed()
        }
    }
}
