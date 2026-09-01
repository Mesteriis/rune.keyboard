package io.github.mesteriis.rune.keyboard.settings

import org.junit.Assert.assertEquals
import org.junit.Test

class SizeBucketTest {
    @Test
    fun `the cover screen covers everything below the inner-screen width`() {
        assertEquals(
            SizeBucket.COVER_PORTRAIT,
            SizeBucket.resolve(smallestScreenWidthDp = 360, isLandscape = false),
        )
        assertEquals(
            SizeBucket.COVER_LANDSCAPE,
            SizeBucket.resolve(smallestScreenWidthDp = 360, isLandscape = true),
        )
    }

    @Test
    fun `the boundary matches the resource qualifier`() {
        assertEquals(
            SizeBucket.COVER_PORTRAIT,
            SizeBucket.resolve(
                smallestScreenWidthDp = SizeBucket.INNER_SCREEN_MIN_WIDTH_DP - 1,
                isLandscape = false,
            ),
        )
        assertEquals(
            SizeBucket.INNER_PORTRAIT,
            SizeBucket.resolve(
                smallestScreenWidthDp = SizeBucket.INNER_SCREEN_MIN_WIDTH_DP,
                isLandscape = false,
            ),
        )
    }

    @Test
    fun `the unfolded screen keeps its own orientation buckets`() {
        assertEquals(
            SizeBucket.INNER_PORTRAIT,
            SizeBucket.resolve(smallestScreenWidthDp = 674, isLandscape = false),
        )
        assertEquals(
            SizeBucket.INNER_LANDSCAPE,
            SizeBucket.resolve(smallestScreenWidthDp = 674, isLandscape = true),
        )
    }
}
