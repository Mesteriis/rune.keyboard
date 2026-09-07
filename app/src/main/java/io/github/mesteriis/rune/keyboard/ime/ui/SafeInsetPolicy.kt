package io.github.mesteriis.rune.keyboard.ime.ui

internal data class SafeInsets(val left: Int = 0, val right: Int = 0, val bottom: Int = 0)

internal data class SafePadding(val left: Int, val top: Int, val right: Int, val bottom: Int)

internal object SafeInsetPolicy {
    /** Always derive from the base, never the previously padded view or another display. */
    fun padding(
        base: Int,
        visible: SafeInsets,
        stable: SafeInsets? = null,
        legacyFallback: Boolean = false,
    ): SafePadding {
        val safe = when {
            stable == null -> visible
            legacyFallback -> SafeInsets(
                maxOf(stable.left, visible.left),
                maxOf(stable.right, visible.right),
                maxOf(stable.bottom, visible.bottom),
            )
            else -> stable
        }
        return SafePadding(base + safe.left, base, base + safe.right, base + safe.bottom)
    }
}
