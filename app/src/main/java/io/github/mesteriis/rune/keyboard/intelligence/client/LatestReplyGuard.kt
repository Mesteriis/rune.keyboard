package io.github.mesteriis.rune.keyboard.intelligence.client

import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringToken

/** PR7 supplies its current composition revision; this guard never retains editor payload. */
class LatestReplyGuard {
    private var session: Long? = null
    private var eligible = false
    private var latest: ScoringToken? = null
    private var lastRequest = 0L
    fun attach(sessionId: Long?, effectiveAvailability: Boolean) {
        require(sessionId == null || sessionId > 0)
        session = sessionId; eligible = effectiveAvailability && sessionId != null
        latest = null; lastRequest = 0
    }
    fun begin(token: ScoringToken): Boolean {
        if (!eligible || session != token.sessionId || token.requestId <= lastRequest) return false
        lastRequest = token.requestId; latest = token; return true
    }
    fun accepts(token: ScoringToken, currentCompositionRevision: Long): Boolean =
        eligible && latest == token && token.revision == currentCompositionRevision
    fun invalidate() { latest = null }
    fun shouldBind() = eligible
}
