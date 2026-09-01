package io.github.mesteriis.rune.keyboard.intelligence.delivery

class DeliveryStateException(message: String, cause: Throwable? = null) : IllegalArgumentException(message, cause)

object DeliveryStateCodec {
    private val safeDirectory = Regex("[a-z0-9][a-z0-9._-]{0,126}")
    private val schemaV1 = Regex(
        """\A\{"schemaVersion":1,"operation":"([A-Z_]+)","downloadId":(null|[0-9]+),"allowMetered":(true|false),"failureCode":(null|"[A-Z_]+")\}\z""",
    )
    private val schemaV2 = Regex(
        """\A\{"schemaVersion":2,"operation":"([A-Z_]+)","downloadId":(null|[0-9]+),"allowMetered":(true|false),"failureCode":(null|"[A-Z_]+"),"activationPhase":(null|"[A-Z_]+")\}\z""",
    )
    private val schemaV3 = Regex(
        """\A\{"schemaVersion":3,"operation":"([A-Z_]+)","downloadId":(null|[0-9]+),"allowMetered":(true|false),"failureCode":(null|"[A-Z_]+"),"activationPhase":(null|"[A-Z_]+"),"activationDirectory":(null|"[a-z0-9][a-z0-9._-]{0,126}")\}\z""",
    )

    fun encode(state: DeliveryJournal): String = buildString {
        require(state.activationDirectory == null || safeDirectory.matches(state.activationDirectory)) {
            "invalid activation directory"
        }
        append("{\"schemaVersion\":3,\"operation\":\"")
        append(state.operation.name)
        append("\",\"downloadId\":")
        append(state.downloadId?.toString() ?: "null")
        append(",\"allowMetered\":")
        append(state.allowMetered)
        append(",\"failureCode\":")
        append(state.failureCode?.let { "\"${it.name}\"" } ?: "null")
        append(",\"activationPhase\":")
        append(state.activationPhase?.let { "\"${it.name}\"" } ?: "null")
        append(",\"activationDirectory\":")
        append(state.activationDirectory?.let { "\"$it\"" } ?: "null")
        append('}')
    }

    fun decode(json: String): DeliveryJournal {
        val schema = when {
            schemaV3.matches(json) -> 3
            schemaV2.matches(json) -> 2
            schemaV1.matches(json) -> 1
            else -> throw DeliveryStateException("malformed delivery state")
        }
        val match = when (schema) {
            3 -> schemaV3
            2 -> schemaV2
            else -> schemaV1
        }.matchEntire(json)!!
        return try {
            DeliveryJournal(
                operation = JournalOperation.valueOf(match.groupValues[1]),
                downloadId = match.groupValues[2].takeUnless { it == "null" }?.toLong(),
                allowMetered = match.groupValues[3].toBooleanStrict(),
                failureCode = match.groupValues[4].takeUnless { it == "null" }
                    ?.removeSurrounding("\"")
                    ?.let(ModelFailureCode::valueOf),
                activationPhase = if (schema >= 2) {
                    match.groupValues[5].takeUnless { it == "null" }
                        ?.removeSurrounding("\"")
                        ?.let(ActivationPhase::valueOf)
                } else {
                    null
                },
                activationDirectory = if (schema == 3) {
                    match.groupValues[6].takeUnless { it == "null" }?.removeSurrounding("\"")
                } else {
                    null
                },
            )
        } catch (error: Exception) {
            throw DeliveryStateException("invalid delivery state value", error)
        }
    }
}
