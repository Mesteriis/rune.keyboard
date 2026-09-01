package io.github.mesteriis.rune.keyboard.intelligence.delivery

import android.app.DownloadManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class ModelDownloadReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != DownloadManager.ACTION_DOWNLOAD_COMPLETE) return
        val completedId = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1L)
        if (completedId < 0) return
        val journal = runCatching { DeliveryStateStore.forApplication(context).read() }.getOrNull() ?: return
        if (journal.downloadId != completedId) return
        ModelDeliveryJobScheduler.schedule(context)
    }
}
