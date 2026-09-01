package io.github.mesteriis.rune.keyboard.intelligence.runtime

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class ActiveModelPointerCodecTest {
    @Test
    fun roundTripsSchemaV1() {
        val pointer = ActiveModelPointer("rune-text-v1-0.1.0", "rune-text-v1-0.0.9")
        assertEquals(pointer, ActiveModelPointerCodec.decode(ActiveModelPointerCodec.encode(pointer)))
    }

    @Test
    fun rejectsTraversalAndUnknownSchema() {
        assertThrows(IllegalArgumentException::class.java) {
            ActiveModelPointerCodec.decode("{\"schemaVersion\":1,\"active\":\"../bad\",\"rollback\":null}")
        }
        assertThrows(IllegalArgumentException::class.java) {
            ActiveModelPointerCodec.decode("{\"schemaVersion\":2,\"active\":null,\"rollback\":null}")
        }
    }
}
