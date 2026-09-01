package io.github.mesteriis.rune.keyboard.intelligence.ui

import android.app.AlertDialog
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.Button
import android.widget.ProgressBar
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.intelligence.delivery.DeliveryStateStore
import io.github.mesteriis.rune.keyboard.intelligence.delivery.ModelDeliveryManager
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelOperationState
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelSnapshot
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelSnapshotReader
import io.github.mesteriis.rune.keyboard.settings.ThemedActivity
import java.io.File
import java.util.concurrent.Executors

class ModelSettingsActivity : ThemedActivity() {
    private val worker = Executors.newSingleThreadExecutor()
    private val handler = Handler(Looper.getMainLooper())
    private val refreshRunnable = Runnable(::refresh)
    private lateinit var manager: ModelDeliveryManager
    private lateinit var name: TextView
    private lateinit var status: TextView
    private lateinit var details: TextView
    private lateinit var progress: ProgressBar
    private lateinit var download: Button
    private lateinit var metered: Button
    private lateinit var retry: Button
    private lateinit var verify: Button
    private lateinit var importModel: Button
    private lateinit var export: Button
    private lateinit var delete: Button
    private var snapshot: ModelSnapshot? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_model_settings)
        setTitle(R.string.model_settings_title)
        applySystemBarInsets(findViewById(R.id.model_settings_scroll))
        manager = ModelDeliveryManager(this)
        name = findViewById(R.id.model_name)
        status = findViewById(R.id.model_status)
        details = findViewById(R.id.model_details)
        progress = findViewById(R.id.model_progress)
        download = findViewById(R.id.model_download)
        metered = findViewById(R.id.model_metered)
        retry = findViewById(R.id.model_retry)
        verify = findViewById(R.id.model_verify)
        importModel = findViewById(R.id.model_import)
        export = findViewById(R.id.model_export)
        delete = findViewById(R.id.model_delete)

        download.setOnClickListener { background { manager.enqueueDownload() } }
        metered.setOnClickListener { background { manager.downloadOverMeteredNetwork() } }
        retry.setOnClickListener { background { manager.retry() } }
        verify.setOnClickListener { background { manager.retry() } }
        importModel.setOnClickListener { openImportDocument() }
        export.setOnClickListener { createExportDocument() }
        delete.setOnClickListener { confirmDelete() }
    }

    override fun onResume() {
        super.onResume()
        manager.reconcileOnSettingsOpen()
        refresh()
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        worker.shutdownNow()
        super.onDestroy()
    }

    @Deprecated("SAF result is supported back to API 26")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        when (requestCode) {
            REQUEST_IMPORT -> background {
                manager.importDocument(uri)
                manager.reconcileOnSettingsOpen()
            }
            REQUEST_EXPORT -> background { exportTo(uri) }
        }
    }

    private fun refresh() {
        handler.removeCallbacks(refreshRunnable)
        val current = runCatching { ModelSnapshotReader(this).read() }.getOrElse {
            status.setText(R.string.model_state_unavailable)
            setActionsEnabled(false)
            return
        }
        snapshot = current
        val view = ModelSettingsViewState.from(current)
        name.text = current.available.displayName
        status.setText(statusText(view.status, current.operation))
        details.text = view.failureCode?.let { failure ->
            getString(
                R.string.model_details_with_failure,
                current.available.version,
                current.available.sizeBytes,
                current.available.architecture,
                "Q4_K_M",
                failure,
            )
        } ?: getString(
            R.string.model_details,
            current.available.version,
            current.available.sizeBytes,
            current.available.architecture,
            "Q4_K_M",
        )
        progress.visibility = if (view.isBusy) View.VISIBLE else View.GONE
        (current.operation as? ModelOperationState.Downloading)?.let { downloading ->
            progress.isIndeterminate = downloading.totalBytes <= 0
            if (downloading.totalBytes > 0) {
                progress.max = 10_000
                progress.progress = ((downloading.bytesDownloaded * 10_000) / downloading.totalBytes)
                    .coerceIn(0, 10_000).toInt()
            }
        } ?: run { progress.isIndeterminate = true }
        download.visibility = if (
            view.canDownload && (current.active == null || current.updateAvailable) &&
            current.operation !is ModelOperationState.Failed
        ) View.VISIBLE else View.GONE
        metered.visibility = if (current.operation is ModelOperationState.WaitingForUnmeteredNetwork) View.VISIBLE else View.GONE
        retry.visibility = if (current.operation is ModelOperationState.Failed) View.VISIBLE else View.GONE
        verify.visibility = if (current.candidate != null && !view.isBusy) View.VISIBLE else View.GONE
        importModel.isEnabled = view.canImport
        export.visibility = if (view.canExport) View.VISIBLE else View.GONE
        delete.visibility = if (view.canDelete) View.VISIBLE else View.GONE
        if (view.isBusy) handler.postDelayed(refreshRunnable, REFRESH_INTERVAL_MS)
    }

    private fun statusText(card: ModelCardStatus, operation: ModelOperationState): Int = when {
        operation is ModelOperationState.WaitingForUnmeteredNetwork -> R.string.model_state_waiting_wifi
        operation is ModelOperationState.Queued -> R.string.model_state_queued
        operation is ModelOperationState.Downloading -> R.string.model_state_downloading
        operation is ModelOperationState.Verifying -> R.string.model_state_verifying
        operation is ModelOperationState.Installing -> R.string.model_state_installing
        operation is ModelOperationState.SelfTesting -> R.string.model_state_self_testing
        operation is ModelOperationState.Importing -> R.string.model_state_importing
        operation is ModelOperationState.Exporting -> R.string.model_state_exporting
        card == ModelCardStatus.READY -> R.string.model_state_ready
        card == ModelCardStatus.UPDATE_AVAILABLE -> R.string.model_state_update_available
        card == ModelCardStatus.VERIFYING_CANDIDATE -> R.string.model_state_candidate
        else -> R.string.model_state_not_installed
    }

    private fun background(action: () -> Unit) {
        setActionsEnabled(false)
        worker.execute {
            runCatching(action)
            handler.post(::refresh)
        }
    }

    private fun setActionsEnabled(enabled: Boolean) {
        listOf(download, metered, retry, verify, importModel, export, delete).forEach { it.isEnabled = enabled }
    }

    @Suppress("DEPRECATION")
    private fun openImportDocument() {
        startActivityForResult(
            Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = "application/octet-stream"
            },
            REQUEST_IMPORT,
        )
    }

    @Suppress("DEPRECATION")
    private fun createExportDocument() {
        val descriptor = snapshot?.available ?: return
        startActivityForResult(
            Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = "application/octet-stream"
                putExtra(Intent.EXTRA_TITLE, descriptor.fileName)
            },
            REQUEST_EXPORT,
        )
    }

    private fun exportTo(uri: Uri) {
        val current = requireNotNull(snapshot)
        val active = requireNotNull(current.active)
        val root = DeliveryStateStore.forApplication(this).stateFile.parentFile!!
        val source = File(root, "versions/${active.directoryName}/${active.descriptor.fileName}")
        manager.exportActive(source, uri)
    }

    private fun confirmDelete() {
        AlertDialog.Builder(this)
            .setTitle(R.string.model_delete)
            .setMessage(R.string.model_delete_confirmation)
            .setNegativeButton(android.R.string.cancel, null)
            .setPositiveButton(R.string.model_delete) { _, _ -> background(manager::deleteAllModels) }
            .show()
    }

    companion object {
        private const val REQUEST_IMPORT = 2001
        private const val REQUEST_EXPORT = 2002
        private const val REFRESH_INTERVAL_MS = 1_000L
    }
}
