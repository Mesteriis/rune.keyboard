package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyLexicon
import java.util.Locale

internal enum class NounCaseRevisionRefusal {
    UNCHANGED, PREVIOUS_NOT_UNAMBIGUOUS_INSTRUMENTAL, PROPOSAL_NOT_UNAMBIGUOUS_ACCUSATIVE,
    LEMMA_UNAVAILABLE, DIFFERENT_LEMMA, NO_ACCUSATIVE_CUE,
}

/** Restrict a separately scored/admitted noun revision; never authority to edit. */
internal class NounCaseRevisionScope(private val dictionary: GrammarFeatureDictionary) {
    private val grammar = GrammaticalContextFeatures(dictionary)

    fun preconditionRefusal(context: String, previous: String,
        morphology: MorphologyLexicon): NounCaseRevisionRefusal? {
        val analyses = dictionary.analyses(previous).analyses
        if (analyses.isEmpty() || analyses.any { it.pos != "NOUN" || it.case != "ablt" || it.number != "sing" })
            return NounCaseRevisionRefusal.PREVIOUS_NOT_UNAMBIGUOUS_INSTRUMENTAL
        val lemma = morphology.lookup(KeyboardLanguage.RUSSIAN, previous.lowercase(Locale.ROOT))
        if (!lemma.available || !lemma.present || (lemma.lemmaId ?: 0) <= 0)
            return NounCaseRevisionRefusal.LEMMA_UNAVAILABLE
        return if (grammar.extract(context, previous)[ACCUSATIVE_CUE] == 1.0) null
            else NounCaseRevisionRefusal.NO_ACCUSATIVE_CUE
    }

    fun refusal(context: String, previous: String, proposed: String,
        morphology: MorphologyLexicon): NounCaseRevisionRefusal? {
        if (previous == proposed) return NounCaseRevisionRefusal.UNCHANGED
        val before = dictionary.analyses(previous).analyses
        val after = dictionary.analyses(proposed).analyses
        if (before.isEmpty() || before.any { it.pos != "NOUN" || it.case != "ablt" || it.number != "sing" })
            return NounCaseRevisionRefusal.PREVIOUS_NOT_UNAMBIGUOUS_INSTRUMENTAL
        if (after.isEmpty() || after.any { it.pos != "NOUN" || it.case != "accs" || it.number != "sing" })
            return NounCaseRevisionRefusal.PROPOSAL_NOT_UNAMBIGUOUS_ACCUSATIVE
        val oldLemma = morphology.lookup(KeyboardLanguage.RUSSIAN, previous.lowercase(Locale.ROOT))
        val newLemma = morphology.lookup(KeyboardLanguage.RUSSIAN, proposed.lowercase(Locale.ROOT))
        if (!oldLemma.available || !oldLemma.present || (oldLemma.lemmaId ?: 0) <= 0 ||
            !newLemma.available || !newLemma.present || (newLemma.lemmaId ?: 0) <= 0)
            return NounCaseRevisionRefusal.LEMMA_UNAVAILABLE
        if (oldLemma.lemmaId != newLemma.lemmaId) return NounCaseRevisionRefusal.DIFFERENT_LEMMA
        return if (grammar.extract(context, proposed)[ACCUSATIVE_SUPPORTED] == 1.0) null
            else NounCaseRevisionRefusal.NO_ACCUSATIVE_CUE
    }

    companion object {
        const val VERSION = 1
        private const val ACCUSATIVE_CUE = 36
        private const val ACCUSATIVE_SUPPORTED = 37
    }
}
