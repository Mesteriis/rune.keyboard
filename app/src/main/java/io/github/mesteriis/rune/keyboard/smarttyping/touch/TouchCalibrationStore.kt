package io.github.mesteriis.rune.keyboard.smarttyping.touch

import android.content.Context
import android.util.AtomicFile
import java.io.File
import java.io.FileNotFoundException
import java.io.IOException
import java.util.concurrent.Executors

/** One process owner, bounded background I/O and atomic no-backup aggregate persistence. */
class TouchCalibrationStore private constructor(context: Context) {
    val model = TouchCalibrationModel()
    @Volatile var isReady: Boolean = false
        private set
    @Volatile var storageAvailable: Boolean = true
        private set
    private val file = AtomicFile(File(context.noBackupFilesDir, "personal-touch-v1.tsv"))
    private val executor = Executors.newSingleThreadExecutor { task ->
        Thread(task, "RuneTouchStore").apply { isDaemon = true }
    }
    private val lock = Any()
    private data class PendingWrite(
        val snapshot: String,
        val resetGeneration: Long? = null,
        val completions: List<(Boolean) -> Unit> = emptyList(),
    )
    private var pendingSnapshot: PendingWrite? = null
    private var resetGeneration = 0L
    private var writeScheduled = false
    private var resetBeforeLoad = false

    init {
        executor.execute {
            val snapshot = try {
                file.openRead().use { input ->
                    val bytes = input.readBytesBounded(TouchCalibrationModel.MAX_SNAPSHOT_BYTES)
                    bytes?.toString(Charsets.UTF_8)
                }
            } catch (_: FileNotFoundException) {
                if (file.baseFile.exists() || File("${file.baseFile.path}.bak").exists()) storageAvailable = false
                null
            } catch (_: IOException) {
                storageAvailable = false
                null
            } catch (_: SecurityException) {
                storageAvailable = false
                null
            }
            synchronized(lock) {
                if (!resetBeforeLoad && snapshot != null && !model.restoreSnapshot(snapshot)) {
                    storageAvailable = false
                }
                if (!resetBeforeLoad) isReady = storageAvailable
            }
        }
    }

    /** Call after acknowledged explicit training. A single pending snapshot coalesces rapid saves. */
    fun scheduleSave(): Boolean = synchronized(lock) {
        if (!isReady) return false
        pendingSnapshot = PendingWrite(model.encodeSnapshot())
        scheduleWriterLocked()
        true
    }

    /**
     * Clears memory immediately; callback runs on the I/O worker after the atomic empty write.
     * Learning remains unavailable until that write succeeds, including recovery from load errors.
     */
    fun reset(onComplete: (Boolean) -> Unit = {}) = synchronized(lock) {
        resetBeforeLoad = true
        isReady = false
        resetGeneration++
        model.reset()
        pendingSnapshot = PendingWrite(
            model.encodeSnapshot(),
            resetGeneration,
            (pendingSnapshot?.completions ?: emptyList()) + onComplete,
        )
        scheduleWriterLocked()
    }

    private fun scheduleWriterLocked() {
        if (writeScheduled) return
        writeScheduled = true
        executor.execute {
            while (true) {
                val snapshot = synchronized(lock) {
                    val next = pendingSnapshot
                    pendingSnapshot = null
                    if (next == null) writeScheduled = false
                    next
                } ?: break
                val success = writeSnapshot(snapshot.snapshot)
                synchronized(lock) {
                    if (!success || snapshot.resetGeneration == resetGeneration) isReady = success
                    if (!success) model.clearPending()
                }
                // The caller can post UI work to its main-thread owner; never call it under a lock.
                snapshot.completions.forEach { it(success) }
            }
        }
    }

    private fun writeSnapshot(snapshot: String): Boolean {
        var output: java.io.FileOutputStream? = null
        try {
            output = file.startWrite()
            output.write(snapshot.toByteArray(Charsets.UTF_8))
            file.finishWrite(output)
            storageAvailable = true
            return true
        } catch (_: IOException) {
            file.failWrite(output)
            storageAvailable = false
            return false
        } catch (_: SecurityException) {
            file.failWrite(output)
            storageAvailable = false
            return false
        }
    }

    private fun java.io.InputStream.readBytesBounded(limit: Int): ByteArray? {
        val output = java.io.ByteArrayOutputStream()
        val buffer = ByteArray(4096)
        while (true) {
            val count = read(buffer)
            if (count < 0) return output.toByteArray()
            if (output.size() + count > limit) {
                storageAvailable = false
                return null
            }
            output.write(buffer, 0, count)
        }
    }

    companion object {
        @Volatile private var instance: TouchCalibrationStore? = null

        fun get(context: Context): TouchCalibrationStore = instance ?: synchronized(this) {
            instance ?: TouchCalibrationStore(context.applicationContext).also { instance = it }
        }
    }
}
