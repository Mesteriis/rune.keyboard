package io.github.mesteriis.rune.keyboard.smarttyping.learning

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.util.concurrent.Executor
import org.junit.Assert.*
import org.junit.Test

class LearningStoreTest {
    private val en = KeyboardLanguage.ENGLISH
    private class Queue : Executor {
        private val tasks = ArrayDeque<Runnable>()
        override fun execute(command: Runnable) { tasks.addLast(command) }
        fun next() { tasks.removeFirst().run() }
        fun drain() { while (tasks.isNotEmpty()) next() }
    }
    private class MemoryStorage : LearningStorage {
        var bytes: ByteArray? = null
        var unreadable = false
        var writeFailure = false
        var silentFailure = false
        override fun read(): ByteArray? { check(!unreadable); return bytes?.copyOf() }
        override fun write(bytes: ByteArray) {
            check(!writeFailure)
            if (!silentFailure) { this.bytes = bytes.copyOf(); unreadable = false }
        }
    }
    @Test fun maximumSupplementaryUnicodeSnapshotPersistsAndReloadsAtCapacity() {
        val storage = MemoryStorage(); val queue = Queue(); val store = LearningStore(storage, queue)
        queue.drain(); store.configure(true, true, true)
        maximumWords().forEach { assertTrue(store.confirmed(it, en)) }
        queue.drain()
        assertEquals(true, store.lastWriteSucceeded)
        assertEquals(372749, checkNotNull(storage.bytes).size)
        assertTrue(checkNotNull(storage.bytes).size <= LearningCodec.MAX_BYTES)
        val restored = LearningStore(storage, queue); queue.drain()
        assertEquals(store.snapshot(), restored.snapshot())
        assertEquals(512, restored.snapshot().examples.size)
    }
    @Test fun resetBlocksFeedbackAndFailedRecoveryStaysFailedUntilDurableReset() {
        val storage = MemoryStorage().apply { unreadable = true; writeFailure = true }
        val queue = Queue(); val store = LearningStore(storage, queue)
        store.configure(true, true, true); queue.drain()
        assertEquals(LearningStore.Readiness.FAILED, store.readiness)
        var completed: Boolean? = null
        store.reset { completed = it }
        assertEquals(LearningStore.Readiness.RESETTING, store.readiness)
        assertFalse(store.confirmed("word", en)); assertNull(completed)
        queue.drain()
        assertEquals(false, completed)
        assertEquals(LearningStore.Readiness.FAILED, store.readiness)
        assertFalse(store.confirmed("word", en))
        storage.writeFailure = false
        store.reset { completed = it }; queue.drain()
        assertEquals(true, completed); assertTrue(store.isReady)
        assertTrue(store.confirmed("word", en))
    }
    @Test fun silentCommitFailureCannotClaimResetSuccessOrResumeLearning() {
        val storage = MemoryStorage(); val queue = Queue(); val store = LearningStore(storage, queue)
        queue.drain(); store.configure(true, true, true)
        store.confirmed("word", en); queue.drain()
        storage.silentFailure = true
        var completed: Boolean? = null
        store.reset { completed = it }; queue.drain()
        assertEquals(false, completed); assertFalse(store.isReady)
        assertEquals(LearningStore.Readiness.FAILED, store.readiness)
        assertEquals(1, LearningCodec.decode(checkNotNull(storage.bytes)).examples.size)
        assertFalse(store.confirmed("another", en))
    }
    @Test fun resetInvalidatesLoadAndQueuedSavesCannotRestoreOldEvidence() {
        val storage = MemoryStorage(); val queue = Queue(); val store = LearningStore(storage, queue)
        store.configure(true, true, true)
        store.reset(); queue.drain()
        assertTrue(store.isReady); assertTrue(store.snapshot().evidence.isEmpty())
        store.confirmed("word", en)
        store.reset()
        assertFalse(store.confirmed("another", en))
        queue.drain()
        assertTrue(LearningCodec.decode(checkNotNull(storage.bytes)).evidence.isEmpty())
        assertTrue(store.isReady)
    }

    @Test fun candidateActivatesOnlyAfterDurablePromotionAndCanRollback() {
        val storage = MemoryStorage(); val queue = Queue(); val store = LearningStore(storage, queue)
        queue.drain(); store.configure(true, true, true)
        val training = listOf("cat", "dog", "bird", "apple", "tree", "blue", "green")
            .filterNot { LearningModel.holdout(en, it) }.take(3)
        training.forEach { assertTrue(store.accepted(it + "z", it, en)) }
        queue.drain()
        assertEquals(0.0, store.preference("plantz", "plant", en), 0.0)
        val candidate = store.snapshot()
        var promoted: Boolean? = null
        store.promoteCandidate(candidate) { promoted = it }
        assertEquals(LearningStore.Readiness.PROMOTING, store.readiness)
        assertEquals(0.0, store.preference("plantz", "plant", en), 0.0)
        queue.drain()
        assertEquals(true, promoted)
        assertTrue(store.preference("plantz", "plant", en) > 0.0)

        var rolledBack: Boolean? = null
        store.rollback { rolledBack = it }
        queue.drain()
        assertEquals(true, rolledBack)
        assertEquals(0.0, store.preference("plantz", "plant", en), 0.0)
    }

    @Test fun failedPromotionNeverChangesActivePolicy() {
        val storage = MemoryStorage(); val queue = Queue(); val store = LearningStore(storage, queue)
        queue.drain(); store.configure(true, true, true)
        val training = listOf("cat", "dog", "bird", "apple", "tree", "blue", "green")
            .filterNot { LearningModel.holdout(en, it) }.take(3)
        training.forEach { store.accepted(it + "z", it, en) }
        queue.drain(); val candidate = store.snapshot(); storage.writeFailure = true
        var promoted: Boolean? = null
        store.promoteCandidate(candidate) { promoted = it }
        queue.drain()
        assertEquals(false, promoted)
        assertEquals(0.0, store.preference("plantz", "plant", en), 0.0)
        assertTrue(store.isReady)
    }

    @Test fun staleEvaluatedSnapshotCannotPromoteNewUnevaluatedEvidence() {
        val storage = MemoryStorage(); val queue = Queue(); val store = LearningStore(storage, queue)
        queue.drain(); store.configure(true, true, true)
        val evaluated = store.snapshot()
        assertTrue(store.confirmed("word", en))
        var promoted: Boolean? = null
        store.promoteCandidate(evaluated) { promoted = it }
        queue.drain()
        assertEquals(false, promoted)
        assertEquals(LearningStore.Readiness.READY, store.readiness)
        assertTrue(store.snapshot().activePolicy.counts.isEmpty())
    }

    @Test fun staleCanarySnapshotCannotRollbackAcrossNewEvidence() {
        val storage = MemoryStorage(); val queue = Queue(); val store = LearningStore(storage, queue)
        queue.drain(); store.configure(true, true, true)
        val training = listOf("cat", "dog", "bird", "apple", "tree", "blue", "green")
            .filterNot { LearningModel.holdout(en, it) }.take(3)
        training.forEach { store.accepted(it + "z", it, en) }
        queue.drain(); store.promoteCandidate(store.snapshot()); queue.drain()
        val evaluated = store.snapshot()
        assertTrue(store.confirmed("word", en))
        var rolledBack: Boolean? = null
        store.rollback(evaluated) { rolledBack = it }
        queue.drain()
        assertEquals(false, rolledBack)
        assertTrue(store.snapshot().activePolicy.counts.isNotEmpty())
    }
    companion object {
        /** 48 supplementary lowercase letters: modified UTF uses 288 bytes per word. */
        fun maximumWords(): List<String> = (0 until 512).map { i ->
            buildString {
                repeat(46) { appendCodePoint(0x10428) }
                appendCodePoint(0x10428 + i / 32)
                appendCodePoint(0x10428 + i % 32)
            }
        }
    }
}
