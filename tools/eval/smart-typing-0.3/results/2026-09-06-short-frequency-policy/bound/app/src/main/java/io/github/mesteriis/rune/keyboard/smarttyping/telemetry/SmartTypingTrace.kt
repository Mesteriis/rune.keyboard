package io.github.mesteriis.rune.keyboard.smarttyping.telemetry

/** Fixed, content-free Perfetto vocabulary. Dynamic user or editor data cannot enter a name. */
enum class SmartTypingTraceSection(val sectionName: String) {
    COMPOSE_UPDATE("Rune#composeUpdate"),
    CANDIDATE_GENERATE("Rune#candidateGenerate"),
    CANDIDATE_RANK("Rune#candidateRank"),
    MODEL_REQUEST("Rune#modelRequest"),
    MODEL_RESULT("Rune#modelResult"),
    CANDIDATE_RENDER("Rune#candidateRender"),
    CORRECTION_COMMIT("Rune#correctionCommit"),
    CORRECTION_UNDO("Rune#correctionUndo"),
    PUNCTUATION_RULE("Rune#punctuationRule"),
}

/** Android supplies the trace sink at the composition root; host tests use the no-op default. */
interface SmartTypingTracer {
    fun begin(section: SmartTypingTraceSection)
    fun end()
}

object NoopSmartTypingTracer : SmartTypingTracer {
    override fun begin(section: SmartTypingTraceSection) = Unit
    override fun end() = Unit
}

internal inline fun <T> SmartTypingTracer.section(
    section: SmartTypingTraceSection,
    block: () -> T,
): T {
    begin(section)
    return try {
        block()
    } finally {
        end()
    }
}
