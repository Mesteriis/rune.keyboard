package io.github.mesteriis.rune.keyboard.intelligence.storage

import java.io.File
import java.io.RandomAccessFile
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

/** Serializes model filesystem mutations across the app, :model_worker, and :model_runtime processes. */
class ModelOperationGate(private val root: File) {
    private val lockFile = File(root, "model-operation.lock")
    private val localLock = localLocks.computeIfAbsent(root.canonicalPath) { ReentrantLock() }

    fun <T> withLock(block: () -> T): T = localLock.withLock {
        check(root.mkdirs() || root.isDirectory) { "cannot create model root" }
        RandomAccessFile(lockFile, "rw").use { file ->
            file.channel.lock().use { return block() }
        }
    }

    /** Read-only consumers never create directories or lock files. Same OS lock as mutations. */
    fun <T> withReadLock(block: () -> T): T = localLock.withLock {
        check(root.isDirectory && lockFile.isFile) { "model store is unavailable" }
        RandomAccessFile(lockFile, "r").use { file ->
            file.channel.lock(0L, Long.MAX_VALUE, true).use { return block() }
        }
    }

    private companion object {
        val localLocks = ConcurrentHashMap<String, ReentrantLock>()
    }
}
