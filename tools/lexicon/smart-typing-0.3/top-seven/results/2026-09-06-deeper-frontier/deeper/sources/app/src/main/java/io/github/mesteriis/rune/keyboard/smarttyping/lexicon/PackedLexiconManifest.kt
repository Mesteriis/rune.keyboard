package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.nio.charset.StandardCharsets
import java.security.MessageDigest

data class PackedAsset(val path: String, val bytes: Long, val sha256: String)

/** Immutable typed release metadata. Notice identity stays separate from frequency-derived ranks. */
class PackedLexiconManifest(
    val language: KeyboardLanguage,
    val wordCount: Int,
    val nodeCount: Int,
    val trie: PackedAsset,
    val lengths: PackedAsset,
    val ranks: PackedAsset,
    val canonicalWordsSha256: String,
    val provenanceSha256: String,
    notices: List<PackedAsset>,
    val normalization: String = NORMALIZATION,
    val maximumFrequencyRank: Int = 50_000,
) {
    val notices: List<PackedAsset> = java.util.Collections.unmodifiableList(ArrayList(notices))

    /** Fixed LF-delimited ASCII identity, not a parser accepting arbitrary asset-supplied metadata. */
    internal fun identity(): String {
        val text = buildString {
            append("RUNE_PACKED_LEXICON_1\n")
            append(language.name).append('\n').append(normalization).append('\n')
            append(wordCount).append('\n').append(nodeCount).append('\n')
            append(maximumFrequencyRank).append('\n')
            for (asset in listOf(trie, lengths, ranks)) {
                append(asset.path).append('\n').append(asset.bytes).append('\n').append(asset.sha256).append('\n')
            }
            append(canonicalWordsSha256).append('\n').append(provenanceSha256).append('\n')
            append(notices.size).append('\n')
            for (notice in notices) {
                append(notice.path).append('\n').append(notice.bytes).append('\n').append(notice.sha256).append('\n')
            }
        }
        return hex(MessageDigest.getInstance("SHA-256").digest(text.toByteArray(StandardCharsets.US_ASCII)))
    }

    companion object {
        const val NORMALIZATION = "NFC_ROOT_LOWER_NFC_32_V1"
        internal fun hex(bytes: ByteArray): String {
            val digits = "0123456789abcdef"
            val out = CharArray(bytes.size * 2)
            for (i in bytes.indices) {
                val value = bytes[i].toInt() and 255
                out[i * 2] = digits[value ushr 4]
                out[i * 2 + 1] = digits[value and 15]
            }
            return String(out)
        }
    }
}

/** expectedSha256 and language MUST come from application release constants, never the same asset. */
data class TrustedPackedLexicon(
    val language: KeyboardLanguage,
    val expectedSha256: String,
    val manifest: PackedLexiconManifest,
)

enum class PackedLoadFailure { MANIFEST, HASH, HEADER, INDEX, STRUCTURE, LENGTHS, RANKS, CANONICAL, ASSET_RANGE, IO, CANCELLED }

sealed interface PackedLexiconLoad {
    data class Ready(val lexicon: PackedLexiconData) : PackedLexiconLoad
    data class Failed(val reason: PackedLoadFailure) : PackedLexiconLoad
}

internal class PackedValidationException(val reason: PackedLoadFailure) : Exception(reason.name)
internal fun packedRequire(condition: Boolean, reason: PackedLoadFailure) {
    if (!condition) throw PackedValidationException(reason)
}
