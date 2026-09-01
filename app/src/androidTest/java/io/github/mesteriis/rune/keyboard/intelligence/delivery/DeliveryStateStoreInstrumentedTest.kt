package io.github.mesteriis.rune.keyboard.intelligence.delivery

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
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

    @Test
    fun concurrentInstancesSerializeWithinOneProcess() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val root = File(context.cacheDir, "delivery-state-concurrent-${System.nanoTime()}")
        val first = DeliveryStateStore(root)
        val second = DeliveryStateStore(root)
        val start = CountDownLatch(1)
        val failure = AtomicReference<Throwable>()
        val workers = List(2) { index ->
            Thread {
                start.await(5, TimeUnit.SECONDS)
                runCatching {
                    repeat(100) {
                        if (index == 0) first.write(DeliveryJournal(JournalOperation.QUEUED, it.toLong()))
                        else second.read()
                    }
                }.exceptionOrNull()?.let(failure::set)
            }
        }

        workers.forEach(Thread::start)
        start.countDown()
        workers.forEach(Thread::join)

        assertEquals(null, failure.get())
    }
}
