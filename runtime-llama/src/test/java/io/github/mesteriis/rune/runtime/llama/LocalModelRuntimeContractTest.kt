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

    @Test
    fun loadAndScoringWithoutPredicateDelegateToUncancelledOverloads() {
        val fake = FakeRuntime()
        val request = CandidateScoringRequest("prefix", listOf(ScoringCandidate(1, " continuation")))

        assertEquals(CandidateScoringResult.Failure(RuntimeErrorCode.NOT_LOADED), fake.scoreCandidates(request))
        assertEquals(CandidateScoringResult.Failure(RuntimeErrorCode.CANCELLED), fake.scoreCandidates(request) { true })
        assertEquals(ModelLoadResult.Failure(RuntimeErrorCode.MODEL_NOT_FOUND), fake.load(File("missing.gguf")))
        assertEquals(ModelLoadResult.Failure(RuntimeErrorCode.CANCELLED), fake.load(File("missing.gguf")) { true })
    }

    private class FakeRuntime : LocalModelRuntime {
        var unloads = 0
        override fun load(modelFile: File, isCancelled: () -> Boolean): ModelLoadResult =
            ModelLoadResult.Failure(if (isCancelled()) RuntimeErrorCode.CANCELLED else RuntimeErrorCode.MODEL_NOT_FOUND)
        override fun selfTest(): ModelSelfTestResult = ModelSelfTestResult.Failure(RuntimeErrorCode.NOT_LOADED)
        override fun scoreCandidates(
            request: CandidateScoringRequest,
            isCancelled: () -> Boolean,
        ): CandidateScoringResult = CandidateScoringResult.Failure(
            if (isCancelled()) RuntimeErrorCode.CANCELLED else RuntimeErrorCode.NOT_LOADED,
        )
        override fun cancelCurrentOperation() = Unit
        override fun unload() { unloads++ }
    }
}
