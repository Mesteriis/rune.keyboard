package io.github.mesteriis.rune.keyboard.ime.layout

import io.github.mesteriis.rune.keyboard.ime.model.*
import org.junit.Assert.*
import org.junit.Test

class MechanicalPunctuationAccessTest {
    @Test fun `comma exposes mechanical punctuation without changing letters layer geometry or action`() {
        val provider = KeyboardLayoutProvider()
        for (language in KeyboardLanguage.entries) {
            val state = KeyboardState(language)
            val bottom = provider.layoutFor(state, EditorContext.from(1, 0)).rows.last()
            val comma = bottom.single { it.action == KeyboardAction.CommitText(",") }
            assertEquals(",", comma.label)
            assertEquals(listOf("?", "!", ":", ";"), comma.longPressAlternates.map { it.label })
            assertEquals(listOf("?", "!", ":", ";").map { KeyboardAction.CommitText(it) }, comma.longPressAlternates.map { it.action })
            assertEquals(5, bottom.size)
            assertEquals(bottom.single { it.action == KeyboardAction.CommitText(".") }.weight, comma.weight)
            assertEquals(KeyboardLayer.LETTERS, state.layer)
        }
    }
}
