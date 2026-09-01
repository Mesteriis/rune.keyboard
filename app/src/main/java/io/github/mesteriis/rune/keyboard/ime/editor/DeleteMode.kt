package io.github.mesteriis.rune.keyboard.ime.editor

/** Selects the least-observing deletion strategy allowed by the active editor. */
internal enum class DeleteMode {
    /** A bounded, ephemeral read is allowed so one visible grapheme can be deleted atomically. */
    GRAPHEME_AWARE,

    /** Sensitive editors are never read; deletion is limited to one Unicode code point. */
    CODE_POINT,

    /** TYPE_NULL editors receive hardware-style key events. */
    RAW_KEY_EVENT,
}
