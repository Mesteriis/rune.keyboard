package io.github.mesteriis.rune.keyboard.ime

import android.os.Trace

/** Perfetto sections are constant and must never contain editor or user content. */
internal object RuneTrace {
    inline fun <T> section(name: String, block: () -> T): T {
        Trace.beginSection(name)
        return try {
            block()
        } finally {
            Trace.endSection()
        }
    }
}
