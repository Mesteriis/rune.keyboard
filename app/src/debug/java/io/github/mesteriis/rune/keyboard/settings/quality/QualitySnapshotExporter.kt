package io.github.mesteriis.rune.keyboard.settings.quality

import io.github.mesteriis.rune.keyboard.smarttyping.quality.QualityCodec
import io.github.mesteriis.rune.keyboard.smarttyping.quality.QualitySnapshotTicket
import java.io.OutputStream
import java.util.concurrent.Executor

/** Debug UI owns the sink. No URI or stream capability is passed into the IME or repository. */
internal class QualitySnapshotExporter(
    private val worker: Executor,
    private val isCurrent: (QualitySnapshotTicket) -> Boolean,
) : AutoCloseable {
    private val lock = Any()
    private var closed = false
    private var busy = false

    fun export(ticket: QualitySnapshotTicket, open: () -> OutputStream?, done: (Boolean) -> Unit) {
        val accepted = synchronized(lock) {
            if (closed || busy) false else { busy = true; true }
        }
        if (!accepted) { done(false); return }
        try {
            worker.execute {
                val success = try {
                    val bytes = QualityCodec.encode(ticket.snapshot)
                    QualityCodec.decode(bytes) // Validate bounded numeric payload before opening a document.
                    if (!valid(ticket)) false else open()?.use { stream ->
                        if (!valid(ticket)) false else {
                            stream.write(bytes)
                            valid(ticket)
                        }
                    } ?: false
                } catch (_: Exception) { false }
                synchronized(lock) { busy = false }
                done(success)
            }
        } catch (_: java.util.concurrent.RejectedExecutionException) {
            synchronized(lock) { busy = false }
            done(false)
        }
    }

    private fun valid(ticket: QualitySnapshotTicket): Boolean =
        synchronized(lock) { !closed } && isCurrent(ticket)

    // Cancellation prevents a future write; bytes already handed to a provider cannot be retracted.
    override fun close() { synchronized(lock) { closed = true } }
}
