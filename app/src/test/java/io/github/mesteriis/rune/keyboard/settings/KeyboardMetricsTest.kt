package io.github.mesteriis.rune.keyboard.settings

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class KeyboardMetricsTest {
    @Test
    fun `presets scale the base height`() {
        assertEquals(133, KeyboardMetrics.keyHeightPx(156, HeightPreset.COMPACT))
        assertEquals(156, KeyboardMetrics.keyHeightPx(156, HeightPreset.NORMAL))
        assertEquals(179, KeyboardMetrics.keyHeightPx(156, HeightPreset.LARGE))
    }

    @Test
    fun `scaling rounds instead of truncating`() {
        assertEquals(45, KeyboardMetrics.keyHeightPx(53, HeightPreset.COMPACT))
    }

    @Test
    fun `a height never collapses to zero`() {
        assertTrue(KeyboardMetrics.keyHeightPx(1, HeightPreset.COMPACT) >= 1)
    }

    @Test
    fun `sizes must stay positive`() {
        assertThrows(IllegalArgumentException::class.java) {
            KeyboardViewMetrics(keyHeightPx = 0, keyGapPx = 4)
        }
        assertThrows(IllegalArgumentException::class.java) {
            KeyboardViewMetrics(keyHeightPx = 10, keyGapPx = -1)
        }
    }
}
