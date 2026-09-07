package io.github.mesteriis.rune.keyboard.ime.ui

import org.junit.Assert.assertEquals
import org.junit.Test

class SafeInsetPolicyTest {
    @Test
    fun visibleBarsAndSideCutoutAddToBaseExactlyOnce() {
        assertEquals(SafePadding(24, 4, 16, 52), SafeInsetPolicy.padding(
            4, SafeInsets(20, 12, 48), SafeInsets(20, 12, 48),
        ))
    }

    @Test
    fun temporarilyHiddenNavigationBarKeepsStableBottomClearance() {
        assertEquals(SafePadding(4, 4, 4, 52), SafeInsetPolicy.padding(
            base = 4, visible = SafeInsets(), stable = SafeInsets(bottom = 48),
        ))
    }

    @Test
    fun changedDisplayReplacesPreviousInsetsIncludingReturningToZero() {
        val deliveries = listOf(SafeInsets(bottom = 48), SafeInsets(left = 36), SafeInsets())
        assertEquals(listOf(SafePadding(4, 4, 4, 52), SafePadding(40, 4, 4, 4),
            SafePadding(4, 4, 4, 4)), deliveries.map {
            SafeInsetPolicy.padding(4, SafeInsets(bottom = 48), it)
        })
    }

    @Test
    fun repeatedHiddenAndVisibleDeliveriesNeverAccumulatePadding() {
        val stable = SafeInsets(12, 20, 48)
        repeat(10) { delivery ->
            assertEquals(SafePadding(16, 4, 24, 52), SafeInsetPolicy.padding(
                4, if (delivery % 2 == 0) stable else SafeInsets(), stable,
            ))
        }
    }

    @Test
    fun absentStableInsetsFallBackToSystemWindowInsets() {
        assertEquals(SafePadding(16, 4, 24, 52), SafeInsetPolicy.padding(4, SafeInsets(12, 20, 48)))
        assertEquals(SafePadding(4, 4, 4, 4), SafeInsetPolicy.padding(4, SafeInsets()))
    }

    @Test
    fun legacyUsesStableBarsWithConservativeSystemFallbackPerEdge() {
        assertEquals(SafePadding(16, 4, 24, 52), SafeInsetPolicy.padding(
            4, SafeInsets(12, 20, 0), SafeInsets(bottom = 48), legacyFallback = true,
        ))
    }
}
