package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.TokenUnicode
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.util.BitSet

/** Validated immutable mapping. Only the loader can construct it; buffers never escape. */
class PackedLexiconData private constructor(
    val language: KeyboardLanguage,
    val wordCount: Int,
    val nodeCount: Int,
    private val trie: ByteBuffer,
    private val lengths: ByteBuffer,
    private val ranks: ByteBuffer,
) {
    internal fun label(node: Int): Int = trie.getInt(16 + 16 * node)
    internal fun child(node: Int): Int = trie.getInt(20 + 16 * node)
    internal fun sibling(node: Int): Int = trie.getInt(24 + 16 * node)
    internal fun terminal(node: Int): Int = trie.getInt(28 + 16 * node)
    internal fun minLength(node: Int): Int = lengths.get(16 + 2 * node).toInt() and 255
    internal fun maxLength(node: Int): Int = lengths.get(17 + 2 * node).toInt() and 255
    internal fun rank(terminal: Int): Int = ranks.getInt(16 + 4 * terminal)
    override fun toString(): String = "PackedLexiconData(language=$language, words=$wordCount, nodes=$nodeCount)"

    companion object {
        /**
         * Off-main-thread load. Inputs must be read-only, position zero, full limit, with immutable
         * backing storage for the handle's lifetime (APK mappings in production). A read-only view
         * cannot make an externally writable alias safe; callers must not supply one.
         */
        fun validate(trusted: TrustedPackedLexicon, trie: ByteBuffer, lengths: ByteBuffer, ranks: ByteBuffer): PackedLexiconLoad {
            return try {
                verifyManifest(trusted)
                val manifest = trusted.manifest
                val data = PackedLexiconData(manifest.language, manifest.wordCount, manifest.nodeCount,
                    verifiedBuffer(trie, manifest.trie), verifiedBuffer(lengths, manifest.lengths), verifiedBuffer(ranks, manifest.ranks))
                data.validateStructure(manifest.canonicalWordsSha256, manifest.maximumFrequencyRank)
                PackedLexiconLoad.Ready(data)
            } catch (failure: PackedValidationException) {
                PackedLexiconLoad.Failed(failure.reason)
            } catch (_: Exception) {
                PackedLexiconLoad.Failed(if (Thread.currentThread().isInterrupted) PackedLoadFailure.CANCELLED else PackedLoadFailure.IO)
            }
        }

        internal fun verifyManifest(trusted: TrustedPackedLexicon) {
            val m = trusted.manifest
            fun hash(value: String) = value.length == 64 && value.all { it in '0'..'9' || it in 'a'..'f' }
            fun asset(value: PackedAsset): Boolean = value.bytes in 1..Int.MAX_VALUE.toLong() && hash(value.sha256) &&
                value.path.length in 1..160 && !value.path.startsWith('/') &&
                value.path.all { it in 'a'..'z' || it in 'A'..'Z' || it in '0'..'9' || it in "._-/" } &&
                value.path.split('/').all { it.isNotEmpty() && it != "." && it != ".." }
            packedRequire(m.language == trusted.language && hash(trusted.expectedSha256) &&
                m.normalization == PackedLexiconManifest.NORMALIZATION && m.wordCount > 0 && m.nodeCount > 1 &&
                m.maximumFrequencyRank in 1 until Int.MAX_VALUE &&
                hash(m.canonicalWordsSha256) && hash(m.provenanceSha256) && m.notices.size in 1..32 &&
                listOf(m.trie, m.lengths, m.ranks).all(::asset) && m.notices.all(::asset), PackedLoadFailure.MANIFEST)
            val paths = listOf(m.trie.path, m.lengths.path, m.ranks.path) + m.notices.map { it.path }
            packedRequire(paths.distinct().size == paths.size && m.notices.map { it.path } == m.notices.map { it.path }.sorted(), PackedLoadFailure.MANIFEST)
            // Trust identity before using declared sizes/counts to inspect assets or allocate validation state.
            packedRequire(m.identity() == trusted.expectedSha256, PackedLoadFailure.MANIFEST)
            packedRequire(m.trie.bytes == 16L + 16L * m.nodeCount && m.lengths.bytes == 16L + 2L * m.nodeCount &&
                m.ranks.bytes == 16L + 4L * (m.wordCount.toLong() + 1), PackedLoadFailure.HEADER)
            checkInterrupted()
        }

        private fun verifiedBuffer(input: ByteBuffer, asset: PackedAsset): ByteBuffer {
            packedRequire(input.isReadOnly && input.position() == 0 && input.limit() == input.capacity() &&
                input.capacity().toLong() == asset.bytes, PackedLoadFailure.HEADER)
            val digest = MessageDigest.getInstance("SHA-256")
            val scratch = ByteArray(8_192)
            val view = input.duplicate()
            while (view.hasRemaining()) {
                checkInterrupted()
                val count = minOf(view.remaining(), scratch.size)
                view.get(scratch, 0, count)
                digest.update(scratch, 0, count)
            }
            packedRequire(PackedLexiconManifest.hex(digest.digest()) == asset.sha256, PackedLoadFailure.HASH)
            return input.asReadOnlyBuffer().order(ByteOrder.LITTLE_ENDIAN)
        }

        internal fun checkInterrupted() {
            packedRequire(!Thread.currentThread().isInterrupted, PackedLoadFailure.CANCELLED)
        }
    }

    private fun validateStructure(wordsSha256: String, maximumRank: Int) {
        packedRequire(trie.getInt(0) == 0x31525452 && trie.getInt(4) == wordCount && trie.getInt(8) == nodeCount && trie.getInt(12) == 16,
            PackedLoadFailure.HEADER)
        packedRequire(lengths.getInt(0) == 0x314e454c && lengths.getInt(4) == 1 && lengths.getInt(8) == nodeCount && lengths.getInt(12) == 0,
            PackedLoadFailure.HEADER)
        packedRequire(ranks.getInt(0) == 0x314b4e52 && ranks.getInt(4) == wordCount && ranks.getInt(8) == 4 && ranks.getInt(12) == 0,
            PackedLoadFailure.HEADER)
        packedRequire(label(0) == 0 && sibling(0) == 0 && terminal(0) == 0, PackedLoadFailure.STRUCTURE)
        for (node in 0 until nodeCount) {
            if (node and 1023 == 0) checkInterrupted()
            val cp = label(node)
            packedRequire(cp in 0..0x10ffff && cp !in 0xd800..0xdfff, PackedLoadFailure.STRUCTURE)
            packedRequire(child(node) in 0 until nodeCount && sibling(node) in 0 until nodeCount && terminal(node) in 0..wordCount,
                PackedLoadFailure.INDEX)
            packedRequire(minLength(node) in 1..32 && maxLength(node) in minLength(node)..32, PackedLoadFailure.LENGTHS)
        }
        packedRequire(rank(0) == Int.MAX_VALUE, PackedLoadFailure.RANKS)
        for (ordinal in 1..wordCount) {
            if (ordinal and 1023 == 0) checkInterrupted()
            packedRequire(rank(ordinal) in 1..maximumRank || rank(ordinal) == Int.MAX_VALUE, PackedLoadFailure.RANKS)
        }

        // One bit per node and depth<=32 stacks. No node objects, recursion, or retained word list.
        val visited = BitSet(nodeCount)
        val nodes = IntArray(33)
        val next = IntArray(33)
        val lastLabel = IntArray(33) { -1 }
        val low = IntArray(33) { 33 }
        val high = IntArray(33)
        val path = IntArray(32)
        val digest = MessageDigest.getInstance("SHA-256")
        visited.set(0)
        var visitedCount = 1
        var ordinal = 0
        var depth = 0
        next[0] = child(0)
        while (depth >= 0) {
            if (visitedCount and 1023 == 0) checkInterrupted()
            val node = next[depth]
            if (node == 0) {
                packedRequire(low[depth] == minLength(nodes[depth]) && high[depth] == maxLength(nodes[depth]), PackedLoadFailure.LENGTHS)
                if (depth > 0) {
                    low[depth - 1] = minOf(low[depth - 1], low[depth])
                    high[depth - 1] = maxOf(high[depth - 1], high[depth])
                }
                depth--
                continue
            }
            packedRequire(!visited[node] && depth < 32 && label(node) > lastLabel[depth], PackedLoadFailure.STRUCTURE)
            visited.set(node)
            visitedCount++
            lastLabel[depth] = label(node)
            next[depth] = sibling(node)
            path[depth] = label(node)
            depth++
            nodes[depth] = node
            next[depth] = child(node)
            lastLabel[depth] = -1
            val terminal = terminal(node)
            low[depth] = if (terminal != 0) depth else 33
            high[depth] = if (terminal != 0) depth else 0
            if (terminal != 0) {
                packedRequire(terminal == ++ordinal, PackedLoadFailure.STRUCTURE)
                val word = String(path, 0, depth)
                val canonical = try { TokenUnicode.bounded(word) && TokenUnicode.folded(word) == word }
                    catch (_: IllegalArgumentException) { false }
                packedRequire(canonical, PackedLoadFailure.CANONICAL)
                digest.update(word.toByteArray(StandardCharsets.UTF_8))
                digest.update(10.toByte())
            }
        }
        checkInterrupted()
        packedRequire(visitedCount == nodeCount && ordinal == wordCount, PackedLoadFailure.STRUCTURE)
        packedRequire(PackedLexiconManifest.hex(digest.digest()) == wordsSha256, PackedLoadFailure.CANONICAL)
    }
}
