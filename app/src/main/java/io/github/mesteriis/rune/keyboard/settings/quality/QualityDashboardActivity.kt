package io.github.mesteriis.rune.keyboard.settings.quality

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences
import io.github.mesteriis.rune.keyboard.settings.ThemedActivity
import io.github.mesteriis.rune.keyboard.smarttyping.quality.QualityEvent
import io.github.mesteriis.rune.keyboard.smarttyping.quality.QualityRepository
import io.github.mesteriis.rune.keyboard.smarttyping.quality.QualityStore
import io.github.mesteriis.rune.keyboard.smarttyping.quality.ShadowResult

class QualityDashboardActivity : ThemedActivity() {
    private lateinit var store: QualityStore
    private val handler = Handler(Looper.getMainLooper())
    private val refresh = object : Runnable {
        override fun run() {
            render()
            if (store.readiness == QualityRepository.Readiness.LOADING ||
                store.readiness == QualityRepository.Readiness.RESETTING
            ) handler.postDelayed(this, 250)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_quality_dashboard)
        setTitle(R.string.quality_dashboard_title)
        applySystemBarInsets(findViewById(R.id.quality_scroll))
        store = QualityStore.get(this)
        findViewById<Button>(R.id.quality_refresh).setOnClickListener { render() }
        findViewById<Button>(R.id.quality_reset).setOnClickListener {
            store.reset { success ->
                runOnUiThread {
                    if (!isFinishing && !isDestroyed) {
                        render()
                        Toast.makeText(this, if (success) R.string.quality_reset_done else R.string.quality_reset_failed, Toast.LENGTH_LONG).show()
                    }
                }
            }
            render()
        }
    }

    override fun onResume() {
        super.onResume()
        handler.post(refresh)
    }

    override fun onPause() {
        handler.removeCallbacks(refresh)
        super.onPause()
    }

    private fun render() {
        val settings = KeyboardPreferences(this).readSettings()
        fun state(enabled: Boolean) = getString(if (enabled) R.string.quality_enabled else R.string.quality_disabled)
        val storageStatus = when (store.readiness) {
            QualityRepository.Readiness.LOADING -> R.string.quality_storage_loading
            QualityRepository.Readiness.READY -> R.string.quality_storage_ready
            QualityRepository.Readiness.RESETTING -> R.string.quality_storage_resetting
            QualityRepository.Readiness.FAILED -> R.string.quality_storage_failed
        }
        findViewById<TextView>(R.id.quality_status).text = getString(
            R.string.quality_status_format, state(settings.qualityMetrics), state(settings.shadowComparison), getString(storageStatus),
        )
        val snapshot = store.snapshot()
        val eventLabels = listOf(
            R.string.quality_automatic_applied, R.string.quality_explicit_undo,
            R.string.quality_correction_picked, R.string.quality_kept_original,
            R.string.quality_boundary_picked, R.string.quality_abbreviation_picked, R.string.quality_phrase_picked,
        )
        findViewById<TextView>(R.id.quality_actions).text = QualityEvent.entries.joinToString("\n") {
            getString(R.string.quality_count_format, getString(eventLabels[it.ordinal]), snapshot[it])
        }
        val latencyLabels = resources.getStringArray(R.array.quality_latency_labels)
        findViewById<TextView>(R.id.quality_latency).text = snapshot.candidateResponseBuckets.mapIndexed { index, count ->
            getString(R.string.quality_count_format, latencyLabels[index], count)
        }.joinToString("\n")
        val shadowLabels = listOf(
            R.string.quality_shadow_agreement, R.string.quality_shadow_disagreement,
            R.string.quality_shadow_primary, R.string.quality_shadow_experimental,
            R.string.quality_shadow_both, R.string.quality_shadow_neither,
        )
        findViewById<TextView>(R.id.quality_shadow).text = ShadowResult.entries.joinToString("\n") {
            getString(R.string.quality_count_format, getString(shadowLabels[it.ordinal]), snapshot[it])
        }
        findViewById<Button>(R.id.quality_reset).isEnabled = store.readiness != QualityRepository.Readiness.RESETTING
    }
}
