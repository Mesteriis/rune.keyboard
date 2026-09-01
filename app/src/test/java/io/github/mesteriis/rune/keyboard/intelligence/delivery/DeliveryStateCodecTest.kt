package io.github.mesteriis.rune.keyboard.intelligence.delivery

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class DeliveryStateCodecTest {
    @Test
    fun roundTripsSchemaV1WithoutKeyboardPreferences() {
        val state = DeliveryJournal(
            operation = JournalOperation.DOWNLOADING,
            downloadId = 123,
            allowMetered = true,
            failureCode = null,
        )

        assertEquals(state, DeliveryStateCodec.decode(DeliveryStateCodec.encode(state)))
    }

    @Test
    fun rejectsUnknownSchemaAndMalformedState() {
        assertThrows(DeliveryStateException::class.java) {
            DeliveryStateCodec.decode("{\"schemaVersion\":2,\"operation\":\"IDLE\",\"downloadId\":null,\"allowMetered\":false,\"failureCode\":null}")
        }
        assertThrows(DeliveryStateException::class.java) {
            DeliveryStateCodec.decode("{\"schemaVersion\":1,\"operation\":\"NOPE\",\"downloadId\":null,\"allowMetered\":false,\"failureCode\":null}")
        }
    }
}
