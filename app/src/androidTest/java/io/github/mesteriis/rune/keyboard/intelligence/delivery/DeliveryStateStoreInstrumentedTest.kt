package io.github.mesteriis.rune.keyboard.intelligence.delivery

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DeliveryStateStoreInstrumentedTest {
    @Test
    fun atomicallyRoundTripsInDedicatedDirectory() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val root = File(context.cacheDir, "delivery-state-test-${System.nanoTime()}")
        val store = DeliveryStateStore(root)
        val expected = DeliveryJournal(JournalOperation.DOWNLOADING, 91, allowMetered = true)

        store.write(expected)

        assertEquals(expected, store.read())
        assertEquals("delivery-state.json", store.stateFile.name)
        assertFalse(store.stateFile.path.contains("keyboard_preferences"))
    }
}
