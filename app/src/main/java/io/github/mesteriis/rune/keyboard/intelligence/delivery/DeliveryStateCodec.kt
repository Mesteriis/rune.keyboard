package io.github.mesteriis.rune.keyboard.intelligence.delivery

class DeliveryStateException(message: String, cause: Throwable? = null) : IllegalArgumentException(message, cause)

object DeliveryStateCodec {
    private val pattern = Regex(
        """\A\{"schemaVersion":1,"operation":"([A-Z_]+)","downloadId":(null|[0-9]+),"allowMetered":(true|false),"failureCode":(null|"[A-Z_]+")\}\z""",
    )

    fun encode(state: DeliveryJournal): String = buildString {
        append("{\"schemaVersion\":1,\"operation\":\"")
        append(state.operation.name)
        append("\",\"downloadId\":")
        append(state.downloadId?.toString() ?: "null")
        append(",\"allowMetered\":")
        append(state.allowMetered)
        append(",\"failureCode\":")
        append(state.failureCode?.let { "\"${it.name}\"" } ?: "null")
        append('}')
    }

    fun decode(json: String): DeliveryJournal {
        val match = pattern.matchEntire(json) ?: throw DeliveryStateException("malformed delivery state")
        return try {
            DeliveryJournal(
                operation = JournalOperation.valueOf(match.groupValues[1]),
                downloadId = match.groupValues[2].takeUnless { it == "null" }?.toLong(),
                allowMetered = match.groupValues[3].toBooleanStrict(),
                failureCode = match.groupValues[4].takeUnless { it == "null" }
                    ?.removeSurrounding("\"")
                    ?.let(ModelFailureCode::valueOf),
            )
        } catch (error: Exception) {
            throw DeliveryStateException("invalid delivery state value", error)
        }
    }
}
