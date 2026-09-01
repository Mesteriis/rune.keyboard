package io.github.mesteriis.rune.runtime.llama

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LocalModelRuntimeContractTest {
    @Test
    fun closeDelegatesToUnloadAndResultsCarryStableCodes() {
        val fake = FakeRuntime()

        assertTrue(fake.load(File("missing.gguf")) is ModelLoadResult.Failure)
        assertEquals(RuntimeErrorCode.MODEL_NOT_FOUND, (fake.load(File("missing.gguf")) as ModelLoadResult.Failure).code)
        fake.close()

        assertEquals(1, fake.unloads)
    }

    private class FakeRuntime : LocalModelRuntime {
        var unloads = 0
        override fun load(modelFile: File): ModelLoadResult = ModelLoadResult.Failure(RuntimeErrorCode.MODEL_NOT_FOUND)
        override fun selfTest(): ModelSelfTestResult = ModelSelfTestResult.Failure(RuntimeErrorCode.NOT_LOADED)
        override fun cancelCurrentOperation() = Unit
        override fun unload() { unloads++ }
    }
}
