package io.github.mesteriis.rune.keyboard.intelligence.delivery

import android.app.DownloadManager
import android.content.Context
import android.database.Cursor
import android.net.Uri
import android.os.Environment
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelDescriptor
import java.io.File

class ModelDownloadClient(private val context: Context) {
    private val manager = context.getSystemService(DownloadManager::class.java)

    fun enqueue(descriptor: ModelDescriptor, allowMetered: Boolean): Long {
        val relativePath = "rune-models/${descriptor.id}-${descriptor.version}/${descriptor.fileName}"
        val request = DownloadManager.Request(Uri.parse(descriptor.downloadUrl))
            .setTitle(descriptor.displayName)
            .setDescription(descriptor.fileName)
            .setMimeType("application/octet-stream")
            .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
            .setAllowedOverMetered(allowMetered)
            .setAllowedOverRoaming(false)
            .setDestinationInExternalFilesDir(context, Environment.DIRECTORY_DOWNLOADS, relativePath)
        return manager.enqueue(request)
    }

    fun remove(id: Long) {
        manager.remove(id)
    }

    fun query(id: Long): DownloadObservation {
        manager.query(DownloadManager.Query().setFilterById(id)).use { cursor ->
            if (!cursor.moveToFirst()) return DownloadObservation.MISSING
            return when (cursor.int(DownloadManager.COLUMN_STATUS)) {
                DownloadManager.STATUS_PENDING -> DownloadObservation.PENDING
                DownloadManager.STATUS_RUNNING -> DownloadObservation.RUNNING
                DownloadManager.STATUS_PAUSED -> DownloadObservation.PAUSED
                DownloadManager.STATUS_SUCCESSFUL -> DownloadObservation.SUCCESSFUL
                DownloadManager.STATUS_FAILED -> DownloadObservation.FAILED
                else -> DownloadObservation.MISSING
            }
        }
    }

    fun findMatching(descriptor: ModelDescriptor): Long? = matchingIds(descriptor).maxOrNull()

    fun removeMatching(descriptor: ModelDescriptor) {
        val ids = matchingIds(descriptor)
        if (ids.isNotEmpty()) manager.remove(*ids.toLongArray())
    }

    private fun matchingIds(descriptor: ModelDescriptor): List<Long> {
        manager.query(DownloadManager.Query()).use { cursor ->
            val idColumn = cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_ID)
            val uriColumn = cursor.getColumnIndexOrThrow(DownloadManager.COLUMN_URI)
            val ids = mutableListOf<Long>()
            while (cursor.moveToNext()) {
                if (cursor.getString(uriColumn) == descriptor.downloadUrl) {
                    ids += cursor.getLong(idColumn)
                }
            }
            return ids
        }
    }

    fun open(id: Long) = manager.openDownloadedFile(id)

    private fun Cursor.int(column: String): Int = getInt(getColumnIndexOrThrow(column))

    companion object {
        fun externalStaging(context: Context): File = requireNotNull(
            context.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS),
        ) { "External app-specific storage is unavailable" }
    }
}
