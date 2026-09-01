package io.github.mesteriis.rune.keyboard.intelligence.delivery

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class DeliveryStateCodecTest {
    @Test
    fun roundTripsSchemaV3WithoutKeyboardPreferences() {
        val state = DeliveryJournal(
            operation = JournalOperation.SELF_TESTING,
            failureCode = ModelFailureCode.RUNTIME_SELF_TEST_FAILED,
            activationPhase = ActivationPhase.ROLLBACK_COMMIT,
            activationDirectory = "rune-text-0.1.0",
        )

        assertEquals(state, DeliveryStateCodec.decode(DeliveryStateCodec.encode(state)))
    }

    @Test
    fun readsPreRuntimeSchemaV1AsHavingNoActivationPhase() {
        val json = "{\"schemaVersion\":1,\"operation\":\"DOWNLOADING\",\"downloadId\":123,\"allowMetered\":true,\"failureCode\":null}"

        assertEquals(
            DeliveryJournal(JournalOperation.DOWNLOADING, 123, allowMetered = true),
            DeliveryStateCodec.decode(json),
        )
    }

    @Test
    fun readsPhaseOnlySchemaV2WithoutGuessingActivationDirectory() {
        val json = "{\"schemaVersion\":2,\"operation\":\"SELF_TESTING\",\"downloadId\":null,\"allowMetered\":false,\"failureCode\":null,\"activationPhase\":\"POINTER_COMMIT\"}"

        assertEquals(
            DeliveryJournal(
                operation = JournalOperation.SELF_TESTING,
                activationPhase = ActivationPhase.POINTER_COMMIT,
            ),
            DeliveryStateCodec.decode(json),
        )
    }

    @Test
    fun rejectsUnknownSchemaAndMalformedState() {
        assertThrows(DeliveryStateException::class.java) {
            DeliveryStateCodec.decode("{\"schemaVersion\":4,\"operation\":\"IDLE\",\"downloadId\":null,\"allowMetered\":false,\"failureCode\":null,\"activationPhase\":null,\"activationDirectory\":null}")
        }
        assertThrows(DeliveryStateException::class.java) {
            DeliveryStateCodec.decode("{\"schemaVersion\":1,\"operation\":\"NOPE\",\"downloadId\":null,\"allowMetered\":false,\"failureCode\":null}")
        }
        assertThrows(IllegalArgumentException::class.java) {
            DeliveryStateCodec.encode(DeliveryJournal(activationDirectory = "../escape"))
        }
    }

    @Test
    fun onlyDurableCommitPhasesRequestJobRetry() {
        assertTrue(
            DeliveryJournal(
                operation = JournalOperation.SELF_TESTING,
                activationPhase = ActivationPhase.POINTER_COMMIT,
                activationDirectory = "rune-text-0.1.0",
            ).needsActivationRetry(),
        )
        assertFalse(
            DeliveryJournal(
                operation = JournalOperation.SELF_TESTING,
                activationPhase = ActivationPhase.CANDIDATE_SELF_TEST,
                activationDirectory = "rune-text-0.1.0",
            ).needsActivationRetry(),
        )
        assertFalse(
            DeliveryJournal(
                operation = JournalOperation.FAILED,
                activationPhase = ActivationPhase.ROLLBACK_COMMIT,
                activationDirectory = "rune-text-0.1.0",
            ).needsActivationRetry(),
        )
    }
}
