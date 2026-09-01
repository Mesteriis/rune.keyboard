package io.github.mesteriis.rune.keyboard.ime.editor

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DoubleSpacePeriodTest {
    @Test
    fun `a word followed by our space converts`() {
        assertTrue(DoubleSpacePeriod.canConvert("a "))
        assertTrue(DoubleSpacePeriod.canConvert("5 "))
        assertTrue(DoubleSpacePeriod.canConvert("я "))
    }

    @Test
    fun `sentence punctuation is never doubled`() {
        listOf(". ", ", ", "! ", "? ").forEach { before ->
            assertFalse(before, DoubleSpacePeriod.canConvert(before))
        }
    }

    @Test
    fun `whitespace before our space does not convert`() {
        listOf("  ", "\n ", "\t ").forEach { before ->
            assertFalse(before, DoubleSpacePeriod.canConvert(before))
        }
    }

    @Test
    fun `a missing trailing space does not convert`() {
        assertFalse(DoubleSpacePeriod.canConvert("ab"))
        assertFalse(DoubleSpacePeriod.canConvert(" a"))
    }

    @Test
    fun `too little context does not convert`() {
        assertFalse(DoubleSpacePeriod.canConvert(" "))
        assertFalse(DoubleSpacePeriod.canConvert(""))
        assertFalse(DoubleSpacePeriod.canConvert(null))
    }

    @Test
    fun `revert only accepts our own conversion`() {
        assertTrue(DoubleSpacePeriod.canRevert(". "))
        assertFalse(DoubleSpacePeriod.canRevert("a "))
        assertFalse(DoubleSpacePeriod.canRevert("."))
        assertFalse(DoubleSpacePeriod.canRevert(null))
    }
}
