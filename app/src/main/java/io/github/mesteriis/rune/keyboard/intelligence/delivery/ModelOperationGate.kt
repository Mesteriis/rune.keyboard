package io.github.mesteriis.rune.keyboard.intelligence.delivery

import java.io.File
import java.io.RandomAccessFile
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.locks.ReentrantLock
import kotlin.concurrent.withLock

/** Serializes model filesystem mutations across the app and :model_worker processes. */
class ModelOperationGate(private val root: File) {
    private val lockFile = File(root, "model-operation.lock")
    private val localLock = localLocks.computeIfAbsent(root.canonicalPath) { ReentrantLock() }

    fun <T> withLock(block: () -> T): T = localLock.withLock {
        check(root.mkdirs() || root.isDirectory) { "cannot create model root" }
        RandomAccessFile(lockFile, "rw").use { file ->
            file.channel.lock().use { return block() }
        }
    }

    private companion object {
        val localLocks = ConcurrentHashMap<String, ReentrantLock>()
    }
}
