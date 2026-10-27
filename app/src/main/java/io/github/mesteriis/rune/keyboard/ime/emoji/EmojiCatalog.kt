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
        private val CATEGORY_ID = Regex("[a-z]+")

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
            val lines = text.dropLast(1).split('\n')
            require(lines.firstOrNull() == "# rune-emoji-catalog-v1") { "Unknown emoji catalog schema" }
            val categories = linkedMapOf<String, EmojiCategory>()
            val entries = linkedMapOf<String, MutableList<EmojiEntry>>()
            val seenGlyphs = hashSetOf<String>()
            var readingEntries = false
            lines.drop(1).forEach { line ->
                val columns = line.split('\t')
                require(columns.size == 6 && columns.all { field ->
                    field.isNotBlank() && field.none { it.isISOControl() || it == '\u2028' || it == '\u2029' }
                }) { "Invalid emoji catalog row" }
                val (kind, id, glyph) = columns
                require(id.matches(CATEGORY_ID)) { "Invalid emoji category ID" }
                val names = EmojiNames(columns[3], columns[4], columns[5])
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
            require(categories.isNotEmpty() && entries.values.all { it.isNotEmpty() }) {
                "Empty emoji category or catalog"
            }
            return EmojiCatalog(categories.map { (id, category) -> category.copy(entries = entries.getValue(id).toList()) })
        }
    }
}
