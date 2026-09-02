package io.github.mesteriis.rune.runtime.llama

import java.nio.CharBuffer
import java.nio.charset.CharacterCodingException
import java.nio.charset.CodingErrorAction

/** Bounded continuation scoring only. No text is generated or returned by the runtime. */
data class CandidateScoringRequest(val prefix: String, val candidates: List<ScoringCandidate>)
data class ScoringCandidate(val id: Int, val continuation: String)
data class CandidateScore(val id: Int, val sumLogProbability: Double, val scoredTokenCount: Int)

sealed interface CandidateScoringResult {
    data class Success(val scores: List<CandidateScore>, val durationMillis: Long) : CandidateScoringResult
    data class Failure(val error: RuntimeErrorCode) : CandidateScoringResult
}

internal sealed interface EncodedCandidateScoringRequest {
    data class Success(
        val prefix: ByteArray,
        val ids: IntArray,
        val continuations: Array<ByteArray>,
    ) : EncodedCandidateScoringRequest
    data class Failure(val error: RuntimeErrorCode) : EncodedCandidateScoringRequest
}

/** Version 1: [version, code, milliseconds, count, (id, double raw bits, token count)*]. */
internal object CandidateScoringWire {
    fun encode(request: CandidateScoringRequest): EncodedCandidateScoringRequest {
        if (request.candidates.isEmpty()) return failure(RuntimeErrorCode.INVALID_REQUEST)
        if (request.candidates.size > 8) return failure(RuntimeErrorCode.TOO_MANY_CANDIDATES)
        // A UTF-8 encoding cannot use fewer bytes than the number of UTF-16 code units.
        // These prechecks bound encoder allocations, including malformed input.
        if (request.prefix.length > 4096) return failure(RuntimeErrorCode.CONTEXT_TOO_LONG)
        val ids = IntArray(request.candidates.size)
        val continuations = Array(request.candidates.size) { ByteArray(0) }
        try {
            val prefix = strictUtf8(request.prefix)
            if (prefix.size > 4096) return failure(RuntimeErrorCode.CONTEXT_TOO_LONG)
            request.candidates.forEachIndexed { index, candidate ->
                if (candidate.id < 0 || candidate.continuation.isEmpty() ||
                    (0 until index).any { ids[it] == candidate.id }
                ) return failure(RuntimeErrorCode.INVALID_REQUEST)
                if (candidate.continuation.length > 512) return failure(RuntimeErrorCode.CONTEXT_TOO_LONG)
                val bytes = strictUtf8(candidate.continuation)
                if (bytes.size > 512) return failure(RuntimeErrorCode.CONTEXT_TOO_LONG)
                ids[index] = candidate.id
                continuations[index] = bytes
            }
            return EncodedCandidateScoringRequest.Success(prefix, ids, continuations)
        } catch (_: CharacterCodingException) {
            return failure(RuntimeErrorCode.INVALID_UTF8)
        }
    }

    fun decode(values: LongArray, expectedIds: IntArray): CandidateScoringResult {
        fun malformed() = CandidateScoringResult.Failure(RuntimeErrorCode.SCORING_FAILED)
        if (expectedIds.size !in 1..8 || expectedIds.any { it < 0 } ||
            expectedIds.toSet().size != expectedIds.size || values.size !in 4..28 ||
            values[0] != 1L || values[2] < 0
        ) return malformed()
        val code = RuntimeErrorCode.entries.firstOrNull { it.stableCode.toLong() == values[1] }
            ?: return malformed()
        if (code != RuntimeErrorCode.OK) {
            if (values.size != 4 || values[3] != 0L) return malformed()
            return CandidateScoringResult.Failure(code)
        }
        if (values[3] != expectedIds.size.toLong() || values.size != 4 + 3 * expectedIds.size) {
            return malformed()
        }
        val scores = ArrayList<CandidateScore>(expectedIds.size)
        expectedIds.forEachIndexed { index, id ->
            val offset = 4 + index * 3
            val sum = Double.fromBits(values[offset + 1])
            val count = values[offset + 2]
            if (values[offset] != id.toLong() || !sum.isFinite() || sum > 0.0 || count !in 1L..255L) {
                return malformed()
            }
            scores += CandidateScore(id, sum, count.toInt())
        }
        return CandidateScoringResult.Success(scores, values[2])
    }

    private fun strictUtf8(text: String): ByteArray {
        val buffer = Charsets.UTF_8.newEncoder()
            .onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT)
            .encode(CharBuffer.wrap(text))
        return ByteArray(buffer.remaining()).also { buffer.get(it) }
    }

    private fun failure(error: RuntimeErrorCode) = EncodedCandidateScoringRequest.Failure(error)
}
