package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import android.content.Context
import android.content.res.AssetManager
import android.os.Handler
import android.os.Looper
import android.os.Trace
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.SmartTypingTraceSection
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

    /** Obtaining the shared handle does not request any RU asset I/O. */
    fun get(): ExperimentModels = models

    /** The language owner requests this once Russian is enabled. */
    internal fun loadRussian(context: Context) {
        synchronized(lock) {
            if (started) return
            started = true
        }
        val assets = context.applicationContext.assets
        val executor = Executors.newSingleThreadExecutor { task -> Thread(task, "rune-experiment-assets") }
        executor.execute {
            try {
                loadAssets(assets)
            } finally {
                val pending = synchronized(lock) {
                    finished = true
                    callbacks.toList().also { callbacks.clear() }
                }
                pending.forEach { callback -> main.post { callback() } }
                executor.shutdown()
            }
        }
    }

    private fun loadAssets(assets: AssetManager) {
        Trace.beginSection(SmartTypingTraceSection.CONTEXTUAL_ASSETS_LOAD.sectionName)
        try {
            asset(assets, "ru-ranker.bin", FrozenExperimentAssets.RANK_BYTES, FrozenExperimentAssets.RANK_SHA256)
                ?.let(models::loadRanker)
            asset(assets, "ru-ranker-auto-v1.bin", FrozenExperimentAssets.LEGACY_AUTOMATIC_RANK_BYTES,
                FrozenExperimentAssets.LEGACY_AUTOMATIC_RANK_SHA256)
                ?.let(models::loadLegacyAutomaticRanker)
            asset(assets, "ru-neighbor-ranker.bin",
                io.github.mesteriis.rune.keyboard.smarttyping.correction.RecoveryQualification.RANKER_BYTES,
                io.github.mesteriis.rune.keyboard.smarttyping.correction.RecoveryQualification.RANKER_SHA256)
                ?.let(models::loadRecoveryRanker)
            asset(assets, "ru-joint-ranker.bin",
                io.github.mesteriis.rune.keyboard.smarttyping.correction.JointQualification.RANKER_BYTES,
                io.github.mesteriis.rune.keyboard.smarttyping.correction.JointQualification.RANKER_SHA256)
                ?.let(models::loadJointRanker)
            asset(assets, "ru-joint-rescue-ranker.bin",
                io.github.mesteriis.rune.keyboard.smarttyping.correction.JointRescueQualification.RANKER_BYTES,
                io.github.mesteriis.rune.keyboard.smarttyping.correction.JointRescueQualification.RANKER_SHA256)
                ?.let(models::loadRescueRanker)
            asset(assets, "ru-ranking-context.bin", FrozenExperimentAssets.RANKING_CONTEXT_BYTES, FrozenExperimentAssets.RANKING_CONTEXT_SHA256)
                ?.let(models::loadContext)
            asset(assets, "ru-context.bin", FrozenExperimentAssets.CONTEXT_BYTES, FrozenExperimentAssets.CONTEXT_SHA256)
                ?.let(models::loadTapContext)
            if (asset(assets, "ru-contextual-policy.json", FrozenContextualAssets.POLICY_BYTES,
                    FrozenContextualAssets.POLICY_SHA256) != null) {
                asset(assets, "ru-contextual-ranker.bin", FrozenContextualAssets.MODEL_BYTES, FrozenContextualAssets.MODEL_SHA256)
                    ?.let { AndroidContextualRankerLoader.load(assets, it) }
                    ?.let(models::loadContextualRanker)
            }
            if (models.contextualReady) {
                Trace.beginSection(SmartTypingTraceSection.CONTEXTUAL_READY.sectionName)
                Trace.endSection()
            }
            if (models.contextualReady && asset(assets, "ru-infinitive-revision-policy.json",
                    FrozenInfinitiveRevisionAssets.POLICY_BYTES, FrozenInfinitiveRevisionAssets.POLICY_SHA256) != null) {
                asset(assets, "ru-infinitive-revision-ranker.bin", FrozenInfinitiveRevisionAssets.MODEL_BYTES,
                    FrozenInfinitiveRevisionAssets.MODEL_SHA256)?.let(models::loadGrammarRevisionRanker)
            }
            if (models.grammarRevisionReady && asset(assets, "ru-noun-case-policy.json",
                    FrozenNounCaseAssets.POLICY_BYTES, FrozenNounCaseAssets.POLICY_SHA256) != null) {
                asset(assets, "ru-noun-case-ranker.bin", FrozenNounCaseAssets.MODEL_BYTES,
                    FrozenNounCaseAssets.MODEL_SHA256)?.let(models::loadNounCaseRanker)
            }
        } finally {
            Trace.endSection()
        }
    }

    private fun asset(assets: AssetManager, name: String, size: Int, hash: String): ByteArray? = try {
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

    /** Fires after a requested RU load, including failure; stays pending while RU is deferred. */
    fun whenReady(callback: () -> Unit): Closeable {
        var active = true
        val guarded = { synchronized(lock) { if (active) callback() } }
        synchronized(lock) {
            if (finished) main.post { guarded() } else callbacks.add(guarded)
        }
        return Closeable { synchronized(lock) { active = false; callbacks.remove(guarded) } }
    }
}
