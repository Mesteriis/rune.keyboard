package io.github.mesteriis.rune.keyboard.ime.editor

/** Opt-in, bounded RAM-only QA metadata. No text, positions, package names or persistence. */
object EditorCallbackTrace {
    const val STATIONARY_CURSOR = 1
    const val COMPOSING_SPAN = 2
    const val SESSION_DISABLED_EXTERNALLY = 4
    const val SESSION_ENABLED = 8
    const val EXTERNAL_CHANGE = 16
    const val INVALID_SELECTION = 32
    const val MASK = 63
    private const val LIMIT = 128
    data class Snapshot(val active: Boolean, val total: Int, val dropped: Int, val events: List<Int>)
    private var active = false
    private var total = 0
    private val events = java.util.ArrayDeque<Int>()

    @Synchronized fun begin(): Boolean {
        if (active) return false
        events.clear(); total = 0; active = true
        return true
    }
    @Synchronized fun record(flags: Int) {
        if (!active || flags and MASK.inv() != 0) return
        if (total < Int.MAX_VALUE) total++
        if (events.size == LIMIT) events.removeFirst()
        events.addLast(flags)
    }
    @Synchronized fun snapshot() = Snapshot(active, total, total - events.size, events.toList())
    @Synchronized fun end(): Snapshot {
        val result = snapshot().copy(active = false)
        active = false; events.clear(); total = 0
        return result
    }
}
