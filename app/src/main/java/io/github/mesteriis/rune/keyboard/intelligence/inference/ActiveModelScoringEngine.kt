package io.github.mesteriis.rune.keyboard.intelligence.inference

import io.github.mesteriis.rune.keyboard.intelligence.ipc.NumericScore
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringCode
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringInput
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import io.github.mesteriis.rune.keyboard.intelligence.storage.ActiveModelResolver
import io.github.mesteriis.rune.keyboard.intelligence.storage.ModelOperationGate
import io.github.mesteriis.rune.keyboard.intelligence.storage.ResolvedActiveModel
import io.github.mesteriis.rune.runtime.llama.CandidateScoringRequest
import io.github.mesteriis.rune.runtime.llama.CandidateScoringResult
import io.github.mesteriis.rune.runtime.llama.LlamaLocalModelRuntime
import io.github.mesteriis.rune.runtime.llama.LocalModelRuntime
import io.github.mesteriis.rune.runtime.llama.ModelLoadResult
import io.github.mesteriis.rune.runtime.llama.ScoringCandidate
import java.io.File
import java.util.concurrent.atomic.AtomicBoolean

/** Native adapter only; activation and delivery remain install-worker responsibilities. */
class ActiveModelScoringEngine(root: File, changed: () -> Unit,
    private val createRuntime: () -> LocalModelRuntime = { LlamaLocalModelRuntime() }) : ScoringEngine {
    private val gate = ModelOperationGate(root)
    private val resolver = ActiveModelResolver(root)
    private val watch = ActiveModelWatch(root, changed)
    @Volatile private var runtime: LocalModelRuntime? = null
    private var loaded: ResolvedActiveModel? = null // serial worker only
    override fun score(request: ScoringInput, cancelled: AtomicBoolean): ScoringReply {
        fun failure(code: Int) = ScoringReply(request.token, code, 0, emptyList())
        if (cancelled.get()) return failure(ScoringCode.CANCELLED)
        try {
            val ready = gate.withReadLock {
                val active = resolver.resolve() ?: return@withReadLock ScoringCode.NO_MODEL
                if (loaded != active) {
                    unload()
                    if (!watch.start(active.directory)) return@withReadLock ScoringCode.UNAVAILABLE
                    if (cancelled.get()) return@withReadLock ScoringCode.CANCELLED
                    val native = runtime ?: createRuntime().also { runtime = it }
                    // Installation mutations cannot rename/remove the model during native load.
                    when (val result = native.load(active.file, cancelled::get)) {
                        is ModelLoadResult.Failure -> return@withReadLock result.code.stableCode
                        is ModelLoadResult.Success -> loaded = active
                    }
                }
                if (resolver.resolve() != loaded) ScoringCode.UNAVAILABLE else ScoringCode.OK
            }
            if (ready != ScoringCode.OK) { unload(); return failure(ready) }
            if (cancelled.get()) return failure(ScoringCode.CANCELLED)
            val result = runtime!!.scoreCandidates(CandidateScoringRequest(request.prefix,
                request.token.candidateIds.zip(request.continuations) { id, text -> ScoringCandidate(id, text) }),
                cancelled::get)
            // Score does not hold the filesystem lock. This is the version-validity linearization point.
            val sameVersion = gate.withReadLock { resolver.resolve() == loaded }
            if (cancelled.get() || !sameVersion) { unload(); return failure(ScoringCode.CANCELLED) }
            return when (result) {
                is CandidateScoringResult.Failure -> failure(result.error.stableCode)
                is CandidateScoringResult.Success -> ScoringReply(request.token, 0, result.durationMillis,
                    result.scores.map { NumericScore(it.id, it.sumLogProbability, it.scoredTokenCount) })
            }
        } catch (_: Exception) { unload(); return failure(ScoringCode.UNAVAILABLE) }
        catch (_: LinkageError) { unload(); return failure(ScoringCode.UNAVAILABLE) }
    }
    override fun cancel() { runtime?.cancelCurrentOperation() }
    override fun unload() { loaded = null; watch.close(); runtime?.unload() }
    override fun close() { loaded = null; watch.close(); runtime?.close(); runtime = null }
}
