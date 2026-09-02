package io.github.mesteriis.rune.keyboard.intelligence.inference

import android.os.FileObserver
import android.system.Os
import android.system.OsConstants
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.io.File
import java.util.concurrent.atomic.AtomicBoolean

/** Exactly three nonrecursive watches; all invalidation callbacks are payload-free. */
@Suppress("DEPRECATION")
class ActiveModelWatch(private val root: File, private val changed: () -> Unit) : AutoCloseable {
    private val watchers = mutableListOf<FileObserver>()
    private val invalidated = AtomicBoolean()
    private var ready = CountDownLatch(3)
    fun start(versionDirectory: String): Boolean {
        close(); invalidated.set(false); ready = CountDownLatch(3)
        val versions = File(root, "versions")
        val active = File(versions, versionDirectory)
        if (!root.isDirectory || !versions.isDirectory || !active.isDirectory) return false
        add(root) { path -> path == null || path.startsWith("active-model.json") || path == "versions" }
        add(versions) { path -> path == null || path == versionDirectory }
        add(active) { true }
        // startWatching has no return status. Probe self-OPEN without enumerating directory entries.
        try {
            listOf(root, versions, active).forEach { directory ->
                Os.close(Os.open(directory.path, OsConstants.O_RDONLY, 0))
            }
            if (!ready.await(250, TimeUnit.MILLISECONDS)) { close(); return false }
        } catch (_: Exception) { close(); return false }
        return !invalidated.get() && root.isDirectory && versions.isDirectory && active.isDirectory
    }
    private fun add(directory: File, relevant: (String?) -> Boolean) {
        val seenOpen = AtomicBoolean()
        val readyLatch = ready
        val watcher = object : FileObserver(directory.path, OPEN or CLOSE_WRITE or MOVED_TO or MOVED_FROM or
            CREATE or DELETE or DELETE_SELF or MOVE_SELF or ATTRIB) {
            override fun onEvent(event: Int, path: String?) {
                if (event and OPEN != 0) {
                    if (path == null && seenOpen.compareAndSet(false, true)) readyLatch.countDown()
                    return
                }
                // Kernel overflow/unknown path fails closed. Revalidation also happens every request.
                if ((path == null || relevant(path)) && invalidated.compareAndSet(false, true)) changed()
            }
        }
        watchers += watcher; watcher.startWatching()
    }
    override fun close() { watchers.forEach { it.stopWatching() }; watchers.clear() }
}
