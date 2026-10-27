package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import org.junit.Assert.*
import org.junit.Test

class PackedContextIndexTest {
    private val magic = "RUCNTX01"
    private fun digest(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes)
    private fun hash(bytes: ByteArray) = digest(bytes).joinToString("") { "%02x".format(it.toInt() and 255) }
    private fun sealed(body: ByteArray) = body + digest(body)

    private fun fixture(records: List<Pair<String, ByteArray>>): ByteArray {
        val output = ByteArrayOutputStream()
        val offsets = ArrayList<Int>()
        var previous = byteArrayOf()
        records.forEachIndexed { index, (key, payload) ->
            val bytes = key.toByteArray(Charsets.UTF_8)
            var prefix = 0
            if (index % 32 == 0) offsets.add(output.size()) else {
                while (prefix < minOf(previous.size, bytes.size) && previous[prefix] == bytes[prefix]) prefix++
            }
            output.write(prefix); output.write(bytes.size - prefix)
            output.write(payload.size and 255); output.write(payload.size ushr 8)
            output.write(bytes, prefix, bytes.size - prefix); output.write(payload)
            previous = bytes
        }
        offsets.add(output.size())
        val header = ByteBuffer.allocate(24 + offsets.size * 4).order(ByteOrder.LITTLE_ENDIAN)
        header.put(magic.toByteArray()).putInt(32).putInt(records.size).putInt(offsets.size - 1).putInt(header.capacity())
        offsets.forEach { header.putInt(it) }
        return sealed(header.array() + output.toByteArray())
    }

    private fun open(bytes: ByteArray, expected: String = hash(bytes)) =
        PackedContextIndex.validate(ByteBuffer.wrap(bytes), magic, expected) { input, offset, size ->
            size == 4 && input.get(offset) != (-1).toByte()
        }

    private fun packaged(bytes: ByteArray, source: ByteBuffer = ByteBuffer.wrap(bytes).asReadOnlyBuffer(),
        size: Long = bytes.size.toLong()) = PackedContextIndex.openPackaged(source, magic, size) { input, offset, length ->
            length == 4 && input.get(offset) != (-1).toByte()
        }

    @Test fun exactLookupCrossesBlocksAndDistinguishesUtf8AndPairKeys() {
        val records = (0..64).map { "слово%03d".format(it) to byteArrayOf(it.toByte(), 0, 0, 0) } +
            listOf("я\u0000ел" to byteArrayOf(70, 0, 0, 0), "я\u0000ёл" to byteArrayOf(71, 0, 0, 0))
        val bytes = fixture(records)
        for (index in listOf(open(bytes)!!, packaged(bytes)!!)) {
            records.forEach { (key, payload) -> assertArrayEquals(key, payload, index.payload(key)) }
            for (key in listOf("", "а", "слово", "слово032x", "слово999", "я", "я\u0000ель", "я\u0000ёлка"))
                assertNull(key, index.payload(key))
            assertNull(index.payload("я".repeat(128)))
        }
    }

    @Test fun truncatedTamperedOrWrongIdentityNeverLoads() {
        val bytes = fixture(listOf("слово" to byteArrayOf(1, 0, 0, 0)))
        assertNull(open(bytes.copyOf(bytes.size - 1)))
        assertNull(open(bytes, "0".repeat(64)))
        assertNull(open(bytes.copyOf().apply { this[lastIndex] = (this[lastIndex].toInt() xor 1).toByte() }))
        assertNull(PackedContextIndex.open(ByteBuffer.wrap(bytes), "RUGRM001", hash(bytes)) { _, _, _ -> true })
    }

    @Test fun structuralAndPayloadValidationIsIndependentOfChecksum() {
        val bytes = fixture(listOf("слово" to byteArrayOf(1, 0, 0, 0)))
        val start = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).getInt(20)
        val edits: List<(ByteArray) -> Unit> = listOf(
            { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(8, 31) },
            { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(12, Int.MAX_VALUE) },
            { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(24, 1) },
            { it[start] = 1 },
            { it[start + 1] = 0 },
            { it[start + 2] = 0 },
            { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(28, 1) },
            { it[start + 4 + "слово".toByteArray().size] = -1 },
        )
        edits.forEachIndexed { number, edit ->
            val body = bytes.copyOf(bytes.size - 32); edit(body)
            assertNull("mutation $number", open(sealed(body)))
        }
        assertNull(open(fixture(listOf("б" to byteArrayOf(1, 0, 0, 0), "а" to byteArrayOf(2, 0, 0, 0)))))
        assertNull(open(fixture(listOf("а" to byteArrayOf(1, 0, 0, 0), "а" to byteArrayOf(2, 0, 0, 0)))))
    }

    @Test fun packagedPathRejectsMalformedHeadersBlocksAnchorsAndViews() {
        val bytes = fixture((0..64).map { "слово%03d".format(it) to byteArrayOf(1, 0, 0, 0) })
        val source = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN)
        val start = source.getInt(20)
        val secondBlock = start + source.getInt(28)
        val edits: List<(ByteArray) -> Unit> = listOf(
            { it[0] = 0 },
            { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(8, 31) },
            { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(12, Int.MAX_VALUE) },
            { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(16, 0) },
            { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(20, Int.MAX_VALUE) },
            { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(24, -1) },
            { ByteBuffer.wrap(it).order(ByteOrder.LITTLE_ENDIAN).putInt(28, Int.MAX_VALUE) },
            { it[secondBlock] = 1 }, { it[secondBlock + 1] = 0 },
            { it[secondBlock + 2] = -1; it[secondBlock + 3] = -1 },
        )
        edits.forEachIndexed { i, edit -> assertNull("mutation $i", packaged(bytes.copyOf().also(edit))) }
        assertNull(packaged(bytes, ByteBuffer.wrap(bytes)))
        assertNull(packaged(bytes, source.asReadOnlyBuffer().apply { position(1) }))
        assertNull(packaged(bytes, source.asReadOnlyBuffer().apply { limit(bytes.size - 1) }))
        assertNull(packaged(bytes, size = bytes.size.toLong() + 1))
    }

    @Test fun packagedLookupRefusesCorruptRecordsAndPayloadsBeforeReturningBytes() {
        val records = listOf("аб" to byteArrayOf(1, 0, 0, 0), "ав" to byteArrayOf(2, 0, 0, 0))
        val bytes = fixture(records)
        val start = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).getInt(20)
        val second = start + 4 + "аб".toByteArray().size + 4
        val suffix = bytes[second + 1].toInt() and 255
        val edits: List<(ByteArray) -> Unit> = listOf(
            { it[second] = 127 }, { it[second + 1] = 0 }, { it[second + 1] = -1 },
            { it[second + 2] = -1; it[second + 3] = -1 },
            { it[second + 4 + suffix] = -1 },
        )
        for (edit in edits) {
            val corrupt = bytes.copyOf().also(edit)
            val index = packaged(corrupt)!!
            assertArrayEquals(records[0].second, index.payload(records[0].first))
            assertNull(index.payload(records[1].first))
        }
    }

    @Test fun packagedPathIsNotAReplacementForChecksumValidation() {
        val bytes = fixture(listOf("слово" to byteArrayOf(1, 0, 0, 0)))
        bytes[bytes.lastIndex] = (bytes.last().toInt() xor 1).toByte()
        assertNotNull(packaged(bytes))
        assertNull(open(bytes))
    }
}
