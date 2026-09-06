package io.github.mesteriis.rune.keyboard.ime.model

import io.github.mesteriis.rune.keyboard.settings.KeyboardSettings
import io.github.mesteriis.rune.keyboard.settings.StartingLanguage
import org.junit.Assert.assertEquals
import org.junit.Test

class ConfigurationVisualContinuityTest {
    private val cover = ConfigurationSize(320, 780, 320)
    private val inner = ConfigurationSize(690, 780, 690)
    private val editor = VisualEditorIdentity("public.fixture", 42, 1, 6)
    private val settings = KeyboardSettings.DEFAULT
    private val shifted = KeyboardState(KeyboardLanguage.ENGLISH, shiftMode = ShiftMode.ONCE)

    @Test fun `fresh recreated editor preserves manual shift only once`() {
        val tracker = primed()
        tracker.onConfigurationChanged(inner, shifted, 100)
        val continued = start(tracker, shifted, configuration = inner, now = 101)
        assertEquals(ShiftMode.ONCE, continued.shiftMode)
        assertEquals(KeyboardLayer.LETTERS, continued.layer)
        assertEquals(ShiftMode.OFF, start(tracker, continued, configuration = inner, now = 102).shiftMode)
    }

    @Test fun `configuration handoff survives IME service replacement`() {
        val store = ConfigurationVisualContinuityStore()
        val original = store.attach(cover)
        start(original, shifted)
        original.onConfigurationChanged(inner, shifted, 100)
        store.detach(original)

        val recreated = store.attach(inner)
        val continued = start(recreated, shifted, configuration = inner, now = 101)

        assertEquals(ShiftMode.ONCE, continued.shiftMode)
        store.detach(recreated)
    }

    @Test fun `framework restarting callback does not consume the later fresh start`() {
        val tracker = primed()
        tracker.onConfigurationChanged(inner, shifted, 100)
        val intermediate = start(tracker, shifted, restarting = true, configuration = inner, now = 101)
        assertEquals(ShiftMode.ONCE, intermediate.shiftMode)
        assertEquals(ShiftMode.ONCE, start(tracker, intermediate, configuration = inner, now = 102).shiftMode)
    }

    @Test fun `resources first start preserves before late config callback without rearming`() {
        val tracker = primed()
        val continued = start(tracker, shifted, configuration = inner, now = 100)
        assertEquals(ShiftMode.ONCE, continued.shiftMode)
        tracker.onConfigurationChanged(inner, continued, 101)
        assertEquals(ShiftMode.OFF, start(tracker, continued, configuration = inner, now = 102).shiftMode)
    }

    @Test fun `editor identity drift across stable field IDs can still restore visual state`() {
        for (other in listOf(editor.copy(inputType = 129), editor.copy(imeOptions = 3))) {
            val tracker = primed()
            tracker.onConfigurationChanged(inner, shifted, 100)
            val continued = start(tracker, shifted, configuration = inner, identity = other, now = 101)
            assertEquals(ShiftMode.ONCE, continued.shiftMode)
            assertEquals(KeyboardLayer.LETTERS, continued.layer)
            assertEquals(ShiftMode.OFF, start(tracker, continued, configuration = inner, now = 102).shiftMode)
        }
    }

    @Test fun `unrelated or unidentifiable editors discard the pending snapshot`() {
        val alternatives = listOf(null, editor.copy(packageName = ""), editor.copy(fieldId = 0),
            editor.copy(fieldId = -1), editor.copy(packageName = "other.fixture"), editor.copy(fieldId = 43))
        for (other in alternatives) {
            val tracker = primed()
            tracker.onConfigurationChanged(inner, shifted, 100)
            val reset = start(tracker, shifted, identity = other, configuration = inner, now = 101)
            assertEquals(ShiftMode.OFF, reset.shiftMode)
            assertEquals(KeyboardLayer.LETTERS, reset.layer)
            assertEquals(ShiftMode.OFF, start(tracker, reset, configuration = inner, now = 102).shiftMode)
        }
    }

    @Test fun `unidentifiable prior editor cannot lend visual state to a later known editor`() {
        for (unknown in listOf(null, editor.copy(fieldId = 0), editor.copy(fieldId = -1),
            editor.copy(packageName = " "))) {
            val tracker = ConfigurationVisualContinuity(cover)
            start(tracker, shifted, identity = unknown)
            tracker.onConfigurationChanged(inner, shifted, 100)
            assertEquals(ShiftMode.OFF, start(tracker, shifted, configuration = inner, now = 101).shiftMode)
        }
    }

    @Test fun `no size change and explicit invalidation reset fresh editor`() {
        val unchanged = primed()
        unchanged.onConfigurationChanged(cover, shifted, 100)
        assertEquals(ShiftMode.OFF, start(unchanged, shifted, now = 101).shiftMode)
        val invalidated = primed()
        invalidated.onConfigurationChanged(inner, shifted, 100)
        invalidated.invalidate()
        assertEquals(ShiftMode.OFF, start(invalidated, shifted, configuration = inner, now = 101).shiftMode)
    }

    @Test fun `continuation expires exactly at five seconds without extending on restart`() {
        val live = primed()
        live.onConfigurationChanged(inner, shifted, 100)
        assertEquals(ShiftMode.ONCE, start(live, shifted, configuration = inner, now = 5099).shiftMode)
        val expired = primed()
        expired.onConfigurationChanged(inner, shifted, 100)
        start(expired, shifted, restarting = true, configuration = inner, now = 5099)
        assertEquals(ShiftMode.OFF, start(expired, shifted, configuration = inner, now = 5100).shiftMode)
    }

    @Test fun `visual continuation keeps language caps and alternate layer against fresh defaults`() {
        val tracker = primed()
        val previous = KeyboardState(KeyboardLanguage.SPANISH, layer = KeyboardLayer.SYMBOLS_ALT,
            shiftMode = ShiftMode.LOCKED)
        tracker.onConfigurationChanged(inner, previous, 100)
        val continued = start(tracker, previous, configuration = inner, now = 101,
            currentSettings = settings.copy(startingLanguage = StartingLanguage.Fixed(KeyboardLanguage.RUSSIAN)))
        assertEquals(KeyboardLanguage.SPANISH, continued.language)
        assertEquals(KeyboardLayer.SYMBOLS_ALT, continued.layer)
        assertEquals(ShiftMode.LOCKED, continued.shiftMode)
    }

    @Test fun `restored state uses current settings and drops automatic shift and tap timing`() {
        val narrowed = primed()
        narrowed.onConfigurationChanged(inner, shifted.copy(layer = KeyboardLayer.SYMBOLS), 100)
        val result = start(narrowed, shifted, configuration = inner, now = 101,
            currentSettings = settings.copy(enabledLanguages = listOf(KeyboardLanguage.RUSSIAN),
                doubleSpacePeriod = false))
        assertEquals(KeyboardLanguage.RUSSIAN, result.language)
        assertEquals(KeyboardLayer.LETTERS, result.layer)
        assertEquals(false, result.doubleSpacePeriodEnabled)

        val automatic = primed()
        val auto = shifted.copy(shiftMode = ShiftMode.AUTO)
        automatic.onConfigurationChanged(inner, auto, 100)
        assertEquals(ShiftMode.OFF, start(automatic, auto, configuration = inner, now = 101).shiftMode)

        val taps = primed()
        val firstTap = KeyboardState(KeyboardLanguage.ENGLISH).onShiftPressed(100)
        taps.onConfigurationChanged(inner, firstTap, 101)
        val restored = start(taps, firstTap, configuration = inner, now = 102)
        assertEquals(ShiftMode.ONCE, restored.shiftMode)
        // A new shift tap must not complete a pre-fold double tap and unexpectedly lock caps.
        assertEquals(ShiftMode.OFF, restored.onShiftPressed(103).shiftMode)
    }

    @Test fun `explicit shift off survives post restoration caps refresh without retaining tap timing`() {
        for (source in listOf(ShiftMode.AUTO, ShiftMode.LOCKED)) {
            val tracker = primed()
            val manualOff = shifted.copy(shiftMode = source).onShiftPressed(100)
            assertEquals(ShiftMode.OFF, manualOff.shiftMode)
            tracker.onConfigurationChanged(inner, manualOff, 101)
            val restored = start(tracker, manualOff, configuration = inner, now = 102)
            assertEquals(ShiftMode.OFF, restored.withAutomaticCapitalization(true).shiftMode)
            // Suppression is user intent; it ends at the next text action as before the fold.
            assertEquals(ShiftMode.AUTO,
                restored.afterTextCommitted().withAutomaticCapitalization(true).shiftMode)
            // AUTO -> OFF records a tap timestamp, which must not survive with that intent.
            assertEquals(ShiftMode.ONCE, restored.onShiftPressed(103).shiftMode)
        }
    }

    private fun primed(): ConfigurationVisualContinuity = ConfigurationVisualContinuity(cover).also {
        start(it, shifted)
    }

    private fun start(
        tracker: ConfigurationVisualContinuity,
        previous: KeyboardState,
        restarting: Boolean = false,
        identity: VisualEditorIdentity? = editor,
        configuration: ConfigurationSize = cover,
        now: Long = 0,
        currentSettings: KeyboardSettings = settings,
    ): KeyboardState = tracker.onStartInput(previous, restarting, currentSettings,
        KeyboardLanguage.ENGLISH, identity, configuration, now)
}
