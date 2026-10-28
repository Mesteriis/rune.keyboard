package io.github.mesteriis.rune.keyboard.settings.quality

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.ThemedActivity
import io.github.mesteriis.rune.keyboard.smarttyping.quality.QualityRepository
import io.github.mesteriis.rune.keyboard.smarttyping.quality.QualitySnapshotTicket
import io.github.mesteriis.rune.keyboard.smarttyping.quality.QualityStore
import java.lang.ref.WeakReference
import java.util.concurrent.Executors

/** Explicit debug-only document export of numeric aggregates, independent of input recording. */
class QualityExportActivity : ThemedActivity() {
    private lateinit var store: QualityStore
    private lateinit var exporter: QualitySnapshotExporter
    private val worker = Executors.newSingleThreadExecutor { task ->
        Thread(task, "RuneQualityExport").apply { isDaemon = true }
    }
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var status: TextView
    private lateinit var button: Button
    private var pending: QualitySnapshotTicket? = null
    private var busy = false
    private val refresh = Runnable { render() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setTitle(R.string.quality_export_title)
        val source = QualityStore.get(this)
        store = source
        exporter = QualitySnapshotExporter(worker, source::isSnapshotCurrent)
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val pad = (16 * resources.displayMetrics.density).toInt()
            setPadding(pad, pad, pad, pad)
        }
        content.addView(TextView(this).apply { setText(R.string.quality_export_description) })
        status = TextView(this).apply { id = R.id.quality_export_status }
        content.addView(status)
        button = Button(this).apply {
            id = R.id.quality_export_choose
            setText(R.string.quality_export_choose)
            setOnClickListener { if (!busy) choose() }
        }
        content.addView(button)
        val scroll = ScrollView(this).apply { addView(content) }
        setContentView(scroll); applySystemBarInsets(scroll)
        render()
    }

    private fun choose() {
        pending = store.captureSnapshot() ?: run { render(); return }
        busy = true; render(R.string.diagnostics_working)
        val intent = Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
            .setType("text/plain").putExtra(Intent.EXTRA_TITLE, "rune-quality.txt")
        try { @Suppress("DEPRECATION") startActivityForResult(intent, EXPORT_REQUEST) }
        catch (_: RuntimeException) { pending = null; busy = false; render(R.string.diagnostics_failed) }
    }

    @Deprecated("Framework Activity result bridge for API 26 without another dependency")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != EXPORT_REQUEST) return
        val ticket = pending ?: return
        pending = null
        val uri = data?.data
        if (resultCode != Activity.RESULT_OK || uri?.scheme != "content") {
            busy = false; render(); return
        }
        val resolver = applicationContext.contentResolver
        val weak = WeakReference(this)
        exporter.export(ticket, { resolver.openOutputStream(uri, "wt") }) { success ->
            weak.get()?.let { activity -> activity.runOnUiThread {
                if (!activity.isDestroyed && !activity.isFinishing) {
                    activity.busy = false
                    activity.render(if (success) R.string.diagnostics_exported else R.string.diagnostics_failed)
                }
            } }
        }
    }

    private fun render(message: Int? = null) {
        handler.removeCallbacks(refresh)
        button.isEnabled = !busy && store.isReady
        status.setText(message ?: when (store.readiness) {
            QualityRepository.Readiness.READY -> R.string.quality_export_ready
            QualityRepository.Readiness.FAILED -> R.string.diagnostics_failed
            else -> R.string.diagnostics_working
        })
        if (!busy && store.readiness in listOf(QualityRepository.Readiness.LOADING, QualityRepository.Readiness.RESETTING))
            handler.postDelayed(refresh, 100)
    }

    override fun onDestroy() {
        handler.removeCallbacks(refresh)
        pending = null
        if (::exporter.isInitialized) exporter.close()
        worker.shutdown()
        super.onDestroy()
    }

    private companion object { const val EXPORT_REQUEST = 7404 }
}
