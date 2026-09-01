package io.github.mesteriis.rune.keyboard.intelligence.model

import io.github.mesteriis.rune.keyboard.intelligence.delivery.DeliveryJournal
import io.github.mesteriis.rune.keyboard.intelligence.delivery.JournalOperation
import io.github.mesteriis.rune.keyboard.intelligence.delivery.ModelFailureCode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class OperationStateMapperTest {
    @Test
    fun mapsAllDurableOperationsAndStableFailures() {
        assertTrue(OperationStateMapper.map(DeliveryJournal(JournalOperation.SELF_TESTING)) is ModelOperationState.SelfTesting)
        val failed = OperationStateMapper.map(
            DeliveryJournal(JournalOperation.FAILED, failureCode = ModelFailureCode.HASH_MISMATCH),
        ) as ModelOperationState.Failed
        assertEquals("hash_mismatch", failed.failure.stableCode)
    }
}
