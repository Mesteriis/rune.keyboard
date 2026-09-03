package io.github.mesteriis.rune.keyboard.smarttyping.session

import io.github.mesteriis.rune.keyboard.intelligence.client.ModelScoringClient
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelScoringListener
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessSource
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessHint
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringCode

/** Owner-thread scheduling seam. A delayed task contains numeric identity only, never input text. */
interface ModelPauseScheduler {
    fun postDelayed(task: Runnable, millis: Long)
    fun remove(task: Runnable)
}

/**
 * Local candidates are ready immediately; model results rank only that allowlist.
 * Eligibility/readiness are cached owner facts. Neither a timer nor a reconnect replays old input.
 */
class ModelCandidateCoordinator(
    private val controller: TypingSessionController,
    clientFactory: (ModelScoringListener) -> ModelScoringClient,
    private val scheduler: ModelPauseScheduler,
    private val ownerState: () -> CandidateOwnerState,
    private val readiness: ModelReadinessSource,
    private val changed: () -> Unit,
) : ModelScoringListener, AutoCloseable {
    private val ownerThread = Thread.currentThread()
    private val client = clientFactory(this)
    private var timer: Runnable? = null
    private var epoch = 0L
    private var requestId = 0L
    private var closed = false
    private var pendingOwner: CandidateOwnerState? = null

    /** Cached metadata only, independent of transport connectivity and quality qualification. */
    val modelReadinessHint: ModelReadinessHint
        get() { checkOwner(); return readiness.hint }

    /** Called only after a newly accepted local candidate result, never by rendering/readiness. */
    fun candidatesChanged() {
        checkOwner()
        if (closed) return
        cancel()
        val session = controller.state.sessionId
        val revision = controller.state.revision
        readiness.setActive(featureEligible())
        if (!eligible() || !controller.canRequestModelRanking) { client.attachSession(session, false); return }
        val owner = ownerState()
        client.attachSession(session, true)
        val scheduledEpoch = epoch
        val task = object : Runnable {
            override fun run() {
                checkOwner()
                if (closed || timer !== this || epoch != scheduledEpoch) return
                timer = null
                if (!eligible() || ownerState() != owner || controller.state.sessionId != session ||
                    controller.state.revision != revision || !client.available || requestId == Long.MAX_VALUE) return
                val input = controller.beginModelRanking(++requestId) ?: return
                pendingOwner = owner
                client.score(input)
            }
        }
        timer = task
        scheduler.postDelayed(task, PAUSE_MILLIS)
    }

    /** Text/tap action barrier. Retain the binding within the same eligible session. */
    fun cancel() {
        checkOwner()
        if (closed) return
        epoch++
        pendingOwner = null
        timer?.let(scheduler::remove); timer = null
        controller.cancelModelRanking()
        client.cancel()
    }

    /** Session/view/layer/language/settings/privacy invalidation, not an ordinary keystroke. */
    fun invalidate() {
        checkOwner()
        if (closed) return
        cancel()
        client.attachSession(null, false)
        readiness.setActive(featureEligible())
    }

    override fun currentCompositionRevision(): Long { checkOwner(); return controller.state.revision }
    override fun onReply(reply: ScoringReply) {
        checkOwner()
        if (closed || !eligible() || pendingOwner != ownerState() || !controller.isCurrentModelRanking(reply.token)) return
        if (reply.code == ScoringCode.NO_MODEL || reply.code == ScoringCode.LOAD_FAILED) {
            cancel(); client.attachSession(null, false); readiness.setActive(false)
            return
        }
        if (controller.acceptModelRanking(reply)) { pendingOwner = null; changed() }
    }
    override fun onAvailabilityChanged(available: Boolean) {
        checkOwner()
        if (!available && !closed) cancel()
        // A new connection never resubmits an earlier composition.
    }
    override fun close() {
        checkOwner()
        if (closed) return
        cancel(); closed = true; client.close(); readiness.close()
    }
    private fun featureEligible() = !closed && ownerState().canRequestModelSpelling && controller.state.enabled
    private fun eligible() = featureEligible() && readiness.hint == ModelReadinessHint.READY &&
        controller.canRequestCandidates
    private fun checkOwner() = check(Thread.currentThread() === ownerThread) { "Model candidate owner thread required" }
    companion object {
        /** Development pause, not a measured latency/energy budget; service CPU duty still applies. */
        const val PAUSE_MILLIS = 400L
    }
}
