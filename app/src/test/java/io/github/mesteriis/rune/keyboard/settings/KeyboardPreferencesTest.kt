package io.github.mesteriis.rune.keyboard.settings

import android.content.SharedPreferences
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class KeyboardPreferencesTest {
    private val store = FakeSharedPreferences()
    private val preferences = KeyboardPreferences(store)

    @Test
    fun `a fresh store reads the defaults`() {
        assertEquals(KeyboardSettings.DEFAULT.enabledLanguages, preferences.readSettings().enabledLanguages)
        assertEquals(null, preferences.readLanguage())
    }

    @Test
    fun `writes round-trip through the snapshot`() {
        preferences.writeLanguage(KeyboardLanguage.SPANISH)
        preferences.writeEnabledLanguages(listOf(KeyboardLanguage.SPANISH, KeyboardLanguage.ENGLISH))
        preferences.writeStartingLanguage(StartingLanguage.Fixed(KeyboardLanguage.ENGLISH))
        preferences.writeHeightPreset(SizeBucket.INNER_PORTRAIT, HeightPreset.LARGE)
        preferences.writeKeyGap(GapPreset.TIGHT)
        preferences.writeNumberRow(true)
        preferences.writeTheme(ThemePreference.DARK)
        preferences.writeHapticMode(HapticMode.LIGHT)
        preferences.writeSoundMode(SoundMode.QUIET)
        preferences.writeKeyPreview(false)
        preferences.writeDoubleSpacePeriod(false)

        val settings = preferences.readSettings()

        assertEquals(KeyboardLanguage.SPANISH, preferences.readLanguage())
        assertEquals(
            listOf(KeyboardLanguage.SPANISH, KeyboardLanguage.ENGLISH),
            settings.enabledLanguages,
        )
        assertEquals(StartingLanguage.Fixed(KeyboardLanguage.ENGLISH), settings.startingLanguage)
        assertEquals(HeightPreset.LARGE, settings.heightPreset(SizeBucket.INNER_PORTRAIT))
        assertEquals(GapPreset.TIGHT, settings.keyGap)
        assertTrue(settings.numberRow)
        assertEquals(ThemePreference.DARK, settings.theme)
        assertEquals(HapticMode.LIGHT, settings.hapticMode)
        assertEquals(SoundMode.QUIET, settings.soundMode)
        assertFalse(settings.keyPreview)
        assertFalse(settings.doubleSpacePeriod)
    }

    @Test
    fun `an empty language list is refused`() {
        assertThrows(IllegalArgumentException::class.java) {
            preferences.writeEnabledLanguages(emptyList())
        }
    }

    @Test
    fun `every write stamps the schema version`() {
        preferences.writeNumberRow(true)

        assertEquals(SettingsCodec.SCHEMA_VERSION, store.all[SettingsCodec.KEY_SCHEMA_VERSION])
    }

    @Test
    fun `listeners are notified about written keys and stop after unregistering`() {
        val changedKeys = mutableListOf<String?>()
        val listener = SharedPreferences.OnSharedPreferenceChangeListener { _, key ->
            changedKeys += key
        }

        preferences.registerListener(listener)
        preferences.writeNumberRow(true)

        assertTrue(SettingsCodec.KEY_NUMBER_ROW in changedKeys)

        changedKeys.clear()
        preferences.unregisterListener(listener)
        preferences.writeNumberRow(false)

        assertTrue(changedKeys.isEmpty())
    }

    private class FakeSharedPreferences : SharedPreferences {
        private val values = mutableMapOf<String, Any?>()
        private val listeners = mutableSetOf<SharedPreferences.OnSharedPreferenceChangeListener>()

        override fun getAll(): MutableMap<String, *> = values.toMutableMap()

        override fun getString(key: String?, defValue: String?): String? =
            values[key] as? String ?: defValue

        @Suppress("UNCHECKED_CAST")
        override fun getStringSet(key: String?, defValues: MutableSet<String>?): MutableSet<String>? =
            (values[key] as? MutableSet<String>) ?: defValues

        override fun getInt(key: String?, defValue: Int): Int = values[key] as? Int ?: defValue

        override fun getLong(key: String?, defValue: Long): Long = values[key] as? Long ?: defValue

        override fun getFloat(key: String?, defValue: Float): Float = values[key] as? Float ?: defValue

        override fun getBoolean(key: String?, defValue: Boolean): Boolean =
            values[key] as? Boolean ?: defValue

        override fun contains(key: String?): Boolean = values.containsKey(key)

        override fun edit(): SharedPreferences.Editor = FakeEditor()

        override fun registerOnSharedPreferenceChangeListener(
            listener: SharedPreferences.OnSharedPreferenceChangeListener?,
        ) {
            listener?.let(listeners::add)
        }

        override fun unregisterOnSharedPreferenceChangeListener(
            listener: SharedPreferences.OnSharedPreferenceChangeListener?,
        ) {
            listener?.let(listeners::remove)
        }

        private inner class FakeEditor : SharedPreferences.Editor {
            private val pending = mutableMapOf<String, Any?>()
            private val removals = mutableSetOf<String>()
            private var clearRequested = false

            override fun putString(key: String, value: String?): SharedPreferences.Editor = put(key, value)

            override fun putStringSet(
                key: String,
                value: MutableSet<String>?,
            ): SharedPreferences.Editor = put(key, value)

            override fun putInt(key: String, value: Int): SharedPreferences.Editor = put(key, value)

            override fun putLong(key: String, value: Long): SharedPreferences.Editor = put(key, value)

            override fun putFloat(key: String, value: Float): SharedPreferences.Editor = put(key, value)

            override fun putBoolean(key: String, value: Boolean): SharedPreferences.Editor = put(key, value)

            override fun remove(key: String): SharedPreferences.Editor {
                removals += key
                return this
            }

            override fun clear(): SharedPreferences.Editor {
                clearRequested = true
                return this
            }

            override fun commit(): Boolean {
                apply()
                return true
            }

            override fun apply() {
                if (clearRequested) values.clear()
                removals.forEach(values::remove)
                values.putAll(pending)
                val changedKeys = pending.keys + removals
                listeners.toList().forEach { listener ->
                    changedKeys.forEach { key ->
                        listener.onSharedPreferenceChanged(this@FakeSharedPreferences, key)
                    }
                }
            }

            private fun put(key: String, value: Any?): SharedPreferences.Editor {
                pending[key] = value
                return this
            }
        }
    }
}
