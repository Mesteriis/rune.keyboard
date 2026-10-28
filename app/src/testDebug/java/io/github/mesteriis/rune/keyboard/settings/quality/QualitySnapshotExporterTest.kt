package io.github.mesteriis.rune.keyboard.settings.quality

import io.github.mesteriis.rune.keyboard.smarttyping.quality.*
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.util.concurrent.Executor
import java.util.concurrent.RejectedExecutionException
import org.junit.Assert.*
import org.junit.Test

class QualitySnapshotExporterTest {
    private class Worker : Executor {
        val tasks = ArrayDeque<Runnable>()
        override fun execute(command: Runnable) { tasks.addLast(command) }
        fun drain() { while (tasks.isNotEmpty()) tasks.removeFirst().run() }
    }
    private val worker = Worker()
    private val repository = QualityRepository(object : QualityStorage {
        override fun read(): QualitySnapshot? = null
        override fun write(snapshot: QualitySnapshot) = true
    }, worker).also { worker.drain() }
    private val exporter = QualitySnapshotExporter(worker, repository::isSnapshotCurrent)

    @Test fun `exports only the captured bounded numeric codec and closes its sink`() {
        repository.configure(true, false, true)
        repository.recordAutomatic(AutomaticQualitySource.MODEL, AutomaticQualityOutcome.APPLIED)
        val ticket = repository.captureSnapshot()!!
        val sink = object : ByteArrayOutputStream() {
            var closed = false
            override fun close() { closed = true; super.close() }
        }
        var result: Boolean? = null
        exporter.export(ticket, { sink }) { result = it }
        repository.recordAutomatic(AutomaticQualitySource.MODEL, AutomaticQualityOutcome.APPLIED)
        worker.drain()
        assertEquals(true, result)
        assertTrue(sink.closed)
        assertTrue(sink.size() <= QualityCodec.MAX_BYTES)
        assertEquals(ticket.snapshot, QualityCodec.decode(sink.toByteArray()))
        assertEquals(1L, QualityCodec.decode(sink.toByteArray())[AutomaticQualitySource.MODEL, AutomaticQualityOutcome.APPLIED])
    }

    @Test fun `busy duplicate and cancelled queued export never open a second document`() {
        val ticket = repository.captureSnapshot()!!
        var opens = 0
        val results = mutableListOf<Boolean>()
        repeat(2) { exporter.export(ticket, { opens++; ByteArrayOutputStream() }, results::add) }
        assertEquals(listOf(false), results)
        exporter.close()
        worker.drain()
        exporter.export(ticket, { opens++; ByteArrayOutputStream() }, results::add)
        assertEquals(listOf(false, false, false), results)
        assertEquals(0, opens)
    }

    @Test fun `reset before queued export prevents opening provider even after reset completes`() {
        val ticket = repository.captureSnapshot()!!
        repository.reset()
        var opens = 0
        var result: Boolean? = null
        exporter.export(ticket, { opens++; ByteArrayOutputStream() }) { result = it }
        worker.drain()
        assertEquals(false, result)
        assertEquals(0, opens)
    }

    @Test fun `reset or close during provider open prevents write and closes stream`() {
        for (reset in listOf(true, false)) {
            val local = QualitySnapshotExporter(worker, repository::isSnapshotCurrent)
            val ticket = repository.captureSnapshot()!!
            var closed = false
            val sink = object : ByteArrayOutputStream() {
                override fun close() { closed = true }
            }
            var result: Boolean? = null
            local.export(ticket, {
                if (reset) repository.reset() else local.close()
                sink
            }) { result = it }
            worker.drain()
            assertEquals(false, result)
            assertTrue(closed)
            assertEquals(0, sink.size())
        }
    }

    @Test fun `invalid mutable numeric payload is rejected before opening provider`() {
        val values = MutableList(8) { 0L }
        val ticket = QualitySnapshotTicket(QualitySnapshotOrigin(), QualitySnapshot(events = values))
        values[0] = -1
        val local = QualitySnapshotExporter(worker) { true }
        var opens = 0
        var result: Boolean? = null
        local.export(ticket, { opens++; ByteArrayOutputStream() }) { result = it }
        worker.drain()
        assertEquals(false, result)
        assertEquals(0, opens)
    }

    @Test fun `provider failures close stream and release busy state without retry`() {
        val ticket = repository.captureSnapshot()!!
        var closed = false
        val results = mutableListOf<Boolean>()
        val sink = object : java.io.OutputStream() {
            override fun write(value: Int) { throw IOException("synthetic") }
            override fun close() { closed = true }
        }
        exporter.export(ticket, { sink }, results::add)
        worker.drain()
        assertTrue(closed)
        exporter.export(ticket, { null }, results::add)
        worker.drain()
        exporter.export(ticket, { throw IOException("synthetic open") }, results::add)
        worker.drain()
        assertEquals(listOf(false, false, false), results)
    }

    @Test fun `executor rejection reports failure without opening a provider`() {
        val local = QualitySnapshotExporter(Executor { throw RejectedExecutionException() }) { true }
        var result: Boolean? = null
        local.export(repository.captureSnapshot()!!, { fail("must not open"); null }) { result = it }
        assertEquals(false, result)
    }
}
