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
            val entries = linkedMapOf<String, MutableList<EmojiEntry>>()
            val seenGlyphs = hashSetOf<String>()
            var readingEntries = false
            // Scan delimiters and validate controls/blank fields once. Reuse six field slots;
            // no whole-file line list, per-row split lists or repeated Unicode blank scans.
            val fields = arrayOfNulls<String>(6)
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
                require(column < fields.size && nonBlank) { "Invalid emoji catalog field" }
                fields[column++] = text.substring(fieldStart, cursor)
                fieldStart = ++cursor
                nonBlank = false
                if (char == '\t') continue
                require(column == fields.size) { "Invalid emoji catalog row" }
                column = 0
                val kind = fields[0]!!
                val id = fields[1]!!
                val glyph = fields[2]!!
                require(id.all { it in 'a'..'z' }) { "Invalid emoji category ID" }
                val names = EmojiNames(fields[3]!!, fields[4]!!, fields[5]!!)
                when (kind) {
                    "G" -> {
                        require(!readingEntries && id !in categories) { "Duplicate or late emoji category" }
                        entries[id] = mutableListOf()
                        categories[id] = EmojiCategory(id, glyph, names, emptyList())
                    }
                    "E" -> {
                        readingEntries = true
                        val group = requireNotNull(entries[id]) { "Unknown emoji category" }
                        require(seenGlyphs.add(glyph)) { "Duplicate emoji sequence" }
                        group.add(EmojiEntry(glyph, names))
                    }
                    else -> throw IllegalArgumentException("Unknown emoji catalog row type")
                }
            }
            require(column == 0 && fieldStart == text.length) { "Incomplete emoji catalog row" }
            require(categories.isNotEmpty() && entries.values.all { it.isNotEmpty() }) {
                "Empty emoji category or catalog"
            }
            return EmojiCatalog(categories.map { (id, category) -> category.copy(entries = entries.getValue(id).toList()) })
        }
    }
}
