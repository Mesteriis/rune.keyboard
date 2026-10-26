package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

data class RareWordMembership(val available: Boolean, val present: Boolean, val rank: Int? = null) {
    companion object {
        val UNAVAILABLE = RareWordMembership(false, false)
        val ABSENT = RareWordMembership(true, false)
    }
}

/** Immutable exact public-entity lookup. Rank is the frozen descending occurrence order. */
fun interface RareWordLexicon {
    fun lookup(key: String): RareWordMembership

    companion object {
        val UNAVAILABLE = RareWordLexicon { RareWordMembership.UNAVAILABLE }
    }
}
