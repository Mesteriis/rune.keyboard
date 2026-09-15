package io.github.mesteriis.rune.keyboard.smarttyping.quality

import android.content.Context
import android.util.AtomicFile
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileNotFoundException
import java.util.concurrent.Executors

/** One process-wide owner shared by the IME and dashboard; numeric aggregates never enter backups. */
class QualityStore private constructor(context: Context) : QualityRecorder {
    private val repository = QualityRepository(
        AtomicQualityStorage(File(context.applicationContext.noBackupFilesDir, "typing-quality-v1.txt")),
        Executors.newSingleThreadExecutor { task -> Thread(task, "RuneQualityStore").apply { isDaemon = true } },
    )
    val readiness: QualityRepository.Readiness get() = repository.readiness
    val isReady: Boolean get() = repository.isReady
    val lastWriteSucceeded: Boolean? get() = repository.lastWriteSucceeded
    override fun configure(metricsEnabled: Boolean, shadowEnabled: Boolean, eligible: Boolean) =
        repository.configure(metricsEnabled, shadowEnabled, eligible)
    override fun record(event: QualityEvent) = repository.record(event)
    override fun candidateResponseNanos(durationNanos: Long) = repository.candidateResponseNanos(durationNanos)
    override fun compare(revision: Long, source: String, primaryChoice: String, experimentalChoice: String) =
        repository.compare(revision, source, primaryChoice, experimentalChoice)
    override fun explicitChoice(revision: Long, chosen: String) = repository.explicitChoice(revision, chosen)
    override fun invalidatePending() = repository.invalidatePending()
    fun snapshot(): QualitySnapshot = repository.snapshot()
    fun reset(onComplete: (Boolean) -> Unit = {}) = repository.reset(onComplete)

    companion object {
        @Volatile private var instance: QualityStore? = null
        fun get(context: Context): QualityStore = instance ?: synchronized(this) {
            instance ?: QualityStore(context.applicationContext).also { instance = it }
        }
    }
}

private class AtomicQualityStorage(path: File) : QualityStorage {
    private val file = AtomicFile(path)
    override fun read(): QualitySnapshot? = try {
        file.openRead().use { input ->
            val bytes = ByteArrayOutputStream()
            val buffer = ByteArray(256)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                require(bytes.size() + count <= QualityCodec.MAX_BYTES)
                bytes.write(buffer, 0, count)
            }
            QualityCodec.decode(bytes.toByteArray())
        }
    } catch (error: FileNotFoundException) {
        if (file.baseFile.exists() || File("${file.baseFile.path}.bak").exists()) throw error
        null
    }

    override fun write(snapshot: QualitySnapshot): Boolean {
        var output: java.io.FileOutputStream? = null
        return try {
            output = file.startWrite()
            output.write(QualityCodec.encode(snapshot))
            file.finishWrite(output)
            true
        } catch (_: Exception) {
            file.failWrite(output)
            false
        }
    }
}
