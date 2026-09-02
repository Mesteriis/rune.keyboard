package io.github.mesteriis.rune.keyboard.intelligence.client

import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringInput
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply

interface ModelScoringClient : AutoCloseable {
    /** Caller passes false for sensitive/TYPE_NULL/disabled/non-text sessions. Main thread only. */
    fun attachSession(sessionId: Long?, effectiveAvailability: Boolean)
    fun score(input: ScoringInput)
    fun cancel()
    val available: Boolean
}
interface ModelScoringListener {
    fun currentCompositionRevision(): Long
    fun onReply(reply: ScoringReply)
    fun onAvailabilityChanged(available: Boolean)
}
