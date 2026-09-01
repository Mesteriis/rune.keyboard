package io.github.mesteriis.rune.keyboard.ime.ui

import io.github.mesteriis.rune.keyboard.ime.layout.KeyStyle
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PopupGeometryTest {
    @Test
    fun `preview is centred above the key`() {
        val placement = PopupGeometry.previewPlacement(
            keyLeft = 200,
            keyTop = 300,
            keyWidth = 100,
            previewWidth = 60,
            previewHeight = 80,
            verticalGap = 4,
            containerLeft = 0,
            containerRight = 1000,
        )

        assertEquals(220, placement.x)
        assertEquals(216, placement.y)
        assertEquals(60, placement.width)
        assertEquals(80, placement.height)
    }

    @Test
    fun `preview is clamped at both container edges`() {
        val atLeftEdge = PopupGeometry.previewPlacement(
            keyLeft = 4,
            keyTop = 300,
            keyWidth = 40,
            previewWidth = 60,
            previewHeight = 80,
            verticalGap = 4,
            containerLeft = 4,
            containerRight = 1000,
        )
        val atRightEdge = PopupGeometry.previewPlacement(
            keyLeft = 960,
            keyTop = 300,
            keyWidth = 40,
            previewWidth = 60,
            previewHeight = 80,
            verticalGap = 4,
            containerLeft = 4,
            containerRight = 1000,
        )

        assertEquals(4, atLeftEdge.x)
        assertEquals(940, atRightEdge.x)
    }

    @Test
    fun `a popup with no room above clamps to the IME top edge`() {
        val placement = PopupGeometry.previewPlacement(
            keyLeft = 100,
            keyTop = 20,
            keyWidth = 100,
            previewWidth = 60,
            previewHeight = 80,
            verticalGap = 4,
            containerLeft = 0,
            containerRight = 1000,
        )

        assertEquals(0, placement.y)
    }

    @Test
    fun `alternates start over the key and grow to the right`() {
        val placement = PopupGeometry.alternatesPlacement(
            keyLeft = 200,
            keyTop = 300,
            keyWidth = 100,
            cellWidth = 50,
            cellCount = 4,
            rowHeight = 60,
            verticalGap = 4,
            containerLeft = 0,
            containerRight = 1000,
        )

        assertEquals(225, placement.x)
        assertEquals(200, placement.width)
        assertEquals(236, placement.y)
    }

    @Test
    fun `alternates shift left when the row would overflow`() {
        val placement = PopupGeometry.alternatesPlacement(
            keyLeft = 900,
            keyTop = 300,
            keyWidth = 100,
            cellWidth = 50,
            cellCount = 4,
            rowHeight = 60,
            verticalGap = 4,
            containerLeft = 0,
            containerRight = 1000,
        )

        assertEquals(800, placement.x)
    }

    @Test
    fun `a row wider than the container starts at its left edge`() {
        val placement = PopupGeometry.alternatesPlacement(
            keyLeft = 40,
            keyTop = 300,
            keyWidth = 60,
            cellWidth = 50,
            cellCount = 8,
            rowHeight = 60,
            verticalGap = 4,
            containerLeft = 10,
            containerRight = 300,
        )

        assertEquals(10, placement.x)
    }

    @Test
    fun `the selected cell follows the finger and clamps at both ends`() {
        assertEquals(
            0,
            PopupGeometry.selectedAlternateIndex(
                touchXInWindow = 210,
                popupX = 200,
                cellWidth = 50,
                cellCount = 4,
            ),
        )
        assertEquals(
            2,
            PopupGeometry.selectedAlternateIndex(
                touchXInWindow = 320,
                popupX = 200,
                cellWidth = 50,
                cellCount = 4,
            ),
        )
        assertEquals(
            0,
            PopupGeometry.selectedAlternateIndex(
                touchXInWindow = 100,
                popupX = 200,
                cellWidth = 50,
                cellCount = 4,
            ),
        )
        assertEquals(
            3,
            PopupGeometry.selectedAlternateIndex(
                touchXInWindow = 900,
                popupX = 200,
                cellWidth = 50,
                cellCount = 4,
            ),
        )
    }

    @Test
    fun `a single alternate is always the selected one`() {
        assertEquals(
            0,
            PopupGeometry.selectedAlternateIndex(
                touchXInWindow = -400,
                popupX = 200,
                cellWidth = 50,
                cellCount = 1,
            ),
        )
    }

    @Test
    fun `dragging a key height below the key cancels the selection`() {
        assertFalse(PopupGeometry.isCancelled(touchYInWindow = 360, keyBottom = 352, keyHeight = 52))
        assertTrue(PopupGeometry.isCancelled(touchYInWindow = 420, keyBottom = 352, keyHeight = 52))
    }

    @Test
    fun `preview is limited to character keys in non-sensitive fields`() {
        assertTrue(
            PopupGeometry.shouldShowPreview(KeyStyle.CHARACTER, true, InputPolicy.NORMAL),
        )
        assertFalse(
            PopupGeometry.shouldShowPreview(KeyStyle.CHARACTER, false, InputPolicy.NORMAL),
        )
        assertFalse(
            PopupGeometry.shouldShowPreview(KeyStyle.CHARACTER, true, InputPolicy.SENSITIVE),
        )
        listOf(KeyStyle.ACTION, KeyStyle.SPACE, KeyStyle.SPACER).forEach { style ->
            assertFalse(
                style.name,
                PopupGeometry.shouldShowPreview(style, true, InputPolicy.NORMAL),
            )
        }
    }
}
