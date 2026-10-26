package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyLexicon
import java.util.Locale

internal enum class InfinitiveRevisionRefusal {
    UNCHANGED, PREVIOUS_NOT_UNAMBIGUOUS_FINITE, PROPOSAL_NOT_UNAMBIGUOUS_INFINITIVE,
    LEMMA_UNAVAILABLE, DIFFERENT_LEMMA, NO_INFINITIVE_CUE,
}

/** A restriction on a separately scored/admitted revision, never authority to edit. */
internal class InfinitiveRevisionScope(private val dictionary: GrammarFeatureDictionary) {
    private val grammar = GrammaticalContextFeatures(dictionary)

    fun refusal(context: String, previous: String, proposed: String,
        morphology: MorphologyLexicon): InfinitiveRevisionRefusal? {
        if (previous == proposed) return InfinitiveRevisionRefusal.UNCHANGED
        val before = dictionary.analyses(previous).analyses
        val after = dictionary.analyses(proposed).analyses
        if (before.isEmpty() || before.any { it.pos != "VERB" })
            return InfinitiveRevisionRefusal.PREVIOUS_NOT_UNAMBIGUOUS_FINITE
        if (after.isEmpty() || after.any { it.pos != "INFN" })
            return InfinitiveRevisionRefusal.PROPOSAL_NOT_UNAMBIGUOUS_INFINITIVE
        val oldLemma = morphology.lookup(KeyboardLanguage.RUSSIAN, previous.lowercase(Locale.ROOT))
        val newLemma = morphology.lookup(KeyboardLanguage.RUSSIAN, proposed.lowercase(Locale.ROOT))
        if (!oldLemma.available || !oldLemma.present || oldLemma.lemmaId == null ||
            !newLemma.available || !newLemma.present || newLemma.lemmaId == null)
            return InfinitiveRevisionRefusal.LEMMA_UNAVAILABLE
        if (oldLemma.lemmaId != newLemma.lemmaId) return InfinitiveRevisionRefusal.DIFFERENT_LEMMA
        return if (grammar.extract(context, proposed)[INFINITIVE_SUPPORTED] == 1.0) null
            else InfinitiveRevisionRefusal.NO_INFINITIVE_CUE
    }

    companion object {
        // Frozen 38-feature schema: cue at 24, infinitive-supported at 25.
        private const val INFINITIVE_SUPPORTED = 25
    }
}
