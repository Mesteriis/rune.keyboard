package io.github.mesteriis.rune.keyboard.smarttyping.personalization

import android.content.Context
import android.util.AtomicFile
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.File
import java.io.FileNotFoundException
import java.io.InputStream
import java.util.concurrent.Executors

/**
 * One process-wide owner, stored only under noBackupFilesDir. Reads, imports and atomic writes run
 * on one background thread. Main-thread callers gate queries on [isReady] and mutate via [update].
 * Updates before readiness return false; they are never queued with raw editor text. Callbacks run
 * on the storage thread (the UI caller must dispatch them). A failed load requires explicit reset.
 * Import providers are opened on the storage thread and their streams are always closed there.
 */
class PersonalTypingStore private constructor(context: Context, val model: PersonalTypingModel) {
    enum class Readiness { LOADING, READY, FAILED }
    enum class ImportResult { IMPORTED, EMPTY, INVALID_PROFILE, IO_FAILURE, NOT_READY, CANCELLED }

    private val root = File(context.applicationContext.noBackupFilesDir, "personal-typing")
    private val file = AtomicFile(File(root, "profile.bin"))
    private val lock = Any()
    private val worker = Executors.newSingleThreadExecutor { task -> Thread(task, "rune-personal-store").apply { isDaemon = true } }
    private var saveQueued = false
    private var generation = 0L
    @Volatile var readiness = Readiness.LOADING
        private set
    @Volatile var lastWriteSucceeded: Boolean? = null
        private set
    val isReady: Boolean get() = readiness == Readiness.READY

    init {
        val startGeneration = generation
        worker.execute {
            try {
                val snapshot = try {
                    file.openRead().use { PersonalTypingCodec.decode(PersonalTypingCodec.readBounded(it)) }
                } catch (error: FileNotFoundException) {
                    // An unreadable existing profile is a failure, not permission to erase its evidence.
                    if (file.baseFile.exists() || File(root, "profile.bin.bak").exists()) throw error
                    PersonalTypingSnapshot()
                }
                synchronized(lock) {
                    if (generation == startGeneration) {
                        model.restore(snapshot)
                        readiness = Readiness.READY
                    }
                }
            } catch (_: Exception) {
                synchronized(lock) { if (generation == startGeneration) readiness = Readiness.FAILED }
            }
        }
    }

    fun update(change: (PersonalTypingModel) -> Unit): Boolean = synchronized(lock) {
        if (!isReady) return false
        change(model)
        lastWriteSucceeded = null
        scheduleSaveLocked()
        true
    }

    /** Stops in-flight imports from repopulating the model; reset is durable when callback is true. */
    fun reset(onComplete: (Boolean) -> Unit = {}) {
        synchronized(lock) {
            generation++
            model.reset()
            lastWriteSucceeded = null
            readiness = Readiness.READY
            worker.execute {
                val success = writeCurrent()
                onComplete(success)
            }
        }
    }

    fun importProfile(openInput: () -> InputStream, onComplete: (ImportResult) -> Unit) {
        val requestedGeneration = synchronized(lock) { generation }
        worker.execute {
            val result = try {
                val imported = openInput().use(PersonalTypingCodec::decodeProfile)
                var snapshot: PersonalTypingSnapshot? = null
                val outcome = synchronized(lock) {
                    when {
                        generation != requestedGeneration -> ImportResult.CANCELLED
                        !isReady -> ImportResult.NOT_READY
                        else -> {
                            val count = model.importPhrases(imported)
                            snapshot = model.snapshot()
                            if (count == 0) ImportResult.EMPTY else ImportResult.IMPORTED
                        }
                    }
                }
                if (snapshot != null && !write(checkNotNull(snapshot))) ImportResult.IO_FAILURE else outcome
            } catch (_: IllegalArgumentException) { ImportResult.INVALID_PROFILE
            } catch (_: java.nio.charset.CharacterCodingException) { ImportResult.INVALID_PROFILE
            } catch (_: Exception) { ImportResult.IO_FAILURE }
            onComplete(result)
        }
    }

    private fun scheduleSaveLocked() {
        if (saveQueued) return
        saveQueued = true
        worker.execute {
            // Snapshot and clear the coalescing flag together so a concurrent update schedules a new write.
            val snapshot = synchronized(lock) { saveQueued = false; model.snapshot() }
            write(snapshot)
        }
    }

    private fun writeCurrent(): Boolean = write(synchronized(lock) { model.snapshot() })

    private fun write(snapshot: PersonalTypingSnapshot): Boolean {
        val success = try {
            check(root.mkdirs() || root.isDirectory)
            val bytes = PersonalTypingCodec.encode(snapshot)
            val output = file.startWrite()
            try {
                output.write(bytes)
                file.finishWrite(output)
            } catch (error: Exception) {
                file.failWrite(output)
                throw error
            }
            true
        } catch (_: Exception) { false }
        lastWriteSucceeded = success
        return success
    }

    companion object {
        @Volatile private var instance: PersonalTypingStore? = null

        /** Shared by the service and settings; never create independent writers for the same file. */
        fun get(context: Context, dictionaryContains: (String, KeyboardLanguage) -> Boolean): PersonalTypingStore =
            instance ?: synchronized(this) {
                instance ?: PersonalTypingStore(context.applicationContext, PersonalTypingModel(dictionaryContains)).also { instance = it }
            }
    }
}
