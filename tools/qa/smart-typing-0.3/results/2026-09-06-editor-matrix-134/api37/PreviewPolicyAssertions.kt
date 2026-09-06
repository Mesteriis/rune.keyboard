package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.graphics.Rect
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.ime.layout.KeySpec
import io.github.mesteriis.rune.keyboard.ime.layout.KeyStyle
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import org.junit.Assert.*

/** Test-local policy/spec inspection; exceptions return to the test thread, never app main. */
internal fun assertPreviewFixture(bounds: Rect, enabled: Boolean, policy: InputPolicy) {
    val instrumentation = InstrumentationRegistry.getInstrumentation()
    val snapshot = keyboardSnapshot()
    var result: Result<Unit>? = null
    instrumentation.runOnMainSync {
        result = runCatching {
            fun field(owner: Any, name: String): Any? = owner.javaClass.getDeclaredField(name)
                .apply { isAccessible = true }.get(owner)
            val raw = instrumentation.targetContext.getSharedPreferences(
                ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE).all
            assertEquals(enabled, SettingsCodec.decode(raw).keyPreview)
            assertEquals(enabled, field(snapshot.keyboard, "previewEnabled"))
            assertEquals(policy, field(snapshot.keyboard, "inputPolicy"))
            val matched = snapshot.keys.filter { key ->
                val location = IntArray(2); key.getLocationOnScreen(location)
                Rect(location[0], location[1], location[0] + key.width, location[1] + key.height) == bounds
            }
            assertEquals("Expected one actual key at the frozen screen bounds", 1, matched.size)
            val spec = field(matched.single(), "spec") as KeySpec
            assertEquals(KeyStyle.CHARACTER, spec.style)
            assertTrue("Preview fixture must have no alternate-key timer", spec.longPressAlternates.isEmpty())
        }
    }
    checkNotNull(result).getOrThrow()
}
