package io.github.mesteriis.rune.keyboard.ime.layout

import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction

enum class KeyStyle {
    CHARACTER,
    ACTION,
    SPACE,
    SPACER,
}

data class KeySpec(
    val label: String,
    val action: KeyboardAction?,
    val weight: Float = 1f,
    val style: KeyStyle = KeyStyle.CHARACTER,
    val longPressAction: KeyboardAction? = null,
    val accessibilityLabel: String? = null,
) {
    init {
        require(weight > 0f) { "Key weight must be positive" }
        require(action != null || style == KeyStyle.SPACER) { "Only spacer keys may omit an action" }
    }

    companion object {
        fun spacer(weight: Float = 1f): KeySpec = KeySpec(
            label = "",
            action = null,
            weight = weight,
            style = KeyStyle.SPACER,
        )
    }
}

data class KeyboardLayout(val rows: List<List<KeySpec>>) {
    init {
        require(rows.isNotEmpty()) { "Keyboard must contain rows" }
        require(rows.none { it.isEmpty() }) { "Keyboard rows must not be empty" }
    }
}
