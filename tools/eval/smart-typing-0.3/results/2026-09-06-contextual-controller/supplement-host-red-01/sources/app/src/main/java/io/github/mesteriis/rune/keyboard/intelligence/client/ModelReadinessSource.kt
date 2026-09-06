package io.github.mesteriis.rune.keyboard.intelligence.client

/** Metadata hint only. No payload, files, editor or inference in this client-facing contract. */
interface ModelReadinessSource : AutoCloseable {
    val hint: ModelReadinessHint
    /** Active edges refresh metadata; repeated active calls may retry only UNKNOWN, never poll Ready. */
    fun setActive(active: Boolean)
}
