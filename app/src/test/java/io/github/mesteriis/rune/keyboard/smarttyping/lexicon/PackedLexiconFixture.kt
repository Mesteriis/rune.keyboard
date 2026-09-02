package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest

internal class PackedFixture(
    val words: List<String>,
    val trie: ByteArray,
    val lengths: ByteArray,
    val ranks: ByteArray,
    val language: KeyboardLanguage,
) {
    fun trusted(
        wordHash: String = sha((words.joinToString("\n") + "\n").toByteArray(Charsets.UTF_8)),
        normalization: String = PackedLexiconManifest.NORMALIZATION,
    ): TrustedPackedLexicon {
        val manifest = PackedLexiconManifest(language, words.size, (trie.size - 16) / 16,
            PackedAsset("lexicon/words.trie", trie.size.toLong(), sha(trie)),
            PackedAsset("lexicon/words.lengths", lengths.size.toLong(), sha(lengths)),
            PackedAsset("lexicon/frequency.ranks", ranks.size.toLong(), sha(ranks)), wordHash, "f".repeat(64),
            listOf(PackedAsset("lexicon/notices/license.txt", 1, "0".repeat(64))), normalization)
        return TrustedPackedLexicon(language, manifest.identity(), manifest)
    }

    fun load(trusted: TrustedPackedLexicon = trusted()): PackedLexiconLoad =
        PackedLexiconData.validate(trusted, readOnly(trie), readOnly(lengths), readOnly(ranks))

    fun ready(): PackedLexiconData = (load() as PackedLexiconLoad.Ready).lexicon

    fun put(bytes: ByteArray, offset: Int, value: Int) { ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).putInt(offset, value) }

    companion object {
        fun readOnly(bytes: ByteArray): ByteBuffer = ByteBuffer.wrap(bytes).asReadOnlyBuffer()
        fun sha(bytes: ByteArray): String = PackedLexiconManifest.hex(MessageDigest.getInstance("SHA-256").digest(bytes))

        fun build(input: List<String>, language: KeyboardLanguage = KeyboardLanguage.ENGLISH): PackedFixture {
            val words = input.distinct().sortedWith { a, b ->
                val left = a.codePoints().toArray()
                val right = b.codePoints().toArray()
                var order = 0
                for (i in 0 until minOf(left.size, right.size)) if (left[i] != right[i]) { order = left[i].compareTo(right[i]); break }
                if (order == 0) left.size.compareTo(right.size) else order
            }
            class Node(val label: Int, val depth: Int) {
                var ordinal = 0
                var id = 0
                val children = sortedMapOf<Int, Node>()
            }
            val root = Node(0, 0)
            for ((ordinal, word) in words.withIndex()) {
                var node = root
                for (cp in word.codePoints().toArray()) {
                    val parent = node
                    node = node.children.getOrPut(cp) { Node(cp, parent.depth + 1) }
                }
                node.ordinal = ordinal + 1
            }
            val nodes = mutableListOf<Node>()
            fun collect(node: Node) { node.id = nodes.size; nodes.add(node); node.children.values.forEach(::collect) }
            collect(root)
            val trie = ByteBuffer.allocate(16 + nodes.size * 16).order(ByteOrder.LITTLE_ENDIAN)
            trie.putInt(0x31525452).putInt(words.size).putInt(nodes.size).putInt(16)
            for (node in nodes) {
                trie.putInt(16 + node.id * 16, node.label)
                trie.putInt(20 + node.id * 16, node.children.values.firstOrNull()?.id ?: 0)
                trie.putInt(28 + node.id * 16, node.ordinal)
                node.children.values.zipWithNext().forEach { (left, right) -> trie.putInt(24 + left.id * 16, right.id) }
            }
            val lengths = ByteBuffer.allocate(16 + nodes.size * 2).order(ByteOrder.LITTLE_ENDIAN)
            lengths.putInt(0x314e454c).putInt(1).putInt(nodes.size).putInt(0)
            fun bounds(node: Node): Pair<Int, Int> {
                var low = if (node.ordinal != 0) node.depth else 33
                var high = if (node.ordinal != 0) node.depth else 0
                for (child in node.children.values) {
                    val pair = bounds(child)
                    low = minOf(low, pair.first); high = maxOf(high, pair.second)
                }
                lengths.put(16 + node.id * 2, low.toByte()).put(17 + node.id * 2, high.toByte())
                return low to high
            }
            bounds(root)
            val ranks = ByteBuffer.allocate(16 + (words.size + 1) * 4).order(ByteOrder.LITTLE_ENDIAN)
            ranks.putInt(0x314b4e52).putInt(words.size).putInt(4).putInt(0).putInt(Int.MAX_VALUE)
            for (ordinal in words.indices) ranks.putInt(ordinal + 1)
            return PackedFixture(words, trie.array(), lengths.array(), ranks.array(), language)
        }
    }
}
