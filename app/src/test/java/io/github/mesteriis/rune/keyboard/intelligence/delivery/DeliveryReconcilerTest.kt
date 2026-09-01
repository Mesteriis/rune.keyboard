package io.github.mesteriis.rune.keyboard.intelligence.delivery

import org.junit.Assert.assertEquals
import org.junit.Test

class DeliveryReconcilerTest {
    @Test
    fun downloadObservationsDriveRecoveryWithoutTrustingBroadcasts() {
        val queued = DeliveryJournal(operation = JournalOperation.QUEUED, downloadId = 41, allowMetered = false)

        assertEquals(ReconcileAction.WaitingForDownload, DeliveryReconciler.reconcile(queued, DownloadObservation.RUNNING, PrivateObservation.EMPTY))
        assertEquals(ReconcileAction.WaitingForUnmeteredNetwork, DeliveryReconciler.reconcile(queued, DownloadObservation.PAUSED, PrivateObservation.EMPTY))
        assertEquals(ReconcileAction.VerifyDownload(41), DeliveryReconciler.reconcile(queued, DownloadObservation.SUCCESSFUL, PrivateObservation.EMPTY))
        assertEquals(ReconcileAction.Fail(ModelFailureCode.DOWNLOAD_MISSING), DeliveryReconciler.reconcile(queued, DownloadObservation.MISSING, PrivateObservation.EMPTY))
    }

    @Test
    fun privateCandidateWinsOverStaleJournalAcrossCrashWindows() {
        val installing = DeliveryJournal(operation = JournalOperation.INSTALLING, downloadId = 41, allowMetered = false)

        assertEquals(ReconcileAction.AdoptVerifiedCandidate, DeliveryReconciler.reconcile(installing, DownloadObservation.MISSING, PrivateObservation(candidateExists = true, installingExists = false)))
        assertEquals(ReconcileAction.RemovePartialAndRetry, DeliveryReconciler.reconcile(installing, DownloadObservation.SUCCESSFUL, PrivateObservation(candidateExists = false, installingExists = true)))
    }

    @Test
    fun meteredOverrideReplacesOnlyTheRecordedRequestAndKeepsRoamingForbidden() {
        val action = DeliveryReconciler.requestMeteredOverride(
            DeliveryJournal(operation = JournalOperation.WAITING_UNMETERED, downloadId = 41, allowMetered = false),
        )

        assertEquals(41, action.removeDownloadId)
        assertEquals(true, action.requeueAllowedOverMetered)
        assertEquals(false, action.requeueAllowedOverRoaming)
    }
}
