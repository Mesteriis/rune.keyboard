package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.IOException
import java.lang.ref.WeakReference
import java.util.Collections
import java.util.concurrent.CountDownLatch
import java.util.concurrent.ThreadFactory
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicReference
import java.util.concurrent.locks.LockSupport
import org.junit.Assert.*
import org.junit.Test

class LazyPackedLexiconsTest {
    @Test fun constructionAndProtectedRouteNeverStartLoading() {
        val threads = Threads()
        val calls = AtomicInteger()
        val loader = LazyPackedLexicons(PackedLanguageSource { calls.incrementAndGet(); ready(it) }, threads)
        assertEquals(1, threads.values.size)
        assertEquals(Thread.State.NEW, threads.values.single().state)
        assertFalse(loader.request(LanguageRouter.route("secret_path", EN)))
        assertFalse(loader.isReady(single(EN)))
        assertEquals(LexiconAvailability.NOT_REQUESTED, loader.availability(EN))
        loader.close()
        assertFalse(loader.request(single(EN)))
        assertEquals(0, calls.get())
        assertEquals(Thread.State.NEW, threads.values.single().state)
    }

    @Test fun coalescesSerialEnumDemandAndRequiresBothRoutesReady() {
        val first = Gate()
        val second = Gate()
        val calls = Collections.synchronizedList(mutableListOf<KeyboardLanguage>())
        val active = AtomicInteger()
        val maximum = AtomicInteger()
        val threads = Threads()
        val owner = Thread.currentThread()
        val loader = LazyPackedLexicons(PackedLanguageSource { language ->
            assertNotSame(owner, Thread.currentThread())
            maximum.accumulateAndGet(active.incrementAndGet(), ::maxOf)
            calls.add(language)
            try {
                if (language == EN) first.awaitRelease() else if (language == ES) second.awaitRelease()
                ready(language)
            } finally { active.decrementAndGet() }
        }, threads)
        try {
            val latin = LanguageRouter.route("casa", EN)
            assertFalse(loader.request(latin))
            first.awaitEntered()
            repeat(200) { assertFalse(loader.request(latin)) }
            assertEquals(LexiconAvailability.REQUESTED, loader.availability(ES))
            assertEquals(LexiconAvailability.NOT_REQUESTED, loader.availability(RU))
            assertEquals(listOf(EN), calls.toList())
            first.release.countDown()
            second.awaitEntered()
            assertEquals(LexiconAvailability.READY, loader.availability(EN))
            assertFalse(loader.isReady(latin))
            assertEquals(ExactMembership.UNAVAILABLE, loader.lexicon.exact(ES, "cat", control()))
            second.release.countDown()
            until { loader.isReady(latin) }
            repeat(200) { assertTrue(loader.request(latin)) }
            assertEquals(listOf(EN, ES), calls.toList())
            assertEquals(1, maximum.get())
            assertEquals(1, threads.values.size)
        } finally { first.release.countDown(); second.release.countDown(); loader.close(); threads.join() }
    }

    @Test fun approvedRouterRequestsOnlySpanishOrRussianForStrongEvidence() {
        for ((word, language) in listOf("niño" to ES, "кот" to RU)) {
            val calls = Collections.synchronizedList(mutableListOf<KeyboardLanguage>())
            val threads = Threads()
            val loader = LazyPackedLexicons(PackedLanguageSource { calls.add(it); ready(it) }, threads)
            try {
                val route = LanguageRouter.route(word, EN)
                loader.request(route)
                until { loader.isReady(route) }
                assertEquals(listOf(language), calls.toList())
                for (other in KeyboardLanguage.entries.filter { it != language }) {
                    assertEquals(LexiconAvailability.NOT_REQUESTED, loader.availability(other))
                }
            } finally { loader.close(); threads.join() }
        }
    }

    @Test fun failuresAndWrongLanguageNeverPublishOrRetryWithinLifetime() {
        val corrupt = PackedFixture.build(listOf("cat"))
        corrupt.trie[20] = 127
        // The real validator rejects corrupted bytes; use its typed failure rather than fake Ready.
        val trusted = PackedFixture.build(listOf("cat")).trusted()
        val invalid = corrupt.load(trusted)
        assertEquals(PackedLexiconLoad.Failed(PackedLoadFailure.HASH), invalid)
        for (answer in listOf(PackedLexiconLoad.Failed(PackedLoadFailure.IO), invalid, ready(ES))) {
            val calls = AtomicInteger()
            val threads = Threads()
            val loader = LazyPackedLexicons(PackedLanguageSource { calls.incrementAndGet(); answer }, threads)
            try {
                loader.request(single(EN))
                until { loader.availability(EN) == LexiconAvailability.UNAVAILABLE }
                repeat(20) { assertFalse(loader.request(single(EN))) }
                loader.invalidate()
                assertFalse(loader.request(single(EN)))
                assertEquals(1, calls.get())
                assertEquals(ExactMembership.UNAVAILABLE, loader.lexicon.exact(EN, "cat", control()))
                assertNull(loader.failure)
            } finally { loader.close(); threads.join() }
        }
    }

    @Test fun recoverableAndInterruptedLoadsAreRedactedAndDoNotPoisonNextLanguage() {
        for (interrupt in listOf(false, true)) {
            val threads = Threads()
            val nextInterrupt = AtomicBoolean(true)
            val loader = LazyPackedLexicons(PackedLanguageSource {
                if (it == EN) {
                    if (interrupt) throw InterruptedException(SENTINEL)
                    throw IOException(SENTINEL)
                }
                nextInterrupt.set(Thread.currentThread().isInterrupted)
                ready(it)
            }, threads)
            try {
                loader.request(single(EN))
                until { loader.availability(EN) == LexiconAvailability.UNAVAILABLE }
                loader.request(single(ES))
                until { loader.isReady(single(ES)) }
                assertFalse(nextInterrupt.get())
                assertNull(loader.failure)
                assertFalse(loader.toString().contains(SENTINEL))
                assertFalse(loader.lexicon.toString().contains(SENTINEL))
            } finally { loader.close(); threads.join() }
        }
    }

    @Test fun invalidationDropsPendingAndRejectsLateReadyEvenIfSourceIgnoresInterrupt() {
        val gate = Gate()
        val calls = Collections.synchronizedList(mutableListOf<KeyboardLanguage>())
        val threads = Threads()
        val loader = LazyPackedLexicons(PackedLanguageSource {
            calls.add(it)
            if (calls.size == 1) gate.awaitRelease(ignoreInterrupt = true)
            ready(it)
        }, threads)
        try {
            loader.request(LanguageRouter.route("casa", EN))
            gate.awaitEntered()
            loader.invalidate()
            assertEquals(LexiconAvailability.NOT_REQUESTED, loader.availability(EN))
            assertEquals(LexiconAvailability.NOT_REQUESTED, loader.availability(ES))
            loader.request(single(RU))
            gate.release.countDown()
            until { loader.isReady(single(RU)) }
            assertEquals(listOf(EN, RU), calls.toList())
            assertFalse(loader.isReady(single(EN)))
            assertEquals(LexiconAvailability.NOT_REQUESTED, loader.availability(ES))
            assertTrue(gate.interrupted.get())
        } finally { gate.release.countDown(); loader.close(); threads.join() }
    }

    @Test fun sameLanguageCanBeRequestedAgainAfterInvalidationWithoutObsoletePublication() {
        val old = Gate()
        val fresh = Gate()
        val calls = AtomicInteger()
        val threads = Threads()
        val loader = LazyPackedLexicons(PackedLanguageSource {
            if (calls.incrementAndGet() == 1) old.awaitRelease(true) else fresh.awaitRelease()
            ready(it)
        }, threads)
        try {
            loader.request(single(EN)); old.awaitEntered()
            loader.invalidate(); loader.request(single(EN)); old.release.countDown()
            fresh.awaitEntered()
            assertEquals(LexiconAvailability.REQUESTED, loader.availability(EN))
            assertFalse(loader.isReady(single(EN)))
            fresh.release.countDown()
            until { loader.isReady(single(EN)) }
            assertEquals(2, calls.get())
        } finally { old.release.countDown(); fresh.release.countDown(); loader.close(); threads.join() }
    }

    @Test fun existingReadySurvivesInvalidationAndLaterPublicationOnTheSameBridge() {
        val threads = Threads()
        val counts = IntArray(3)
        val loader = LazyPackedLexicons(PackedLanguageSource { counts[it.ordinal]++; ready(it) }, threads)
        try {
            val bridge = loader.lexicon
            loader.request(single(EN)); until { loader.isReady(single(EN)) }
            loader.invalidate()
            assertTrue(loader.request(single(EN)))
            loader.request(single(RU)); until { loader.isReady(single(RU)) }
            assertSame(bridge, loader.lexicon)
            assertEquals(ExactMembership.PRESENT, bridge.exact(EN, "cat", control()))
            assertEquals(ExactMembership.PRESENT, bridge.exact(RU, "кот", control()))
            assertEquals(1, counts[EN.ordinal])
            assertEquals(1, counts[RU.ordinal])
        } finally { loader.close(); threads.join() }
    }

    @Test fun bridgePreservesSharedAccountingVisitorStopAndCancellation() {
        val threads = Threads()
        val loader = LazyPackedLexicons(PackedLanguageSource { ready(it) }, threads)
        try {
            loader.request(LanguageRouter.route("casa", EN)); until { loader.isReady(LanguageRouter.route("casa", EN)) }
            val bridge = loader.lexicon
            val direct = PackedCandidateLexicon(listOf((ready(EN) as PackedLexiconLoad.Ready).lexicon,
                (ready(ES) as PackedLexiconLoad.Ready).lexicon))
            fun exercise(lexicon: CandidateLexicon): Pair<List<String>, Int> {
                val shared = control()
                val words = mutableListOf<String>()
                for (language in listOf(EN, ES)) {
                    assertEquals(ExactMembership.PRESENT, lexicon.exact(language, "cat", shared))
                    assertEquals(LexiconScanStatus.COMPLETE, lexicon.scan(language, "cat", 1, shared,
                        CandidateVisitor { key, _ -> words.add(key); true }))
                }
                return words to shared.inspectedStates
            }
            assertEquals(exercise(direct), exercise(bridge))
            val capped = control()
            repeat(CandidateSearchControl.MAX_STATES - 1) { assertTrue(capped.inspectState()) }
            assertEquals(ExactMembership.UNAVAILABLE, bridge.exact(EN, "cat", capped))
            assertEquals(CandidateCompletion.STATES_EXHAUSTED, capped.stop)
            assertEquals(ExactMembership.UNAVAILABLE, bridge.exact(ES, "cat", capped))
            assertEquals(CandidateSearchControl.MAX_STATES, capped.inspectedStates)
            val stopped = AtomicInteger()
            assertEquals(LexiconScanStatus.UNAVAILABLE, bridge.scan(EN, "cat", 1, control(),
                CandidateVisitor { _, _ -> stopped.incrementAndGet(); false }))
            assertEquals(1, stopped.get())
            val cancel = AtomicBoolean()
            val shared = CandidateSearchControl(CandidateCancellation { cancel.get() })
            assertEquals(LexiconScanStatus.UNAVAILABLE, bridge.scan(EN, "cat", 1, shared,
                CandidateVisitor { _, _ -> cancel.set(true); true }))
            assertEquals(CandidateCompletion.CANCELLED, shared.stop)
            assertEquals(ExactMembership.PRESENT, bridge.exact(EN, "cat", control()))
        } finally { loader.close(); threads.join() }
    }

    @Test fun closeIsNonjoiningRejectsLateReadyAndStopsAnyFurtherDemand() {
        val gate = Gate()
        val calls = AtomicInteger()
        val threads = Threads()
        val loader = LazyPackedLexicons(PackedLanguageSource { calls.incrementAndGet(); gate.awaitRelease(true); ready(it) }, threads)
        loader.request(LanguageRouter.route("casa", EN)); gate.awaitEntered()
        loader.close() // Must return while the source is deliberately still blocked.
        assertTrue(threads.values.single().isAlive)
        assertFalse(loader.request(single(RU)))
        assertEquals(LexiconAvailability.CLOSED, loader.availability(EN))
        assertEquals(ExactMembership.UNAVAILABLE, loader.lexicon.exact(EN, "cat", control()))
        assertEquals(LexiconScanStatus.UNAVAILABLE, loader.lexicon.scan(EN, "cat", 1, control(), CandidateVisitor { _, _ -> fail(); false }))
        gate.release.countDown(); threads.join()
        assertFalse(loader.isReady(single(EN)))
        assertEquals(1, calls.get())
        loader.close()
    }

    @Test fun bridgeDoesNotRetainQueryControlOrVisitorWhileLoaderRemainsIdle() {
        val threads = Threads()
        val loader = LazyPackedLexicons(PackedLanguageSource { ready(it) }, threads)
        try {
            loader.request(single(EN)); until { loader.isReady(single(EN)) }
            val references = useQueryAndCallbacks(loader.lexicon)
            val positive = Any()
            val strongControl = WeakReference(positive)
            collect(references)
            assertSame(positive, strongControl.get())
            assertTrue(threads.values.single().isAlive)
        } finally { loader.close(); threads.join() }
    }

    @Test fun closedOwnerAndSourceCanBeCollectedWithLoaderAndBridgeStillRetained() {
        val threads = Threads()
        val gate = Gate()
        val pair = retainedOwnerSource(threads, gate)
        val loader = pair.first
        loader.request(single(EN)); gate.awaitEntered()
        loader.close()
        assertNotNull(pair.second.get()) // The currently executing source is a positive retention control.
        gate.release.countDown(); threads.join()
        collect(listOf(pair.second))
        assertEquals(LexiconAvailability.CLOSED, loader.availability(EN))
        assertEquals(ExactMembership.UNAVAILABLE, loader.lexicon.exact(EN, "cat", control()))
    }

    @Test fun wrongThreadMutationAndUnexpectedWorkerFailureAreContentFree() {
        val threads = Threads()
        val loader = LazyPackedLexicons(PackedLanguageSource { throw AssertionError(SENTINEL) }, threads)
        try {
            val error = AtomicReference<Throwable>()
            Thread { try { loader.request(single(EN)) } catch (failure: Throwable) { error.set(failure) } }.apply { start(); join(2000) }
            assertEquals("LEXICON_OWNER_THREAD_REQUIRED", error.get()?.message)
            loader.request(single(EN)); until { loader.failure != null }
            assertEquals(LexiconLoaderFailure.WORKER_STOPPED, loader.failure)
            assertEquals(LexiconAvailability.CLOSED, loader.availability(EN))
            assertFalse(loader.toString().contains(SENTINEL))
        } finally { loader.close(); threads.join() }
    }

    @Test fun rejectedThreadStartStopsWithoutRetryOrPayload() {
        val attempts = AtomicInteger()
        val loader = LazyPackedLexicons(PackedLanguageSource { fail(); ready(it) }, ThreadFactory { task ->
            object : Thread(task) { override fun start() { attempts.incrementAndGet(); throw SecurityException(SENTINEL) } }
        })
        assertFalse(loader.request(single(EN)))
        assertEquals(LexiconLoaderFailure.WORKER_STOPPED, loader.failure)
        assertFalse(loader.request(single(RU)))
        assertEquals(1, attempts.get())
        loader.close()
    }

    private class Threads : ThreadFactory {
        val values = mutableListOf<Thread>()
        override fun newThread(task: Runnable): Thread = Thread(task, "lexicon-test").apply { isDaemon = true; values.add(this) }
        fun join() { values.filter { it.state != Thread.State.NEW }.forEach { it.join(2000); assertFalse("LOADER_DID_NOT_STOP", it.isAlive) } }
    }

    private class Gate {
        val entered = CountDownLatch(1)
        val release = CountDownLatch(1)
        val interrupted = AtomicBoolean()
        fun awaitEntered() { assertTrue("LOAD_NOT_ENTERED", entered.await(2, TimeUnit.SECONDS)) }
        fun awaitRelease(ignoreInterrupt: Boolean = false) {
            entered.countDown()
            val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(3)
            while (release.count != 0L) {
                try { assertTrue("LOAD_NOT_RELEASED", release.await(maxOf(1L, deadline - System.nanoTime()), TimeUnit.NANOSECONDS)) }
                catch (error: InterruptedException) { interrupted.set(true); if (!ignoreInterrupt) throw error }
            }
        }
    }

    companion object {
        private val EN = KeyboardLanguage.ENGLISH
        private val ES = KeyboardLanguage.SPANISH
        private val RU = KeyboardLanguage.RUSSIAN
        private const val SENTINEL = "private-query-sentinel-never-diagnose"
        private fun single(language: KeyboardLanguage) = LanguageRoute(language, null, 4, 0, 0)
        private fun ready(language: KeyboardLanguage): PackedLexiconLoad = PackedFixture.build(
            if (language == RU) listOf("кот", "кит") else listOf("cat", "cot", "cut"), language).load()
        private fun control() = CandidateSearchControl(CandidateCancellation { false })
        private fun until(condition: () -> Boolean) {
            val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(3)
            while (!condition() && System.nanoTime() < deadline) LockSupport.parkNanos(100_000)
            assertTrue("LIFECYCLE_TIMEOUT", condition())
        }
        private fun collect(references: List<WeakReference<out Any>>) {
            repeat(30) {
                if (references.all { it.get() == null }) return
                System.gc()
                // Bounded allocation and yielding aid observation; no deadline is treated as success.
                ByteArray(64 * 1024).fill(1)
                LockSupport.parkNanos(1_000_000)
            }
            assertTrue("RETAINED_AFTER_FRAME_RETURN", references.all { it.get() == null })
        }
        private fun useQueryAndCallbacks(bridge: CandidateLexicon): List<WeakReference<out Any>> {
            val query = String(charArrayOf('c', 'a', 't'))
            val owner = Any()
            val visitor = CandidateVisitor { _, _ -> owner.hashCode(); true }
            val cancellation = CandidateCancellation { owner.hashCode(); false }
            val control = CandidateSearchControl(cancellation)
            assertEquals(ExactMembership.PRESENT, bridge.exact(EN, query, control))
            assertEquals(LexiconScanStatus.COMPLETE, bridge.scan(EN, query, 1, control, visitor))
            return listOf(WeakReference(query), WeakReference(owner), WeakReference(visitor), WeakReference(control), WeakReference(cancellation))
        }
        private fun retainedOwnerSource(threads: Threads, gate: Gate): Pair<LazyPackedLexicons, WeakReference<Any>> {
            val retiredOwner = Any()
            val source = PackedLanguageSource { language -> gate.awaitRelease(true); retiredOwner.hashCode(); ready(language) }
            return LazyPackedLexicons(source, threads) to WeakReference(retiredOwner)
        }
    }
}
