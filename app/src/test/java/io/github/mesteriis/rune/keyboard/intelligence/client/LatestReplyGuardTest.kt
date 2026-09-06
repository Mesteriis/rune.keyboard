package io.github.mesteriis.rune.keyboard.intelligence.client

import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringToken
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LatestReplyGuardTest {
    private fun token(id: Long, session: Long = 1, revision: Long = 1) =
        ScoringToken(session, revision, id, listOf(7, 8))

    @Test fun sameNormalizedAttachmentPreservesActiveReplyAndWatermark() {
        val guard = LatestReplyGuard()
        guard.attach(1, true)
        assertTrue(guard.begin(token(5)))
        guard.attach(1, true)
        assertTrue(guard.accepts(token(5), 1))
        assertFalse(guard.begin(token(5)))
        assertFalse(guard.begin(token(4)))
        assertTrue(guard.begin(token(6)))
    }

    @Test fun demandOffOnAndNullDetachDoNotRecycleSameSessionRequestIds() {
        val guard = LatestReplyGuard()
        guard.attach(1, true)
        assertTrue(guard.begin(token(5)))
        guard.attach(1, false)
        assertFalse(guard.accepts(token(5), 1))
        guard.attach(null, false)
        guard.attach(null, true) // both normalize to no binding
        guard.attach(1, true)
        assertFalse(guard.begin(token(5)))
        assertTrue(guard.begin(token(6)))
    }

    @Test fun sessionReplacementAllowsItsOwnSequenceAndRejectsOldReply() {
        val guard = LatestReplyGuard()
        guard.attach(1, true)
        assertTrue(guard.begin(token(Long.MAX_VALUE)))
        guard.attach(2, true)
        assertFalse(guard.accepts(token(Long.MAX_VALUE), 1))
        assertTrue(guard.begin(token(1, session = 2)))
        assertFalse(guard.begin(token(2)))
        assertFalse(guard.accepts(token(1, session = 2), 2))
        assertFalse(guard.accepts(ScoringToken(2, 1, 1, listOf(8, 7)), 1))
        guard.invalidate()
        assertFalse(guard.accepts(token(1, session = 2), 1))
        assertFalse(guard.begin(token(1, session = 2)))
    }
}
