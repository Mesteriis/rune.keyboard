package io.github.mesteriis.rune.keyboard.smarttyping.quality

import java.util.concurrent.Executor
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class QualityRepositoryTest {
    private class Worker : Executor {
        val tasks = ArrayDeque<Runnable>()
        override fun execute(command: Runnable) { tasks.addLast(command) }
        fun runNext() { tasks.removeFirst().run() }
        fun drain() { while (tasks.isNotEmpty()) runNext() }
    }
    private class Storage : QualityStorage {
        var persisted: QualitySnapshot? = null
        var readFails = false
        var writesSucceed = true
        var writes = 0
        override fun read(): QualitySnapshot? {
            if (readFails) error("Synthetic load failure")
            return persisted
        }
        override fun write(snapshot: QualitySnapshot): Boolean {
            writes++
            if (writesSucceed) persisted = snapshot
            return writesSucceed
        }
    }

    @Test fun `loading drops actions and rapid ready actions coalesce to one numeric save`() {
        val worker = Worker()
        val storage = Storage()
        val repository = QualityRepository(storage, worker)
        repository.configure(true, true, true)
        repository.record(QualityEvent.AUTOMATIC_APPLIED)
        assertEquals(QualitySnapshot(), repository.snapshot())
        worker.drain()
        repeat(100) { repository.record(QualityEvent.AUTOMATIC_APPLIED) }
        assertEquals(1, worker.tasks.size)
        assertEquals(0, storage.writes)
        worker.drain()
        assertEquals(1, storage.writes)
        assertEquals(100L, storage.persisted!![QualityEvent.AUTOMATIC_APPLIED])
    }

    @Test fun `reset before load cannot resurrect existing counters and callback waits for persistence`() {
        val worker = Worker()
        val storage = Storage().apply { persisted = QualitySnapshot(events = List(QualityEvent.entries.size) { 17L }) }
        val repository = QualityRepository(storage, worker)
        var completion: Boolean? = null
        repository.reset { completion = it }
        assertNull(completion)
        assertFalse(repository.isReady)
        worker.runNext()
        assertEquals(QualitySnapshot(), repository.snapshot())
        assertNull(completion)
        worker.runNext()
        assertEquals(true, completion)
        assertEquals(QualitySnapshot(), storage.persisted)
        assertTrue(repository.isReady)
    }

    @Test fun `queued save cannot undo reset and collection stays paused until saved`() {
        val worker = Worker()
        val storage = Storage()
        val repository = QualityRepository(storage, worker)
        repository.configure(true, true, true)
        worker.drain()
        repository.record(QualityEvent.AUTOMATIC_APPLIED)
        repository.compare(1, "source", "primary", "experimental")
        repository.reset()
        repository.record(QualityEvent.AUTOMATIC_APPLIED)
        worker.drain()
        repository.explicitChoice(1, "primary")
        assertEquals(QualitySnapshot(), repository.snapshot())
        assertEquals(QualitySnapshot(), storage.persisted)
    }

    @Test fun `load and save failures require successful durable reset before collection resumes`() {
        val worker = Worker()
        val storage = Storage().apply { readFails = true; writesSucceed = false }
        val repository = QualityRepository(storage, worker)
        repository.configure(true, true, true)
        worker.drain()
        assertEquals(QualityRepository.Readiness.FAILED, repository.readiness)
        var completion: Boolean? = null
        repository.reset { completion = it }
        worker.drain()
        assertEquals(false, completion)
        assertFalse(repository.isReady)
        repository.record(QualityEvent.AUTOMATIC_APPLIED)
        assertEquals(QualitySnapshot(), repository.snapshot())
        storage.writesSucceed = true
        repository.reset { completion = it }
        worker.drain()
        assertEquals(true, completion)
        assertTrue(repository.isReady)
        storage.writesSucceed = false
        repository.record(QualityEvent.AUTOMATIC_APPLIED)
        worker.drain()
        assertEquals(QualityRepository.Readiness.FAILED, repository.readiness)
        assertEquals(false, repository.lastWriteSucceeded)
    }

    @Test fun `repeated reset cannot accumulate unbounded callbacks`() {
        val worker = Worker()
        val repository = QualityRepository(Storage(), worker)
        worker.drain()
        var completed = 0
        repository.reset { assertTrue(it); completed++ }
        repeat(100) { repository.reset { assertFalse(it); completed++ } }
        assertEquals(1, worker.tasks.size)
        worker.drain()
        assertEquals(101, completed)
    }
}
