package io.github.mesteriis.rune.keyboard.intelligence.delivery

import java.nio.file.Files
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ModelOperationGateTest {
    @Test
    fun serializesTwoGateInstancesForTheSameRoot() {
        val root = Files.createTempDirectory("model-operation-gate").toFile()
        val firstEntered = CountDownLatch(1)
        val releaseFirst = CountDownLatch(1)
        val secondEntered = CountDownLatch(1)
        val first = Thread {
            ModelOperationGate(root).withLock {
                firstEntered.countDown()
                releaseFirst.await(5, TimeUnit.SECONDS)
            }
        }
        val second = Thread {
            firstEntered.await(5, TimeUnit.SECONDS)
            ModelOperationGate(root).withLock { secondEntered.countDown() }
        }

        first.start()
        second.start()
        assertTrue(firstEntered.await(5, TimeUnit.SECONDS))
        assertFalse(secondEntered.await(100, TimeUnit.MILLISECONDS))
        releaseFirst.countDown()
        assertTrue(secondEntered.await(5, TimeUnit.SECONDS))
        first.join()
        second.join()
    }

    @Test
    fun cleanupRunsAfterTheStaleWorkerLeavesTheGate() {
        val root = Files.createTempDirectory("model-operation-cleanup").toFile()
        val state = root.resolve("state")
        val workerEntered = CountDownLatch(1)
        val releaseWorker = CountDownLatch(1)
        val cleanupFinished = AtomicBoolean(false)
        val worker = Thread {
            ModelOperationGate(root).withLock {
                state.writeText("stale-before-cancel")
                workerEntered.countDown()
                releaseWorker.await(5, TimeUnit.SECONDS)
                state.writeText("stale-after-cancel")
            }
        }
        val cleanup = Thread {
            workerEntered.await(5, TimeUnit.SECONDS)
            ModelOperationGate(root).withLock {
                state.delete()
                state.writeText("idle-after-cleanup")
                cleanupFinished.set(true)
            }
        }

        worker.start()
        cleanup.start()
        assertTrue(workerEntered.await(5, TimeUnit.SECONDS))
        assertFalse(cleanupFinished.get())
        releaseWorker.countDown()
        worker.join()
        cleanup.join()

        assertTrue(cleanupFinished.get())
        assertTrue(state.readText() == "idle-after-cleanup")
    }
}
