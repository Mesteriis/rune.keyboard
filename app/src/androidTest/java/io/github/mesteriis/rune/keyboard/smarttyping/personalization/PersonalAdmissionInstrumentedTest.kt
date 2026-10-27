package io.github.mesteriis.rune.keyboard.smarttyping.personalization

import android.os.Build
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.controls.TypingControlStore
import io.github.mesteriis.rune.keyboard.smarttyping.correction.AutomaticAdmissionRefusal
import io.github.mesteriis.rune.keyboard.smarttyping.correction.CasePattern
import io.github.mesteriis.rune.keyboard.smarttyping.correction.EditFeatures
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateCompletion
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.CandidateGeneration
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidate
import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** These fixtures reset stores, so require the task's disposable emulator before accessing them. */
class PersonalAdmissionInstrumentedTest {
    private fun resources(): PersonalTypingResources {
        check(Build.HARDWARE in setOf("ranchu", "goldfish")) { "Disposable emulator required" }
        check(InstrumentationRegistry.getArguments().getString("runeOwnedEmulator") == "q3-personal")
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val resources = PersonalTypingResources.get(context)
        await { done -> resources.controls.whenReady { done() } }
        await { done -> resources.personal.whenReady { done() } }
        assertTrue(resources.controls.isReady)
        assertTrue(resources.personal.isReady)
        reset(resources)
        return resources
    }

    @Test fun protectedOriginalIsExplainedInOrdinaryAndRefinementPaths() {
        val resources = resources()
        try {
            val subject = AndroidTypingPersonalization(resources).apply { protectionEnabled = true }
            assertTrue(subject.automaticDecision(input, winner, language).allowed)
            assertTrue(subject.refinementDecision(input, winner.text, language).allowed)
            await { done -> resources.controls.protect("helloo", language) {
                assertEquals(TypingControlStore.Result.SAVED, it); done()
            } }
            assertRefused(subject, AutomaticAdmissionRefusal.PROTECTED_WORD)
            subject.protectionEnabled = false
            assertTrue(subject.automaticDecision(input, winner, language).allowed)
            assertTrue(subject.refinementDecision(input, winner.text, language).allowed)
        } finally { reset(resources) }
    }

    @Test fun explicitPairRejectionAndConfirmationAreExplainedWithoutChangingTheirGate() {
        val resources = resources()
        try {
            val subject = AndroidTypingPersonalization(resources).apply { learningEnabled = true }
            assertTrue(subject.automaticDecision(input, winner, language).allowed)
            assertTrue(resources.personal.update { it.recordRejected("helloo", "hello", language) })
            assertRefused(subject, AutomaticAdmissionRefusal.PERSONAL_VETO)
            subject.learningEnabled = false
            assertTrue(subject.automaticDecision(input, winner, language).allowed)
            assertTrue(subject.refinementDecision(input, winner.text, language).allowed)
            reset(resources)
            assertTrue(resources.personal.update { assertTrue(it.recordConfirmedWord("helloo", language)) })
            subject.learningEnabled = true
            assertRefused(subject, AutomaticAdmissionRefusal.PERSONAL_VETO)
        } finally { reset(resources) }
    }

    @Test fun compactPathKeepsProtectedAndPersonalVetoesWithRealRussianResources() {
        val resources = resources()
        try {
            val deadline = android.os.SystemClock.elapsedRealtime() + 15_000
            while (!resources.dictionaryLoaded && android.os.SystemClock.elapsedRealtime() < deadline) Thread.sleep(10)
            assertTrue(resources.dictionaryLoaded)
            val ru = KeyboardLanguage.RUSSIAN
            val original = "нужнн"
            assertFalse(resources.lexicon.lookup(ru, original).present)
            assertFalse(resources.rareWords.lookup(original).present)
            val target = winner.copy(text = "нужен", canonicalKey = "нужен", terminalKey = "нужен",
                language = ru, lengthDifference = 0)
            val generation = input.copy(original = original, alternatives = emptyList(), compactAlternatives = listOf(target))
            val subject = AndroidTypingPersonalization(resources).apply {
                protectionEnabled = true; learningEnabled = true
            }
            assertTrue(subject.compactAutomaticDecision(generation, target, ru).allowed)
            await { done -> resources.controls.protect(original, ru) {
                assertEquals(TypingControlStore.Result.SAVED, it); done()
            } }
            val protected = subject.compactAutomaticDecision(generation, target, ru)
            assertFalse(protected.allowed)
            assertEquals(AutomaticAdmissionRefusal.PROTECTED_WORD, protected.refusal)
            subject.protectionEnabled = false
            assertTrue(subject.compactAutomaticDecision(generation, target, ru).allowed)
            assertTrue(resources.personal.update { it.recordRejected(original, target.text, ru) })
            val rejected = subject.compactAutomaticDecision(generation, target, ru)
            assertFalse(rejected.allowed)
            assertEquals(AutomaticAdmissionRefusal.PERSONAL_VETO, rejected.refusal)
            subject.learningEnabled = false
            assertTrue(subject.compactAutomaticDecision(generation, target, ru).allowed)
        } finally { reset(resources) }
    }

    private fun assertRefused(subject: AndroidTypingPersonalization, reason: AutomaticAdmissionRefusal) {
        val ordinary = subject.automaticDecision(input, winner, language)
        val refinement = subject.refinementDecision(input, winner.text, language)
        assertFalse(ordinary.allowed)
        assertFalse(refinement.allowed)
        assertEquals(reason, ordinary.refusal)
        assertEquals(reason, refinement.refusal)
    }

    private fun reset(resources: PersonalTypingResources) {
        await { done -> resources.controls.reset { assertEquals(TypingControlStore.Result.SAVED, it); done() } }
        await { done -> resources.personal.reset { assertTrue(it); done() } }
    }

    private fun await(work: (() -> Unit) -> Unit) {
        val latch = CountDownLatch(1)
        work { latch.countDown() }
        assertTrue(latch.await(15, TimeUnit.SECONDS))
    }

    private val language = KeyboardLanguage.ENGLISH
    private val winner = GeneratedCandidate("hello", "hello", "hello", language, false, 4, 1, 1,
        EditFeatures(1.0, 0, 0.0), -1, CasePattern.LOWER)
    private val input = CandidateGeneration("helloo", listOf(winner), CandidateCompletion.COMPLETE,
        false, null, 1, 1)
}
