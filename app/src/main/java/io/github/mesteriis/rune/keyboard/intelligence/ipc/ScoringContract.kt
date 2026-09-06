package io.github.mesteriis.rune.keyboard.intelligence.ipc

import java.nio.CharBuffer
import java.nio.charset.CodingErrorAction

/** Opaque ids only. Never put editor text into ids or failure codes. */
class ScoringToken(val sessionId: Long, val revision: Long, val requestId: Long,
    candidateIds: List<Int>) {
    val candidateIds: List<Int> = java.util.Collections.unmodifiableList(candidateIds.also { require(it.size in 1..8) }.toList())
    override fun equals(other: Any?): Boolean = other is ScoringToken && sessionId == other.sessionId &&
        revision == other.revision && requestId == other.requestId && candidateIds == other.candidateIds
    override fun hashCode(): Int = 31 * (31 * (31 * sessionId.hashCode() + revision.hashCode()) +
        requestId.hashCode()) + candidateIds.hashCode()
    init {
        require(sessionId > 0 && revision >= 0 && requestId > 0)
        require(candidateIds.size in 1..8 && candidateIds.all { it >= 0 } && candidateIds.distinct().size == candidateIds.size)
    }
}
class ScoringInput(val token: ScoringToken, val prefix: String, continuations: List<String>) {
    val continuations: List<String> = java.util.Collections.unmodifiableList(continuations.also { require(it.size in 1..8) }.toList())
    init {
        require(continuations.size == token.candidateIds.size)
        require(validText(prefix, 4096, true) && continuations.all { validText(it, 512, false) })
    }
    // No generated toString: payload must not accidentally enter diagnostics.
}
data class NumericScore(val candidateId: Int, val sumLogProbability: Double, val tokenCount: Int) {
    init { require(candidateId >= 0 && sumLogProbability.isFinite() && sumLogProbability <= 0 && tokenCount in 1..255) }
}
class ScoringReply(val token: ScoringToken, val code: Int, val elapsedMillis: Long,
    scores: List<NumericScore>) {
    val scores: List<NumericScore> = java.util.Collections.unmodifiableList(scores.also { require(it.size in 0..8) }.toList())
    init {
        require(code in 0..15 && elapsedMillis >= 0)
        require(if (code == 0) scores.map { it.candidateId } == token.candidateIds else scores.isEmpty())
    }
}
object ScoringCode {
    const val OK = 0
    const val NO_MODEL = 1
    const val LOAD_FAILED = 2
    const val UNAVAILABLE = 3
    const val CANCELLED = 9
    const val INTERNAL = 10
    const val INVALID = 12
}
private fun validText(value: String, maxBytes: Int, allowEmpty: Boolean): Boolean {
    if (value.length > maxBytes || (!allowEmpty && value.isEmpty())) return false
    return try {
        Charsets.UTF_8.newEncoder().onMalformedInput(CodingErrorAction.REPORT)
            .onUnmappableCharacter(CodingErrorAction.REPORT).encode(CharBuffer.wrap(value)).remaining() <= maxBytes
    } catch (_: java.nio.charset.CharacterCodingException) { false }
}
