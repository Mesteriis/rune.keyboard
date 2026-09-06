package io.github.mesteriis.rune.keyboard.qa

import android.os.SystemClock
import androidx.test.ext.junit.runners.AndroidJUnit4
import io.github.mesteriis.rune.keyboard.intelligence.inference.LifecycleModelInferenceService as Remote
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/** Ordinary-CI real IME/model-service/editor Binder matrix. Numeric fake scores are not quality evidence. */
@RunWith(AndroidJUnit4::class)
class LiveFakeModelBinderInstrumentedTest : ImeTestBase() {
    @Test fun originalControlThenModelCorrectionOnSpaceAndOwnedUndo(): Unit = LiveFakeModelBinderFixture.install(driver).use { f ->
        val original = f.blockedWord(Remote.SCORES_PUBLIC_ORIGINAL)
        val beforeOriginal = f.editor("a helllo", 8, 1, 8)
        // Admission captures its mode. A later control cannot alter this blocked request's result.
        f.setMode(Remote.SCORES_PUBLIC_CORRECTION)
        f.release()
        f.awaitCompletion(original, Remote.MODE_PUBLIC_ORIGINAL)
        f.awaitRanking(original, 0)
        f.assertUnchanged(beforeOriginal)
        f.space()
        f.editor("a helllo ", 9, 8, 9)

        val correction = f.blockedWord(Remote.SCORES_PUBLIC_CORRECTION)
        val beforeCorrection = f.editor("a helllo", 8, 1, 8)
        f.release()
        f.awaitCompletion(correction, Remote.MODE_PUBLIC_CORRECTION)
        f.awaitRanking(correction, 1)
        f.assertUnchanged(beforeCorrection)
        f.space() // No candidate tap and no direct controller edit.
        val corrected = f.editor("a hello ", 8, 7, 8)
        f.assertCommandDelta(beforeCorrection, corrected, mapOf("commit" to 1, "region" to 1))
        f.backspace()
        val restored = f.editor("a helllo", 8, 1, 8)
        f.assertCommandDelta(corrected, restored, mapOf("region" to 1, "compose" to 1))
        f.assertOriginalSelected()
        f.backspace()
        val deleted = f.editor("a helll", 7, 1, 7)
        f.assertCommandDelta(restored, deleted, mapOf("compose" to 1))
    }

    @Test fun blockedReplyAfterRealOriginalTapCannotReviveCorrection(): Unit = LiveFakeModelBinderFixture.install(driver).use { f ->
        val stale = f.blockedWord(Remote.SCORES_PUBLIC_CORRECTION)
        f.originalTap(stale)
        val beforeRelease = f.editor("a helllo", 8, 1, 8)
        f.release()
        f.awaitCompletion(stale, Remote.MODE_PUBLIC_CORRECTION)
        f.assertStale(stale)
        f.assertUnchanged(beforeRelease)
        f.space()
        f.editor("a helllo ", 9, 8, 9)
        Unit
    }

    @Test fun heldBackspaceUndoesModelCorrectionThenRepeatsOrdinaryDeletion(): Unit = LiveFakeModelBinderFixture.install(driver).use { f ->
        val token = f.blockedWord(Remote.SCORES_PUBLIC_CORRECTION)
        val before = f.editor("a helllo", 8, 1, 8)
        f.release()
        f.awaitCompletion(token, Remote.MODE_PUBLIC_CORRECTION)
        f.awaitRanking(token, 1)
        f.assertUnchanged(before)
        f.space()
        val corrected = f.editor("a hello ", 8, 7, 8)
        f.assertCommandDelta(before, corrected, mapOf("commit" to 1, "region" to 1))

        // One uninterrupted hold: first action restores helllo, later actions delete from it.
        val actions = f.holdBackspaceUntilRepeated()
        assertTrue("Hold must Undo, repeat at least twice and retain an owned letter", actions in 3..6)
        val expected = "a helllo".dropLast(actions - 1)
        val deleted = f.editor(expected, expected.length, 1, expected.length)
        f.assertCommandDelta(corrected, deleted, mapOf("region" to 1, "compose" to actions))
        SystemClock.sleep(900)
        f.assertUnchanged(deleted)
    }

    @Test fun remoteProcessDeathPreservesEditorAndRetryDoesNotReplay(): Unit = LiveFakeModelBinderFixture.install(driver).use { f ->
        val positive = f.blockedWord(Remote.SCORES_PUBLIC_CORRECTION)
        val beforePositive = f.editor("a helllo", 8, 1, 8)
        f.release()
        f.awaitCompletion(positive, Remote.MODE_PUBLIC_CORRECTION)
        f.awaitRanking(positive, 1)
        f.assertUnchanged(beforePositive)

        val killed = f.blockedWord(Remote.SCORES_PUBLIC_CORRECTION)
        val beforeDeath = f.editor("a helllo", 8, 1, 8)
        val keyboard = keyboardSnapshot()
        f.killAndAwaitClientLoss(killed)
        f.assertUnchanged(beforeDeath)
        assertSameKeys(keyboard, keyboardSnapshot())
        f.awaitReconnectWithoutReplay()
        f.assertUnchanged(beforeDeath)
        assertSameKeys(keyboard, keyboardSnapshot())
        f.space()
        f.editor("a helllo ", 9, 8, 9)
        f.typeZ()
        f.editor("a helllo z", 10, 8, 10)
        Unit
    }
}
