package io.github.mesteriis.rune.keyboard.smarttyping.experiments

/** Source-v2 cue evidence. Frozen model inputs continue using the separate v1 extractor. */
internal class ReliableRightContextGrammarFeatures(lookup: (String) -> List<GrammarAnalysis>) {
    constructor(dictionary: GrammarFeatureDictionary) : this({ dictionary.analyses(it).analyses })

    private val features = RightContextGrammarFeatures { word ->
        val tags = lookup(word)
        if (tags.any { it.pos in FUNCTION_PARTS }) tags.filter { it.pos !in NOMINAL_PARTS } else tags
    }

    fun extract(rightContext: String, candidate: String): DoubleArray = features.extract(rightContext, candidate)

    companion object {
        const val VERSION = 2
        const val COUNT = RightContextGrammarFeatures.COUNT
        private val FUNCTION_PARTS = setOf("PREP", "CONJ", "PRCL")
        private val NOMINAL_PARTS = setOf("NOUN", "NPRO")
    }
}
