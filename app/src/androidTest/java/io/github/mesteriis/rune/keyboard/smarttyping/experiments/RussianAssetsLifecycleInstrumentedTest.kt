package io.github.mesteriis.rune.keyboard.smarttyping.experiments

import android.os.SystemClock
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.RareWordLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingResources
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import org.junit.Assert.*
import org.junit.Test

/** Run alone in a fresh separate target process. Never mutates the owner's Rune preferences. */
class RussianAssetsLifecycleInstrumentedTest {
    @Test fun disabledStartupThenEnablingRussianLoadsSharedAssetsOnce() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        check(context.packageName == "io.github.mesteriis.rune.keyboard.qualification") {
            "Requires the separate qualification app"
        }
        val preferences = KeyboardPreferences(context)
        val previousLanguages = preferences.readSettings().enabledLanguages
        val ready = CountDownLatch(1)
        val completions = AtomicInteger()
        val closed = CountDownLatch(1)
        try {
            instrumentation.runOnMainSync { preferences.writeEnabledLanguages(listOf(KeyboardLanguage.ENGLISH)) }
            AndroidExperimentResources.whenReady { completions.incrementAndGet(); ready.countDown() }.use {
                AndroidExperimentResources.whenReady { closed.countDown() }.close()
                val resources = PersonalTypingResources.get(context)
                assertFalse("Run this case alone in a fresh target process", resources.dictionaryLoaded)
                assertSame(MorphologyLexicon.UNAVAILABLE, resources.lexicon)
                assertSame(RareWordLexicon.UNAVAILABLE, resources.rareWords)
                assertFalse("Disabled RU must not complete a background load", ready.await(1, TimeUnit.SECONDS))
                val models = resources.experiments
                assertFalse(models.learnedReady); assertFalse(models.contextReady); assertFalse(models.tapReady)
                assertFalse(models.contextualReady); assertFalse(models.grammarRevisionReady)
                assertSame(MorphologyLexicon.UNAVAILABLE, resources.lexicon)
                assertSame(RareWordLexicon.UNAVAILABLE, resources.rareWords)

                val start = SystemClock.elapsedRealtimeNanos()
                instrumentation.runOnMainSync {
                    preferences.writeEnabledLanguages(listOf(KeyboardLanguage.ENGLISH, KeyboardLanguage.RUSSIAN))
                }
                assertTrue("Enabling RU in the same process must load context", ready.await(20, TimeUnit.SECONDS))
                val contextNanos = SystemClock.elapsedRealtimeNanos() - start
                val deadline = SystemClock.uptimeMillis() + 20_000
                while (!resources.dictionaryLoaded && SystemClock.uptimeMillis() < deadline) SystemClock.sleep(10)
                assertTrue(resources.dictionaryLoaded)
                assertTrue(resources.lexicon.lookup(KeyboardLanguage.RUSSIAN, "слово").present)
                assertTrue(resources.rareWords.lookup("кармен").present)
                assertTrue(models.learnedReady); assertTrue(models.contextReady); assertTrue(models.tapReady)
                assertTrue(models.contextualReady); assertTrue(models.grammarRevisionReady); assertTrue(models.nounCaseReady)
                val lexicon = resources.lexicon
                val rareWords = resources.rareWords
                repeat(3) {
                    instrumentation.runOnMainSync {
                        preferences.writeEnabledLanguages(listOf(KeyboardLanguage.ENGLISH))
                        preferences.writeEnabledLanguages(listOf(KeyboardLanguage.RUSSIAN, KeyboardLanguage.ENGLISH))
                    }
                }
                instrumentation.waitForIdleSync()
                assertSame(resources, PersonalTypingResources.get(context))
                assertSame(models, resources.experiments)
                assertSame(lexicon, resources.lexicon); assertSame(rareWords, resources.rareWords)
                assertEquals(1, completions.get())
                assertEquals(1L, closed.count)
                File(context.cacheDir, "russian-assets-lifecycle.json").writeText(
                    "{\"disabledObservationMs\":1000,\"deferred\":true,\"contextAfterEnableNanos\":$contextNanos," +
                        "\"dictionaryReady\":true,\"completions\":${completions.get()},\"sameHandles\":true}")
            }
        } finally {
            instrumentation.runOnMainSync { preferences.writeEnabledLanguages(previousLanguages) }
        }
    }
}
