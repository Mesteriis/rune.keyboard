package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import android.content.Context
import android.os.Handler
import android.os.Looper
import java.io.Closeable
import java.io.IOException
import java.security.MessageDigest
import java.util.concurrent.Executors

/** One process resource owner; all asset reads, digest checks and decoding run off the UI thread. */
object AndroidExperimentResources {
    private val models = ExperimentModels()
    private val lock = Any()
    private val callbacks = LinkedHashSet<() -> Unit>()
    private var started = false
    private var finished = false
    private val main by lazy { Handler(Looper.getMainLooper()) }

    fun get(context: Context): ExperimentModels {
        synchronized(lock) {
            if (started) return models
            started = true
        }
        val assets = context.applicationContext.assets
        val executor = Executors.newSingleThreadExecutor { task -> Thread(task, "rune-experiment-assets") }
        executor.execute {
            try {
                fun asset(name: String, size: Int, hash: String): ByteArray? = try {
                    assets.open("smarttyping/experiments/$name").use { input ->
                        val buffer = ByteArray(size + 1)
                        var count = 0
                        while (count < buffer.size) {
                            val read = input.read(buffer, count, buffer.size - count)
                            if (read < 0) break
                            if (read == 0) return@use null
                            count += read
                        }
                        val bytes = buffer.copyOf(count)
                        if (bytes.size != size) null else {
                            val actual = MessageDigest.getInstance("SHA-256").digest(bytes)
                                .joinToString("") { "%02x".format(it) }
                            bytes.takeIf { actual == hash }
                        }
                    }
                } catch (_: IOException) { null }
                asset("ru-ranker.bin", FrozenExperimentAssets.RANK_BYTES, FrozenExperimentAssets.RANK_SHA256)
                    ?.let(models::loadRanker)
                asset("ru-context.bin", FrozenExperimentAssets.CONTEXT_BYTES, FrozenExperimentAssets.CONTEXT_SHA256)
                    ?.let(models::loadContext)
            } finally {
                val pending = synchronized(lock) {
                    finished = true
                    callbacks.toList().also { callbacks.clear() }
                }
                pending.forEach { callback -> main.post { callback() } }
                executor.shutdown()
            }
        }
        return models
    }

    /** Completion fires even if assets are unavailable. Close on editor/service teardown. */
    fun whenReady(callback: () -> Unit): Closeable {
        var active = true
        val guarded = { synchronized(lock) { if (active) callback() } }
        synchronized(lock) {
            if (finished) main.post { guarded() } else callbacks.add(guarded)
        }
        return Closeable { synchronized(lock) { active = false; callbacks.remove(guarded) } }
    }
}
