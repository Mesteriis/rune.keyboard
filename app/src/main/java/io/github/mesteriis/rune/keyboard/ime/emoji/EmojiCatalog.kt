package io.github.mesteriis.rune.keyboard.ime.emoji

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.InputStream
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction

internal data class EmojiNames(val english: String, val russian: String, val spanish: String) {
    fun inLanguage(language: KeyboardLanguage): String = when (language) {
        KeyboardLanguage.ENGLISH -> english
        KeyboardLanguage.RUSSIAN -> russian
        KeyboardLanguage.SPANISH -> spanish
    }
}

internal data class EmojiEntry(val glyph: String, val names: EmojiNames)

internal data class EmojiCategory(
    val id: String,
    val icon: String,
    val names: EmojiNames,
    val entries: List<EmojiEntry>,
)

/** Count and invalid-index checks need no names; successful access decodes one category once. */
internal class DeferredEmojiEntries(
    override val size: Int,
    decode: () -> List<EmojiEntry>,
) : AbstractList<EmojiEntry>() {
    private val values by lazy {
        decode().also { require(it.size == size) { "Emoji category count mismatch" } }
    }

    init { require(size > 0) }

    override fun get(index: Int): EmojiEntry {
        if (index !in 0 until size) throw IndexOutOfBoundsException("Emoji entry index out of range")
        return values[index]
    }
}

/** Packaged, build-verified data. Parsing preserves sequence bytes and source order. */
internal class EmojiCatalog private constructor(val categories: List<EmojiCategory>) {
    companion object {
        const val ASSET_PATH = "emoji/catalog-v1.tsv"
        private const val MAX_BYTES = 320_000
        private const val HEADER = "# rune-emoji-catalog-v1\n"

        /** Owns and closes the supplied stream, including on a malformed/oversized asset. */
        fun read(input: InputStream): EmojiCatalog = input.use { stream ->
            val output = java.io.ByteArrayOutputStream()
            val buffer = ByteArray(8192)
            while (true) {
                val count = stream.read(buffer)
                if (count < 0) break
                require(output.size() + count <= MAX_BYTES) { "Emoji catalog exceeds byte budget" }
                output.write(buffer, 0, count)
            }
            val decoder = Charsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
            parse(decoder.decode(ByteBuffer.wrap(output.toByteArray())).toString())
        }

        private fun parse(text: String): EmojiCatalog {
            require(text.endsWith('\n')) { "Emoji catalog must end with LF" }
            require(text.startsWith(HEADER)) { "Unknown emoji catalog schema" }
            val categories = linkedMapOf<String, EmojiCategory>()
            val entries = linkedMapOf<String, MutableList<EntrySource>>()
            val seenGlyphs = hashSetOf<String>()
            var readingEntries = false
            // Scan delimiters and validate controls/blank fields once. Reuse six field slots;
            // no whole-file line list, per-row split lists or repeated Unicode blank scans.
            val fields = IntArray(12)
            var fieldStart = HEADER.length
            var column = 0
            var nonBlank = false
            var cursor = fieldStart
            while (cursor < text.length) {
                val char = text[cursor]
                if (char != '\t' && char != '\n') {
                    require(char > '\u001F' && char !in '\u007F'..'\u009F' &&
                        char != '\u2028' && char != '\u2029') { "Invalid emoji catalog control" }
                    if (!nonBlank && !char.isWhitespace()) nonBlank = true
                    cursor++
                    continue
                }
                require(column < 6 && nonBlank) { "Invalid emoji catalog field" }
                fields[column * 2] = fieldStart
                fields[column * 2 + 1] = cursor
                column++
                fieldStart = ++cursor
                nonBlank = false
                if (char == '\t') continue
                require(column == 6) { "Invalid emoji catalog row" }
                column = 0
                require(fields[1] - fields[0] == 1) { "Invalid emoji catalog row type" }
                val kind = text[fields[0]]
                val id = text.substring(fields[2], fields[3])
                val glyph = text.substring(fields[4], fields[5])
                require(id.all { it in 'a'..'z' }) { "Invalid emoji category ID" }
                when (kind) {
                    'G' -> {
                        require(!readingEntries && id !in categories) { "Duplicate or late emoji category" }
                        entries[id] = mutableListOf()
                        categories[id] = EmojiCategory(id, glyph, EmojiNames(
                            text.substring(fields[6], fields[7]), text.substring(fields[8], fields[9]),
                            text.substring(fields[10], fields[11])), emptyList())
                    }
                    'E' -> {
                        readingEntries = true
                        val group = requireNotNull(entries[id]) { "Unknown emoji category" }
                        require(seenGlyphs.add(glyph)) { "Duplicate emoji sequence" }
                        group.add(EntrySource(glyph, fields[6], fields[7], fields[8], fields[9], fields[10], fields[11]))
                    }
                    else -> throw IllegalArgumentException("Unknown emoji catalog row type")
                }
            }
            require(column == 0 && fieldStart == text.length) { "Incomplete emoji catalog row" }
            require(categories.isNotEmpty() && entries.values.all { it.isNotEmpty() }) {
                "Empty emoji category or catalog"
            }
            return EmojiCatalog(categories.map { (id, category) ->
                val sources = entries.getValue(id).toList()
                category.copy(entries = DeferredEmojiEntries(sources.size) {
                    sources.map { source -> EmojiEntry(source.glyph, EmojiNames(
                        text.substring(source.enStart, source.enEnd), text.substring(source.ruStart, source.ruEnd),
                        text.substring(source.esStart, source.esEnd))) }
                })
            })
        }

        private data class EntrySource(val glyph: String, val enStart: Int, val enEnd: Int,
            val ruStart: Int, val ruEnd: Int, val esStart: Int, val esEnd: Int)
    }
}
