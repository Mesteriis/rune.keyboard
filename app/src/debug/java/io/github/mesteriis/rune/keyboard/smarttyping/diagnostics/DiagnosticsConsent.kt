package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

internal data class DiagnosticsPreferences(val metadata: Boolean = false, val text: Boolean = false) {
    companion object {
        fun decode(raw: Map<String, *>): DiagnosticsPreferences = DiagnosticsPreferences(
            metadata = raw[METADATA] == true,
            text = raw[TEXT] == true && raw[CONSENT] is Int && raw[CONSENT] == 1,
        )
        const val METADATA = "metadata_enabled"
        const val TEXT = "text_enabled"
        const val CONSENT = "text_consent_version"
    }
}

internal class DiagnosticsConsent(private val generation: () -> Long) {
    class Ticket internal constructor(internal val generation: Long)
    class Grant internal constructor(internal val generation: Long)
    private var current: Ticket? = null
    private var scoped = false
    fun begin(): Ticket = Ticket(generation()).also { current = it; scoped = false }
    fun scope(ticket: Ticket): Boolean {
        if (ticket !== current || scoped || ticket.generation != generation()) return false
        scoped = true
        return true
    }
    fun storage(ticket: Ticket): Grant? {
        if (ticket !== current || !scoped || ticket.generation != generation()) return null
        cancel()
        return Grant(ticket.generation)
    }
    fun cancel() { current = null; scoped = false }
}
