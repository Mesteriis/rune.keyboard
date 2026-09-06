package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.view.LayoutInflater
import android.view.View
import android.widget.CheckBox
import android.widget.LinearLayout
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R
import java.lang.ref.WeakReference

/** Two independent settings; an incomplete/dismissed workflow never grants text consent. */
internal class DiagnosticsSettingsContribution(private val activity: Activity, container: LinearLayout) : AutoCloseable {
    private val recorder = TypingDiagnosticsProvider.create(activity) as DiagnosticsRecorder
    private val consent = DiagnosticsConsent { recorder.generation }
    private var closed = false
    private var busy = true
    private var busyMessage = R.string.diagnostics_working
    private var confirmed = recorder.preferences
    private var dialog: AlertDialog? = null
    private val metadata: View
    private val text: View

    init {
        val inflater = LayoutInflater.from(activity)
        container.addView((inflater.inflate(R.layout.view_settings_section, container, false) as TextView)
            .apply { setText(R.string.diagnostics_title) })
        fun row(id: Int, title: Int, summary: Int): View =
            inflater.inflate(R.layout.view_settings_row, container, false).apply {
                this.id = id
                findViewById<TextView>(R.id.row_title).setText(title)
                findViewById<TextView>(R.id.row_summary).apply { setText(summary); visibility = View.VISIBLE }
                container.addView(this)
            }
        metadata = row(R.id.diagnostics_metadata_toggle, R.string.diagnostics_metadata_title,
            R.string.diagnostics_metadata_summary)
        text = row(R.id.diagnostics_text_toggle, R.string.diagnostics_text_title, R.string.diagnostics_text_summary)
        row(R.id.diagnostics_manage, R.string.diagnostics_manage, R.string.diagnostics_manage_summary).setOnClickListener {
            if (!closed) activity.startActivity(Intent(activity, DiagnosticsActivity::class.java))
        }
        metadata.setOnClickListener {
            if (!busy && !closed) {
                val enabled = !recorder.preferences.metadata
                busy = true; busyMessage = if (enabled) R.string.diagnostics_working else R.string.diagnostics_stopping
                refresh()
                recorder.setMetadata(enabled, completion())
            }
        }
        text.setOnClickListener {
            if (!busy && !closed) {
                if (recorder.preferences.text) {
                    busy = true; busyMessage = R.string.diagnostics_stopping
                    refresh(); recorder.disableText(completion())
                } else showScope()
            }
        }
        refresh()
        recorder.barrier(completion())
    }

    private fun showScope() {
        val ticket = consent.begin()
        show(AlertDialog.Builder(activity).setTitle(R.string.diagnostics_scope_title)
            .setMessage(R.string.diagnostics_scope_message)
            .setNegativeButton(android.R.string.cancel, null)
            .setPositiveButton(R.string.diagnostics_continue) { _, _ ->
                if (!closed && consent.scope(ticket)) showStorage(ticket)
            }.create())
    }
    private fun showStorage(ticket: DiagnosticsConsent.Ticket) {
        show(AlertDialog.Builder(activity).setTitle(R.string.diagnostics_storage_title)
            .setMessage(R.string.diagnostics_storage_message)
            .setNegativeButton(android.R.string.cancel, null)
            .setPositiveButton(R.string.diagnostics_enable) { _, _ ->
                if (!closed) consent.storage(ticket)?.let { grant ->
                    dialog = null; busy = true; busyMessage = R.string.diagnostics_working; refresh()
                    recorder.enableText(grant, completion())
                }
            }.create())
    }
    private fun show(next: AlertDialog) {
        dialog = next
        next.setOnDismissListener {
            if (dialog === next) { dialog = null; consent.cancel(); refresh() }
        }
        next.show()
    }
    private fun completion(): (Boolean) -> Unit {
        val weak = WeakReference(this)
        return { success -> weak.get()?.let { owner -> owner.activity.runOnUiThread {
            if (!owner.closed && !owner.activity.isDestroyed) {
                owner.busy = false; owner.confirmed = owner.recorder.preferences; owner.refresh()
                if (!success) AlertDialog.Builder(owner.activity).setMessage(R.string.diagnostics_failed)
                    .setPositiveButton(android.R.string.ok, null).show()
            }
        } } }
    }
    private fun refresh() {
        for ((row, enabled) in listOf(metadata to confirmed.metadata, text to confirmed.text)) {
            row.isEnabled = !busy && !closed
            row.findViewById<CheckBox>(R.id.row_checkbox).apply { visibility = View.VISIBLE; isChecked = enabled }
            row.findViewById<TextView>(R.id.row_summary).setText(if (busy) busyMessage else
                if (row === metadata) R.string.diagnostics_metadata_summary else R.string.diagnostics_text_summary)
        }
    }
    override fun close() {
        if (closed) return
        closed = true; consent.cancel()
        dialog?.dismiss(); dialog = null
    }
}
