package io.github.mesteriis.rune.keyboard.smarttyping.learning

import android.content.Context
import android.util.AtomicFile
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.File
import java.io.FileNotFoundException
import java.util.concurrent.Executor
import java.util.concurrent.Executors

/** Single asynchronous no-backup writer. Callbacks run on its worker; load failures require reset. */
class LearningStore internal constructor(private val storage: LearningStorage, private val worker: Executor) {
    enum class Readiness { LOADING, RESETTING, READY, FAILED }
    private constructor(context: Context) : this(AndroidLearningStorage(context),
        Executors.newSingleThreadExecutor { task -> Thread(task, "rune-learning-store").apply { isDaemon = true } })
    private val lock = Any()
    private val model = LearningModel()
    private var saveQueued = false
    private var generation = 0L
    @Volatile private var dictionary: (String, KeyboardLanguage) -> Boolean = { _, _ -> false }
    @Volatile var readiness = Readiness.LOADING; private set
    @Volatile var lastWriteSucceeded: Boolean? = null; private set
    val isReady get() = readiness == Readiness.READY
    init {
        worker.execute {
            try {
                val snapshot = storage.read()?.let(LearningCodec::decode) ?: LearningSnapshot()
                synchronized(lock) { if (generation == 0L) { model.restore(snapshot); readiness = Readiness.READY } }
            } catch (_: Exception) { synchronized(lock) { if (generation == 0L) readiness = Readiness.FAILED } }
        }
    }
    fun configure(collectExamples: Boolean, learnPatterns: Boolean, eligible: Boolean) = synchronized(lock) {
        model.configure(collectExamples, learnPatterns, eligible)
    }
    fun accepted(original: String, replacement: String, language: KeyboardLanguage) = record(original, replacement, language, FeedbackSource.ACCEPTED)
    fun confirmed(word: String, language: KeyboardLanguage) = record(word, word, language, FeedbackSource.CONFIRMED)
    fun rejected(original: String, replacement: String, language: KeyboardLanguage) = record(original, replacement, language, FeedbackSource.REJECTED)
    fun manualRetype(original: String, replacement: String, language: KeyboardLanguage) = record(original, replacement, language, FeedbackSource.MANUAL_RETYPE)
    private fun record(original: String, expected: String, language: KeyboardLanguage, source: FeedbackSource): Boolean = synchronized(lock) {
        if (!isReady || !model.record(original, expected, language, source, dictionary)) return false
        lastWriteSucceeded = null
        if (!saveQueued) {
            saveQueued = true
            worker.execute {
                val snapshot = synchronized(lock) { saveQueued = false; model.snapshot() }
                write(snapshot)
            }
        }
        true
    }
    fun preference(original: String, candidate: String, language: KeyboardLanguage): Double = synchronized(lock) {
        if (isReady) model.preference(original, candidate, language) else 0.0
    }
    fun snapshot(): LearningSnapshot = synchronized(lock) { model.snapshot() }
    fun reset(callback: (Boolean) -> Unit = {}) = synchronized(lock) {
        val resetGeneration = ++generation
        model.reset(); readiness = Readiness.RESETTING; lastWriteSucceeded = null
        worker.execute {
            val success = write(LearningSnapshot())
            val current = synchronized(lock) {
                if (generation != resetGeneration) false else {
                    readiness = if (success) Readiness.READY else Readiness.FAILED
                    true
                }
            }
            callback(success && current)
        }
    }
    private fun write(snapshot: LearningSnapshot): Boolean {
        val success = try {
            val bytes = LearningCodec.encode(snapshot)
            storage.write(bytes)
            // AtomicFile.finishWrite logs some failures instead of throwing. Verify committed bytes.
            check(storage.read()?.contentEquals(bytes) == true) { "LEARNING_COMMIT" }
            true
        } catch (_: Exception) { false }
        lastWriteSucceeded = success
        return success
    }
    companion object {
        @Volatile private var instance: LearningStore? = null
        fun get(context: Context, dictionaryContains: ((String, KeyboardLanguage) -> Boolean)? = null): LearningStore {
            val store = instance ?: synchronized(this) {
                instance ?: LearningStore(context.applicationContext).also { instance = it }
            }
            if (dictionaryContains != null) store.dictionary = dictionaryContains
            return store
        }
    }
}

/** Serial worker-only storage boundary; injectable for scheduling and failed-commit regression tests. */
internal interface LearningStorage {
    fun read(): ByteArray?
    fun write(bytes: ByteArray)
}

private class AndroidLearningStorage(context: Context) : LearningStorage {
    private val root = File(context.applicationContext.noBackupFilesDir, "learning-lab")
    private val file = AtomicFile(File(root, "learning.bin"))
    override fun read(): ByteArray? = try {
        file.openRead().use(LearningCodec::readBounded)
    } catch (failure: FileNotFoundException) {
        if (file.baseFile.exists() || File(root, "learning.bin.bak").exists()) throw failure
        null
    }
    override fun write(bytes: ByteArray) {
        check(root.mkdirs() || root.isDirectory)
        val out = file.startWrite()
        try {
            out.write(bytes)
            out.fd.sync() // Propagate sync failures that AtomicFile itself would only log.
            file.finishWrite(out)
        } catch (failure: Exception) { file.failWrite(out); throw failure }
    }
}
