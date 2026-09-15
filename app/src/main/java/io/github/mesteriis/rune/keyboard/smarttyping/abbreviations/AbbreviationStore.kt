package io.github.mesteriis.rune.keyboard.smarttyping.abbreviations

import android.content.Context
import android.util.AtomicFile
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.io.File
import java.io.FileNotFoundException
import java.util.concurrent.Executors

/** Process-wide no-backup owner. All IO and completion callbacks run on its single worker. */
class AbbreviationStore private constructor(context: Context) {
    enum class Readiness { LOADING, READY, FAILED }
    val model = AbbreviationModel()
    @Volatile var readiness = Readiness.LOADING
        private set
    val isReady: Boolean get() = readiness == Readiness.READY
    private val root = File(context.applicationContext.noBackupFilesDir, "abbreviations")
    private val file = AtomicFile(File(root, "entries.bin"))
    private val worker = Executors.newSingleThreadExecutor { task ->
        Thread(task, "rune-abbreviation-store").apply { isDaemon = true }
    }

    init {
        worker.execute {
            try {
                val entries = try {
                    file.openRead().use { AbbreviationCodec.decode(AbbreviationCodec.readBounded(it)) }
                } catch (error: FileNotFoundException) {
                    if (file.baseFile.exists() || File(root, "entries.bin.bak").exists()) throw error
                    emptyList()
                }
                model.restore(entries)
                readiness = Readiness.READY
            } catch (_: Exception) { readiness = Readiness.FAILED }
        }
    }

    fun whenReady(onComplete: (Readiness) -> Unit) { worker.execute { onComplete(readiness) } }

    fun save(language: KeyboardLanguage, key: String, expansion: String, original: Abbreviation? = null,
        onComplete: (AbbreviationResult) -> Unit) = mutate(onComplete) { it.save(language, key, expansion, original) }

    fun delete(entry: Abbreviation, onComplete: (AbbreviationResult) -> Unit) =
        mutate(onComplete) { it.delete(entry) }

    /** Explicit recovery after unreadable data; failed writes retain the old model and readiness. */
    fun reset(onComplete: (AbbreviationResult) -> Unit) {
        worker.execute { onComplete(commit(emptyList())) }
    }

    private fun mutate(onComplete: (AbbreviationResult) -> Unit, change: (AbbreviationModel) -> AbbreviationResult) {
        worker.execute {
            if (!isReady) {
                onComplete(AbbreviationResult.NOT_READY)
                return@execute
            }
            val candidate = AbbreviationModel().apply { restore(model.snapshot()) }
            val result = change(candidate)
            onComplete(if (result == AbbreviationResult.SAVED) commit(candidate.snapshot()) else result)
        }
    }

    private fun commit(entries: List<Abbreviation>): AbbreviationResult {
        try {
            check(root.mkdirs() || root.isDirectory)
            val bytes = AbbreviationCodec.encode(entries)
            val output = file.startWrite()
            try {
                output.write(bytes)
                file.finishWrite(output)
            } catch (error: Exception) {
                file.failWrite(output)
                throw error
            }
        } catch (_: Exception) { return AbbreviationResult.IO_FAILURE }
        model.restore(entries)
        readiness = Readiness.READY
        return AbbreviationResult.SAVED
    }

    companion object {
        @Volatile private var instance: AbbreviationStore? = null
        fun get(context: Context): AbbreviationStore = instance ?: synchronized(this) {
            instance ?: AbbreviationStore(context.applicationContext).also { instance = it }
        }
    }
}
