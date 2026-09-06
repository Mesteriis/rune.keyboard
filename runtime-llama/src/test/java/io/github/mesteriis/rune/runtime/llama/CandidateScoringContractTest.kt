package io.github.mesteriis.rune.runtime.llama

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

class CandidateScoringContractTest {
    private fun request(prefix: String = "x", continuation: String = " y") =
        CandidateScoringRequest(prefix, listOf(ScoringCandidate(7, continuation)))

    private fun failure(request: CandidateScoringRequest): RuntimeErrorCode =
        (CandidateScoringWire.encode(request) as EncodedCandidateScoringRequest.Failure).error

    @Test fun utf8PreservesNulSupplementaryAndMultilingualCharacters() {
        val text = "\u0000😀Привет niño"
        val result = CandidateScoringWire.encode(request(text, text)) as EncodedCandidateScoringRequest.Success
        assertArrayEquals(text.toByteArray(Charsets.UTF_8), result.prefix)
        assertArrayEquals(result.prefix, result.continuations.single())
        assertArrayEquals(intArrayOf(7), result.ids)
    }

    @Test fun unpairedSurrogatesAreReportedWithoutReplacement() {
        for (bad in listOf("\uD800", "\uDC00", "a\uD800b", "\uDC00\uD800")) {
            assertEquals(RuntimeErrorCode.INVALID_UTF8, failure(request(prefix = bad)))
            assertEquals(RuntimeErrorCode.INVALID_UTF8, failure(request(continuation = bad)))
        }
    }

    @Test fun byteBoundsApplyAfterStrictEncoding() {
        assertTrue(CandidateScoringWire.encode(request("я".repeat(2048), "😀".repeat(128))) is EncodedCandidateScoringRequest.Success)
        assertEquals(RuntimeErrorCode.CONTEXT_TOO_LONG, failure(request("я".repeat(2048) + "x")))
        assertEquals(RuntimeErrorCode.CONTEXT_TOO_LONG, failure(request(continuation = "😀".repeat(128) + "x")))
        assertEquals(RuntimeErrorCode.CONTEXT_TOO_LONG, failure(request("x".repeat(4097))))
    }

    @Test fun candidateAdmissionRejectsEmptyDuplicateNegativeAndOversizedSets() {
        assertEquals(RuntimeErrorCode.INVALID_REQUEST, failure(request(continuation = "")))
        assertEquals(RuntimeErrorCode.INVALID_REQUEST, failure(CandidateScoringRequest("", emptyList())))
        assertEquals(RuntimeErrorCode.INVALID_REQUEST, failure(CandidateScoringRequest("", listOf(ScoringCandidate(-1, "a")))))
        assertEquals(RuntimeErrorCode.INVALID_REQUEST, failure(CandidateScoringRequest("", listOf(ScoringCandidate(2, "a"), ScoringCandidate(2, "b")))))
        val candidates = (0..8).map { ScoringCandidate(it, "a") }
        assertTrue(CandidateScoringWire.encode(CandidateScoringRequest("", candidates.take(8))) is EncodedCandidateScoringRequest.Success)
        assertEquals(RuntimeErrorCode.TOO_MANY_CANDIDATES, failure(CandidateScoringRequest("", candidates)))
    }

    @Test fun wireRoundTripPreservesNumericBitsAndCandidateOrder() {
        val wire = longArrayOf(1, 0, 12, 2, 8, (-2.5).toRawBits(), 2, 1, (-7.75).toRawBits(), 3)
        assertEquals(CandidateScoringResult.Success(listOf(CandidateScore(8, -2.5, 2), CandidateScore(1, -7.75, 3)), 12),
            CandidateScoringWire.decode(wire, intArrayOf(8, 1)))
    }

    @Test fun malformedOrPartialSuccessIsRejectedAsAWhole() {
        val valid = longArrayOf(1, 0, 12, 1, 8, (-2.5).toRawBits(), 2)
        val malformed = mutableListOf(LongArray(0), LongArray(29), valid.copyOf(6), valid + 0)
        for ((index, value) in listOf(0 to 2L, 1 to 100L, 2 to -1L, 3 to 0L, 4 to 9L,
            5 to Double.NaN.toRawBits(), 5 to Double.POSITIVE_INFINITY.toRawBits(),
            5 to 0.01.toRawBits(), 6 to 0L, 6 to 256L, 6 to Long.MAX_VALUE)) {
            malformed += valid.copyOf().also { it[index] = value }
        }
        malformed.forEach {
            assertEquals(CandidateScoringResult.Failure(RuntimeErrorCode.SCORING_FAILED), CandidateScoringWire.decode(it, intArrayOf(8)))
        }
    }

    @Test fun failureProtocolRejectsAttachedScores() {
        for (code in RuntimeErrorCode.entries.filter { it != RuntimeErrorCode.OK }) {
            assertEquals(CandidateScoringResult.Failure(code), CandidateScoringWire.decode(longArrayOf(1, code.stableCode.toLong(), 0, 0), intArrayOf(8)))
        }
        assertEquals(CandidateScoringResult.Failure(RuntimeErrorCode.SCORING_FAILED),
            CandidateScoringWire.decode(longArrayOf(1, 9, 0, 1, 8, 0, 1), intArrayOf(8)))
    }

    @Test fun cancellationDoesNotWaitForScoringWorkerAndNextAdmissionResetsIt() {
        val worker = Executors.newSingleThreadExecutor()
        val callers = Executors.newFixedThreadPool(2)
        val entered = CountDownLatch(1)
        val release = CountDownLatch(1)
        val cancelled = AtomicBoolean(false)
        val lifecycle = NativeHandleLifecycle(worker, 1, { cancelled.set(false) },
            { cancelled.set(true) }, {}, {})
        try {
            val scoring = callers.submit<NativeCallResult<Boolean>> {
                lifecycle.beginOperation {
                    entered.countDown()
                    check(release.await(2, TimeUnit.SECONDS))
                    cancelled.get()
                }
            }
            assertTrue(entered.await(1, TimeUnit.SECONDS))
            callers.submit { lifecycle.cancel() }.get(1, TimeUnit.SECONDS)
            assertTrue(cancelled.get())
            release.countDown()
            assertEquals(NativeCallResult.Completed(true), scoring.get(1, TimeUnit.SECONDS))
            assertEquals(NativeCallResult.Completed(false), lifecycle.beginOperation { cancelled.get() })
        } finally {
            release.countDown()
            lifecycle.close()
            callers.shutdownNow()
        }
    }

    @Test fun publishedStableCodesRemainUnchangedAndOnlyFourCodesAreAppended() {
        assertEquals(listOf("OK", "MODEL_NOT_FOUND", "MODEL_LOAD_FAILED", "NOT_LOADED", "CONTEXT_CREATE_FAILED",
            "TOKENIZE_FAILED", "DECODE_FAILED", "EMPTY_OUTPUT", "INVALID_UTF8", "CANCELLED", "INTERNAL_ERROR",
            "NATIVE_LIBRARY_UNAVAILABLE", "INVALID_REQUEST", "CONTEXT_TOO_LONG", "TOO_MANY_CANDIDATES", "SCORING_FAILED"),
            RuntimeErrorCode.entries.map { it.name })
        assertEquals((0..15).toList(), RuntimeErrorCode.entries.map { it.stableCode })
    }
}
