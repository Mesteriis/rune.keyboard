package io.github.mesteriis.rune.keyboard.intelligence.delivery

import android.util.AtomicFile
import java.io.File
import java.io.RandomAccessFile
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

class DeliveryStateStore(private val root: File) {
    val stateFile = File(root, "delivery-state.json")
    private val lockFile = File(root, "delivery-state.lock")
    private val localLock = localLocks.computeIfAbsent(lockFile.canonicalPath) { ReentrantLock() }
    private val atomicFile get() = AtomicFile(stateFile)

    init {
        check(root.mkdirs() || root.isDirectory) { "Cannot create model delivery state directory" }
    }

    fun read(): DeliveryJournal = locked {
        if (!stateFile.exists()) DeliveryJournal() else DeliveryStateCodec.decode(atomicFile.readFully().toString(Charsets.UTF_8))
    }

    fun write(state: DeliveryJournal) = locked {
        val output = atomicFile.startWrite()
        try {
            output.write(DeliveryStateCodec.encode(state).toByteArray(Charsets.UTF_8))
            atomicFile.finishWrite(output)
        } catch (error: Throwable) {
            atomicFile.failWrite(output)
            throw error
        }
    }

    fun update(transform: (DeliveryJournal) -> DeliveryJournal): DeliveryJournal = locked {
        val current = if (stateFile.exists()) {
            DeliveryStateCodec.decode(atomicFile.readFully().toString(Charsets.UTF_8))
        } else {
            DeliveryJournal()
        }
        transform(current).also { next ->
            val output = atomicFile.startWrite()
            try {
                output.write(DeliveryStateCodec.encode(next).toByteArray(Charsets.UTF_8))
                atomicFile.finishWrite(output)
            } catch (error: Throwable) {
                atomicFile.failWrite(output)
                throw error
            }
        }
    }

    private fun <T> locked(block: () -> T): T = localLock.withLock {
        RandomAccessFile(lockFile, "rw").use { randomAccess ->
            randomAccess.channel.lock().use { return block() }
        }
    }

    companion object {
        private val localLocks = ConcurrentHashMap<String, ReentrantLock>()

        fun forApplication(context: android.content.Context): DeliveryStateStore =
            DeliveryStateStore(File(context.noBackupFilesDir, "model-delivery"))
    }
}
