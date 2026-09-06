package io.github.mesteriis.rune.keyboard.intelligence.client

import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringInput
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringToken

interface ModelScoringClient : AutoCloseable {
    /**
     * Legacy explicit demand entry point. False for sensitive/raw/non-text or absent model consumers.
     * Same normalized session/demand is idempotent. Main thread only; close is terminal.
     * Owners issue distinct session identities; request IDs increase within each session, including OFF/ON.
     */
    fun attachSession(sessionId: Long?, effectiveAvailability: Boolean)
    fun attachSession(demand: ModelDemand) = attachSession(demand.sessionId, demand.shouldBind)
    fun score(input: ScoringInput)
    fun cancel()
    /** Connected transport only; does not mean a model is loaded or inference is qualified. */
    val available: Boolean
}
interface ModelScoringListener {
    fun currentCompositionRevision(): Long
    /** Owner may certify one unchanged Rune-owned word after its space was committed. */
    fun isCurrentRequest(token: ScoringToken): Boolean = token.revision == currentCompositionRevision()
    fun onReply(reply: ScoringReply)
    /** Transport transitions only; initial/unmodified false is not repeatedly published. */
    fun onAvailabilityChanged(available: Boolean)
}
