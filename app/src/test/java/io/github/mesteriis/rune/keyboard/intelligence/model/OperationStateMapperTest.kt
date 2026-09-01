package io.github.mesteriis.rune.keyboard.intelligence.model

import io.github.mesteriis.rune.keyboard.intelligence.delivery.DeliveryJournal
import io.github.mesteriis.rune.keyboard.intelligence.delivery.DownloadObservation
import io.github.mesteriis.rune.keyboard.intelligence.delivery.JournalOperation
import io.github.mesteriis.rune.keyboard.intelligence.delivery.ModelFailureCode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class OperationStateMapperTest {
    @Test
    fun liveDownloadStateOverridesStaleBusyJournal() {
        val journal = DeliveryJournal(JournalOperation.DOWNLOADING, downloadId = 7)

        assertTrue(OperationStateMapper.map(journal, DownloadObservation.PAUSED) is ModelOperationState.WaitingForUnmeteredNetwork)
        assertTrue(OperationStateMapper.map(journal, DownloadObservation.PENDING) is ModelOperationState.Queued)
        assertTrue(OperationStateMapper.map(journal, DownloadObservation.RUNNING) is ModelOperationState.Downloading)
        assertTrue(OperationStateMapper.map(journal, DownloadObservation.FAILED) is ModelOperationState.Failed)
    }

    @Test
    fun mapsAllDurableOperationsAndStableFailures() {
        assertTrue(OperationStateMapper.map(DeliveryJournal(JournalOperation.SELF_TESTING)) is ModelOperationState.SelfTesting)
        val failed = OperationStateMapper.map(
            DeliveryJournal(JournalOperation.FAILED, failureCode = ModelFailureCode.HASH_MISMATCH),
        ) as ModelOperationState.Failed
        assertEquals("hash_mismatch", failed.failure.stableCode)
        val deleteFailed = OperationStateMapper.map(
            DeliveryJournal(JournalOperation.FAILED, failureCode = ModelFailureCode.DELETE_FAILED),
        ) as ModelOperationState.Failed
        assertEquals("delete_failed", deleteFailed.failure.stableCode)
    }
}
