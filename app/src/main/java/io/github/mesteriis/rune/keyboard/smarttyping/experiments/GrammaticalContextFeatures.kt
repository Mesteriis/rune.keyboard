package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import java.text.Normalizer
import java.util.Locale

/** Exact port of the frozen training feature schema. Evidence only; never an admission rule. */
internal class GrammaticalContextFeatures(private val dictionary: GrammarFeatureDictionary) {
    fun extract(context: String, candidate: String): DoubleArray {
        val entry = dictionary.analyses(candidate)
        val analyses = entry.analyses
        val words = precedingWords(context)
        val tags = words.map { dictionary.analyses(it).analyses }
        val result = DoubleArray(COUNT)
        var position = 0
        fun add(value: Boolean) { result[position++] = if (value) 1.0 else 0.0 }
        add(analyses.isNotEmpty())
        result[position++] = entry.ambiguity / 8.0
        for (pos in PARTS) add(analyses.any { it.pos == pos })
        for (case in CASES) add(analyses.any { it.case == case })
        for (number in listOf("sing", "plur")) add(analyses.any { it.number == number })
        for (person in listOf("1per", "2per", "3per")) add(analyses.any { it.person == person })
        var infinitive = false
        var accusative = false
        for (index in words.lastIndex downTo maxOf(0, words.size - 4)) {
            val variants = tags[index]
            if (words[index] in TRANSPARENT || variants.any { it.pos == "NPRO" && it.case == "datv" }) continue
            infinitive = (variants.isNotEmpty() && words[index] in IMPERSONAL) ||
                variants.any { it.modal && it.pos in VERBS }
            accusative = variants.any { it.accusativeVerb && it.pos in VERBS }
            break
        }
        val subject = words.takeLast(6).asReversed().firstNotNullOfOrNull { SUBJECTS[it] }
        val finite = analyses.filter { it.pos == "VERB" }
        val predicates = analyses.filter { it.pos == "ADJS" || it.pos == "PRTS" }
        fun subjectMatch(analysis: GrammarAnalysis): Boolean = subject != null &&
            analysis.number == subject.number && (analysis.person == null || analysis.person == subject.person) &&
            (analysis.gender == null || subject.gender == null || analysis.gender == subject.gender)
        var preposition: Set<String>? = null
        for (index in words.lastIndex downTo 0) {
            val cases = PREPOSITIONS[words[index]]
            if (cases != null && tags[index].any { it.pos == "PREP" }) {
                if (tags.drop(index + 1).all { variants -> variants.any { it.pos == "ADJF" } }) preposition = cases
                break
            }
        }
        val caseAnalyses = analyses.filter { it.pos in CASE_PARTS && it.case != null }
        val adjective = tags.lastOrNull()?.any { left ->
            left.pos == "ADJF" && analyses.any { right ->
                right.pos in NOUNS && left.case != null && left.case == right.case &&
                    left.number != null && left.number == right.number &&
                    (left.number == "plur" || (left.gender != null && left.gender == right.gender))
            }
        } == true
        add(infinitive)
        add(infinitive && analyses.any { it.pos == "INFN" })
        add(infinitive && finite.isNotEmpty())
        add(subject != null)
        add(subject != null && finite.any(::subjectMatch))
        add(subject != null && finite.isNotEmpty() && finite.none(::subjectMatch))
        add(subject != null && predicates.any(::subjectMatch))
        add(subject != null && predicates.isNotEmpty() && predicates.none(::subjectMatch))
        add(preposition != null)
        add(preposition != null && caseAnalyses.any { it.case in preposition })
        add(preposition != null && caseAnalyses.isNotEmpty() && caseAnalyses.none { it.case in preposition })
        add(adjective)
        add(accusative)
        add(accusative && analyses.any { it.pos == "NOUN" && it.case == "accs" })
        check(position == COUNT)
        return result
    }

    companion object {
        const val COUNT = 38
        private val PARTS = listOf("NOUN", "ADJF", "ADJS", "VERB", "INFN", "PRTF", "PRTS", "GRND", "NPRO", "ADVB", "PRED")
        private val CASES = listOf("nomn", "gent", "datv", "accs", "ablt", "loct")
        private val VERBS = setOf("VERB", "INFN")
        private val NOUNS = setOf("NOUN", "NPRO")
        private val CASE_PARTS = setOf("NOUN", "NPRO", "ADJF")
        private val CONTEXT = Regex("[а-яё]+(?:[ \\t]+[а-яё]+){0,7}[ \\t]*\\z")
        private val TRANSPARENT = setOf("не", "очень", "немного", "уже", "снова", "ещё", "еще", "теперь", "просто", "только", "бы", "же")
        private val IMPERSONAL = setOf("надо", "нужно", "необходимо", "можно", "нельзя", "пора", "хочется", "пришлось", "удалось", "должен", "должна", "должны")
        private data class Subject(val number: String, val person: String, val gender: String? = null)
        private val SUBJECTS = mapOf("я" to Subject("sing", "1per"), "ты" to Subject("sing", "2per"),
            "он" to Subject("sing", "3per", "masc"), "она" to Subject("sing", "3per", "femn"),
            "оно" to Subject("sing", "3per", "neut"), "мы" to Subject("plur", "1per"),
            "вы" to Subject("plur", "2per"), "они" to Subject("plur", "3per"))
        private val PREPOSITIONS = mapOf("в" to setOf("accs", "loct"), "на" to setOf("accs", "loct"),
            "с" to setOf("gent", "ablt"), "к" to setOf("datv"), "ко" to setOf("datv"),
            "из" to setOf("gent"), "у" to setOf("gent"), "для" to setOf("gent"), "без" to setOf("gent"),
            "до" to setOf("gent"), "от" to setOf("gent"), "после" to setOf("gent"), "около" to setOf("gent"),
            "перед" to setOf("ablt"), "над" to setOf("ablt"), "между" to setOf("ablt", "gent"),
            "о" to setOf("loct", "accs"), "об" to setOf("loct", "accs"), "по" to setOf("datv", "loct", "accs"),
            "за" to setOf("accs", "ablt"), "под" to setOf("accs", "ablt"))

        internal fun precedingWords(context: String): List<String> {
            val normalized = Normalizer.normalize(context, Normalizer.Form.NFC).lowercase(Locale.ROOT)
            val count = normalized.codePointCount(0, normalized.length)
            val start = normalized.offsetByCodePoints(0, maxOf(0, count - 128))
            val match = CONTEXT.find(normalized.substring(start)) ?: return emptyList()
            val absolute = start + match.range.first
            if (absolute > 0) {
                val previous = normalized.codePointBefore(absolute)
                val type = Character.getType(previous)
                if (Character.isLetterOrDigit(previous) || type == Character.LETTER_NUMBER.toInt() ||
                    type == Character.OTHER_NUMBER.toInt() || previous == '_'.code || previous == '-'.code) return emptyList()
            }
            return match.value.trim().split(Regex("[ \\t]+"))
        }
    }
}
