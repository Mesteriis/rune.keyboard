package io.github.mesteriis.rune.keyboard.intelligence.readiness

import android.content.ComponentName
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.content.ServiceConnection
import android.os.IBinder
import android.os.Looper
import android.os.SystemClock
import android.text.InputType
import androidx.test.core.app.ApplicationProvider
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.EditorMode
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLayer
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessHint
import io.github.mesteriis.rune.keyboard.intelligence.inference.LifecycleModelInferenceService
import io.github.mesteriis.rune.keyboard.intelligence.storage.ActiveModelPointer
import io.github.mesteriis.rune.keyboard.intelligence.storage.ActiveModelPointerCodec
import io.github.mesteriis.rune.keyboard.intelligence.storage.ModelOperationGate
import io.github.mesteriis.rune.keyboard.smarttyping.android.AndroidModelCandidates
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import io.github.mesteriis.rune.keyboard.smarttyping.correction.EditFeatures
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCompletion
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalCandidateReply
import io.github.mesteriis.rune.keyboard.smarttyping.session.CandidateOwnerState
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingSessionController
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingTextResult
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPolicy
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.util.concurrent.Callable
import java.util.concurrent.CountDownLatch
import java.util.concurrent.FutureTask
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/** Real factory, metadata reader, Handler, client and remote Binder; synthetic engine and owned editor fixture. */
class AndroidModelCandidatesInstrumentedTest {
    @Test fun realBinderReplyAfterSpaceUsesOwnedSuffixAndImmediateUndo() = Fixture().use { f ->
        onMain { f.owner = f.owner.copy(modelAutoReplaceQualified = true); f.ranking.invalidate() }
        await { onMain { f.ranking.modelReadinessHint == ModelReadinessHint.READY } }
        onMain { f.prepare("helo", "hello", 1); f.ranking.candidatesChanged() }
        await { f.context.remote.get() > 0 }
        onMain {
            // Establish transport first; do not depend on a cold service binding within the pause.
            f.ranking.cancel()
            f.controller.typeText("s") { f.editorWrites.incrementAndGet(); true }
            f.publish("hellos", 2); f.ranking.candidatesChanged()
            val policy = MechanicalPunctuationPolicy(InputPolicy.NORMAL, EditorMode.TEXT, false, false, false)
            assertEquals(TypingTextResult.HANDLED, f.ranking.editSpace({ f.editorWrites.incrementAndGet(); true }) {
                f.controller.typeText(" ", policy, KeyboardState(KeyboardLanguage.ENGLISH),
                    autocorrectionMode = AutocorrectionMode.HIGH_CONFIDENCE) { f.editorWrites.incrementAndGet(); true }
            })
            assertEquals("helos ", f.controller.state.contextText)
            assertTrue(f.controller.hasSpaceCorrection)
        }
        await { onMain { f.controller.state.lastAutoEdit != null } }
        onMain {
            assertEquals("hellos ", f.controller.state.contextText)
            assertNotNull(f.controller.state.lastAutoEdit)
            assertEquals(TypingTextResult.HANDLED, f.controller.deletePrevious { f.editorWrites.incrementAndGet(); true })
            assertEquals("helos", f.controller.state.contextText)
            assertTrue(f.controller.state.originalSelected)
        }
        assertEquals(1, f.context.attempts.get()); assertEquals(0, f.context.mainReads.get())
    }

    @Test fun current95ProfileAppliesRemoteModelCorrectionAndImmediateUndo() = Fixture().use { f ->
        onMain { f.ranking.invalidate() }
        await { onMain { f.ranking.modelReadinessHint == ModelReadinessHint.READY } }
        onMain {
            f.prepare("helos", "hellos", 1)
            f.ranking.candidatesChanged()
        }
        await { f.context.remote.get() > 0 && onMain { !f.controller.canRequestModelRanking } }
        onMain {
            assertEquals("hellos", f.controller.candidateViewState.candidates.single {
                it.id == f.controller.candidateViewState.selectedCandidateId
            }.text)
            val policy = MechanicalPunctuationPolicy(
                InputPolicy.NORMAL, EditorMode.TEXT, false, false, false)
            assertEquals(TypingTextResult.HANDLED,
                f.controller.typeText(" ", policy, KeyboardState(KeyboardLanguage.ENGLISH),
                autocorrectionMode = AutocorrectionMode.HIGH_CONFIDENCE) {
                    f.editorWrites.incrementAndGet(); true
                })
            assertEquals("hellos ", f.controller.state.contextText)
            assertNotNull(f.controller.state.lastAutoEdit)
            assertEquals(TypingTextResult.HANDLED,
                f.controller.deletePrevious { f.editorWrites.incrementAndGet(); true })
            assertEquals("helos", f.controller.state.contextText)
            assertTrue(f.controller.state.originalSelected)
        }
        assertEquals(1, f.context.attempts.get())
        assertEquals(0, f.context.mainReads.get())
    }

    @Test fun contextualCandidatesUseOneBoundedRemoteRequestAndEqualScoresKeepOriginal() = Fixture().use { f ->
        onMain {
            f.owner = f.owner.copy(autocorrectionMode = AutocorrectionMode.OFF,
                contextualPunctuationEnabled = true)
            f.ranking.invalidate()
        }
        await { onMain { f.ranking.modelReadinessHint == ModelReadinessHint.READY } }
        onMain {
            f.owner = f.owner.copy(contextualModelReady = true)
            f.prepareContextual("hello", "world", 1)
            assertTrue(f.controller.canRequestContextualRanking)
            f.ranking.candidatesChanged()
        }
        await { f.context.remote.get() > 0 && onMain { !f.controller.canRequestContextualRanking } }
        assertEquals(1, f.context.attempts.get())
        assertEquals(0, f.context.mainReads.get())
        onMain {
            assertEquals("hello world", f.controller.state.contextText)
            assertTrue(f.controller.candidateViewState.candidates.none {
                it is io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem.Punctuation
            })
        }
    }

    @Test fun readyDoesNotReplayAndNextEditUsesRealRemoteClientWithoutEditorWrite() = Fixture().use { f ->
        onMain { f.prepare("helo", "hello", 1); f.ranking.candidatesChanged() }
        await { onMain { f.ranking.modelReadinessHint == ModelReadinessHint.READY } }
        assertEquals(0, f.context.attempts.get())
        assertEquals(0, f.context.mainReads.get())
        assertEquals(0, f.changes.get())
        onMain {
            f.controller.typeText("s") { f.editorWrites.incrementAndGet(); true }
            f.publish("hellos", 2)
            f.ranking.candidatesChanged()
        }
        val writes = f.editorWrites.get()
        assertTrue(f.changed.await(5, TimeUnit.SECONDS))
        assertEquals(1, f.context.attempts.get())
        assertTrue(f.context.remote.get() > 0)
        assertEquals(0, f.context.mainReads.get())
        assertEquals(writes, f.editorWrites.get())
        onMain {
            assertEquals("helos", f.controller.state.composing!!.typedWord)
            // With equal model evidence the calibrated OOV/lexicon margin still prefers the
            // only alternative. Completion consumes the request without mutating the editor.
            val view = f.controller.candidateViewState
            assertEquals(view.candidates.single { it.text == "hellos" }.id, view.selectedCandidateId)
            assertFalse(f.controller.canRequestModelRanking)
            assertFalse(f.controller.state.originalSelected)
        }
    }

    @Test fun inactiveOrSensitiveFactoryNeverReadsMetadataOrBinds() {
        for (sensitive in listOf(false, true)) Fixture(active = false).use { f ->
            onMain {
                f.owner = f.owner.copy(inputViewActive = sensitive, editorAllowsSmartTyping = !sensitive)
                f.prepare("helo", "hello", 1)
                f.ranking.invalidate(); f.ranking.candidatesChanged()
            }
            assertFalse(f.context.read.await(150, TimeUnit.MILLISECONDS))
            assertEquals(0, f.context.attempts.get())
            assertEquals(ModelReadinessHint.UNKNOWN, onMain { f.ranking.modelReadinessHint })
        }
    }

    @Test fun endingSessionClearsReadyAndLaterSessionRechecksRemovedModel() = Fixture().use { f ->
        onMain { f.ranking.invalidate() }
        await { onMain { f.ranking.modelReadinessHint == ModelReadinessHint.READY } }
        onMain {
            f.owner = f.owner.copy(inputViewActive = false)
            f.ranking.invalidate(); f.controller.endSession()
            assertEquals(ModelReadinessHint.UNKNOWN, f.ranking.modelReadinessHint)
        }
        ModelOperationGate(f.store).withLock { assertTrue(File(f.store, "active-model.json").delete()) }
        onMain {
            f.controller.startSession(EditorContext.from(InputType.TYPE_CLASS_TEXT, 0), 0, 0)
            f.owner = f.owner.copy(inputViewActive = true)
            f.ranking.invalidate()
        }
        await { onMain { f.ranking.modelReadinessHint == ModelReadinessHint.MISSING } }
        assertEquals(0, f.context.attempts.get())
        assertEquals(0, f.context.mainReads.get())
    }

    private class Fixture(active: Boolean = true) : AutoCloseable {
        val base = ApplicationProvider.getApplicationContext<Context>()
        private val directory = File(base.cacheDir, "readiness-fixture-${System.nanoTime()}").apply { check(mkdirs()) }
        val store = File(directory, "model-delivery")
        val context = RedirectingContext(base, directory)
        val controller = onMain { TypingSessionController().also {
            it.startSession(EditorContext.from(InputType.TYPE_CLASS_TEXT, 0), 0, 0)
        } }
        var owner = CandidateOwnerState(true, active, KeyboardLayer.LETTERS, KeyboardLanguage.ENGLISH, false)
        val changes = AtomicInteger(); val editorWrites = AtomicInteger(); val changed = CountDownLatch(1)
        val ranking = onMain { AndroidModelCandidates.create(context, controller, { owner }, {
            changes.incrementAndGet(); changed.countDown()
        }) }
        init {
            ModelOperationGate(store).withLock {
                val version = File(store, "versions/fixture-1.0.0").apply { check(mkdirs()) }
                File(store, "active-model.json").writeText(ActiveModelPointerCodec.encode(ActiveModelPointer("fixture-1.0.0", null)))
                File(version, "fixture.gguf").writeBytes(byteArrayOf(0))
                File(version, "model-manifest.json").writeText("""{"schemaVersion":1,"modelId":"fixture","version":"1.0.0","displayName":"Fixture","fileName":"fixture.gguf","url":"https://github.com/Mesteriis/rune.keyboard/releases/download/fixture/fixture.gguf","sha256":"${"0".repeat(64)}","sizeBytes":1,"runtimeApi":1,"minimumRuneVersionCode":2,"ggufVersion":3,"architecture":"qwen3","fileType":15}""")
            }
        }
        fun prepare(word: String, alternative: String, id: Long) {
            controller.typeText(word) { editorWrites.incrementAndGet(); true }
            publish(alternative, id)
        }
        fun publish(alternative: String, id: Long) {
            val request = checkNotNull(controller.beginCandidateRequest(id, KeyboardLanguage.ENGLISH))
            val item = GeneratedCandidate(alternative, alternative, alternative, KeyboardLanguage.ENGLISH,
                false, 4, 1, 1, EditFeatures(1.0, 0, 0.0), 1, CasePattern.LOWER)
            assertTrue(controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId,
                CandidateGeneration(request.token, listOf(item), CandidateCompletion.COMPLETE, false, null, 1, 1))))
        }
        fun prepareContextual(left: String, word: String, id: Long) {
            controller.typeText(left) { editorWrites.incrementAndGet(); true }
            controller.typeText(" ") { editorWrites.incrementAndGet(); true }
            controller.typeText(word) { editorWrites.incrementAndGet(); true }
            val request = checkNotNull(controller.beginCandidateRequest(id, KeyboardLanguage.ENGLISH))
            assertTrue(controller.acceptCandidates(LocalCandidateReply(request.sessionId, request.revision, request.requestId,
                CandidateGeneration(request.token, emptyList(), CandidateCompletion.COMPLETE, true, null, 1, 1))))
        }
        override fun close() {
            onMain { ranking.close(); controller.endSession() }
            assertEquals(context.attempts.get(), context.unbinds.get())
            check(directory.deleteRecursively())
        }
    }

    private class RedirectingContext(base: Context, private val directory: File) : ContextWrapper(base) {
        val read = CountDownLatch(1)
        val mainReads = AtomicInteger(); val attempts = AtomicInteger(); val unbinds = AtomicInteger(); val remote = AtomicInteger()
        private val registrations = mutableMapOf<ServiceConnection, ServiceConnection>()
        override fun getApplicationContext(): Context = this
        override fun getNoBackupFilesDir(): File {
            if (Looper.myLooper() == Looper.getMainLooper()) mainReads.incrementAndGet()
            read.countDown(); return directory
        }
        override fun bindService(intent: Intent, connection: ServiceConnection, flags: Int): Boolean {
            check(intent.component?.className == "io.github.mesteriis.rune.keyboard.intelligence.inference.ModelInferenceService")
            attempts.incrementAndGet()
            val forwarding = object : ServiceConnection {
                override fun onServiceConnected(name: ComponentName, binder: IBinder) {
                    if (binder.queryLocalInterface("io.github.mesteriis.rune.keyboard.intelligence.ipc.IModelScoringService") == null) remote.incrementAndGet()
                    connection.onServiceConnected(name, binder)
                }
                override fun onServiceDisconnected(name: ComponentName) { connection.onServiceDisconnected(name) }
            }
            registrations[connection] = forwarding
            return baseContext.bindService(Intent(intent).setComponent(ComponentName(baseContext, LifecycleModelInferenceService::class.java)), forwarding, flags)
        }
        override fun unbindService(connection: ServiceConnection) {
            unbinds.incrementAndGet(); baseContext.unbindService(checkNotNull(registrations.remove(connection)))
        }
    }

    companion object {
        private fun <T> onMain(action: () -> T): T {
            val task = FutureTask(Callable(action))
            InstrumentationRegistry.getInstrumentation().runOnMainSync(task)
            return task.get(5, TimeUnit.SECONDS)
        }
        private fun await(condition: () -> Boolean) {
            val deadline = SystemClock.uptimeMillis() + 5000
            while (!condition()) {
                check(SystemClock.uptimeMillis() < deadline) { "numeric readiness state timeout" }
                SystemClock.sleep(10)
            }
        }
    }
}
