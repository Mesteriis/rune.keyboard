package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.channels.FileChannel
import java.nio.file.StandardOpenOption
import java.security.MessageDigest

/** Host experiment only. Original exact lookup charges its original shared budget. */
internal class ProbeRadixLexicon(handles: List<PackedLexiconData>, directory: File) : CandidateLexicon {
    private val original = PackedCandidateLexicon(handles)
    private val compressed = handles.associate { handle ->
        val trust = listOf(FrozenPackedLexicons.ENGLISH, FrozenPackedLexicons.RUSSIAN, FrozenPackedLexicons.SPANISH)
            .single { it.language == handle.language }
        handle.language to ProbeRadixData.load(File(directory, "${handle.language.locale.language}.radix"),
            ProbeRadixIdentities.assets.getValue(handle.language), trust.manifest.canonicalWordsSha256, handle)
    }
    private val selector = ProbeRadixTopSeven(compressed::get)

    override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl) =
        original.exact(language, key, control)
    override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int, control: CandidateSearchControl,
        visitor: CandidateVisitor) = original.scan(language, key, unitRadius, control, visitor)
    override fun selectTop(key: String, route: LanguageRoute, pattern: CasePattern, control: CandidateSearchControl) =
        selector.select(key, route, pattern, control)
}

internal class ProbeRadixData private constructor(private val data: ByteBuffer,
    private val rankSource: PackedLexiconData, private val nodes: Int, private val blob: Int) {
    fun child(node: Int) = data.getInt(24 + 20 * node + 4)
    fun sibling(node: Int) = data.getInt(24 + 20 * node + 8)
    fun terminal(node: Int) = data.getInt(24 + 20 * node + 12)
    fun minLength(node: Int) = byte(24 + 20 * node + 18)
    fun maxLength(node: Int) = byte(24 + 20 * node + 19)
    fun rank(ordinal: Int) = rankSource.rank(ordinal)
    private fun byte(offset: Int) = data.get(offset).toInt() and 255

    /** At most128 bytes; no allocation or query retention. Called only after charging this edge. */
    fun copyLabel(node: Int, target: IntArray, start: Int): Int {
        val record = 24 + 20 * node
        val count = byte(record + 16)
        check(start >= 0 && start + count <= target.size && start + count <= 32) { "RADIX_DEPTH" }
        var offset = blob + data.getInt(record)
        val end = offset + byte(record + 17)
        var index = start
        while (offset < end) {
            val first = byte(offset++)
            val size = when (first) { in 0..0x7f -> 1; in 0xc2..0xdf -> 2; in 0xe0..0xef -> 3; in 0xf0..0xf4 -> 4; else -> error("RADIX_UTF8") }
            var cp = first and when (size) { 1 -> 0x7f; 2 -> 0x1f; 3 -> 0xf; else -> 7 }
            check(offset + size - 1 <= end && index < start + count) { "RADIX_UTF8_LENGTH" }
            repeat(size - 1) {
                val next = byte(offset++)
                check(next in 0x80..0xbf) { "RADIX_UTF8_CONTINUATION" }
                cp = cp * 64 + (next and 63)
            }
            check(cp >= when (size) { 1 -> 0; 2 -> 0x80; 3 -> 0x800; else -> 0x10000 } &&
                cp <= 0x10ffff && cp !in 0xd800..0xdfff) { "RADIX_UTF8_SCALAR" }
            target[index++] = cp
        }
        check(index == start + count) { "RADIX_SCALAR_COUNT" }
        return count
    }

    private fun validate(wordsSha: String) {
        var nextNode = 0
        var nextByte = 0
        var ordinal = 0
        val path = IntArray(32)
        val digest = MessageDigest.getInstance("SHA-256")
        fun visit(node: Int, depth: Int) {
            check(!Thread.currentThread().isInterrupted) { "CANCELLED" }
            check(node == nextNode++ && node < nodes) { "RADIX_PREORDER" }
            val record = 24 + 20 * node
            val length = byte(record + 17)
            check(data.getInt(record) == nextByte && nextByte.toLong() + length <= data.capacity() - blob &&
                child(node) in 0 until nodes && sibling(node) in 0 until nodes &&
                terminal(node) in 0..rankSource.wordCount) { "RADIX_FIELDS" }
            val count = copyLabel(node, path, depth)
            check(if (node == 0) count == 0 && length == 0 && terminal(node) == 0 && sibling(node) == 0 else count > 0) { "RADIX_ROOT" }
            nextByte += length
            val endDepth = depth + count
            var low = 33
            var high = 0
            if (terminal(node) != 0) {
                check(terminal(node) == ++ordinal) { "RADIX_ORDINAL" }
                low = endDepth; high = endDepth
                digest.update(String(path, 0, endDepth).toByteArray(Charsets.UTF_8)); digest.update(10.toByte())
            }
            var edge = child(node)
            var last = -1
            var children = 0
            while (edge != 0) {
                visit(edge, endDepth)
                check(path[endDepth] > last) { "RADIX_SIBLING_ORDER" }
                last = path[endDepth]
                low = minOf(low, minLength(edge)); high = maxOf(high, maxLength(edge))
                edge = sibling(edge); children++
            }
            check(low in 1..32 && high in low..32 && minLength(node) == low && maxLength(node) == high &&
                (node == 0 || terminal(node) != 0 || children != 1)) { "RADIX_LENGTHS_OR_COMPRESSION" }
        }
        visit(0, 0)
        check(nextNode == nodes && nextByte == data.capacity() - blob && ordinal == rankSource.wordCount &&
            PackedLexiconManifest.hex(digest.digest()) == wordsSha) { "RADIX_IDENTITY" }
    }

    companion object {
        fun load(file: File, asset: PackedAsset, wordsSha: String, rankSource: PackedLexiconData): ProbeRadixData {
            val mapped = FileChannel.open(file.toPath(), StandardOpenOption.READ).use {
                check(it.size() == asset.bytes && asset.bytes in 24..Int.MAX_VALUE.toLong()) { "RADIX_BYTES" }
                it.map(FileChannel.MapMode.READ_ONLY, 0, it.size()).order(ByteOrder.LITTLE_ENDIAN)
            }
            val digest = MessageDigest.getInstance("SHA-256")
            digest.update(mapped.duplicate())
            check(PackedLexiconManifest.hex(digest.digest()) == asset.sha256) { "RADIX_HASH" }
            val nodes = mapped.getInt(8)
            val blobSize = mapped.getInt(20)
            check(mapped.getInt(0) == 0x31584452 && mapped.getInt(4) == 1 && nodes > 1 &&
                mapped.getInt(12) == rankSource.wordCount && mapped.getInt(16) == 20 && blobSize > 0 &&
                24L + 20L * nodes + blobSize == mapped.capacity().toLong()) { "RADIX_HEADER" }
            return ProbeRadixData(mapped, rankSource, nodes, 24 + 20 * nodes).also { it.validate(wordsSha) }
        }
    }
}
