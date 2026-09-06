package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.nio.ByteBuffer
import java.nio.channels.FileChannel
import java.nio.file.Files
import java.nio.file.StandardOpenOption
import org.junit.Assert.*
import org.junit.Test

class PackedLexiconValidationTest {
    @Test fun `trusted identity is checked before accepting self consistent swapped assets`() {
        val fixture = PackedFixture.build(listOf("a", "ab", "é", "ё", "😀"))
        val original = fixture.trusted()
        assertTrue(fixture.load(original) is PackedLexiconLoad.Ready)
        assertFailure(fixture.load(original.copy(expectedSha256 = "0".repeat(64))), PackedLoadFailure.MANIFEST)
        assertFailure(fixture.load(original.copy(language = KeyboardLanguage.SPANISH)), PackedLoadFailure.MANIFEST)
        fixture.put(fixture.ranks, 20, 5)
        val changed = fixture.trusted()
        assertFailure(fixture.load(changed.copy(expectedSha256 = original.expectedSha256)), PackedLoadFailure.MANIFEST)
        assertFailure(fixture.load(original), PackedLoadFailure.HASH)
        assertFailure(fixture.load(fixture.trusted(normalization = "different")), PackedLoadFailure.MANIFEST)
    }

    @Test fun `headers sizes positions mutability and overflow are rejected before node access`() {
        val fixture = PackedFixture.build(listOf("aa", "ba"))
        val trusted = fixture.trusted()
        for (size in listOf(0, 15, fixture.trie.size - 1, fixture.trie.size + 1)) {
            assertFailure(PackedLexiconData.validate(trusted, PackedFixture.readOnly(ByteArray(size)),
                PackedFixture.readOnly(fixture.lengths), PackedFixture.readOnly(fixture.ranks)), PackedLoadFailure.HEADER)
        }
        assertFailure(PackedLexiconData.validate(trusted, ByteBuffer.wrap(fixture.trie), PackedFixture.readOnly(fixture.lengths),
            PackedFixture.readOnly(fixture.ranks)), PackedLoadFailure.HEADER)
        val shifted = PackedFixture.readOnly(fixture.trie).apply { position(1) }
        assertFailure(PackedLexiconData.validate(trusted, shifted, PackedFixture.readOnly(fixture.lengths),
            PackedFixture.readOnly(fixture.ranks)), PackedLoadFailure.HEADER)
        for ((part, offset, value) in listOf(Triple(0, 0, 0), Triple(0, 4, Int.MAX_VALUE), Triple(0, 12, 8),
            Triple(1, 0, 0), Triple(1, 4, 2), Triple(1, 8, Int.MAX_VALUE), Triple(1, 12, 1),
            Triple(2, 0, 0), Triple(2, 4, Int.MAX_VALUE), Triple(2, 8, 8), Triple(2, 12, 1))) {
            val changed = PackedFixture.build(listOf("aa", "ba"))
            changed.put(listOf(changed.trie, changed.lengths, changed.ranks)[part], offset, value)
            assertFailure(changed.load(), PackedLoadFailure.HEADER)
        }
    }

    @Test fun `scalar root and index invariants are validated independently of asset hashes`() {
        for ((offset, value, reason) in listOf(
            Triple(16, 1, PackedLoadFailure.STRUCTURE), Triple(24, 1, PackedLoadFailure.STRUCTURE),
            Triple(28, 1, PackedLoadFailure.STRUCTURE), Triple(32, 0xd800, PackedLoadFailure.STRUCTURE),
            Triple(32, 0x110000, PackedLoadFailure.STRUCTURE), Triple(36, -1, PackedLoadFailure.INDEX),
            Triple(40, 999, PackedLoadFailure.INDEX), Triple(44, 999, PackedLoadFailure.INDEX),
        )) {
            val fixture = PackedFixture.build(listOf("aa", "ba"))
            fixture.put(fixture.trie, offset, value)
            assertFailure(fixture.load(), reason)
        }
    }

    @Test fun `cycles shared unreachable children sibling order and terminal ordinals fail closed`() {
        // Preorder ids: root=0, a=1, aa=2, b=3, ba=4.
        for ((offset, value) in listOf(40 to 1, 68 to 2, 40 to 0, 64 to 'a'.code, 60 to 2, 92 to 1)) {
            val fixture = PackedFixture.build(listOf("aa", "ba"))
            fixture.put(fixture.trie, offset, value)
            assertFailure(fixture.load(), PackedLoadFailure.STRUCTURE)
        }
    }

    @Test fun `length sidecar must equal actual descendant bounds and depth stays within thirty two`() {
        val fixture = PackedFixture.build(listOf("aa", "ba"))
        fixture.lengths[16] = 1
        assertFailure(fixture.load(), PackedLoadFailure.LENGTHS)
        val deep = PackedFixture.build(listOf("a".repeat(33)))
        for (i in 16 until deep.lengths.size) deep.lengths[i] = 32
        assertFailure(deep.load(), PackedLoadFailure.STRUCTURE)
        assertTrue(PackedFixture.build(listOf("a".repeat(32))).load() is PackedLexiconLoad.Ready)
    }

    @Test fun `rank bounds canonical normalization and lexical word digest are enforced`() {
        for ((offset, rank) in listOf(16 to 0, 20 to 0, 20 to -1, 20 to 50_001)) {
            val fixture = PackedFixture.build(listOf("a"))
            fixture.put(fixture.ranks, offset, rank)
            assertFailure(fixture.load(), PackedLoadFailure.RANKS)
        }
        val unranked = PackedFixture.build(listOf("a"))
        unranked.put(unranked.ranks, 20, Int.MAX_VALUE)
        assertTrue(unranked.load() is PackedLexiconLoad.Ready)
        for (word in listOf("A", "e\u0301", "a" + "\u0344".repeat(31))) {
            assertFailure(PackedFixture.build(listOf(word)).load(), PackedLoadFailure.CANONICAL)
        }
        val fixture = PackedFixture.build(listOf("a"))
        assertFailure(fixture.load(fixture.trusted(wordHash = "0".repeat(64))), PackedLoadFailure.CANONICAL)
    }

    @Test fun `mapping uses exact embedded region without overflow and survives descriptor closure`() {
        val file = Files.createTempFile("packed-region-", ".bin")
        try {
            Files.write(file, byteArrayOf(99, 98, 1, 2, 3, 97))
            val mapped = FileChannel.open(file, StandardOpenOption.READ).use { channel ->
                for ((offset, length, expected) in listOf(Triple(-1L, 3L, 3L), Triple(Long.MAX_VALUE, 3L, 3L),
                    Triple(2L, Long.MAX_VALUE, Long.MAX_VALUE), Triple(2L, 3L, 2L), Triple(4L, 3L, 3L))) {
                    val error = assertThrows(PackedValidationException::class.java) { PackedAssetMapping.map(channel, offset, length, expected) }
                    assertEquals(PackedLoadFailure.ASSET_RANGE, error.reason)
                }
                PackedAssetMapping.map(channel, 2, 3, 3)
            }
            assertTrue(mapped.isReadOnly)
            assertEquals(3, mapped.capacity())
            assertEquals(listOf<Byte>(1, 2, 3), (0..2).map { mapped.get(it) })
        } finally { Files.delete(file) }
    }

    @Test fun `load interruption produces a content free failure without clearing the signal`() {
        val fixture = PackedFixture.build(listOf("private"))
        try {
            Thread.currentThread().interrupt()
            val result = fixture.load()
            assertFailure(result, PackedLoadFailure.CANCELLED)
            assertTrue(Thread.currentThread().isInterrupted)
            assertFalse(result.toString().contains("private"))
        } finally { Thread.interrupted() }
    }

    private fun assertFailure(result: PackedLexiconLoad, reason: PackedLoadFailure) {
        assertEquals(PackedLexiconLoad.Failed(reason), result)
    }
}
