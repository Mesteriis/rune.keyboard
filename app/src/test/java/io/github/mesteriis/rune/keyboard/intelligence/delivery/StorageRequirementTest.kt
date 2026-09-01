package io.github.mesteriis.rune.keyboard.intelligence.delivery

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class StorageRequirementTest {
    @Test
    fun appliesSameAndDifferentVolumePolicies() {
        val size = 400L * 1024 * 1024

        assertEquals(size * 2 + 64L * 1024 * 1024, StorageRequirement.sameVolume(size))
        assertEquals(size + 32L * 1024 * 1024, StorageRequirement.eachDifferentVolume(size))
    }

    @Test
    fun rejectsNonPositiveAndOverflowingSizes() {
        assertThrows(IllegalArgumentException::class.java) { StorageRequirement.sameVolume(0) }
        assertThrows(ArithmeticException::class.java) { StorageRequirement.sameVolume(Long.MAX_VALUE) }
    }
}
