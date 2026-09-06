package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import java.util.concurrent.ThreadFactory

internal fun interface PackedLanguageSource {
    fun load(language: KeyboardLanguage): PackedLexiconLoad
}

enum class LexiconAvailability { NOT_REQUESTED, REQUESTED, READY, UNAVAILABLE, CLOSED }
enum class LexiconLoaderFailure { WORKER_STOPPED }

/**
 * One lazy serial loader; construct/request/invalidate/close on its owner thread. Demand contains
 * only up to three enum bits and a numeric generation. No editor, token, owner callback or dispatcher.
 * Completion publishes readiness only; the next eligible edit decides whether to submit candidates.
 *
 * [lexicon] belongs exclusively to one candidate compute worker for this component's lifetime.
 * Publication adds immutable validated entries; it never replaces Ready readers or restarts workers.
 * close clears handles and interrupts validation without joining or forcing mapped-page reclamation.
 */
class LazyPackedLexicons internal constructor(
    source: PackedLanguageSource,
    threadFactory: ThreadFactory = ThreadFactory { task ->
        Thread(task, "rune-lexicon-loader").apply { isDaemon = true }
    },
) : AutoCloseable {
    private val ownerThread = Thread.currentThread()
    private val state = State(source)
    private val thread: Thread
    private var started = false
    val lexicon: CandidateLexicon = ReadyBridge(state)
    val failure: LexiconLoaderFailure? get() = state.failure

    init {
        // The thread retains State only, not the owner-facing object or constructing thread.
        val shared = state
        thread = threadFactory.newThread(Runnable { runLoop(shared) })
        check(thread.state == Thread.State.NEW) { "LEXICON_NEW_THREAD_REQUIRED" }
    }

    /** Coalesce just this route's missing languages. False means original-only until a later edit. */
    fun request(route: LanguageRoute): Boolean {
        checkOwner()
        val required = mask(route)
        synchronized(state.lock) {
            val snapshot = state.snapshot
            if (snapshot.closed || required == 0) return false
            var missing = 0
            for (language in KeyboardLanguage.entries) {
                val bit = bit(language)
                if (required and bit != 0 && snapshot.reader(language) == null &&
                    snapshot.unavailable and bit == 0 && snapshot.requested and bit == 0) missing = missing or bit
            }
            if (missing != 0) {
                state.pending = state.pending or missing
                state.snapshot = snapshot.copy(requested = snapshot.requested or missing)
                if (!started) {
                    started = true
                    try { thread.start() } catch (_: Exception) { stopLocked(state, failed = true) }
                }
                state.lock.notifyAll()
            }
            return ready(state.snapshot, required)
        }
    }

    fun isReady(route: LanguageRoute): Boolean = ready(state.snapshot, mask(route))

    fun availability(language: KeyboardLanguage): LexiconAvailability {
        val snapshot = state.snapshot
        return when {
            snapshot.closed -> LexiconAvailability.CLOSED
            snapshot.reader(language) != null -> LexiconAvailability.READY
            snapshot.unavailable and bit(language) != 0 -> LexiconAvailability.UNAVAILABLE
            snapshot.requested and bit(language) != 0 -> LexiconAvailability.REQUESTED
            else -> LexiconAvailability.NOT_REQUESTED
        }
    }

    /** Session/privacy/language invalidation drops pending demand; cached public handles may remain. */
    fun invalidate() {
        checkOwner()
        synchronized(state.lock) {
            if (state.snapshot.closed) return
            if (state.generation == Long.MAX_VALUE) {
                stopLocked(state, failed = false)
            } else {
                state.generation++
                state.pending = 0
                state.snapshot = state.snapshot.copy(requested = 0)
            }
            if (state.active) thread.interrupt()
            state.lock.notifyAll()
        }
    }

    override fun close() {
        checkOwner()
        synchronized(state.lock) {
            stopLocked(state, failed = false)
            if (started) thread.interrupt()
            state.lock.notifyAll()
        }
    }

    override fun toString(): String = "LazyPackedLexicons"

    private fun checkOwner() {
        check(Thread.currentThread() === ownerThread) { "LEXICON_OWNER_THREAD_REQUIRED" }
    }

    private data class Snapshot(
        val en: PackedCandidateLexicon? = null,
        val es: PackedCandidateLexicon? = null,
        val ru: PackedCandidateLexicon? = null,
        val requested: Int = 0,
        val unavailable: Int = 0,
        val closed: Boolean = false,
    ) {
        fun reader(language: KeyboardLanguage): PackedCandidateLexicon? = when (language) {
            KeyboardLanguage.ENGLISH -> en
            KeyboardLanguage.SPANISH -> es
            KeyboardLanguage.RUSSIAN -> ru
        }

        fun withReader(language: KeyboardLanguage, reader: PackedCandidateLexicon): Snapshot = when (language) {
            KeyboardLanguage.ENGLISH -> copy(en = reader, requested = requested and bit(language).inv())
            KeyboardLanguage.SPANISH -> copy(es = reader, requested = requested and bit(language).inv())
            KeyboardLanguage.RUSSIAN -> copy(ru = reader, requested = requested and bit(language).inv())
        }
    }

    private class State(var source: PackedLanguageSource?) {
        val lock = Object()
        @Volatile var snapshot = Snapshot()
        @Volatile var failure: LexiconLoaderFailure? = null
        var pending = 0
        var generation = 0L
        var active = false
    }

    /** Worker-only scratch delegates selection over published immutable handles; never loads assets. */
    private class ReadyBridge(private val state: State) : CandidateLexicon {
        private val topSeven by lazy(LazyThreadSafetyMode.NONE) {
            PackedTopSeven { language -> state.snapshot.reader(language)?.handle(language) }
        }

        override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl): ExactMembership =
            state.snapshot.reader(language)?.exact(language, key, control) ?: ExactMembership.UNAVAILABLE

        override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int,
            control: CandidateSearchControl, visitor: CandidateVisitor): LexiconScanStatus =
            state.snapshot.reader(language)?.scan(language, key, unitRadius, control, visitor) ?: LexiconScanStatus.UNAVAILABLE

        override fun selectTop(key: String, route: LanguageRoute, pattern: CasePattern,
            control: CandidateSearchControl, maximumAlternatives: Int): TopCandidateSelection = topSeven.select(key, route, pattern, control, maximumAlternatives)
    }

    private class Work(val language: KeyboardLanguage, val generation: Long, val source: PackedLanguageSource)

    private companion object {
        fun bit(language: KeyboardLanguage): Int = 1 shl language.ordinal

        fun mask(route: LanguageRoute): Int {
            val primary = route.primary ?: return 0
            if (route.protectedReason != null) return 0
            return bit(primary) or (route.fallback?.let(::bit) ?: 0)
        }

        fun ready(snapshot: Snapshot, required: Int): Boolean = !snapshot.closed && required != 0 &&
            KeyboardLanguage.entries.all { required and bit(it) == 0 || snapshot.reader(it) != null }

        fun stopLocked(state: State, failed: Boolean) {
            state.pending = 0
            state.source = null
            state.snapshot = Snapshot(closed = true)
            if (failed) state.failure = LexiconLoaderFailure.WORKER_STOPPED
        }

        fun runLoop(state: State) {
            try {
                // Each completed load frame disappears before the next invocation waits idle.
                while (runNext(state)) Unit
            } catch (_: Throwable) {
                // Match LocalCandidateWorker: unexpected/fatal worker failure stops it content-free.
                synchronized(state.lock) { stopLocked(state, failed = true) }
            }
        }

        fun runNext(state: State): Boolean {
            val work = synchronized(state.lock) {
                Thread.interrupted() // Obsolete validation's interrupt must not cancel the next generation.
                while (!state.snapshot.closed && state.pending == 0) {
                    try { state.lock.wait() } catch (_: InterruptedException) { /* Recheck lifecycle/demand. */ }
                }
                if (state.snapshot.closed) return false
                val language = KeyboardLanguage.entries.first { state.pending and bit(it) != 0 }
                state.pending = state.pending and bit(language).inv()
                state.active = true
                Work(language, state.generation, checkNotNull(state.source))
            }
            val result = try {
                work.source.load(work.language)
            } catch (_: InterruptedException) {
                Thread.currentThread().interrupt()
                PackedLexiconLoad.Failed(PackedLoadFailure.CANCELLED)
            } catch (_: Exception) {
                PackedLexiconLoad.Failed(PackedLoadFailure.IO)
            }
            val reader = if (result is PackedLexiconLoad.Ready && result.lexicon.language == work.language &&
                !Thread.currentThread().isInterrupted) PackedCandidateLexicon(listOf(result.lexicon)) else null
            synchronized(state.lock) {
                state.active = false
                if (!state.snapshot.closed && state.generation == work.generation) {
                    state.snapshot = if (reader != null) state.snapshot.withReader(work.language, reader)
                    else state.snapshot.copy(requested = state.snapshot.requested and bit(work.language).inv(),
                        unavailable = state.snapshot.unavailable or bit(work.language))
                }
            }
            return true
        }
    }
}
