package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.ThemedActivity
import java.lang.ref.WeakReference

/** Explicit SAF only. URI and UI capabilities never enter the IME provider dependency graph. */
class DiagnosticsActivity : ThemedActivity() {
    private lateinit var recorder: DiagnosticsRecorder
    private lateinit var status: TextView
    private val buttons = mutableListOf<Button>()
    private var pending: Pair<Long, DiagnosticStream>? = null
    private var activeExport: Long? = null
    private var busy = true
    private var deleting = false
    private var operation = 0L

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setTitle(R.string.diagnostics_manage)
        recorder = TypingDiagnosticsProvider.create(this) as DiagnosticsRecorder
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val pad = (16 * resources.displayMetrics.density).toInt()
            setPadding(pad, pad, pad, pad)
        }
        status = TextView(this).apply { id = R.id.diagnostics_status }
        content.addView(status)
        content.addView(TextView(this).apply { setText(R.string.diagnostics_export_warning) })
        fun button(id: Int, title: Int, action: () -> Unit) {
            val view = Button(this).apply {
                this.id = id; setText(title)
                setOnClickListener { if (!busy || id == R.id.diagnostics_delete && !deleting) action() }
            }
            buttons.add(view); content.addView(view)
        }
        button(R.id.diagnostics_export_metadata, R.string.diagnostics_export_metadata) { choose(DiagnosticStream.METADATA) }
        button(R.id.diagnostics_export_text, R.string.diagnostics_export_text) { choose(DiagnosticStream.TEXT) }
        button(R.id.diagnostics_delete, R.string.diagnostics_delete) {
            operation++; deleting = true
            pending = null; activeExport = null; busy = true; render(R.string.diagnostics_deleting)
            recorder.delete(completion(R.string.diagnostics_deleted))
        }
        val scroll = ScrollView(this).apply { addView(content) }
        setContentView(scroll); applySystemBarInsets(scroll)
        render(R.string.diagnostics_working)
        recorder.barrier(completion())
    }

    private fun choose(stream: DiagnosticStream) {
        operation++
        val ticket = recorder.newExport()
        activeExport = ticket; pending = ticket to stream
        busy = true; render(R.string.diagnostics_working)
        val intent = Intent(Intent.ACTION_CREATE_DOCUMENT).addCategory(Intent.CATEGORY_OPENABLE)
            .setType("application/x-ndjson")
            .putExtra(Intent.EXTRA_TITLE, if (stream == DiagnosticStream.METADATA) "rune-metadata.jsonl" else "rune-recorded-input.jsonl")
        try { @Suppress("DEPRECATION") startActivityForResult(intent, EXPORT_REQUEST) }
        catch (_: RuntimeException) {
            recorder.cancelExport(ticket); pending = null; activeExport = null; busy = false; render(R.string.diagnostics_failed)
        }
    }

    @Deprecated("Framework Activity result bridge for API 26 without another dependency")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != EXPORT_REQUEST) return
        val request = pending ?: return
        pending = null
        val uri = data?.data
        if (resultCode != Activity.RESULT_OK || uri?.scheme != "content") {
            recorder.cancelExport(request.first); activeExport = null; busy = false; render(); return
        }
        val resolver = applicationContext.contentResolver
        recorder.export(request.first, request.second, { resolver.openOutputStream(uri, "w") },
            completion(R.string.diagnostics_exported))
    }

    private fun completion(successMessage: Int? = null): (Boolean) -> Unit {
        val weak = WeakReference(this)
        val captured = operation
        return { success -> weak.get()?.let { activity -> activity.runOnUiThread {
            if (!activity.isDestroyed && !activity.isFinishing && captured == activity.operation) {
                activity.busy = false; activity.deleting = false; activity.activeExport = null
                activity.render(if (success) successMessage else R.string.diagnostics_failed)
            }
        } } }
    }
    private fun render(message: Int? = null) {
        val state = recorder.preferences
        status.text = getString(R.string.diagnostics_status_format,
            getString(if (state.metadata) R.string.diagnostics_on else R.string.diagnostics_off),
            getString(if (state.text) R.string.diagnostics_on else R.string.diagnostics_off),
            getString(message ?: R.string.diagnostics_next_session))
        buttons.forEach { it.isEnabled = !busy || it.id == R.id.diagnostics_delete && !deleting }
    }
    override fun onDestroy() {
        activeExport?.let(recorder::cancelExport)
        pending = null; activeExport = null
        super.onDestroy()
    }
    private companion object { const val EXPORT_REQUEST = 7403 }
}
