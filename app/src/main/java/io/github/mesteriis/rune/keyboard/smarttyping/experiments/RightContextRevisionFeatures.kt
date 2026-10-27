package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode

/** Frozen v1 model layout, separate from source-v2 admission and editor authority. */
internal class RightContextRevisionFeatures(
    private val right: RightContextGrammarFeatures,
    private val role: RightContextRoleFeatures,
) {
    constructor(dictionary: GrammarFeatureDictionary, pastDictionary: GrammarFeatureDictionary) :
        this(RightContextGrammarFeatures(dictionary), RightContextRoleFeatures(dictionary, pastDictionary))

    fun build(base: DoubleArray, leftContext: String, rightContext: String, applied: String, candidate: String): DoubleArray? {
        if (base.size != BASE || base.any { !it.isFinite() }) return null
        val oldWord = TokenUnicode.nfcOrNull(applied)?.takeIf { WORD.matches(it) } ?: return null
        val newWord = TokenUnicode.nfcOrNull(candidate)?.takeIf { WORD.matches(it) } ?: return null
        val following = right.extract(rightContext, candidate)
        val roles = role.extract(leftContext, rightContext, candidate)
        if (following.size != RightContextGrammarFeatures.COUNT || roles.size != RightContextRoleFeatures.COUNT ||
            following.any { !it.isFinite() } || roles.any { !it.isFinite() }) return null
        return DoubleArray(COUNT).also { result ->
            base.copyInto(result)
            following.copyInto(result, BASE)
            result[APPLIED] = if (TokenUnicode.folded(oldWord) == TokenUnicode.folded(newWord)) 1.0 else 0.0
            roles.copyInto(result, ROLE)
        }
    }

    companion object {
        const val VERSION = 1
        const val BASE = ContextualRanker.FEATURES
        const val APPLIED = BASE + RightContextGrammarFeatures.COUNT
        const val ROLE = APPLIED + 1
        const val COUNT = ROLE + RightContextRoleFeatures.COUNT
        private val WORD = Regex("[а-яёА-ЯЁ]{3,32}")
    }
}
