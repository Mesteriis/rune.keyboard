package io.github.mesteriis.rune.keyboard.smarttyping.controls

import android.content.Context
import android.util.AtomicFile
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.File
import java.io.FileNotFoundException
import java.util.concurrent.Executors

/** One writer; updates become visible only after the exact snapshot is durably committed. */
class TypingControlStore private constructor(context: Context) {
    enum class Readiness { LOADING, READY, FAILED }
    enum class Result { SAVED, INVALID_OR_FULL, NOT_READY, IO_FAILURE }
    @Volatile var readiness = Readiness.LOADING
        private set
    @Volatile var snapshot = TypingControlSnapshot()
        private set
    val isReady get() = readiness == Readiness.READY
    private val file = AtomicFile(File(context.applicationContext.noBackupFilesDir, "typing-controls-v1.bin"))
    private val worker = Executors.newSingleThreadExecutor { task -> Thread(task, "RuneTypingControls").apply { isDaemon = true } }
    init {
        worker.execute {
            try {
                snapshot = try {
                    file.openRead().use { input ->
                        val bytes = java.io.ByteArrayOutputStream()
                        val buffer = ByteArray(1024)
                        while (true) {
                            val count = input.read(buffer)
                            if (count < 0) break
                            require(bytes.size() + count <= TypingControlCodec.MAX_BYTES)
                            bytes.write(buffer, 0, count)
                        }
                        TypingControlCodec.decode(bytes.toByteArray())
                    }
                } catch (error: FileNotFoundException) {
                    if (file.baseFile.exists() || File("${file.baseFile.path}.bak").exists()) throw error
                    TypingControlSnapshot()
                }
                readiness = Readiness.READY
            } catch (_: Exception) { readiness = Readiness.FAILED }
        }
    }
    fun whenReady(callback: (Readiness) -> Unit) { worker.execute { callback(readiness) } }
    fun protect(word: String, language: KeyboardLanguage, callback: (Result) -> Unit) =
        mutate(callback) { TypingControlModel.addWord(it, word, language) }
    fun removeWord(word: ProtectedWord, callback: (Result) -> Unit) = mutate(callback) { it.copy(words = it.words - word) }
    fun observePackage(packageName: String) = mutate({}) { TypingControlModel.observePackage(it, packageName) }
    fun assign(packageName: String, profile: TypingProfile, callback: (Result) -> Unit) =
        mutate(callback) { TypingControlModel.assign(it, packageName, profile) }
    fun removeApp(packageName: String, callback: (Result) -> Unit) = mutate(callback) {
        it.copy(apps = it.apps.filterNot { app -> app.packageName == packageName })
    }
    fun resetWords(callback: (Result) -> Unit) = mutate(callback) { it.copy(words = emptyList()) }
    fun resetApps(callback: (Result) -> Unit) = mutate(callback) { it.copy(apps = emptyList()) }
    /** Full explicit reset also recovers unreadable state. */
    fun reset(callback: (Result) -> Unit) { worker.execute { callback(commit(TypingControlSnapshot())) } }
    private fun mutate(callback: (Result) -> Unit, change: (TypingControlSnapshot) -> TypingControlSnapshot?) {
        worker.execute {
            if (!isReady) { callback(Result.NOT_READY); return@execute }
            val value = change(snapshot)
            callback(when { value == null -> Result.INVALID_OR_FULL; value == snapshot -> Result.SAVED; else -> commit(value) })
        }
    }
    private fun commit(value: TypingControlSnapshot): Result {
        var stream: java.io.FileOutputStream? = null
        return try {
            val bytes = TypingControlCodec.encode(value)
            stream = file.startWrite()
            stream.write(bytes)
            stream.fd.sync()
            file.finishWrite(stream)
            check(file.openRead().use { input ->
                val actual = ByteArray(bytes.size)
                var read = 0
                while (read < actual.size) {
                    val count = input.read(actual, read, actual.size - read)
                    if (count < 0) break
                    read += count
                }
                read == bytes.size && actual.contentEquals(bytes) && input.read() == -1
            })
            snapshot = value
            readiness = Readiness.READY
            Result.SAVED
        } catch (_: Exception) { file.failWrite(stream); Result.IO_FAILURE }
    }
    companion object {
        @Volatile private var instance: TypingControlStore? = null
        fun get(context: Context): TypingControlStore = instance ?: synchronized(this) {
            instance ?: TypingControlStore(context.applicationContext).also { instance = it }
        }
    }
}
