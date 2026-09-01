package io.github.mesteriis.rune.runtime.llama

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class LlamaRuntimeInstrumentedTest {
    @Test
    fun nativeLibraryLoadsAndBadFileReturnsTypedFailure() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val badModel = File(context.cacheDir, "bad-${System.nanoTime()}.gguf").apply {
            writeBytes("not a gguf".toByteArray())
        }

        LlamaLocalModelRuntime().use { runtime ->
            val result = runtime.load(badModel)
            assertTrue(result is ModelLoadResult.Failure)
            assertEquals(RuntimeErrorCode.MODEL_LOAD_FAILED, (result as ModelLoadResult.Failure).code)
        }
    }
}
