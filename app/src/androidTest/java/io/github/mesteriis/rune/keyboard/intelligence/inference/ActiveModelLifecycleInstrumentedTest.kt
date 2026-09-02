package io.github.mesteriis.rune.keyboard.intelligence.inference

import android.content.Context
import android.system.Os
import android.util.AtomicFile
import androidx.test.core.app.ApplicationProvider
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringCode
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringInput
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringToken
import io.github.mesteriis.rune.keyboard.intelligence.storage.ActiveModelPointer
import io.github.mesteriis.rune.keyboard.intelligence.storage.ActiveModelPointerCodec
import io.github.mesteriis.rune.keyboard.intelligence.storage.ModelOperationGate
import io.github.mesteriis.rune.runtime.llama.CandidateScore
import io.github.mesteriis.rune.runtime.llama.CandidateScoringRequest
import io.github.mesteriis.rune.runtime.llama.CandidateScoringResult
import io.github.mesteriis.rune.runtime.llama.LocalModelRuntime
import io.github.mesteriis.rune.runtime.llama.ModelLoadResult
import io.github.mesteriis.rune.runtime.llama.ModelSelfTestResult
import io.github.mesteriis.rune.runtime.llama.RuntimeErrorCode
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.nio.file.Files
import java.util.concurrent.CountDownLatch
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicReference

/** Android kernel watches and the production adapter, without a real model/native-quality claim. */
class ActiveModelLifecycleInstrumentedTest {
    @Test fun pointerRotationCancelsBlockedScoreAndReloadsNextIdentity() = ModelFixture().use { f ->
        f.activate(1)
        f.score(1)
        assertEquals(ScoringCode.OK, f.reply(1).code)
        assertEquals(1, f.runtime.loadedId.get())
        val blocked = f.runtime.blockNextScore()
        f.score(2)
        assertTrue(blocked.entered.await(3, TimeUnit.SECONDS))
        val invalidated = f.nextInvalidation()
        f.activate(2) // real installer-style exclusive lock, while scoring holds no read lock
        assertTrue("FileObserver must observe pointer replacement", invalidated.await(3, TimeUnit.SECONDS))
        assertTrue("native cancellation must be requested", f.runtime.cancelled.await(3, TimeUnit.SECONDS))
        blocked.release.countDown()
        assertTrue(blocked.finished.await(3, TimeUnit.SECONDS))
        f.score(3)
        assertEquals(ScoringCode.OK, f.reply(3).code)
        assertEquals(2, f.runtime.loadedId.get())
        assertEquals(2, f.runtime.loads.get())
        assertTrue(f.replies.isEmpty()) // request 2 was suppressed, never delivered as success/failure
        assertEquals(0, f.runtime.orderViolations.get())
    }

    @Test fun pointerDeletionCancelsBlockedScoreAndLeavesNoModel() = ModelFixture().use { f ->
        f.activate(1)
        val blocked = f.runtime.blockNextScore()
        f.score(10)
        assertTrue(blocked.entered.await(3, TimeUnit.SECONDS))
        val invalidated = f.nextInvalidation()
        f.gate.withLock { assertTrue(f.pointer.delete()) }
        assertTrue(invalidated.await(3, TimeUnit.SECONDS))
        blocked.release.countDown()
        assertTrue(blocked.finished.await(3, TimeUnit.SECONDS))
        f.score(11)
        assertEquals(ScoringCode.NO_MODEL, f.reply(11).code)
        assertTrue(f.replies.isEmpty())
        assertEquals(0, f.runtime.orderViolations.get())
    }

    @Test fun committedBackupWinsWithoutReadSideRecovery() = ModelFixture().use { f ->
        f.activate(2)
        f.gate.withLock {
            f.installVersion(1)
            f.backup.writeText(pointer(1))
        }
        val originalBase = f.pointer.readBytes()
        val originalBackup = f.backup.readBytes()
        f.score(20)
        assertEquals(ScoringCode.OK, f.reply(20).code)
        assertEquals(1, f.runtime.loadedId.get())
        assertArrayEquals(originalBase, f.pointer.readBytes())
        assertArrayEquals(originalBackup, f.backup.readBytes())
        val invalidated = f.nextInvalidation()
        f.gate.withLock { assertTrue(f.backup.delete()) }
        assertTrue(invalidated.await(3, TimeUnit.SECONDS))
        f.score(21)
        assertEquals(ScoringCode.OK, f.reply(21).code)
        assertEquals(2, f.runtime.loadedId.get())
    }

    @Test fun absentCorruptAndOversizedPointersFailClosedBeforeRuntimeLoad() {
        for (mode in 0..3) ModelFixture().use { f ->
            f.gate.withLock {
                f.installVersion(1)
                when (mode) {
                    0 -> Unit
                    1 -> f.pointer.writeText("invalid")
                    2 -> { f.pointer.writeText(pointer(1)); f.backup.writeText("invalid") }
                    3 -> f.pointer.writeText("x".repeat(1025))
                }
            }
            f.score(30 + mode.toLong())
            val result = f.reply(30 + mode.toLong())
            assertEquals(if (mode == 0) ScoringCode.NO_MODEL else ScoringCode.UNAVAILABLE, result.code)
            assertEquals(0, f.runtime.loads.get())
            if (mode == 2) assertEquals("invalid", f.backup.readText())
        }
    }

    @Test fun modelSizeAndSymlinkEscapeAreRejectedBeforeLoad() {
        for (mode in 0..2) ModelFixture().use { f ->
            f.activate(1)
            f.gate.withLock {
                val model = f.model(1)
                when (mode) {
                    0 -> model.writeBytes(byteArrayOf(1, 2))
                    1 -> {
                        val outside = File(f.root, "outside.gguf").apply { writeBytes(byteArrayOf(1)) }
                        assertTrue(model.delete())
                        Os.symlink(outside.path, model.path)
                    }
                    2 -> f.pointer.writeText("{\"schemaVersion\":1,\"active\":\"../outside\",\"rollback\":null}")
                }
            }
            f.score(40 + mode.toLong())
            assertEquals(ScoringCode.UNAVAILABLE, f.reply(40 + mode.toLong()).code)
            assertEquals(0, f.runtime.loads.get())
        }
    }

    @Test fun missingWatchDirectoryFailsRegistrationAndRealWatchObservesVersionDeletion() = ModelFixture().use { f ->
        f.activate(1)
        val changed = CountDownLatch(1)
        ActiveModelWatch(f.root) { changed.countDown() }.use { watch ->
            assertFalse(watch.start("missing-1.0.0"))
            assertTrue("three directory OPEN acknowledgements are required", watch.start(directory(1)))
            f.gate.withLock { assertTrue(f.model(1).delete()) }
            assertTrue(changed.await(3, TimeUnit.SECONDS))
        }
    }

    @Test fun nativeLoadKeepsSharedPhysicalLockUntilSourceIsConsumed() = ModelFixture().use { f ->
        f.activate(1)
        val blocked = f.runtime.blockNextLoad()
        f.score(50)
        assertTrue(blocked.entered.await(3, TimeUnit.SECONDS))
        // Probe the physical lock using another file channel, without the JVM gate mutex.
        java.io.RandomAccessFile(File(f.root, "model-operation.lock"), "rw").use { file ->
            try {
                val lock = file.channel.tryLock()
                if (lock != null) { lock.release(); fail("native load did not hold the physical read lock") }
            } catch (_: java.nio.channels.OverlappingFileLockException) {
                // Same-process JVM channel reporting proves that the shared OS lock is owned.
            }
        }
        blocked.release.countDown()
        assertEquals(ScoringCode.OK, f.reply(50).code)
        assertEquals(1, f.runtime.loadedId.get())
    }

    private class ModelFixture : AutoCloseable {
        val root = Files.createTempDirectory(
            ApplicationProvider.getApplicationContext<Context>().cacheDir.toPath(), "scoring-model-").toFile()
        val gate = ModelOperationGate(root)
        val pointer = File(root, "active-model.json")
        val backup = File(root, "active-model.json.bak")
        val runtime = NumericRuntime()
        val replies = LinkedBlockingQueue<ScoringReply>()
        private val invalidation = AtomicReference<CountDownLatch?>()
        private val engine = ActiveModelScoringEngine(root, changed = {
            worker.invalidate()
            invalidation.get()?.countDown()
        }, createRuntime = { runtime })
        private val stopped = CountDownLatch(1)
        private val worker: LatestScoringWorker = LatestScoringWorker(object : ScoringEngine by engine {
            override fun close() { try { engine.close() } finally { stopped.countDown() } }
        })
        init { gate.withLock { check(File(root, "versions").mkdirs()) } }
        fun nextInvalidation() = CountDownLatch(1).also { invalidation.set(it) }
        fun model(id: Int) = File(root, "versions/${directory(id)}/fixture.gguf")
        fun installVersion(id: Int) {
            val model = model(id)
            check(model.parentFile!!.mkdirs() || model.parentFile!!.isDirectory)
            model.writeBytes(byteArrayOf(id.toByte()))
            File(model.parentFile, "model-manifest.json").writeText(manifest(id))
        }
        fun activate(id: Int) = gate.withLock {
            installVersion(id)
            val file = AtomicFile(pointer)
            val stream = file.startWrite()
            try { stream.write(pointer(id).toByteArray()); file.finishWrite(stream) }
            catch (failure: Exception) { file.failWrite(stream); throw failure }
        }
        fun score(id: Long) = worker.submit(ScoringInput(ScoringToken(1, 1, id, listOf(3)),
            "fixture", listOf(" value")), { replies.add(it) })
        fun reply(id: Long): ScoringReply {
            val result = checkNotNull(replies.poll(4, TimeUnit.SECONDS)) { "adapter reply timeout" }
            assertEquals(id, result.token.requestId)
            assertEquals(0, runtime.timeouts.get())
            return result
        }
        override fun close() {
            runtime.releaseAll()
            worker.close()
            check(stopped.await(3, TimeUnit.SECONDS)) { "worker did not close" }
            check(root.deleteRecursively())
        }
    }

    private class Block {
        val entered = CountDownLatch(1)
        val release = CountDownLatch(1)
        val finished = CountDownLatch(1)
    }

    /** Implements both PR2 predicates. No text, model path, or request is retained in fields. */
    private class NumericRuntime : LocalModelRuntime {
        val loadedId = AtomicInteger()
        val loads = AtomicInteger()
        val orderViolations = AtomicInteger()
        val timeouts = AtomicInteger()
        val cancelled = CountDownLatch(1)
        val closed = CountDownLatch(1)
        private val nextScore = AtomicReference<Block?>()
        private val nextLoad = AtomicReference<Block?>()
        private val activeBlock = AtomicReference<Block?>()
        private val activeCancellation = AtomicReference<(() -> Boolean)?>()
        private val nativeCancelled = AtomicBoolean()

        fun blockNextScore() = Block().also { check(nextScore.compareAndSet(null, it)) }
        fun blockNextLoad() = Block().also { check(nextLoad.compareAndSet(null, it)) }
        private fun admission(cancel: () -> Boolean): Boolean {
            nativeCancelled.set(false) // same ordering contract as PR2 native admission
            activeCancellation.set(cancel)
            return !cancel()
        }
        private fun block(next: AtomicReference<Block?>): Block? = next.getAndSet(null)?.also {
            activeBlock.set(it); it.entered.countDown()
            if (!it.release.await(8, TimeUnit.SECONDS)) timeouts.incrementAndGet()
        }
        override fun load(modelFile: File, isCancelled: () -> Boolean): ModelLoadResult {
            if (!admission(isCancelled)) return ModelLoadResult.Failure(RuntimeErrorCode.CANCELLED)
            val blocked = block(nextLoad)
            return try {
                if (isCancelled() || nativeCancelled.get()) ModelLoadResult.Failure(RuntimeErrorCode.CANCELLED)
                else {
                    loadedId.set(modelFile.readBytes().single().toInt()); loads.incrementAndGet()
                    ModelLoadResult.Success(0)
                }
            } finally { blocked?.finished?.countDown(); activeBlock.set(null); activeCancellation.set(null) }
        }
        override fun scoreCandidates(request: CandidateScoringRequest,
            isCancelled: () -> Boolean): CandidateScoringResult {
            if (!admission(isCancelled)) return CandidateScoringResult.Failure(RuntimeErrorCode.CANCELLED)
            val blocked = block(nextScore)
            return try {
                if (isCancelled() || nativeCancelled.get()) CandidateScoringResult.Failure(RuntimeErrorCode.CANCELLED)
                else CandidateScoringResult.Success(request.candidates.map { CandidateScore(it.id, -1.0, 1) }, 0)
            } finally { blocked?.finished?.countDown(); activeBlock.set(null); activeCancellation.set(null) }
        }
        override fun cancelCurrentOperation() {
            if (activeCancellation.get()?.invoke() == false) orderViolations.incrementAndGet()
            nativeCancelled.set(true); cancelled.countDown()
        }
        override fun selfTest(): ModelSelfTestResult = ModelSelfTestResult.Failure(RuntimeErrorCode.INTERNAL_ERROR)
        fun releaseAll() {
            nextScore.get()?.release?.countDown(); nextLoad.get()?.release?.countDown()
            activeBlock.get()?.release?.countDown()
        }
        override fun unload() { loadedId.set(0) }
        override fun close() { unload(); closed.countDown() }
    }

    companion object {
        private fun directory(id: Int) = "fixture-$id.0.0"
        private fun pointer(id: Int) = ActiveModelPointerCodec.encode(ActiveModelPointer(directory(id), null))
        private fun manifest(id: Int) = """{"schemaVersion":1,"modelId":"fixture","version":"$id.0.0","displayName":"Fixture","fileName":"fixture.gguf","url":"https://github.com/Mesteriis/rune.keyboard/releases/download/fixture/fixture.gguf","sha256":"${"0".repeat(64)}","sizeBytes":1,"runtimeApi":1,"minimumRuneVersionCode":2,"ggufVersion":3,"architecture":"qwen3","fileType":15}"""
    }
}
