package io.github.mesteriis.rune.keyboard.intelligence.storage

object ActiveModelPointerCodec {
    private val json = Regex(
        """\A\{"schemaVersion":1,"active":(null|"[a-z0-9][a-z0-9._-]{0,126}"),"rollback":(null|"[a-z0-9][a-z0-9._-]{0,126}")\}\z""",
    )

    fun encode(pointer: ActiveModelPointer): String =
        "{\"schemaVersion\":1,\"active\":${quoted(pointer.activeDirectory)},\"rollback\":${quoted(pointer.rollbackDirectory)}}"

    fun decode(value: String): ActiveModelPointer {
        val match = requireNotNull(json.matchEntire(value)) { "invalid active model pointer" }
        return ActiveModelPointer(unquote(match.groupValues[1]), unquote(match.groupValues[2]))
    }

    private fun quoted(value: String?) = value?.let { "\"$it\"" } ?: "null"
    private fun unquote(value: String) = value.takeUnless { it == "null" }?.removeSurrounding("\"")
}
