package io.github.mesteriis.rune.keyboard.intelligence.client

import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringToken

/** Main-owner numeric guard. Session identities belong to the owner; no editor payload is retained. */
class LatestReplyGuard {
    private var session: Long? = null
    private var eligible = false
    private var latest: ScoringToken? = null
    private var requestSession: Long? = null
    private var lastRequest = 0L

    /** Returns whether normalized attachment changed; an identical attach preserves active work. */
    fun attach(sessionId: Long?, effectiveAvailability: Boolean): Boolean {
        require(sessionId == null || sessionId > 0)
        val nextEligible = effectiveAvailability && sessionId != null
        if (session == sessionId && eligible == nextEligible) return false
        session = sessionId; eligible = nextEligible; latest = null
        // A temporary null detach or demand toggle must not reset this session's watermark.
        if (sessionId != null && requestSession != sessionId) {
            requestSession = sessionId; lastRequest = 0
        }
        return true
    }
    fun begin(token: ScoringToken): Boolean {
        if (!eligible || session != token.sessionId || token.requestId <= lastRequest) return false
        lastRequest = token.requestId; latest = token; return true
    }
    fun accepts(token: ScoringToken): Boolean = eligible && latest == token
    fun accepts(token: ScoringToken, currentCompositionRevision: Long): Boolean =
        accepts(token) && token.revision == currentCompositionRevision
    fun invalidate() { latest = null }
    fun shouldBind() = eligible
}
