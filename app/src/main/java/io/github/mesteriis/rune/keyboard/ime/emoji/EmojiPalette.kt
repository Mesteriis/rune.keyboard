package io.github.mesteriis.rune.keyboard.ime.emoji

/** View-owned, single-thread palette state. No disk, editor reads or process-global recents. */
internal class EmojiPalette(
    private val loadCatalog: () -> EmojiCatalog,
    private val hasGlyph: (String) -> Boolean,
) {
    private val catalog by lazy(LazyThreadSafetyMode.NONE, loadCatalog)
    private val supported = mutableMapOf<String, Boolean>()
    private val recent = mutableListOf<EmojiEntry>()

    val categories: List<EmojiCategory> get() = catalog.categories
    val recents: List<EmojiEntry> get() = recent.toList()

    /** Only the opened category is filtered; unsupported results are cached as well. */
    fun entries(categoryId: String): List<EmojiEntry> = catalog.categories
        .firstOrNull { it.id == categoryId }?.entries.orEmpty()
        .filter { entry -> supported.getOrPut(entry.glyph) { hasGlyph(entry.glyph) } }

    /** Call only after the editor accepts insertion, so rejected taps cannot pollute recents. */
    fun recordCommitted(glyph: String) {
        val entry = catalog.categories.asSequence().flatMap { it.entries.asSequence() }
            .firstOrNull { it.glyph == glyph } ?: return
        recent.removeAll { it.glyph == glyph }
        recent.add(0, entry)
        if (recent.size > MAX_RECENTS) recent.removeAt(recent.lastIndex)
    }

    companion object {
        const val MAX_RECENTS = 32
    }
}
