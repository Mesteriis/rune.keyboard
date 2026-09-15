package io.github.mesteriis.rune.keyboard.smarttyping.personalization

import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.AndroidMorphologyLexiconLoader
import io.github.mesteriis.rune.keyboard.smarttyping.touch.TouchCalibrationStore
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Uses synthetic text on the test device only, never the user's exported conversations. */
class PersonalizationInstrumentedTest {
    private val context get() = InstrumentationRegistry.getInstrumentation().targetContext

    @Test fun dictionaryMapsRealRareFormsFromApk() {
        val lexicon = AndroidMorphologyLexiconLoader.load(context.assets)
        val language = KeyboardLanguage.RUSSIAN
        assertTrue(lexicon.lookup(language, "почтений").available)
        assertTrue(lexicon.lookup(language, "почтений").present)
        assertTrue(lexicon.lookup(language, "Почтений").present)
        assertFalse(lexicon.lookup(language, "банкьу").present)
    }

    @Test fun phraseImportAndDurableResetStayInNoBackupStorage() {
        val lexicon = AndroidMorphologyLexiconLoader.load(context.assets)
        val store = PersonalTypingStore.get(context) { word, language -> lexicon.lookup(language, word).present }
        reset(store)
        val imported = CountDownLatch(1)
        var result: PersonalTypingStore.ImportResult? = null
        store.importProfile({ "RUNE_PERSONAL_PHRASES_V1\nRUSSIAN\tя\tтебя люблю\t4\n".byteInputStream() }) {
            result = it; imported.countDown()
        }
        assertTrue(imported.await(10, TimeUnit.SECONDS))
        assertEquals(PersonalTypingStore.ImportResult.IMPORTED, result)
        assertEquals(listOf("тебя люблю"), store.model.suggestions("я ", KeyboardLanguage.RUSSIAN).map { it.text })
        val file = File(context.noBackupFilesDir, "personal-typing/profile.bin")
        assertTrue(file.isFile)
        assertEquals(1, PersonalTypingCodec.decode(file.readBytes()).phrases.size)
        val rejected = CountDownLatch(1)
        store.importProfile({ "unrecognized-profile".byteInputStream() }) { result = it; rejected.countDown() }
        assertTrue(rejected.await(10, TimeUnit.SECONDS))
        assertEquals(PersonalTypingStore.ImportResult.INVALID_PROFILE, result)
        assertEquals(1, store.model.snapshot().phrases.size)
        reset(store)
        assertTrue(store.model.snapshot().phrases.isEmpty())
        assertTrue(PersonalTypingCodec.decode(file.readBytes()).phrases.isEmpty())
    }

    @Test fun touchResetAcknowledgesDurableEmptyProfile() {
        val store = TouchCalibrationStore.get(context)
        val done = CountDownLatch(1)
        var result = false
        store.reset { result = it; done.countDown() }
        assertTrue(done.await(10, TimeUnit.SECONDS))
        assertTrue(result)
        assertTrue(store.isReady)
        assertEquals(store.model.encodeSnapshot(), File(context.noBackupFilesDir, "personal-touch-v1.tsv").readText())
    }

    private fun reset(store: PersonalTypingStore) {
        val done = CountDownLatch(1)
        var success = false
        store.reset { success = it; done.countDown() }
        assertTrue(done.await(10, TimeUnit.SECONDS))
        assertTrue(success)
    }
}
