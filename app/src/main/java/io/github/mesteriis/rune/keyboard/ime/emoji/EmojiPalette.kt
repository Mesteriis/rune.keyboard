package io.github.mesteriis.rune.keyboard.ime.emoji

/** View-owned, single-thread palette state. No disk, editor reads or process-global recents. */
internal class EmojiPalette(
    private val loadCatalog: () -> EmojiCatalog,
    private val hasGlyph: (String) -> Boolean,
) {
    private val catalog by lazy(LazyThreadSafetyMode.NONE, loadCatalog)
    private val supported = mutableMapOf<String, Boolean>()
    private var openedEntries: List<EmojiEntry> = emptyList()
    private val recent = mutableListOf<EmojiEntry>()

    val categories: List<EmojiCategory> get() = catalog.categories
    val recents: List<EmojiEntry> get() = recent.toList()

    /** Only the opened category is filtered; unsupported results are cached as well. */
    fun entries(categoryId: String): List<EmojiEntry> {
        val entries = catalog.categories.firstOrNull { it.id == categoryId }?.entries.orEmpty()
        fun allowed(glyph: String) = supported.getOrPut(glyph) { hasGlyph(glyph) }
        return (if (entries is DeferredEmojiEntries) entries.filterGlyphs(::allowed)
            else entries.filter { allowed(it.glyph) }).also { openedEntries = it }
    }

    /** Call only after the editor accepts insertion, so rejected taps cannot pollute recents. */
    fun recordCommitted(glyph: String) {
        val opened = openedEntries
        val entry = (if (opened is EmojiGlyphLookup) opened.findGlyph(glyph)
            else opened.firstOrNull { it.glyph == glyph })
            ?: recent.firstOrNull { it.glyph == glyph }
            ?: catalog.categories.asSequence().flatMap { it.entries.asSequence() }
            .firstOrNull { it.glyph == glyph } ?: return
        recent.removeAll { it.glyph == glyph }
        recent.add(0, entry)
        if (recent.size > MAX_RECENTS) recent.removeAt(recent.lastIndex)
    }

    companion object {
        const val MAX_RECENTS = 32
    }
}
