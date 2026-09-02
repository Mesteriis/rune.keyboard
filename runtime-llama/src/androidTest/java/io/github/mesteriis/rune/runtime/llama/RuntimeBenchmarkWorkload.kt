package io.github.mesteriis.rune.runtime.llama

/** Public synthetic fixtures. Candidate zero is always the unchanged original. */
internal object RuntimeBenchmarkWorkload {
    const val MODEL_BYTES = 396704416L
    const val MODEL_SHA256 = "7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4"
    const val CANCEL_ATTEMPTS = 3

    enum class Profile(val code: Int, val repeats: Int, val deadlineSeconds: Long) {
        PILOT(0, 3, 600), FULL(1, 20, 1800);

        companion object {
            fun parse(value: String?): Profile = when (value) {
                "pilot" -> PILOT
                "full" -> FULL
                else -> throw IllegalArgumentException("profile_required")
            }
        }
    }

    data class Visit(val config: Int, val iteration: Int)

    private val prefixes = listOf("Please check the", "Нужно исправить", "Quiero enviar un")
    private val continuations = listOf(
        listOf(" adress", " address", " addresses", " addressed", " addressee", " dress", " access", " process"),
        listOf(" сообшение", " сообщение", " сообщения", " сообщений", " сообщению", " сообщение.", " обращение", " решение"),
        listOf(" mensage", " mensaje", " mensajes", " mensajero", " mensaje.", " masaje", " mensaje breve", " correo"),
    )
    val counts = listOf(2, 4, 8)

    fun request(config: Int): CandidateScoringRequest {
        require(config in 0..8) { "config_invalid" }
        val language = config / 3
        return CandidateScoringRequest(prefixes[language], continuations[language].take(counts[config % 3])
            .mapIndexed { index, text -> ScoringCandidate(index, text) })
    }

    /** Each round visits every configuration once; successive rounds rotate positions. */
    fun visits(rounds: Int): List<Visit> {
        require(rounds in 1..20) { "rounds_invalid" }
        return (0 until rounds).flatMap { round ->
            (0 until 9).map { slot -> Visit((slot + 4 * round) % 9, round) }
        }
    }

    // Same bounded public request as the existing admission-race qualification.
    fun cancellationRequest() = CandidateScoringRequest(
        "context" + " x".repeat(128),
        (0 until 8).map { index -> ScoringCandidate(index, " ${'a' + index}" + " x".repeat(32)) },
    )

    /** Numeric wire rows: schema and all field meanings are fixed in README. */
    fun row(vararg fields: Long): String {
        require(fields.size == 18 && fields[0] == 1L) { "row_invalid" }
        return fields.joinToString(",")
    }

    fun validatedScore(request: CandidateScoringRequest, value: CandidateScoringResult): CandidateScoringResult.Success {
        val score = value as? CandidateScoringResult.Success ?: error("score_failed")
        check(score.durationMillis >= 0 && score.scores.map { it.id } == request.candidates.map { it.id }) { "score_invalid" }
        check(score.scores.all { it.scoredTokenCount in 1..255 && it.sumLogProbability.isFinite() && it.sumLogProbability <= 0 }) { "score_invalid" }
        return score
    }
}
