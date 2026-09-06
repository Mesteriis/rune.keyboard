package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.PrintStream
import java.lang.ref.WeakReference
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executor
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.RejectedExecutionException
import java.util.concurrent.ThreadFactory
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import org.junit.Assert.*
import org.junit.Test

class LocalCandidateWorkerTest {
    private val en = KeyboardLanguage.ENGLISH
    private fun request(id: Long, token: String = "teh", eligible: Boolean = true) =
        LocalCandidateRequest(7, 11, id, token, en, eligible)

    private open class EmptyLexicon : CandidateLexicon {
        override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl): ExactMembership {
            control.inspectState()
            return ExactMembership.ABSENT
        }
        override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int,
            control: CandidateSearchControl, visitor: CandidateVisitor): LexiconScanStatus = LexiconScanStatus.COMPLETE
    }

    /** Holds the active call after it observes cancellation, to inspect pending cleanup independently. */
    private class GateLexicon : EmptyLexicon() {
        val entered = CountDownLatch(1)
        val cancelled = CountDownLatch(1)
        val release = CountDownLatch(1)
        val visited = ConcurrentLinkedQueue<String>()
        private val first = AtomicBoolean(true)
        override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl): ExactMembership {
            visited.add(key)
            if (first.getAndSet(false)) {
                entered.countDown()
                val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5)
                while (release.count != 0L && System.nanoTime() < deadline) {
                    if (!control.checkpoint()) cancelled.countDown()
                    release.await(1, TimeUnit.MILLISECONDS)
                }
                check(release.count == 0L) { "Test gate timed out" }
            }
            return super.exact(language, key, control)
        }
    }

    private class Harness(lexicon: CandidateLexicon, callback: (LocalCandidateReply) -> Unit = {}) : AutoCloseable {
        val queue = LinkedBlockingQueue<Runnable>()
        @Volatile var rejectNext = false
        val calls = AtomicInteger()
        lateinit var thread: Thread
        val worker = LocalCandidateWorker(CandidateGenerator(object : CandidateLexicon {
            override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl): ExactMembership {
                calls.incrementAndGet()
                return lexicon.exact(language, key, control)
            }
            override fun scan(language: KeyboardLanguage, key: String, unitRadius: Int,
                control: CandidateSearchControl, visitor: CandidateVisitor) = lexicon.scan(language, key, unitRadius, control, visitor)
        }), Executor { action ->
            if (rejectNext) {
                rejectNext = false
                throw RejectedExecutionException("synthetic private payload")
            }
            queue.add(action)
        }, callback, ThreadFactory { action ->
            Thread(action, "candidate-worker-contract").apply { isDaemon = true; thread = this }
        })
        fun posted(): Runnable = requireNotNull(queue.poll(3, TimeUnit.SECONDS)) { "Owner delivery missing" }
        fun idle() = eventually { thread.state == Thread.State.WAITING }
        override fun close() {
            worker.close()
            thread.join(3000)
            assertFalse("Worker did not stop", thread.isAlive)
        }
    }

    @Test fun `latest pending replaces intermediate without queueing cancellation behind active computation`() {
        val lexicon = GateLexicon()
        val replies = mutableListOf<LocalCandidateReply>()
        val h = Harness(lexicon, replies::add)
        try {
            assertTrue(h.worker.submit(request(1, "first")))
            assertTrue(lexicon.entered.await(3, TimeUnit.SECONDS))
            assertTrue(h.worker.submit(request(2, "second")))
            assertTrue(lexicon.cancelled.await(3, TimeUnit.SECONDS))
            assertTrue(h.worker.submit(request(3, "third")))
            assertTrue(h.queue.isEmpty())
            assertFalse(lexicon.visited.contains("second"))
            lexicon.release.countDown()
            h.posted().run(); h.idle()
            assertEquals(listOf(3L), replies.map { it.requestId })
            assertEquals("third", replies.single().generation.original)
            assertFalse(lexicon.visited.contains("second"))
        } finally { lexicon.release.countDown(); h.close() }
    }

    @Test fun `cancel removes both active publication and pending computation`() {
        val lexicon = GateLexicon(); val replies = mutableListOf<LocalCandidateReply>(); val h = Harness(lexicon, replies::add)
        try {
            h.worker.submit(request(1, "first")); assertTrue(lexicon.entered.await(3, TimeUnit.SECONDS))
            h.worker.submit(request(2, "second")); h.worker.cancel()
            assertTrue(lexicon.cancelled.await(3, TimeUnit.SECONDS))
            lexicon.release.countDown(); h.idle()
            assertFalse(lexicon.visited.contains("second")); assertTrue(h.queue.isEmpty()); assertTrue(replies.isEmpty())
            h.worker.submit(request(3, "third")); h.posted().run()
            assertEquals(listOf(3L), replies.map { it.requestId })
        } finally { lexicon.release.countDown(); h.close() }
    }

    @Test fun `already queued callback is guarded again after cancel and close`() {
        for (close in listOf(false, true)) {
            val replies = mutableListOf<LocalCandidateReply>()
            Harness(EmptyLexicon(), replies::add).use { h ->
                h.worker.submit(request(1)); val action = h.posted(); h.idle()
                if (close) h.worker.close() else h.worker.cancel()
                action.run()
                assertTrue(replies.isEmpty())
                if (close) assertFalse(h.worker.submit(request(2)))
            }
        }
    }

    @Test fun `closed active reader sees flag immediately and pending request never starts`() {
        val lexicon = GateLexicon(); val replies = mutableListOf<LocalCandidateReply>(); val h = Harness(lexicon, replies::add)
        try {
            h.worker.submit(request(1, "first")); assertTrue(lexicon.entered.await(3, TimeUnit.SECONDS))
            h.worker.submit(request(2, "second")); h.worker.close()
            assertTrue(lexicon.cancelled.await(3, TimeUnit.SECONDS))
            assertFalse(h.worker.submit(request(3, "third")))
            lexicon.release.countDown(); h.thread.join(3000)
            assertFalse(h.thread.isAlive); assertFalse(lexicon.visited.contains("second")); assertTrue(h.queue.isEmpty())
        } finally { lexicon.release.countDown(); h.close() }
    }

    @Test fun `one queued owner action coalesces completed replacements and reused numeric IDs safely`() {
        val replies = mutableListOf<LocalCandidateReply>()
        Harness(EmptyLexicon(), replies::add).use { h ->
            h.worker.submit(request(1, "first")); val action = h.posted(); h.idle()
            for (token in listOf("second", "third", "fourth")) {
                val before = h.calls.get()
                h.worker.submit(request(1, token)); eventually { h.calls.get() > before }; h.idle()
            }
            assertTrue(h.queue.isEmpty())
            action.run()
            assertEquals(listOf("fourth"), replies.map { it.generation.original })
            assertEquals(7L, replies.single().sessionId); assertEquals(11L, replies.single().revision)
        }
    }

    @Test fun `burst while active never drops final eligible request`() {
        val lexicon = GateLexicon(); val replies = mutableListOf<LocalCandidateReply>(); val h = Harness(lexicon, replies::add)
        try {
            h.worker.submit(request(0, "first")); assertTrue(lexicon.entered.await(3, TimeUnit.SECONDS))
            repeat(100) { assertTrue(h.worker.submit(request(it + 1L, "latest"))) }
            lexicon.release.countDown(); h.posted().run()
            assertEquals(listOf(100L), replies.map { it.requestId })
        } finally { lexicon.release.countDown(); h.close() }
    }

    @Test fun `ineligible protected malformed and overlong input invalidate old result without computation`() {
        val calls = AtomicInteger()
        val lexicon = object : EmptyLexicon() {
            override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl): ExactMembership {
                calls.incrementAndGet(); return super.exact(language,key,control)
            }
        }
        val replies = mutableListOf<LocalCandidateReply>()
        Harness(lexicon, replies::add).use { h ->
            for (bad in listOf(request(2, eligible=false), request(2,"a".repeat(33)), request(2,"\uD800"),
                request(2,"HTTP"), request(2,"a@b"), request(-1), request(2,""))) {
                h.worker.submit(request(1)); val action=h.posted(); h.idle(); val before=calls.get()
                assertFalse(h.worker.submit(bad)); action.run()
                assertEquals(before,calls.get()); assertTrue(replies.isEmpty())
            }
            assertTrue(h.worker.submit(request(3,"a".repeat(32)))); h.posted().run()
            assertEquals(32,replies.single().generation.original!!.length)
        }
    }

    @Test fun `reader failure is redacted and next request succeeds`() {
        val first = AtomicBoolean(true)
        val lexicon = object : EmptyLexicon() {
            override fun exact(language: KeyboardLanguage, key: String, control: CandidateSearchControl): ExactMembership {
                if (first.getAndSet(false)) throw IOException("synthetic private payload: $key")
                return super.exact(language,key,control)
            }
        }
        val replies = mutableListOf<LocalCandidateReply>()
        Harness(lexicon, replies::add).use { h ->
            h.worker.submit(request(1)); h.posted().run()
            assertEquals(CandidateCompletion.READER_FAILURE,replies.single().generation.completion)
            assertTrue(replies.single().generation.prohibitsAutoReplace)
            h.worker.submit(request(2)); h.posted().run()
            assertEquals(CandidateCompletion.COMPLETE,replies.last().generation.completion)
            assertEquals(listOf(1L,2L),replies.map { it.requestId })
            assertFalse(replies.first().toString().contains("teh"))
        }
    }

    @Test fun `dispatch rejection and callback failure do not poison next request or expose exceptions`() {
        val count=AtomicInteger()
        Harness(EmptyLexicon()) { if(count.incrementAndGet()==1) throw IllegalStateException("synthetic private payload") }.use { h ->
            h.rejectNext=true; h.worker.submit(request(1))
            eventually { h.worker.lastFailure==LocalCandidateWorkerFailure.OWNER_DISPATCH }
            h.worker.submit(request(2)); h.posted().run()
            assertEquals(LocalCandidateWorkerFailure.OWNER_CALLBACK,h.worker.lastFailure)
            h.worker.submit(request(3)); h.posted().run()
            assertEquals(2,count.get())
            assertFalse(h.worker.lastFailure.toString().contains("synthetic"))
        }
    }

    @Test fun `owner callback can submit next request reentrantly without deadlock`() {
        val ids=mutableListOf<Long>(); lateinit var h:Harness
        h=Harness(EmptyLexicon()) { reply -> ids.add(reply.requestId); if(reply.requestId==1L) h.worker.submit(request(2)) }
        h.use { h.worker.submit(request(1)); h.posted().run(); h.posted().run(); assertEquals(listOf(1L,2L),ids) }
    }

    @Test fun `generator retains verified partial alternatives and original with exhaustion veto`() {
        val lexicon=object:EmptyLexicon() {
            override fun scan(language:KeyboardLanguage,key:String,unitRadius:Int,control:CandidateSearchControl,visitor:CandidateVisitor):LexiconScanStatus {
                if(language==KeyboardLanguage.ENGLISH) {
                    if(control.inspectState()) visitor.visit("the",1)
                    while(control.inspectState()) Unit
                }
                return LexiconScanStatus.COMPLETE
            }
        }
        val replies=mutableListOf<LocalCandidateReply>()
        Harness(lexicon,replies::add).use { h ->
            h.worker.submit(request(1));h.posted().run()
            val g=replies.single().generation
            assertEquals("teh",g.original);assertEquals(listOf("the"),g.alternatives.map { it.text })
            assertEquals(CandidateCompletion.STATES_EXHAUSTED,g.completion)
            assertEquals(8192,g.inspectedStates);assertEquals(1,g.verifiedTerminals);assertTrue(g.prohibitsAutoReplace)
        }
    }

    @Test fun `valid word stays original only with veto`() {
        val lexicon=object:EmptyLexicon() {
            override fun exact(language:KeyboardLanguage,key:String,control:CandidateSearchControl):ExactMembership { control.inspectState(); return ExactMembership.PRESENT }
        }
        val replies=mutableListOf<LocalCandidateReply>()
        Harness(lexicon,replies::add).use { h ->
            h.worker.submit(request(1,"the"));h.posted().run()
            val g=replies.single().generation
            assertEquals(CandidateCompletion.VALID_WORD,g.completion);assertTrue(g.prohibitsAutoReplace);assertTrue(g.alternatives.isEmpty())
        }
    }

    private data class PayloadRefs(val request:WeakReference<LocalCandidateRequest>,val token:WeakReference<String>)
    private fun ephemeral(h:Harness,id:Long):PayloadRefs {
        val token=String(charArrayOf('t','e','h'));val request=request(id,token)
        assertTrue(h.worker.submit(request));return PayloadRefs(WeakReference(request),WeakReference(token))
    }
    private fun released(vararg refs:WeakReference<*>) {
        eventually { System.gc(); refs.all { it.get()==null } }
    }

    @Test fun `cancelled and replaced pending payloads release while active call is still held`() {
        for(cancel in listOf(false,true)) {
            val lexicon=GateLexicon();val h=Harness(lexicon)
            val retained=String(charArrayOf('p','o','s','i','t','i','v','e'));val positive=WeakReference(retained)
            try {
                h.worker.submit(request(1,"first"));assertTrue(lexicon.entered.await(3,TimeUnit.SECONDS))
                val refs=ephemeral(h,2)
                if(cancel)h.worker.cancel() else h.worker.submit(request(3,"latest"))
                released(refs.request,refs.token)
                assertSame(retained,positive.get())
                assertEquals(1L,lexicon.release.count)
            } finally { lexicon.release.countDown();h.close() }
        }
    }

    @Test fun `idle actual worker retains neither last input nor delivered result with positive control`() {
        var replyRef:WeakReference<LocalCandidateReply>?=null
        var generationRef:WeakReference<CandidateGeneration>?=null
        var candidateRef:WeakReference<GeneratedCandidate>?=null
        val lexicon=object:EmptyLexicon() {
            override fun scan(language:KeyboardLanguage,key:String,unitRadius:Int,control:CandidateSearchControl,visitor:CandidateVisitor):LexiconScanStatus {
                if(language==KeyboardLanguage.ENGLISH && control.inspectState())visitor.visit("the",1)
                return LexiconScanStatus.COMPLETE
            }
        }
        val retained=String(charArrayOf('p','o','s','i','t','i','v','e'));val positive=WeakReference(retained)
        Harness(lexicon) { reply ->
            replyRef=WeakReference(reply);generationRef=WeakReference(reply.generation);candidateRef=WeakReference(reply.generation.alternatives.single())
        }.use { h ->
            val refs=ephemeral(h,1);h.posted().run();h.idle()
            released(refs.request,refs.token,replyRef!!,generationRef!!,candidateRef!!)
            assertSame(retained,positive.get());assertTrue(h.thread.isAlive);assertEquals(Thread.State.WAITING,h.thread.state)
        }
    }

    @Test fun `cancel clears completed payload even while queued action is retained`() {
        val retained=String(charArrayOf('p','o','s','i','t','i','v','e'));val positive=WeakReference(retained)
        Harness(EmptyLexicon()).use { h ->
            val refs=ephemeral(h,1);val action=h.posted();h.idle();h.worker.cancel()
            released(refs.request,refs.token);assertSame(retained,positive.get())
            action.run()
        }
    }

    @Test fun `unexpected fatal reader failure stops worker without a text-bearing uncaught diagnostic`() {
        val lexicon=object:EmptyLexicon() {
            override fun exact(language:KeyboardLanguage,key:String,control:CandidateSearchControl):ExactMembership = throw AssertionError("synthetic private payload: $key")
        }
        val bytes=ByteArrayOutputStream();val old=System.err
        try {
            System.setErr(PrintStream(bytes))
            Harness(lexicon).use { h ->
                h.worker.submit(request(1));h.thread.join(3000)
                assertFalse(h.thread.isAlive);assertEquals(LocalCandidateWorkerFailure.WORKER_STOPPED,h.worker.lastFailure)
                assertFalse(h.worker.submit(request(2)));assertTrue(h.queue.isEmpty())
            }
        } finally { System.setErr(old) }
        assertEquals("",bytes.toString())
    }

    @Test fun `owner thread contract prevents cross-thread admission and diagnostics redact snapshots`() {
        Harness(EmptyLexicon()).use { h ->
            var failure:Throwable?=null
            val other=Thread { try { h.worker.submit(request(1)) } catch(t:Throwable) { failure=t } }
            other.start();other.join(3000)
            assertTrue(failure is IllegalStateException);assertFalse(failure!!.message!!.contains("teh"))
            assertFalse(request(1).toString().contains("teh"))
        }
    }

    companion object {
        private fun eventually(condition:()->Boolean) {
            val deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(3)
            while(!condition()) {
                if(System.nanoTime()>=deadline) fail("Bounded worker condition not reached")
                Thread.sleep(5)
            }
        }
    }
}
