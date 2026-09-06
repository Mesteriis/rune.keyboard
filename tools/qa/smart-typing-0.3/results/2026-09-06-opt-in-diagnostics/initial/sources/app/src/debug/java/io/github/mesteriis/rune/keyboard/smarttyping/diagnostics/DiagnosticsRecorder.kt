package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import java.io.OutputStream
import java.util.ArrayDeque
import java.util.concurrent.Executors

internal enum class DiagnosticStream(val cap: Int) { METADATA(1_048_576), TEXT(4_194_304) }
internal interface DiagnosticsBackend {
    fun loadPreferences(): Map<String, *>
    fun savePreferences(value: DiagnosticsPreferences): Boolean
    fun append(stream: DiagnosticStream, bytes: ByteArray)
    fun snapshot(stream: DiagnosticStream): ByteArray
    fun delete()
}

internal class DiagnosticsRecorder(private val backend: DiagnosticsBackend) : TypingDiagnostics, AutoCloseable {
    private val lock = Object()
    private val events = ArrayDeque<Record>()
    private val controls = ArrayDeque<Command>()
    private var epoch = 0L
    private var bytes = 0
    private var session: Long? = null
    private var closed = false
    private var preferencesChanged = false
    private var exportEpoch = 0L
    private var exportBusy = false
    private val exporter = Executors.newSingleThreadExecutor { task ->
        Thread(task, "Rune-debug-export").apply { isDaemon = true }
    }
    @Volatile private var settings = DiagnosticsPreferences()
    val preferences: DiagnosticsPreferences get() = settings
    val generation: Long get() = synchronized(lock) { epoch }
    val queuedEvents: Int get() = synchronized(lock) { events.size }
    val queuedBytes: Int get() = synchronized(lock) { bytes }
    private val writer = Thread(::runWriter, "Rune-debug-diagnostics").apply { isDaemon = true }

    init {
        controls.add(Command({
            val loaded = DiagnosticsPreferences.decode(backend.loadPreferences())
            synchronized(lock) {
                // An early input session may already have advanced the event generation.
                // Load stored choices, but never arm that pre-load session retroactively.
                if (!preferencesChanged && !closed) { settings = loaded; session = null }
            }
            true
        }, {}))
        writer.start()
    }

    fun setMetadata(enabled: Boolean, done: (Boolean) -> Unit) = change(null,
        { it.copy(metadata = enabled) }, done)
    fun enableText(grant: DiagnosticsConsent.Grant, done: (Boolean) -> Unit) = change(grant.generation,
        { it.copy(text = true) }, done)
    fun disableText(done: (Boolean) -> Unit) = change(null, { it.copy(text = false) }, done)

    private fun change(requiredGeneration: Long?, transform: (DiagnosticsPreferences) -> DiagnosticsPreferences,
        done: (Boolean) -> Unit) {
        synchronized(lock) {
            if (closed || requiredGeneration != null && requiredGeneration != epoch) { deliver(done, false); return }
            preferencesChanged = true
            val desired = transform(settings)
            val changed = invalidateQueued()
            // Disable immediately; enabling becomes visible only after successful persistence.
            settings = DiagnosticsPreferences(settings.metadata && desired.metadata, settings.text && desired.text)
            submit(Command({
                val saved = backend.savePreferences(desired)
                synchronized(lock) {
                    if (epoch == changed && !closed) {
                        settings = if (saved) desired else DiagnosticsPreferences()
                        session = null
                    }
                    saved && epoch == changed && !closed
                }
            }, done))
        }
    }

    fun delete(done: (Boolean) -> Unit) {
        synchronized(lock) {
            if (closed) { deliver(done, false); return }
            preferencesChanged = true
            invalidateQueued(); exportEpoch++
            settings = DiagnosticsPreferences()
            submit(Command({
                val saved = try { backend.savePreferences(DiagnosticsPreferences()) } catch (_: Exception) { false }
                backend.delete()
                saved
            }, done))
        }
    }

    /** A fence drains only its bounded current queue, so controls cannot be starved by new typing. */
    fun barrier(done: (Boolean) -> Unit) = synchronized(lock) {
        submit(Command({ flush(); true }, done))
    }

    /** A ticket holds no text and is invalid after delete or any subsequent export request. */
    fun newExport(): Long = synchronized(lock) { ++exportEpoch }
    fun cancelExport(ticket: Long) { synchronized(lock) { if (ticket == exportEpoch) exportEpoch++ } }
    fun export(ticket: Long, stream: DiagnosticStream, open: () -> OutputStream?, done: (Boolean) -> Unit) {
        synchronized(lock) {
            if (closed || exportBusy || ticket != exportEpoch) { deliver(done, false); return }
            exportBusy = true
            submit(Command({
                if (!validExport(ticket)) false else {
                    flush()
                    val snapshot = backend.snapshot(stream)
                    if (snapshot.size > stream.cap || !validExport(ticket)) false else {
                        // Exactly one snapshot/job is admitted. Slow provider I/O never owns
                        // the managed writer or its controls; newer tickets cancel this copy.
                        exporter.execute {
                            val success = try { copyExport(ticket, snapshot, open) } catch (_: Throwable) { false }
                            synchronized(lock) { exportBusy = false }
                            deliver(done, success)
                        }
                        true
                    }
                }
            }, { dispatched ->
                if (!dispatched) {
                    synchronized(lock) { exportBusy = false }
                    deliver(done, false)
                }
            }))
        }
    }
    private fun copyExport(ticket: Long, snapshot: ByteArray, open: () -> OutputStream?): Boolean {
        if (!validExport(ticket)) return false
        val output = open() ?: return false
        return output.use { sink ->
            var offset = 0
            while (offset < snapshot.size && validExport(ticket)) {
                val count = minOf(RECORD_BYTES, snapshot.size - offset)
                sink.write(snapshot, offset, count)
                offset += count
            }
            offset == snapshot.size && validExport(ticket)
        }
    }
    private fun validExport(ticket: Long) = synchronized(lock) { !closed && ticket == exportEpoch }

    override fun startSession(session: Long, eligible: Boolean, fresh: Boolean) {
        synchronized(lock) {
            invalidateQueued()
            this.session = session.takeIf { !closed && eligible && fresh && it >= 0 && (settings.metadata || settings.text) }
        }
    }
    override fun invalidate() { synchronized(lock) { invalidateQueued() } }

    override fun record(event: DiagnosticEvent, text: (() -> DiagnosticText)?) {
        try {
            synchronized(lock) {
                if (closed || session != event.session || event.session < 0) return
                if (settings.metadata) enqueue(DiagnosticStream.METADATA, DiagnosticsEncoding.metadata(event))
                // Gate before invoking the supplier or copying any Rune-owned payload.
                if (settings.text && text != null && events.size < MAX_EVENTS && bytes < QUEUE_BYTES) {
                    val admittedGeneration = epoch
                    val payload = text()
                    if (!closed && settings.text && epoch == admittedGeneration && session == event.session) {
                        enqueue(DiagnosticStream.TEXT, DiagnosticsEncoding.text(event, payload))
                    }
                }
            }
        } catch (_: Throwable) { /* Optional diagnostics cannot change typing. No exception text retained. */ }
    }

    private fun enqueue(stream: DiagnosticStream, value: ByteArray) {
        if (value.size > RECORD_BYTES || events.size >= MAX_EVENTS || value.size > QUEUE_BYTES - bytes) return
        events.add(Record(epoch, stream, value)); bytes += value.size; lock.notifyAll()
    }
    private fun invalidateQueued(): Long {
        epoch++; session = null; events.clear(); bytes = 0
        return epoch
    }
    private fun submit(command: Command) {
        if (closed || controls.size >= MAX_CONTROLS) { deliver(command.done, false); return }
        controls.add(command); lock.notifyAll()
    }
    private fun runWriter() {
        while (true) {
            val work = synchronized(lock) {
                while (!closed && controls.isEmpty() && events.isEmpty()) lock.wait()
                if (closed) return
                if (controls.isNotEmpty()) controls.removeFirst() else removeEvent()
            }
            when (work) {
                is Command -> {
                    val success = try { work.run() } catch (_: Throwable) { false }
                    deliver(work.done, success)
                }
                is Record -> write(work)
            }
        }
    }
    private fun removeEvent(): Record = events.removeFirst().also { bytes -= it.value.size }
    private fun flush() {
        val count = synchronized(lock) { events.size }
        repeat(count) {
            val next = synchronized(lock) { if (events.isEmpty()) null else removeEvent() } ?: return
            write(next)
        }
    }
    private fun write(record: Record) {
        val admitted = synchronized(lock) {
            !closed && record.generation == epoch && when (record.stream) {
                DiagnosticStream.METADATA -> settings.metadata
                DiagnosticStream.TEXT -> settings.text
            }
        }
        if (admitted) try { backend.append(record.stream, record.value) } catch (_: Throwable) { /* No payload logging. */ }
    }
    override fun close() {
        synchronized(lock) {
            if (closed) return
            closed = true; invalidateQueued(); exportEpoch++
            while (controls.isNotEmpty()) deliver(controls.removeFirst().done, false)
            lock.notifyAll()
        }
        exporter.shutdownNow()
        if (Thread.currentThread() !== writer) writer.join(5_000)
    }
    private class Record(val generation: Long, val stream: DiagnosticStream, val value: ByteArray)
    private class Command(val run: () -> Boolean, val done: (Boolean) -> Unit)
    companion object {
        const val MAX_EVENTS = 256
        const val QUEUE_BYTES = 512 * 1024
        const val RECORD_BYTES = 8 * 1024
        private const val MAX_CONTROLS = 16
        private fun deliver(done: (Boolean) -> Unit, success: Boolean) { try { done(success) } catch (_: Throwable) { } }
    }
}
