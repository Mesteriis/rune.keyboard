package io.github.mesteriis.rune.keyboard.qa

import android.os.Build
import android.os.Process
import android.os.SystemClock
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.AndroidTypingPersonalization
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalFeedback
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingCodec
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingResources
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingSnapshot
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalWord
import java.io.File
import java.security.MessageDigest
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Before
import org.junit.Test

/** Synthetic profile mutations are restricted to explicitly selected disposable emulators. */
class CaseRejectionPersistenceInstrumentedTest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext
    private val resources get() = PersonalTypingResources.get(context)
    private val store get() = resources.personal
    private val profile get() = File(context.noBackupFilesDir, "personal-typing/profile.bin")
    private val proof get() = File(context.cacheDir, "case-rejection-process-proof")
    private val ru = KeyboardLanguage.RUSSIAN

    @Before fun requireDisposableEmulator() {
        assumeTrue(Build.HARDWARE in setOf("ranchu", "goldfish") &&
            InstrumentationRegistry.getArguments().getString("runeSyntheticProfileFixture") == "true")
    }

    @Test fun writeCaseRejectionWithoutChangingLegacyEntries() {
        await { store.isReady }
        val legacy = PersonalTypingSnapshot(
            confirmed = listOf(PersonalWord(ru, "слово")),
            feedback = listOf(PersonalFeedback(ru, "ошипка", "ошибка", 0, true)),
        )
        assertTrue(store.update { it.restore(legacy) })
        await { profile.isFile && runCatching { PersonalTypingCodec.decode(profile.readBytes()) == legacy }.getOrDefault(false) }
        assertEquals(0x31, profile.readBytes()[3].toInt())
        val bridge = AndroidTypingPersonalization(resources)
        bridge.learningEnabled = false
        bridge.rejected("клава", "Клава", ru)
        assertEquals(legacy, store.model.snapshot())
        bridge.learningEnabled = true
        bridge.rejected("клава", "Клава", ru)
        await { profile.isFile && runCatching { PersonalTypingCodec.decode(profile.readBytes()).caseRejections.size == 1 }.getOrDefault(false) }
        val saved = PersonalTypingCodec.decode(profile.readBytes())
        assertEquals(legacy.confirmed, saved.confirmed)
        assertEquals(legacy.feedback, saved.feedback)
        assertEquals(listOf(PersonalWord(ru, "клава")), saved.caseRejections)
        assertEquals(0x32, profile.readBytes()[3].toInt())
        proof.writeText("${Process.myPid()}\n${digest(profile)}\n")
    }

    @Test fun caseRejectionSurvivesProcessRestart() {
        await { store.isReady }
        check(proof.isFile) { "Run write phase before process restart" }
        val fields = proof.readLines()
        assertNotEquals("Expected a real process restart", fields[0].toInt(), Process.myPid())
        assertEquals(fields[1], digest(profile))
        assertEquals(PersonalTypingCodec.decode(profile.readBytes()), store.model.snapshot())
        assertTrue(store.model.rejects("клава", "Клава", ru))
        assertFalse(store.model.rejects("клава", "клаву", ru))
        assertTrue(store.model.rejects("ошипка", "ошибка", ru))
        assertTrue(store.model.protectsOriginal("слово", ru))
        try {
            assertTrue(store.update { it.reset() })
            await { profile.isFile && runCatching { PersonalTypingCodec.decode(profile.readBytes()) == PersonalTypingSnapshot() }.getOrDefault(false) }
        } finally { check(proof.delete()) }
    }

    private fun await(predicate: () -> Boolean) {
        val deadline = SystemClock.uptimeMillis() + 10_000
        do { if (predicate()) return; SystemClock.sleep(25) } while (SystemClock.uptimeMillis() < deadline)
        fail("Synthetic personal store did not reach the expected state")
    }

    private fun digest(file: File) = MessageDigest.getInstance("SHA-256").digest(file.readBytes())
        .joinToString("") { "%02x".format(it) }
}
