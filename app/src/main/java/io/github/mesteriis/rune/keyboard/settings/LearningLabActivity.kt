package io.github.mesteriis.rune.keyboard.settings

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.Button
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.smarttyping.learning.AndroidLearningEvaluation
import io.github.mesteriis.rune.keyboard.smarttyping.learning.LearningEvaluation
import io.github.mesteriis.rune.keyboard.smarttyping.learning.LearningEvaluator
import io.github.mesteriis.rune.keyboard.smarttyping.learning.LearningStore
import java.util.concurrent.Executors
import java.util.concurrent.Future

class LearningLabActivity : ThemedActivity() {
    private lateinit var store: LearningStore
    private val handler = Handler(Looper.getMainLooper())
    private val worker = Executors.newSingleThreadExecutor()
    private var running: Future<*>? = null
    private var revision = 0
    private val refresh = object : Runnable {
        override fun run() {
            // Capture before rendering so completion during render still gets a terminal refresh.
            val pending = store.readiness == LearningStore.Readiness.LOADING ||
                store.readiness == LearningStore.Readiness.RESETTING ||
                store.readiness == LearningStore.Readiness.PROMOTING
            render()
            if (pending) handler.postDelayed(this, 250)
        }
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_learning_lab)
        setTitle(R.string.learning_title)
        applySystemBarInsets(findViewById(R.id.learning_scroll))
        store = LearningStore.get(this)
        findViewById<Button>(R.id.learning_run).setOnClickListener { evaluate() }
        findViewById<Button>(R.id.learning_reset).setOnClickListener {
            cancelRun()
            findViewById<TextView>(R.id.learning_results).setText(R.string.learning_resetting)
            store.reset { success -> handler.post {
                if (!isDestroyed && !isFinishing) {
                    render(); findViewById<TextView>(R.id.learning_results).setText(if (success) R.string.learning_reset_done else R.string.learning_failed)
                }
            } }
        }
    }
    override fun onResume() { super.onResume(); handler.post(refresh) }
    override fun onPause() { cancelRun(); handler.removeCallbacks(refresh); super.onPause() }
    override fun onDestroy() { worker.shutdownNow(); handler.removeCallbacksAndMessages(null); super.onDestroy() }
    private fun cancelRun() { revision++; running?.cancel(true); running = null; findViewById<Button>(R.id.learning_run).isEnabled = store.isReady }
    private fun render() {
        val snapshot = store.snapshot()
        val status = when (store.readiness) {
            LearningStore.Readiness.LOADING -> R.string.learning_loading
            LearningStore.Readiness.RESETTING -> R.string.learning_resetting
            LearningStore.Readiness.PROMOTING -> R.string.learning_promoting
            LearningStore.Readiness.READY -> R.string.learning_ready
            LearningStore.Readiness.FAILED -> R.string.learning_failed
        }
        findViewById<TextView>(R.id.learning_status).text = getString(R.string.learning_status_format,
            getString(if (store.lastWriteSucceeded == false) R.string.learning_failed else status), snapshot.examples.size, snapshot.examples.count { !it.holdout }, snapshot.examples.count { it.holdout },
            snapshot.evidence.size, snapshot.counts().values.sum())
        val progress = LearningEvaluator.holdoutProgress(snapshot)
        findViewById<TextView>(R.id.learning_progress).text = getString(R.string.learning_progress_format,
            progress.examples, LearningEvaluator.MINIMUM_HOLDOUT,
            progress.corrections, LearningEvaluator.MINIMUM_CORRECTIONS,
            progress.identities, LearningEvaluator.MINIMUM_IDENTITIES,
            getString(if (progress.hasMinimumSamples) R.string.learning_samples_ready else R.string.learning_samples_needed))
        findViewById<Button>(R.id.learning_run).isEnabled = store.isReady && running == null
    }
    private fun evaluate() {
        if (!store.isReady || running != null) return
        val snapshot = store.snapshot(); val request = ++revision; val assets = applicationContext.assets
        findViewById<Button>(R.id.learning_run).isEnabled = false
        findViewById<TextView>(R.id.learning_results).setText(R.string.learning_running)
        running = worker.submit {
            val result = try { AndroidLearningEvaluation.run(assets, snapshot) { Thread.currentThread().isInterrupted } } catch (_: Exception) { null }
            handler.post {
                if (isDestroyed || isFinishing || request != revision) return@post
                if (result == null) {
                    running = null; render()
                    findViewById<TextView>(R.id.learning_results).setText(R.string.learning_failed)
                } else if (result.promotion.promotionApproved) {
                    findViewById<TextView>(R.id.learning_results).setText(R.string.learning_promoting)
                    store.promoteCandidate(snapshot) { success -> handler.post {
                        if (isDestroyed || isFinishing || request != revision) return@post
                        running = null; render()
                        showResult(result, if (success) R.string.learning_promotion_approved else R.string.learning_promotion_failed)
                    } }
                } else {
                    running = null; render(); showResult(result, R.string.learning_promotion_refused)
                }
            }
        }
    }

    private fun showResult(result: LearningEvaluation, outcome: Int) {
        val metrics = getString(R.string.learning_results_format, result.heldOut, result.evaluated,
            result.unavailable, result.missingCandidates, result.baselineTop, result.evaluated,
            result.learnedTop, result.evaluated, result.baselinePreserved, result.identities,
            result.learnedPreserved, result.identities, result.policyMatches, result.evaluated,
            result.evaluated - result.identities)
        val comparison = getString(R.string.learning_comparison_format, result.improvements, result.regressions)
        val summary = getString(R.string.learning_result_with_decision, metrics, comparison, getString(outcome))
        val reasons = result.promotion.reasons.map { reason -> getString(when (reason) {
                    "CANCELLED" -> R.string.learning_reason_cancelled
                    "CANDIDATE_UNCHANGED" -> R.string.learning_reason_unchanged
                    "INSUFFICIENT_HOLDOUT" -> R.string.learning_samples_needed
                    "INCOMPLETE_EVALUATION" -> R.string.learning_reason_incomplete
                    "NEW_REGRESSION" -> R.string.learning_reason_regression
                    "IDENTITY_REGRESSION" -> R.string.learning_reason_identity
                    "NO_NET_IMPROVEMENT" -> R.string.learning_reason_no_gain
                    else -> R.string.learning_reason_incomplete
                }) }.distinct().joinToString(separator = "\n")
        findViewById<TextView>(R.id.learning_results).text = if (reasons.isEmpty()) summary
            else getString(R.string.learning_result_with_reasons, summary, reasons)
    }
}
