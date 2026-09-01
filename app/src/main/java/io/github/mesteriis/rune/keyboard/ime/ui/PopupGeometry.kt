package io.github.mesteriis.rune.keyboard.ime.ui

import io.github.mesteriis.rune.keyboard.ime.layout.KeyStyle
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy

internal data class PopupPlacement(
    val x: Int,
    val y: Int,
    val width: Int,
    val height: Int,
)

/**
 * Placement and hit-testing for the key preview and the long-press alternates row.
 * Pure integer math so every edge case is unit-testable; all coordinates are window-relative.
 */
internal object PopupGeometry {
    fun previewPlacement(
        keyLeft: Int,
        keyTop: Int,
        keyWidth: Int,
        previewWidth: Int,
        previewHeight: Int,
        verticalGap: Int,
        containerLeft: Int,
        containerRight: Int,
    ): PopupPlacement = PopupPlacement(
        x = clampHorizontally(
            desiredX = keyLeft + (keyWidth - previewWidth) / 2,
            width = previewWidth,
            containerLeft = containerLeft,
            containerRight = containerRight,
        ),
        y = placeAbove(keyTop, previewHeight, verticalGap),
        width = previewWidth,
        height = previewHeight,
    )

    fun alternatesPlacement(
        keyLeft: Int,
        keyTop: Int,
        keyWidth: Int,
        cellWidth: Int,
        cellCount: Int,
        rowHeight: Int,
        verticalGap: Int,
        containerLeft: Int,
        containerRight: Int,
    ): PopupPlacement {
        val width = cellWidth * cellCount
        return PopupPlacement(
            x = clampHorizontally(
                // The first cell sits over the key, so the row grows to the right.
                desiredX = keyLeft + (keyWidth - cellWidth) / 2,
                width = width,
                containerLeft = containerLeft,
                containerRight = containerRight,
            ),
            y = placeAbove(keyTop, rowHeight, verticalGap),
            width = width,
            height = rowHeight,
        )
    }

    fun selectedAlternateIndex(
        touchXInWindow: Int,
        popupX: Int,
        cellWidth: Int,
        cellCount: Int,
    ): Int {
        if (cellCount <= 1 || cellWidth <= 0) return 0
        val offset = touchXInWindow - popupX
        val index = Math.floorDiv(offset, cellWidth)
        return index.coerceIn(0, cellCount - 1)
    }

    /** The finger dragged a full key height below the key: release should commit nothing. */
    fun isCancelled(touchYInWindow: Int, keyBottom: Int, keyHeight: Int): Boolean =
        touchYInWindow > keyBottom + keyHeight

    fun shouldShowPreview(
        style: KeyStyle,
        previewEnabled: Boolean,
        inputPolicy: InputPolicy,
    ): Boolean = previewEnabled &&
        inputPolicy == InputPolicy.NORMAL &&
        style == KeyStyle.CHARACTER

    private fun clampHorizontally(
        desiredX: Int,
        width: Int,
        containerLeft: Int,
        containerRight: Int,
    ): Int {
        val maxX = containerRight - width
        if (maxX <= containerLeft) return containerLeft
        return desiredX.coerceIn(containerLeft, maxX)
    }

    /**
     * Popups draw above the key. When there is no room left in the window (top key row) the popup
     * overlaps the key instead of being clipped away.
     */
    private fun placeAbove(keyTop: Int, popupHeight: Int, verticalGap: Int): Int {
        val above = keyTop - popupHeight - verticalGap
        return if (above < 0) keyTop else above
    }
}
