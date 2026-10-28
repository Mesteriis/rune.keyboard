package io.github.mesteriis.rune.keyboard.smarttyping.personalization

import android.os.Build
import android.os.Bundle
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.AndroidExperimentResources
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.LocalSearchEvidence
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.GeneratedCandidateKind
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyMembership
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.RareWordLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.RareWordMembership
import io.github.mesteriis.rune.keyboard.smarttyping.session.AutomaticTypingDecision
import org.json.JSONObject
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

    @Test fun resourceFailuresHaveSpecificReasonsAndPreserveGateOrder() {
        val resources = resources()
        try {
            val loaded = CountDownLatch(1)
            AndroidExperimentResources
                .whenReady { loaded.countDown() }.use { assertTrue(loaded.await(30, TimeUnit.SECONDS)) }
            val deadline = android.os.SystemClock.elapsedRealtime() + 30_000
            while (!resources.dictionaryLoaded && android.os.SystemClock.elapsedRealtime() < deadline) Thread.sleep(10)
            assertTrue(resources.dictionaryLoaded)
            assertTrue(resources.experiments.nounCaseReady)
            assertTrue(resources.experiments.grammarRevisionReady)
            assertTrue(resources.experiments.contextualReady)
            assertTrue(resources.experiments.rescueReady)
            assertTrue(resources.experiments.jointReady)
            val subject = AndroidTypingPersonalization(resources)
            val ru = KeyboardLanguage.RUSSIAN
            val target = winner.copy(text = "домой", canonicalKey = "домой", terminalKey = "домой",
                language = ru, lengthDifference = 0)
            val pool = LocalSearchEvidence(
                CandidateCompletion.COMPLETE, listOf(target), 1, 1)
            val generation = input.copy(original = "ддмой", alternatives = listOf(target),
                localSearch = pool, jointSearch = pool, jointEvaluated = true, compactAlternatives = listOf(target))
            val failures = mutableListOf<String>()
            fun checkRow(label: String, actual: AutomaticTypingDecision,
                reason: AutomaticAdmissionRefusal? = null) {
                val expectedAllowed = reason == null
                val row = JSONObject().put("label", label).put("allowed", actual.allowed)
                    .put("refusal", actual.refusal?.name ?: "NONE")
                    .put("expectedAllowed", expectedAllowed).put("expectedRefusal", reason?.name ?: "NONE")
                InstrumentationRegistry.getInstrumentation().sendStatus(2,
                    Bundle().apply { putString("admission_resource_row", row.toString()) })
                if (actual.allowed != expectedAllowed || actual.refusal != reason) failures += label
            }
            val paths: Map<String, (CandidateGeneration, KeyboardLanguage) -> AutomaticTypingDecision> =
                linkedMapOf(
                    "joint" to { g, l -> subject.jointAutomaticDecision(g, target, l) },
                    "wordContext" to { g, l -> subject.wordContextAutomaticDecision(g, target, l) },
                    "rescue" to { g, l -> subject.rescueAutomaticDecision(g, target, l) },
                    "contextual" to { g, l -> subject.contextualAutomaticDecision(g, target, l) },
                    "grammar" to { g, l -> subject.grammarRevisionAutomaticDecision(g, target, l) },
                    "nounCase" to { g, l -> subject.nounCaseAutomaticDecision(g, target, l) })
            assertTrue(subject.awaitingJointCandidates(generation.copy(jointEvaluated = false), ru))
            for ((name, decision) in paths) {
                checkRow("$name-ready", decision(generation, ru))
                checkRow("$name-language", decision(generation, language), AutomaticAdmissionRefusal.NOT_QUALIFIED)
                checkRow("$name-length", decision(generation.copy(original = "дд"), ru), AutomaticAdmissionRefusal.NOT_QUALIFIED)
                checkRow("$name-no-pool", decision(generation.copy(jointSearch = pool.copy(alternatives = emptyList())), ru),
                    AutomaticAdmissionRefusal.NOT_QUALIFIED)
                checkRow("$name-not-evaluated", decision(generation.copy(jointEvaluated = false), ru),
                    AutomaticAdmissionRefusal.NOT_QUALIFIED)
                checkRow("$name-incomplete", decision(generation.copy(jointSearch = pool.copy(
                    completion = CandidateCompletion.STATES_EXHAUSTED)), ru), AutomaticAdmissionRefusal.NOT_QUALIFIED)
            }
            // These are already-finished real packaged loaders. Restore every reference in finally;
            // no production injection hook and no reset/close of the loaded resource handles.
            for (field in listOf("dictionaryLoaded", "jointRanker", "neural")) {
                val owner: Any = if (field == "dictionaryLoaded") resources else resources.experiments
                withResourceField(owner, field, if (field == "dictionaryLoaded") false else null) {
                    for ((name, decision) in paths) {
                        checkRow("$name-missing-$field", decision(generation, ru), AutomaticAdmissionRefusal.RESOURCE_UNAVAILABLE)
                        // Model-specific readiness precedes qualification; common joint readiness
                        // checks qualification first, preserving the previous short-circuit order.
                        val modelFirst = field == "neural" && name in setOf("contextual", "grammar", "nounCase")
                        checkRow("$name-missing-$field-language", decision(generation, language),
                            if (modelFirst) AutomaticAdmissionRefusal.RESOURCE_UNAVAILABLE else AutomaticAdmissionRefusal.NOT_QUALIFIED)
                    }
                    assertFalse(subject.awaitingJointCandidates(generation.copy(jointEvaluated = false), ru))
                }
            }
            for ((field, name) in listOf("rescueRanker" to "rescue", "contextualRanker" to "contextual",
                "grammarRevisionRanker" to "grammar", "nounCaseRanker" to "nounCase")) {
                withResourceField(resources.experiments, field, null) {
                    checkRow("$name-missing-own-model", paths.getValue(name)(generation, ru), AutomaticAdmissionRefusal.RESOURCE_UNAVAILABLE)
                    checkRow("$name-missing-own-model-language", paths.getValue(name)(generation, language),
                        if (name == "rescue") AutomaticAdmissionRefusal.NOT_QUALIFIED else AutomaticAdmissionRefusal.RESOURCE_UNAVAILABLE)
                }
            }
            fun compact(g: CandidateGeneration = generation, t: GeneratedCandidate = target,
                l: KeyboardLanguage = ru) = subject.compactAutomaticDecision(g, t, l)
            checkRow("compact-ready", compact())
            checkRow("compact-language", compact(l = language), AutomaticAdmissionRefusal.NOT_QUALIFIED)
            checkRow("compact-no-pool", compact(g = generation.copy(compactAlternatives = emptyList())),
                AutomaticAdmissionRefusal.NOT_QUALIFIED)
            withResourceField(resources, "dictionaryLoaded", false) {
                checkRow("compact-dictionary", compact(), AutomaticAdmissionRefusal.RESOURCE_UNAVAILABLE)
                checkRow("compact-dictionary-language", compact(l = language), AutomaticAdmissionRefusal.NOT_QUALIFIED)
                checkRow("compact-dictionary-no-pool", compact(g = generation.copy(compactAlternatives = emptyList())),
                    AutomaticAdmissionRefusal.RESOURCE_UNAVAILABLE)
            }
            withResourceField(resources, "lexicon", MorphologyLexicon.UNAVAILABLE) {
                checkRow("compact-morphology", compact(), AutomaticAdmissionRefusal.MORPHOLOGY_UNAVAILABLE)
                withResourceField(resources, "rareWords", RareWordLexicon.UNAVAILABLE) {
                    checkRow("compact-both-dictionaries", compact(), AutomaticAdmissionRefusal.MORPHOLOGY_UNAVAILABLE)
                }
            }
            withResourceField(resources, "rareWords", RareWordLexicon.UNAVAILABLE) {
                checkRow("compact-rare", compact(), AutomaticAdmissionRefusal.RESOURCE_UNAVAILABLE)
            }
            val augmented = target.copy(kind = GeneratedCandidateKind.PUBLIC_AUGMENTED)
            checkRow("compact-augmented-ready", compact(t = augmented))
            val originalMorphology = resources.lexicon
            val originalRare = resources.rareWords
            for (mode in listOf("morphology", "rare", "both", "unknown")) {
                val morphology = MorphologyLexicon { l, key ->
                    if (key != target.terminalKey) originalMorphology.lookup(l, key)
                    else if (mode in setOf("morphology", "both"))
                        MorphologyMembership.UNAVAILABLE
                    else if (mode == "unknown") MorphologyMembership.ABSENT
                    else originalMorphology.lookup(l, key)
                }
                val rare = RareWordLexicon { key ->
                    if (key != target.terminalKey) originalRare.lookup(key)
                    else if (mode in setOf("rare", "both"))
                        RareWordMembership.UNAVAILABLE
                    else if (mode == "unknown") RareWordMembership.ABSENT
                    else originalRare.lookup(key)
                }
                withResourceField(resources, "lexicon", morphology) {
                    withResourceField(resources, "rareWords", rare) {
                        checkRow("compact-target-$mode", compact(t = augmented), when (mode) {
                            "morphology", "both" -> AutomaticAdmissionRefusal.MORPHOLOGY_UNAVAILABLE
                            "rare" -> AutomaticAdmissionRefusal.RESOURCE_UNAVAILABLE
                            else -> AutomaticAdmissionRefusal.TARGET_UNKNOWN
                        })
                    }
                }
            }
            for ((name, decision) in paths) checkRow("$name-restored", decision(generation, ru))
            checkRow("compact-restored", compact())
            assertEquals("Diagnostic/gate mismatches", emptyList<String>(), failures)
        } finally { reset(resources) }
    }

    private fun withResourceField(owner: Any, name: String, value: Any?, work: () -> Unit) {
        val field = owner.javaClass.getDeclaredField(name).apply { isAccessible = true }
        val saved = field.get(owner)
        try { field.set(owner, value); work() } finally { field.set(owner, saved) }
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
