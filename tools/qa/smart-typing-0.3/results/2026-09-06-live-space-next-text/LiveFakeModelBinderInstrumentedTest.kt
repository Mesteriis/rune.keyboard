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

    @Test fun releasedReplyWithinSpaceGraceCorrectsAndCanUndo(): Unit = LiveFakeModelBinderFixture.install(driver).use { f ->
        val token = f.blockedWord(Remote.SCORES_PUBLIC_CORRECTION)
        val before = f.editor("a helllo", 8, 1, 8)
        f.spaceThenReleaseWithinGrace(token)
        val corrected = f.editor("a hello ", 8, 7, 8)
        f.assertCommandDelta(before, corrected, mapOf("finish" to 1, "compose" to 1, "region" to 2, "commit" to 1))
        f.backspace()
        val restored = f.editor("a helllo", 8, 1, 8)
        f.assertCommandDelta(corrected, restored, mapOf("region" to 1, "compose" to 1))
        f.assertOriginalSelected()
    }

    @Test fun nextTextWithinSpaceGraceRejectsOldReplyAndKeepsCurrentOriginal(): Unit = LiveFakeModelBinderFixture.install(driver).use { f ->
        val token = f.blockedWord(Remote.SCORES_PUBLIC_CORRECTION)
        val before = f.editor("a helllo", 8, 1, 8)
        f.spaceThenTypeAAndReleaseWithinGrace(token)
        val next = f.editor("a helllo a", 10, 8, 10)
        f.assertCommandDelta(before, next, mapOf("finish" to 1, "compose" to 2))
        f.assertUnchanged(next)
        f.assertCurrentOriginalAAndNoOldReply(token)
    }

    @Test fun releasedReplyAfterSpaceGracePreservesOriginalAndStrip(): Unit = LiveFakeModelBinderFixture.install(driver).use { f ->
        f.proveNormalPipelineObservers()
        val token = f.blockedWord(Remote.SCORES_PUBLIC_CORRECTION)
        val before = f.editor("a helllo", 8, 1, 8)
        f.space()
        SystemClock.sleep(300) // Production grace is 250 ms; no clock or deadline override.
        val spaced = f.editor("a helllo ", 9, 8, 9)
        // Ordinary Space finishes the word and composes its boundary; no correction commit.
        f.assertCommandDelta(before, spaced, mapOf("finish" to 1, "compose" to 1))
        f.releaseInvalidatedReplyWithoutEditorOrStripChanges(token, spaced)
    }

    @Test fun releasedReplyAfterLanguageSwipePreservesTextAndStrip(): Unit = LiveFakeModelBinderFixture.install(driver).use { f ->
        f.proveNormalPipelineObservers()
        val token = f.blockedWord(Remote.SCORES_PUBLIC_CORRECTION)
        val before = f.editor("a helllo", 8, 1, 8)
        driver.switchToRussian()
        val switched = f.editor("a helllo", 8, -1, -1)
        f.assertCommandDelta(before, switched, mapOf("finish" to 1))
        f.releaseInvalidatedReplyWithoutEditorOrStripChanges(token, switched)
        driver.tapKey("я")
        f.editor("a hellloя", 9, 8, 9)
    }

    @Test fun releasedReplyAfterEditorSwitchPreservesBothFields(): Unit = LiveFakeModelBinderFixture.install(driver).use { f ->
        f.proveNormalPipelineObservers()
        val token = f.blockedWord(Remote.SCORES_PUBLIC_CORRECTION)
        val old = f.editor("a helllo", 8, 1, 8)
        // NEW_TASK | MULTIPLE_TASK creates a separate real editor while retaining the old task.
        driver.shell("am start -W -f 0x18000000 -n ${ImeTestDriver.QA_ACTIVITY} --es qa_composing_fixture accept")
        driver.focusField("qa_composing_text")
        f.awaitDifferentEditorSession(token)
        // A known public word starts no unrelated model request in the new editor.
        driver.tapKey("a")
        val next = f.editor("a", 1, 0, 1)
        f.releaseInvalidatedReplyWithoutEditorOrStripChanges(token, next)
        driver.device.pressBack() // Hide the second editor's IME.
        driver.device.pressBack() // Return to the original editor instance.
        driver.focusField("qa_composing_text")
        val returned = f.editor("a helllo", 8, -1, -1)
        f.assertNoPayloadWritesAcrossEditorReturn(old, returned)
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
