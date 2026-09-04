package io.github.mesteriis.rune.keyboard.ime

import android.os.Trace
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.SmartTypingTraceSection
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.SmartTypingTracer

/** Perfetto sections are constant and must never contain editor or user content. */
internal object RuneTrace : SmartTypingTracer {
    override fun begin(section: SmartTypingTraceSection) = Trace.beginSection(section.sectionName)
    override fun end() = Trace.endSection()

    inline fun <T> section(section: SmartTypingTraceSection, block: () -> T): T {
        begin(section)
        return try {
            block()
        } finally {
            end()
        }
    }

    inline fun <T> section(name: String, block: () -> T): T {
        Trace.beginSection(name)
        return try {
            block()
        } finally {
            Trace.endSection()
        }
    }
}
