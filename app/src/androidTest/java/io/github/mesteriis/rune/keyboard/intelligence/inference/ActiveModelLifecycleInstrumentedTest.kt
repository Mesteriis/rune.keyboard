package io.github.mesteriis.rune.keyboard.intelligence.inference

import android.content.Context
import android.os.FileObserver
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
import java.util.concurrent.ConcurrentHashMap
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

    @Test fun ordinaryCancellationSuppressesLateSuccessAndReusesValidatedModel() = ModelFixture().use { f ->
        f.activate(1)
        assertTrue(f.score(60).await(3, TimeUnit.SECONDS))
        assertEquals(ScoringCode.OK, f.reply(60).code)
        val blocked = f.runtime.blockNextScore(returnLateSuccess = true)
        val completed = f.score(61)
        assertTrue(blocked.entered.await(3, TimeUnit.SECONDS))
        f.cancel(61)
        assertTrue(f.runtime.cancelled.await(3, TimeUnit.SECONDS))
        blocked.release.countDown()
        // Worker.finished runs after adapter return AND the delivery/suppression decision.
        assertTrue(completed.await(3, TimeUnit.SECONDS))
        assertEquals(1, f.runtime.lateSuccesses.get())
        assertEquals(ScoringCode.CANCELLED, f.adapterCode(61))
        assertTrue(f.replies.isEmpty())
        assertEquals(1, f.runtime.loadedId.get())
        assertEquals(1, f.runtime.loads.get())
        assertEquals(0, f.runtime.unloads.get())
        assertTrue(f.score(62).await(3, TimeUnit.SECONDS))
        assertEquals(ScoringCode.OK, f.reply(62).code)
        assertEquals(1, f.runtime.loadCalls.get())
        assertEquals(1, f.runtime.loads.get())
        assertEquals(0, f.runtime.unloads.get())
        assertEquals(3, f.runtime.scoreCalls.get())
        assertEquals(0, f.runtime.orderViolations.get())
    }

    @Test fun explicitInvalidationOfUnchangedIdentityStillUnloadsBeforeReload() = ModelFixture().use { f ->
        f.activate(1)
        assertTrue(f.score(70).await(3, TimeUnit.SECONDS))
        assertEquals(ScoringCode.OK, f.reply(70).code)
        val pointerBefore = f.pointer.readBytes()
        val blocked = f.runtime.blockNextScore(returnLateSuccess = true)
        val completed = f.score(71)
        assertTrue(blocked.entered.await(3, TimeUnit.SECONDS))
        f.invalidate() // No filesystem/metadata mutation: explicit lifecycle invalidation is authoritative.
        assertTrue(f.runtime.cancelled.await(3, TimeUnit.SECONDS))
        blocked.release.countDown()
        assertTrue(completed.await(3, TimeUnit.SECONDS))
        assertTrue(f.runtime.firstUnload.await(3, TimeUnit.SECONDS))
        assertEquals(ScoringCode.CANCELLED, f.adapterCode(71))
        assertTrue(f.replies.isEmpty())
        assertEquals(0, f.runtime.loadedId.get())
        assertTrue(f.runtime.unloads.get() >= 1)
        assertArrayEquals(pointerBefore, f.pointer.readBytes())
        assertTrue(f.score(72).await(3, TimeUnit.SECONDS))
        assertEquals(ScoringCode.OK, f.reply(72).code)
        assertEquals(2, f.runtime.loadCalls.get())
        assertEquals(2, f.runtime.loads.get())
        assertEquals(1, f.runtime.loadedId.get())
        assertEquals(0, f.runtime.orderViolations.get())
    }

    @Test fun cancellationBeforeAdapterAdmissionDoesNotLoadScoreOrDiscardWarmModel() = ModelFixture().use { f ->
        f.activate(1)
        assertEquals(ScoringCode.CANCELLED, f.cancelledBeforeAdmission(80).code)
        assertEquals(0, f.runtime.loadCalls.get())
        assertEquals(0, f.runtime.scoreCalls.get())
        assertEquals(0, f.runtime.unloads.get())
        assertTrue(f.score(81).await(3, TimeUnit.SECONDS))
        assertEquals(ScoringCode.OK, f.reply(81).code)
        // Worker is idle after its completion barrier; direct adapter calls stay serial here.
        assertEquals(ScoringCode.CANCELLED, f.cancelledBeforeAdmission(82).code)
        assertEquals(1, f.runtime.loadCalls.get())
        assertEquals(1, f.runtime.scoreCalls.get())
        assertEquals(0, f.runtime.unloads.get())
        assertEquals(1, f.runtime.loadedId.get())
    }

    @Test fun cancellationDuringPartialLoadUnloadsAndNextRequestLoadsAfresh() = ModelFixture().use { f ->
        f.activate(1)
        val blocked = f.runtime.blockNextLoad()
        val completed = f.score(90)
        assertTrue(blocked.entered.await(3, TimeUnit.SECONDS))
        assertEquals(-1, f.runtime.loadedId.get()) // synthetic partially allocated native state
        f.cancel(90)
        blocked.release.countDown()
        assertTrue(completed.await(3, TimeUnit.SECONDS))
        assertEquals(ScoringCode.CANCELLED, f.adapterCode(90))
        assertTrue(f.replies.isEmpty())
        assertEquals(0, f.runtime.loadedId.get())
        assertEquals(0, f.runtime.loads.get())
        assertEquals(1, f.runtime.unloads.get())
        assertEquals(0, f.runtime.scoreCalls.get())
        assertTrue(f.score(91).await(3, TimeUnit.SECONDS))
        assertEquals(ScoringCode.OK, f.reply(91).code)
        assertEquals(2, f.runtime.loadCalls.get())
        assertEquals(1, f.runtime.loads.get())
        assertEquals(0, f.runtime.orderViolations.get())
    }

    @Test fun closeStillReleasesAValidatedWarmModel() {
        val f = ModelFixture()
        f.use {
            f.activate(1)
            assertTrue(f.score(100).await(3, TimeUnit.SECONDS))
            assertEquals(ScoringCode.OK, f.reply(100).code)
            assertEquals(1, f.runtime.loadedId.get())
            assertEquals(0, f.runtime.unloads.get())
        }
        assertEquals(0L, f.runtime.closed.count)
        assertEquals(0, f.runtime.loadedId.get())
        assertTrue(f.runtime.unloads.get() >= 1)
    }

    @Test fun retiredWatchCallbacksAfterCloseCannotInvalidate() = ModelFixture().use { f ->
        f.activate(1)
        val changes = AtomicInteger()
        ActiveModelWatch(f.root) { changes.incrementAndGet() }.use { watch ->
            assertTrue(watch.start(directory(1)))
            val retired = registeredObservers(watch)
            watch.close()
            // Dispatch actual observer callbacks after retirement. The arbitrary non-OPEN null
            // event represents a permitted delayed callback, not a claim about a captured kernel mask.
            retired.forEach { it.onEvent(0, null) }
            assertEquals(0, changes.get())
        }
    }

    @Test fun retiredWatchCallbacksAfterRestartCannotPoisonCurrentRegistration() = ModelFixture().use { f ->
        f.activate(1)
        val changes = AtomicInteger()
        ActiveModelWatch(f.root) { changes.incrementAndGet() }.use { watch ->
            assertTrue(watch.start(directory(1)))
            val retired = registeredObservers(watch)
            assertTrue(watch.start(directory(1)))
            val current = registeredObservers(watch)
            retired.forEach { it.onEvent(0, null) }
            retired.first().onEvent(FileObserver.CLOSE_WRITE, "active-model.json")
            assertEquals(0, changes.get())
            current.first().onEvent(FileObserver.CLOSE_WRITE, "irrelevant-file")
            assertEquals(0, changes.get())
            current.first().onEvent(0, null) // A current unknown/null event must remain fail-closed.
            assertEquals(1, changes.get())
            current.last().onEvent(FileObserver.DELETE_SELF, null)
            assertEquals(1, changes.get()) // One invalidation for the current registration.
        }
    }

    @Test fun failedWatchRestartRetiresCallbacksAndLaterCurrentEventStillInvalidates() = ModelFixture().use { f ->
        f.activate(1)
        val changes = AtomicInteger()
        ActiveModelWatch(f.root) { changes.incrementAndGet() }.use { watch ->
            assertTrue(watch.start(directory(1)))
            val retired = registeredObservers(watch)
            assertFalse(watch.start("missing-1.0.0"))
            retired.forEach { it.onEvent(0, null) }
            assertEquals(0, changes.get())
            assertTrue(watch.start(directory(1)))
            registeredObservers(watch).first().onEvent(FileObserver.CLOSE_WRITE, "active-model.json")
            assertEquals(1, changes.get())
        }
    }

    /** Test-only capture of real callbacks; no production observer factory or synthetic watch. */
    private fun registeredObservers(watch: ActiveModelWatch): List<FileObserver> {
        val field = ActiveModelWatch::class.java.getDeclaredField("watchers").apply { isAccessible = true }
        val result = (field.get(watch) as List<*>).map { it as FileObserver }
        assertEquals(3, result.size)
        return result
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
        private val adapterCodes = ConcurrentHashMap<Long, Int>() // numeric diagnostics only
        private val worker: LatestScoringWorker = LatestScoringWorker(object : ScoringEngine by engine {
            override fun score(request: ScoringInput, cancelled: AtomicBoolean): ScoringReply =
                engine.score(request, cancelled).also { adapterCodes[request.token.requestId] = it.code }
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
        private fun input(id: Long) = ScoringInput(ScoringToken(1, 1, id, listOf(3)), "fixture", listOf(" value"))
        fun score(id: Long): CountDownLatch = CountDownLatch(1).also { completed ->
            worker.submit(input(id), { replies.add(it) }, completed::countDown)
        }
        fun cancel(id: Long) = worker.cancel(1, id)
        fun invalidate() = worker.invalidate()
        fun adapterCode(id: Long): Int = checkNotNull(adapterCodes[id]) { "adapter completion absent" }
        fun cancelledBeforeAdmission(id: Long) = engine.score(input(id), AtomicBoolean(true))
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

    private class Block(val returnLateSuccess: Boolean = false) {
        val entered = CountDownLatch(1)
        val release = CountDownLatch(1)
        val finished = CountDownLatch(1)
    }

    /** Implements both PR2 predicates. No text, model path, or request is retained in fields. */
    private class NumericRuntime : LocalModelRuntime {
        val loadedId = AtomicInteger()
        val loads = AtomicInteger()
        val loadCalls = AtomicInteger()
        val unloads = AtomicInteger()
        val scoreCalls = AtomicInteger()
        val lateSuccesses = AtomicInteger()
        val firstUnload = CountDownLatch(1)
        val orderViolations = AtomicInteger()
        val timeouts = AtomicInteger()
        val cancelled = CountDownLatch(1)
        val closed = CountDownLatch(1)
        private val nextScore = AtomicReference<Block?>()
        private val nextLoad = AtomicReference<Block?>()
        private val activeBlock = AtomicReference<Block?>()
        private val activeCancellation = AtomicReference<(() -> Boolean)?>()
        private val nativeCancelled = AtomicBoolean()

        fun blockNextScore(returnLateSuccess: Boolean = false) = Block(returnLateSuccess).also {
            check(nextScore.compareAndSet(null, it))
        }
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
            loadCalls.incrementAndGet()
            if (!admission(isCancelled)) return ModelLoadResult.Failure(RuntimeErrorCode.CANCELLED)
            loadedId.set(-1) // partial allocation must be cleared even when load never succeeds
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
            scoreCalls.incrementAndGet()
            if (!admission(isCancelled)) return CandidateScoringResult.Failure(RuntimeErrorCode.CANCELLED)
            val blocked = block(nextScore)
            return try {
                val cancelled = isCancelled() || nativeCancelled.get()
                if (cancelled && blocked?.returnLateSuccess != true) CandidateScoringResult.Failure(RuntimeErrorCode.CANCELLED)
                else {
                    if (cancelled) lateSuccesses.incrementAndGet()
                    CandidateScoringResult.Success(request.candidates.map { CandidateScore(it.id, -1.0, 1) }, 0)
                }
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
        override fun unload() { loadedId.set(0); unloads.incrementAndGet(); firstUnload.countDown() }
        override fun close() { unload(); closed.countDown() }
    }

    companion object {
        private fun directory(id: Int) = "fixture-$id.0.0"
        private fun pointer(id: Int) = ActiveModelPointerCodec.encode(ActiveModelPointer(directory(id), null))
        private fun manifest(id: Int) = """{"schemaVersion":1,"modelId":"fixture","version":"$id.0.0","displayName":"Fixture","fileName":"fixture.gguf","url":"https://github.com/Mesteriis/rune.keyboard/releases/download/fixture/fixture.gguf","sha256":"${"0".repeat(64)}","sizeBytes":1,"runtimeApi":1,"minimumRuneVersionCode":2,"ggufVersion":3,"architecture":"qwen3","fileType":15}"""
    }
}
