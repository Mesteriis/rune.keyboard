package io.github.mesteriis.rune.keyboard.smarttyping.abbreviations

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.text.Normalizer
import java.util.Locale

data class Abbreviation(val language: KeyboardLanguage, val key: String, val expansion: String) {
    override fun toString() = "Abbreviation(language=$language)"
}

enum class AbbreviationResult { SAVED, INVALID, DUPLICATE, LIMIT, NOT_FOUND, NOT_READY, IO_FAILURE }

/** Explicit settings entries only. No editor learning, imports, default seeds or automatic edits. */
class AbbreviationModel {
    private var entries = emptyList<Abbreviation>()

    @Synchronized fun snapshot(): List<Abbreviation> = entries.toList()

    @Synchronized fun expansion(token: String, language: KeyboardLanguage): String? {
        val key = normalizeKey(token) ?: return null
        return entries.firstOrNull { it.language == language && it.key == key }?.expansion
    }

    @Synchronized internal fun restore(snapshot: List<Abbreviation>) {
        validate(snapshot)
        entries = snapshot.toList()
    }

    /** A non-null original makes replacement explicit and prevents overwriting another mapping. */
    @Synchronized internal fun save(language: KeyboardLanguage, key: String, expansion: String,
        original: Abbreviation? = null): AbbreviationResult {
        val normalized = normalizeKey(key) ?: return AbbreviationResult.INVALID
        if (!validExpansion(expansion)) return AbbreviationResult.INVALID
        val previous = original?.let { entries.indexOf(it) }
        if (previous == -1) return AbbreviationResult.NOT_FOUND
        if (entries.withIndex().any { (index, value) -> index != previous &&
                value.language == language && value.key == normalized }) return AbbreviationResult.DUPLICATE
        if (original == null && entries.size >= MAX_ENTRIES) return AbbreviationResult.LIMIT
        val updated = entries.toMutableList()
        val entry = Abbreviation(language, normalized, expansion)
        if (previous == null) updated.add(entry) else updated[previous] = entry
        entries = updated
        return AbbreviationResult.SAVED
    }

    @Synchronized internal fun delete(entry: Abbreviation): AbbreviationResult {
        if (entry !in entries) return AbbreviationResult.NOT_FOUND
        entries = entries - entry
        return AbbreviationResult.SAVED
    }

    companion object {
        const val MAX_ENTRIES = 128
        const val MAX_KEY_CODE_POINTS = 32
        const val MAX_EXPANSION_CODE_POINTS = 128

        fun normalizeKey(value: String): String? {
            if (value.length > MAX_KEY_CODE_POINTS * 2 || value.isEmpty()) return null
            val normalized = Normalizer.normalize(value.lowercase(Locale.ROOT), Normalizer.Form.NFC)
            if (normalized.codePointCount(0, normalized.length) > MAX_KEY_CODE_POINTS) return null
            var hasLetter = false
            var offset = 0
            while (offset < normalized.length) {
                val cp = normalized.codePointAt(offset)
                if (Character.isLetter(cp)) hasLetter = true else if (!isMark(cp)) return null
                offset += Character.charCount(cp)
            }
            return normalized.takeIf { hasLetter && Character.isLetter(it.codePointAt(0)) }
        }

        fun validExpansion(value: String): Boolean {
            if (value.isEmpty() || value.length > MAX_EXPANSION_CODE_POINTS * 2 || value != value.trim() ||
                value.codePointCount(0, value.length) > MAX_EXPANSION_CODE_POINTS) return false
            var offset = 0
            while (offset < value.length) {
                val cp = value.codePointAt(offset)
                if (!(Character.isLetterOrDigit(cp) || isMark(cp) || cp == ' '.code ||
                    Character.getType(cp) in punctuationTypes)) return false
                offset += Character.charCount(cp)
            }
            return true
        }

        internal fun validate(snapshot: List<Abbreviation>) {
            require(snapshot.size <= MAX_ENTRIES && snapshot.all {
                normalizeKey(it.key) == it.key && validExpansion(it.expansion)
            } && snapshot.map { it.language to it.key }.distinct().size == snapshot.size) { "Invalid abbreviations" }
        }

        private fun isMark(cp: Int) = Character.getType(cp) in markTypes
        private val markTypes = setOf(Character.NON_SPACING_MARK.toInt(), Character.COMBINING_SPACING_MARK.toInt())
        private val punctuationTypes = setOf(Character.CONNECTOR_PUNCTUATION.toInt(), Character.DASH_PUNCTUATION.toInt(),
            Character.START_PUNCTUATION.toInt(), Character.END_PUNCTUATION.toInt(), Character.OTHER_PUNCTUATION.toInt(),
            Character.INITIAL_QUOTE_PUNCTUATION.toInt(), Character.FINAL_QUOTE_PUNCTUATION.toInt())
    }
}
