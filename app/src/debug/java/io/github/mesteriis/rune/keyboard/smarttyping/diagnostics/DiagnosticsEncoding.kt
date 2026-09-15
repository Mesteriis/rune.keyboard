package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

/** Debug-only serializer. Metadata has no string field other than the fixed enum vocabulary. */
internal object DiagnosticsEncoding {
    fun metadata(event: DiagnosticEvent): ByteArray = (fields(event) + "}\n").toByteArray(Charsets.UTF_8)
    fun text(event: DiagnosticEvent, text: DiagnosticText): ByteArray = buildString {
        append(fields(event))
        append(",\"input\":"); quoted(text.input.take(128))
        append(",\"context\":"); quoted(text.context.takeLast(2048))
        append(",\"original\":"); quoted(text.original.take(128))
        append(",\"candidates\":[")
        text.candidates.take(8).forEachIndexed { index, word ->
            if (index != 0) append(',')
            quoted(word.take(128))
        }
        append("],\"result\":"); quoted(text.result.take(256)); append("}\n")
    }.toByteArray(Charsets.UTF_8)

    private fun features(mask: Int): String = DiagnosticFeature.entries.joinToString(",", "{", "}") {
        "\"${it.field}\":${mask and it.bit != 0}"
    }

    private fun fields(event: DiagnosticEvent) = "{\"schema\":6,\"kind\":\"${event.kind.name}\"," +
        "\"reason\":\"${event.reason.name}\",\"session\":${event.session.coerceIn(0, 1_000_000_000)}," +
        "\"revision\":${event.revision.coerceIn(0, 1_000_000_000)}," +
        "\"typingProfile\":${event.typingProfile.takeIf { it in 0..2 } ?: 0}," +
        "\"features\":${features(event.configuredFeatures)}," +
        "\"effectiveFeatures\":${features(event.effectiveFeatures and event.configuredFeatures)}," +
        "\"candidateCount\":${event.candidateCount.coerceIn(0, 8)}," +
        "\"selectedIndex\":${event.selectedIndex.coerceIn(-1, 7)},\"modelUsed\":${event.modelUsed}," +
        "\"completion\":\"${event.completion.name}\",\"source\":\"${event.source.name}\"," +
        "\"localCompletion\":\"${event.localCompletion.name}\"," +
        "\"localInspectedStates\":${event.localInspectedStates.coerceIn(0, 8_192)}," +
        "\"localVerifiedTerminals\":${event.localVerifiedTerminals.coerceIn(0, 64)}," +
        "\"scoringCode\":${event.scoringCode.coerceIn(-1, 15)},\"elapsedMs\":${event.elapsedMs.coerceIn(0, 60_000)}," +
        "\"requestId\":${event.requestId.coerceIn(0, 1_000_000_000)},\"operationId\":${event.operationId.coerceIn(0, 1_000_000_000)}"

    private fun StringBuilder.quoted(value: String) {
        append('"')
        value.forEach { char ->
            when (char) {
                '\\' -> append("\\\\")
                '"' -> append("\\\"")
                else -> if (char.code < 32 || char.isSurrogate()) {
                    append("\\u"); append(char.code.toString(16).padStart(4, '0'))
                } else append(char)
            }
        }
        append('"')
    }
}
