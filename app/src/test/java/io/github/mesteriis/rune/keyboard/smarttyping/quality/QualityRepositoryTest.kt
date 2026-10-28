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

    @Test fun `source counters and model latency obey loading coalescing and durable reset`() {
        val worker = Worker()
        val storage = Storage()
        val repository = QualityRepository(storage, worker)
        repository.configure(true, false, true)
        repository.recordAutomatic(AutomaticQualitySource.JOINT_SHORT, AutomaticQualityOutcome.APPLIED)
        repository.modelResponseMillis(250)
        assertEquals(QualitySnapshot(), repository.snapshot())
        worker.drain()
        for (source in AutomaticQualitySource.entries) for (outcome in AutomaticQualityOutcome.entries)
            repository.recordAutomatic(source, outcome)
        repository.modelResponseMillis(250)
        assertEquals(1, worker.tasks.size)
        worker.drain()
        assertEquals(List(56) { 1L }, storage.persisted!!.automaticSources)
        assertEquals(listOf(0L, 0L, 0L, 1L, 0L), storage.persisted!!.modelResponseBuckets)
        assertEquals(List(8) { 0L }, storage.persisted!!.events)
        val restartedWorker = Worker()
        val restarted = QualityRepository(storage, restartedWorker)
        restartedWorker.drain()
        assertEquals(repository.snapshot(), restarted.snapshot())
        repository.reset()
        repository.recordAutomatic(AutomaticQualitySource.JOINT_SHORT, AutomaticQualityOutcome.APPLIED)
        repository.modelResponseMillis(50)
        worker.drain()
        assertEquals(QualitySnapshot(), storage.persisted)
        assertEquals(QualitySnapshot(), repository.snapshot())
    }

    @Test fun `failed source counter save pauses new numeric collection until a durable reset`() {
        val worker = Worker()
        val storage = Storage().apply { writesSucceed = false }
        val repository = QualityRepository(storage, worker)
        repository.configure(true, true, true)
        worker.drain()
        repository.recordAutomatic(AutomaticQualitySource.MODEL, AutomaticQualityOutcome.APPLIED)
        worker.drain()
        assertEquals(QualityRepository.Readiness.FAILED, repository.readiness)
        repository.recordAutomatic(AutomaticQualitySource.MODEL, AutomaticQualityOutcome.EXPLICIT_UNDO)
        repository.modelResponseMillis(50)
        assertEquals(0L, repository.snapshot()[AutomaticQualitySource.MODEL, AutomaticQualityOutcome.EXPLICIT_UNDO])
        assertEquals(List(5) { 0L }, repository.snapshot().modelResponseBuckets)
        storage.writesSucceed = true
        repository.reset()
        worker.drain()
        repository.recordAutomatic(AutomaticQualitySource.MODEL, AutomaticQualityOutcome.APPLIED)
        worker.drain()
        assertEquals(1L, storage.persisted!![AutomaticQualitySource.MODEL, AutomaticQualityOutcome.APPLIED])
        assertEquals(0L, storage.persisted!![AutomaticQualitySource.MODEL, AutomaticQualityOutcome.EXPLICIT_UNDO])
    }

    @Test fun `application tickets require loaded counted state and do not survive repository reset`() {
        val worker = Worker()
        val storage = Storage()
        val repository = QualityRepository(storage, worker)
        repository.configure(true, false, true)
        assertNull(repository.recordAutomaticApplication(AutomaticQualitySource.MODEL))
        worker.drain()
        val application = repository.recordAutomaticApplication(AutomaticQualitySource.MODEL)!!
        repository.recordAutomaticUndo(application)
        repository.recordAutomaticUndo(application)
        worker.drain()
        assertEquals(1L, storage.persisted!![AutomaticQualitySource.MODEL, AutomaticQualityOutcome.APPLIED])
        assertEquals(1L, storage.persisted!![AutomaticQualitySource.MODEL, AutomaticQualityOutcome.EXPLICIT_UNDO])
        val old = repository.recordAutomaticApplication(AutomaticQualitySource.MODEL)!!
        repository.reset()
        worker.drain()
        repository.recordAutomaticUndo(old)
        worker.drain()
        assertEquals(QualitySnapshot(), storage.persisted)
    }

    @Test fun `model response admission is content free and needs ready collection without scheduling a save`() {
        val worker = Worker()
        val storage = Storage()
        val repository = QualityRepository(storage, worker)
        repository.configure(true, false, true)
        assertNull(repository.beginModelResponse())
        worker.drain()
        val response = repository.beginModelResponse()!!
        assertTrue(worker.tasks.isEmpty())
        assertEquals(0, storage.writes)
        repository.recordModelResponse(response, 250)
        repository.recordModelResponse(response, 250)
        worker.drain()
        assertEquals(listOf(0L, 0L, 0L, 1L, 0L), storage.persisted!!.modelResponseBuckets)
        val old = repository.beginModelResponse()!!
        repository.reset()
        worker.drain()
        repository.recordModelResponse(old, 500)
        worker.drain()
        assertEquals(QualitySnapshot(), repository.snapshot())
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
