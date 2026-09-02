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
    private val callbackLock = Any()
    private class Registration {
        val ready = CountDownLatch(3)
        var invalidated = false // callbackLock
    }
    private var current: Registration? = null // callbackLock; identity is the registration epoch
    fun start(versionDirectory: String): Boolean {
        close()
        val registration = Registration()
        synchronized(callbackLock) { current = registration }
        val versions = File(root, "versions")
        val active = File(versions, versionDirectory)
        if (!root.isDirectory || !versions.isDirectory || !active.isDirectory) { close(); return false }
        add(registration, root) { path -> path == null || path.startsWith("active-model.json") || path == "versions" }
        add(registration, versions) { path -> path == null || path == versionDirectory }
        add(registration, active) { true }
        // startWatching has no return status. Probe self-OPEN without enumerating directory entries.
        try {
            listOf(root, versions, active).forEach { directory ->
                Os.close(Os.open(directory.path, OsConstants.O_RDONLY, 0))
            }
            if (!registration.ready.await(250, TimeUnit.MILLISECONDS)) { close(); return false }
        } catch (_: Exception) { close(); return false }
        val valid = synchronized(callbackLock) { current === registration && !registration.invalidated } &&
            root.isDirectory && versions.isDirectory && active.isDirectory
        if (!valid) close()
        return valid
    }
    private fun add(registration: Registration, directory: File, relevant: (String?) -> Boolean) {
        val seenOpen = AtomicBoolean()
        val readyLatch = registration.ready
        val watcher = object : FileObserver(directory.path, OPEN or CLOSE_WRITE or MOVED_TO or MOVED_FROM or
            CREATE or DELETE or DELETE_SELF or MOVE_SELF or ATTRIB) {
            override fun onEvent(event: Int, path: String?) = synchronized(callbackLock) {
                // FileObserver permits callbacks after stopWatching. A retired observer cannot
                // acknowledge readiness or invalidate any later registration of the same paths.
                if (current !== registration) return@synchronized
                if (event and OPEN != 0) {
                    if (path == null && seenOpen.compareAndSet(false, true)) readyLatch.countDown()
                    return@synchronized
                }
                // Current overflow/unknown path still fails closed. Do not filter unknown masks.
                if ((path == null || relevant(path)) && !registration.invalidated) {
                    registration.invalidated = true
                    // Linearize delivery with retirement, not just the eligibility check. The
                    // nonblocking worker callback takes its monitor; no monitor path takes this lock.
                    changed()
                }
            }
        }
        watchers += watcher; watcher.startWatching()
    }
    override fun close() {
        // start/close are serial-worker operations. Retire before native stop can enqueue events;
        // probes and the readiness wait remain outside callbackLock so OPEN callbacks can run.
        synchronized(callbackLock) { current = null }
        watchers.forEach { it.stopWatching() }
        watchers.clear()
    }
}
