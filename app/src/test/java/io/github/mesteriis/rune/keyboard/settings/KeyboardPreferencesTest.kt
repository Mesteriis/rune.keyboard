package io.github.mesteriis.rune.keyboard.settings

import android.content.SharedPreferences
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class KeyboardPreferencesTest {
    @Test fun schemaThreeUndoChoiceIsPersistedBeforeAnUnrelatedWriterUpgradesToFour() {
        for (choice in listOf(null, false, true)) {
            val initial = mutableMapOf<String, Any?>(SettingsCodec.KEY_SCHEMA_VERSION to 3)
            if (choice != null) initial[SettingsCodec.KEY_VISIBLE_UNDO] = choice
            val source = FakeSharedPreferences(initial)
            val facade = KeyboardPreferences(source)
            facade.writeNumberRow(true)
            assertEquals(4, source.all[SettingsCodec.KEY_SCHEMA_VERSION])
            assertEquals(choice ?: false, source.all[SettingsCodec.KEY_VISIBLE_UNDO])
            assertEquals(choice ?: false, facade.readSettings().visibleUndo)
        }
    }

    private val store = FakeSharedPreferences()
    private val preferences = KeyboardPreferences(store)

    @Test fun emojiKeyRoundTripsAndRebuildsWithoutEnablingAnyTypingFeature() {
        val before = preferences.readSettings()
        assertFalse(before.emojiKey)
        preferences.writeEmojiKey(true)
        val after = KeyboardPreferences(store).readSettings()
        assertEquals(before.copy(emojiKey = true), after)
        assertTrue(before.affectsKeyboardView(after))
        preferences.disableAdditionalTyping()
        assertTrue(preferences.readSettings().emojiKey)
        assertTrue(AdditionalFeatures.entries.all { !it.value.get(preferences.readSettings()) })
        preferences.writeEmojiKey(false)
        assertFalse(KeyboardPreferences(store).readSettings().emojiKey)
    }

    @Test
    fun `keyboard themes persist independently of app theme and typing settings`() {
        preferences.writeTheme(ThemePreference.LIGHT)
        preferences.writeHeightPreset(SizeBucket.COVER_PORTRAIT, HeightPreset.LARGE)
        preferences.writeAutocorrectionMode(AutocorrectionMode.OFF)
        for (theme in KeyboardTheme.entries) {
            preferences.writeKeyboardTheme(theme)
            val restored = KeyboardPreferences(store).readSettings()
            assertEquals(theme, restored.keyboardTheme)
            assertEquals(ThemePreference.LIGHT, restored.theme)
            assertEquals(HeightPreset.LARGE, restored.heightPreset(SizeBucket.COVER_PORTRAIT))
            assertEquals(AutocorrectionMode.OFF, restored.autocorrectionMode)
        }
    }

    @Test
    fun `absent or malformed keyboard themes fall back without rewriting saved data`() {
        for (value in listOf(null, "FUTURE_THEME", 7, false)) {
            val raw = mapOf(SettingsCodec.KEY_KEYBOARD_THEME to value, SettingsCodec.KEY_THEME to "DARK")
            val source = FakeSharedPreferences(raw)
            val settings = KeyboardPreferences(source).readSettings()
            assertEquals(KeyboardTheme.AIR, settings.keyboardTheme)
            assertEquals(ThemePreference.DARK, settings.theme)
            assertEquals(raw, source.all)
        }
    }

    @Test
    fun `every theme change rebuilds the view but unchanged appearance does not`() {
        for (theme in KeyboardTheme.entries) {
            val before = KeyboardSettings.DEFAULT.copy(keyboardTheme = theme)
            assertFalse(before.affectsKeyboardView(before.copy()))
            for (other in KeyboardTheme.entries.filter { it != theme }) {
                assertTrue(before.affectsKeyboardView(before.copy(keyboardTheme = other)))
            }
        }
    }

    @Test
    fun `key flick preference persists and requests keyboard rebuild without changing opt ins`() {
        val before = preferences.readSettings()
        assertTrue(before.keyFlicks)
        preferences.writeKeyFlicks(false)
        val after = KeyboardPreferences(store).readSettings()
        assertEquals(before.copy(keyFlicks = false), after)
        assertTrue(before.affectsKeyboardView(after))
        preferences.writeKeyFlicks(true)
        assertEquals(before, KeyboardPreferences(store).readSettings())
    }

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


    @Test
    fun `reading fresh legacy malformed and future preferences never persists`() {
        for (initial in listOf(emptyMap(), mapOf(SettingsCodec.KEY_SCHEMA_VERSION to 2),
            mapOf(SettingsCodec.KEY_SCHEMA_VERSION to "broken"), mapOf(SettingsCodec.KEY_SCHEMA_VERSION to 5))) {
            val source = FakeSharedPreferences(initial)
            val facade = KeyboardPreferences(source)
            repeat(3) { facade.readSettings(); facade.readLanguage() }
            assertEquals(initial, source.all)
        }
    }

    @Test
    fun `every existing writer migrates legacy smart values atomically without losing unknown data`() {
        val writers: List<(KeyboardPreferences) -> Unit> = listOf(
            { it.writeLanguage(KeyboardLanguage.SPANISH) },
            { it.writeEnabledLanguages(listOf(KeyboardLanguage.SPANISH)) },
            { it.writeStartingLanguage(StartingLanguage.Fixed(KeyboardLanguage.SPANISH)) },
            { it.writeHeightPreset(SizeBucket.INNER_PORTRAIT, HeightPreset.LARGE) },
            { it.writeKeyGap(GapPreset.TIGHT) }, { it.writeNumberRow(true) },
            { it.writeTheme(ThemePreference.DARK) }, { it.writeHapticMode(HapticMode.OFF) },
            { it.writeSoundMode(SoundMode.OFF) }, { it.writeKeyPreview(false) },
            { it.writeDoubleSpacePeriod(false) },
        )
        for (schema in listOf(null, 1, 2)) for (write in writers) {
            val initial = mutableMapOf<String, Any?>("future_metadata" to setOf("preserve"))
            if (schema != null) initial[SettingsCodec.KEY_SCHEMA_VERSION] = schema
            val source = FakeSharedPreferences(initial)
            val facade = KeyboardPreferences(source)
            val observed = mutableListOf<KeyboardSettings>()
            val listener = SharedPreferences.OnSharedPreferenceChangeListener { _, _ -> observed.add(facade.readSettings()) }
            facade.registerListener(listener)
            write(facade)
            assertEquals(SettingsCodec.SCHEMA_VERSION, source.all[SettingsCodec.KEY_SCHEMA_VERSION])
            assertEquals(setOf("preserve"), source.all["future_metadata"])
            assertTrue(source.all.containsKey(SettingsCodec.KEY_DOUBLE_SPACE_PERIOD))
            assertTrue(observed.isNotEmpty())
            for (result in observed + facade.readSettings()) {
                assertEquals(AutocorrectionMode.HIGH_CONFIDENCE, result.autocorrectionMode)
                assertTrue(result.mechanicalPunctuation && result.candidateStrip)
                assertEquals(ContextualPunctuationMode.OFF, result.contextualPunctuationMode)
            }
        }
    }

    @Test
    fun `all new writers round trip every mode and boolean while preserving independent preferences`() {
        preferences.writeTheme(ThemePreference.DARK)
        for (mode in AutocorrectionMode.entries) {
            preferences.writeAutocorrectionMode(mode)
            assertEquals(mode, preferences.readSettings().autocorrectionMode)
        }
        preferences.writeAutocorrectionMode(AutocorrectionMode.OFF)
        for (mode in ContextualPunctuationMode.entries) {
            preferences.writeContextualPunctuationMode(mode)
            assertEquals(mode, preferences.readSettings().contextualPunctuationMode)
            assertEquals(AutocorrectionMode.OFF, preferences.readSettings().autocorrectionMode)
        }
        for (enabled in listOf(false, true)) {
            preferences.writeMechanicalPunctuation(enabled)
            preferences.writeCandidateStrip(enabled)
            assertEquals(enabled, preferences.readSettings().mechanicalPunctuation)
            assertEquals(enabled, preferences.readSettings().candidateStrip)
            assertEquals(AutocorrectionMode.OFF, preferences.readSettings().autocorrectionMode)
            assertEquals(ContextualPunctuationMode.SUGGESTIONS, preferences.readSettings().contextualPunctuationMode)
            assertEquals(ThemePreference.DARK, preferences.readSettings().theme)
        }
    }

    @Test
    fun `unrelated migration never re enables individually malformed smart preferences`() {
        val initial = mapOf<String, Any?>(SettingsCodec.KEY_SCHEMA_VERSION to 2,
            SettingsCodec.KEY_AUTOCORRECTION_MODE to "bad", SettingsCodec.KEY_MECHANICAL_PUNCTUATION to "true",
            SettingsCodec.KEY_CONTEXTUAL_PUNCTUATION_MODE to null, SettingsCodec.KEY_CANDIDATE_STRIP to 1,
            SettingsCodec.KEY_DOUBLE_SPACE_PERIOD to "true")
        val source = FakeSharedPreferences(initial)
        val facade = KeyboardPreferences(source)
        facade.writeLanguage(KeyboardLanguage.SPANISH)
        facade.writeTheme(ThemePreference.DARK)
        val result = facade.readSettings()
        assertEquals(SettingsCodec.SCHEMA_VERSION, source.all[SettingsCodec.KEY_SCHEMA_VERSION])
        assertEquals(AutocorrectionMode.OFF, result.autocorrectionMode)
        assertFalse(result.mechanicalPunctuation || result.candidateStrip || result.doubleSpacePeriod)
        assertEquals(ContextualPunctuationMode.OFF, result.contextualPunctuationMode)
        facade.writeMechanicalPunctuation(true)
        assertTrue(facade.readSettings().mechanicalPunctuation)
        assertEquals(AutocorrectionMode.OFF, facade.readSettings().autocorrectionMode)
        assertFalse(facade.readSettings().doubleSpacePeriod)
    }

    @Test
    fun `missing schema three fields remain off after unrelated writers`() {
        val source = FakeSharedPreferences(mapOf(SettingsCodec.KEY_SCHEMA_VERSION to 3))
        val facade = KeyboardPreferences(source)
        facade.writeNumberRow(true)
        val result = facade.readSettings()
        assertEquals(AutocorrectionMode.OFF, result.autocorrectionMode)
        assertFalse(result.mechanicalPunctuation || result.candidateStrip || result.doubleSpacePeriod)
        assertEquals(ContextualPunctuationMode.OFF, result.contextualPunctuationMode)
        assertTrue(result.numberRow)
    }

    @Test
    fun `malformed schema repairs to the current version safely and an explicit choice wins over normalization`() {
        for (marker in listOf(null, "3", 3L, 0, -1)) {
            val source = FakeSharedPreferences(mapOf(SettingsCodec.KEY_SCHEMA_VERSION to marker,
                "future_metadata" to "preserve", SettingsCodec.KEY_MECHANICAL_PUNCTUATION to true))
            val facade = KeyboardPreferences(source)
            facade.writeCandidateStrip(true)
            assertEquals(SettingsCodec.SCHEMA_VERSION, source.all[SettingsCodec.KEY_SCHEMA_VERSION])
            assertEquals("preserve", source.all["future_metadata"])
            val result = facade.readSettings()
            assertTrue(result.candidateStrip)
            assertFalse(result.mechanicalPunctuation || result.doubleSpacePeriod)
            assertEquals(AutocorrectionMode.OFF, result.autocorrectionMode)
            assertEquals(ContextualPunctuationMode.OFF, result.contextualPunctuationMode)
        }
    }

    @Test
    fun `future schema preserves marker data and explicit stored choices while effective smart typing stays off`() {
        for (version in listOf(5, Int.MAX_VALUE)) {
            val source = FakeSharedPreferences(mapOf(SettingsCodec.KEY_SCHEMA_VERSION to version,
                "future_metadata" to setOf("preserve"), SettingsCodec.KEY_AUTOCORRECTION_MODE to "FUTURE_MODE",
                SettingsCodec.KEY_MECHANICAL_PUNCTUATION to true))
            val facade = KeyboardPreferences(source)
            facade.writeTheme(ThemePreference.DARK)
            assertEquals("FUTURE_MODE", source.all[SettingsCodec.KEY_AUTOCORRECTION_MODE])
            assertEquals(version, source.all[SettingsCodec.KEY_SCHEMA_VERSION])
            assertEquals(setOf("preserve"), source.all["future_metadata"])
            facade.writeAutocorrectionMode(AutocorrectionMode.HIGH_CONFIDENCE)
            facade.writeMechanicalPunctuation(true)
            facade.writeContextualPunctuationMode(ContextualPunctuationMode.SUGGESTIONS)
            facade.writeCandidateStrip(true)
            facade.writeDoubleSpacePeriod(true)
            assertEquals("HIGH_CONFIDENCE", source.all[SettingsCodec.KEY_AUTOCORRECTION_MODE])
            assertEquals(true, source.all[SettingsCodec.KEY_MECHANICAL_PUNCTUATION])
            assertEquals("SUGGESTIONS", source.all[SettingsCodec.KEY_CONTEXTUAL_PUNCTUATION_MODE])
            assertEquals(true, source.all[SettingsCodec.KEY_CANDIDATE_STRIP])
            assertEquals(true, source.all[SettingsCodec.KEY_DOUBLE_SPACE_PERIOD])
            assertEquals(version, source.all[SettingsCodec.KEY_SCHEMA_VERSION])
            val result = facade.readSettings()
            assertEquals(ThemePreference.DARK, result.theme)
            assertEquals(AutocorrectionMode.OFF, result.autocorrectionMode)
            assertFalse(result.mechanicalPunctuation || result.candidateStrip || result.doubleSpacePeriod)
            assertEquals(ContextualPunctuationMode.OFF, result.contextualPunctuationMode)
        }
    }

    @Test
    fun `concurrent facades cannot overwrite an independent update from a stale migration snapshot`() {
        val source = FakeSharedPreferences(mapOf(SettingsCodec.KEY_SCHEMA_VERSION to 2))
        val first = KeyboardPreferences(source)
        val second = KeyboardPreferences(source)
        val firstRead = CountDownLatch(1)
        val releaseFirst = CountDownLatch(1)
        val secondRead = CountDownLatch(1)
        val failure = AtomicReference<Throwable>()
        source.onRead = {
            when (Thread.currentThread().name) {
                "settings-first" -> {
                    firstRead.countDown()
                    assertTrue("FIRST_WRITER_NOT_RELEASED", releaseFirst.await(3, TimeUnit.SECONDS))
                }
                "settings-second" -> secondRead.countDown()
            }
        }
        val a = Thread({ try { first.writeTheme(ThemePreference.DARK) } catch (error: Throwable) { failure.set(error) } }, "settings-first")
        val b = Thread({ try { second.writeMechanicalPunctuation(false) } catch (error: Throwable) { failure.set(error) } }, "settings-second")
        a.isDaemon = true
        b.isDaemon = true
        try {
            a.start()
            assertTrue("FIRST_SNAPSHOT_NOT_READ", firstRead.await(3, TimeUnit.SECONDS))
            b.start()
            val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(3)
            // Either B reaches its snapshot (the stale-write mutant), or the shared monitor
            // blocks it before that read. The result is ordered by observed state, not a sleep.
            while (b.state != Thread.State.BLOCKED && secondRead.count != 0L && System.nanoTime() < deadline) {
                Thread.yield()
            }
            assertTrue("SECOND_WRITER_NOT_OBSERVED", b.state == Thread.State.BLOCKED || secondRead.count == 0L)
            if (secondRead.count == 0L) b.join(2000) // Ensure stale writer finishes before A is released.
        } finally {
            releaseFirst.countDown()
            a.join(2000)
            if (b.state != Thread.State.NEW) b.join(2000)
            source.onRead = null
        }
        assertFalse(a.isAlive || b.isAlive)
        assertEquals(null, failure.get())
        assertEquals(ThemePreference.DARK, first.readSettings().theme)
        assertFalse(first.readSettings().mechanicalPunctuation)
        assertEquals(SettingsCodec.SCHEMA_VERSION, source.all[SettingsCodec.KEY_SCHEMA_VERSION])
    }

    @Test fun additionalRegistryCoversExactlyTheEighteenPersistedSettings() {
        val expected = mapOf(
            "personal_learning" to "personalLearning", "touch_personalization" to "touchPersonalization",
            "phrase_suggestions" to "phraseSuggestions", "quality_metrics" to "qualityMetrics",
            "shadow_comparison" to "shadowComparison", "word_boundary_suggestions" to "wordBoundarySuggestions",
            "abbreviations" to "abbreviations", "phrase_review" to "phraseReview", "visible_undo" to "visibleUndo",
            "protected_words" to "protectedWords", "app_profiles" to "appProfiles",
            "collect_examples" to "collectExamples", "typo_patterns" to "typoPatterns",
            "learned_ranking" to "learnedRanking", "compact_context" to "compactContext",
            "dynamic_touch" to "dynamicTouch", "dynamic_touch_apply" to "dynamicTouchApply",
            "manual_candidate_expansion" to "manualCandidateExpansion",
        )
        val registry = AdditionalFeatures.entries
        assertEquals(18, registry.size)
        assertEquals(18, registry.map { it.title }.toSet().size)
        assertEquals(expected, registry.associate { it.key to it.value.name })
        // Verify actual codec wiring, rather than trusting the property names in the registry.
        val disabled = expected.keys.associateWith { false } + (SettingsCodec.KEY_SCHEMA_VERSION to 4)
        val base = SettingsCodec.decode(disabled)
        for (feature in registry) {
            val decoded = SettingsCodec.decode(disabled + (feature.key to true))
            assertTrue(feature.value.get(decoded))
            val changedFields = KeyboardSettings::class.java.declaredFields.filter { field ->
                !java.lang.reflect.Modifier.isStatic(field.modifiers) && field.type == Boolean::class.javaPrimitiveType
            }.filter { field ->
                field.isAccessible = true
                field.getBoolean(base) != field.getBoolean(decoded)
            }.map { it.name }
            assertEquals(listOf(expected.getValue(feature.key)), changedFields)
        }
    }

    @Test fun disableAllUsesRegistryInOneTransactionAndPreservesOtherPreferences() {
        val source = FakeSharedPreferences(mapOf("future_metadata" to "keep"))
        val facade = KeyboardPreferences(source)
        AdditionalFeatures.entries.forEach { facade.writeAdditionalFeature(it.key, true) }
        facade.writeNumberRow(true)
        facade.writeEmojiKey(true)
        facade.writeAutocorrectionMode(AutocorrectionMode.SUGGESTIONS)
        val before = source.all
        var notifications = 0
        val listener = SharedPreferences.OnSharedPreferenceChangeListener { _, _ ->
            notifications++
            assertTrue(AdditionalFeatures.entries.all { source.all[it.key] == false })
        }
        facade.registerListener(listener)
        facade.disableAdditionalTyping()
        facade.unregisterListener(listener)
        assertTrue(notifications >= 18)
        val expected = before.toMutableMap().apply { AdditionalFeatures.entries.forEach { put(it.key, false) } }
        assertEquals(expected, source.all)
        assertTrue(AdditionalFeatures.entries.all { !it.value.get(facade.readSettings()) })
    }

    @Test fun additionalFeatureWriterRejectsUnknownAndCoreKeysWithoutWriting() {
        val before = store.all
        for (key in listOf("future_switch", SettingsCodec.KEY_CANDIDATE_STRIP, SettingsCodec.KEY_SCHEMA_VERSION)) {
            assertThrows(NoSuchElementException::class.java) { preferences.writeAdditionalFeature(key, true) }
            assertEquals(before, store.all)
        }
    }

    @Test fun additionalFeaturePagesAreRegistryOwnedAndStableNamesRoundTrip() {
        for (feature in AdditionalFeatures.entries) {
            assertEquals(feature.page, SettingsPage.forRow(0, feature.title))
            assertEquals(feature.page, SettingsPage.forRow(io.github.mesteriis.rune.keyboard.R.string.settings_section_tools, feature.title))
        }
        val experiments = AdditionalFeatures.entries.filter { it.page == SettingsPage.EXPERIMENTS }
        assertEquals(setOf("wordBoundarySuggestions", "phraseReview", "learnedRanking", "compactContext",
            "dynamicTouch", "dynamicTouchApply", "manualCandidateExpansion"), experiments.map { it.value.name }.toSet())
        for (page in SettingsPage.entries) assertEquals(page, SettingsPage.fromName(page.name))
        assertEquals(SettingsPage.EXPERIMENTS, SettingsPage.forRow(0, io.github.mesteriis.rune.keyboard.R.string.controls_disable_all))
        assertEquals(SettingsPage.APPEARANCE, SettingsPage.fromName("APPEARANCE"))
        assertEquals(SettingsPage.TYPING, SettingsPage.fromName("TYPING"))
    }

    @Test fun candidateDisplayDependenciesMatchSettingsWithoutClearingSavedChoices() {
        val hidden = KeyboardSettings.DEFAULT.copy(candidateStrip = false)
        val display = setOf("phraseSuggestions", "wordBoundarySuggestions", "abbreviations", "phraseReview",
            "visibleUndo", "learnedRanking", "compactContext", "manualCandidateExpansion")
        for (feature in AdditionalFeatures.entries) {
            val reason = feature.unavailableReason(hidden)
            if (feature.value.name in display) assertEquals(io.github.mesteriis.rune.keyboard.R.string.feature_requires_candidate_strip, reason)
            else if (feature.value.name != "dynamicTouchApply") assertEquals(null, reason)
        }
        val source = FakeSharedPreferences(mapOf(SettingsCodec.KEY_SCHEMA_VERSION to 4,
            SettingsCodec.KEY_CANDIDATE_STRIP to false, SettingsCodec.KEY_LEARNED_RANKING to true))
        val facade = KeyboardPreferences(source)
        val before = source.all
        val feature = AdditionalFeatures.forKey(SettingsCodec.KEY_LEARNED_RANKING)
        assertTrue(feature.value.get(facade.readSettings()))
        assertEquals(io.github.mesteriis.rune.keyboard.R.string.feature_requires_candidate_strip, feature.unavailableReason(facade.readSettings()))
        assertEquals(before, source.all)
        facade.writeCandidateStrip(true)
        assertEquals(null, feature.unavailableReason(facade.readSettings()))
        assertTrue(feature.value.get(facade.readSettings()))
    }

    @Test fun russianExperimentsRequireAnEnabledRussianLanguageAndApplyRequiresShadow() {
        val english = KeyboardSettings.DEFAULT.copy(enabledLanguages = listOf(KeyboardLanguage.ENGLISH), candidateStrip = true)
        for (feature in AdditionalFeatures.entries) {
            if (feature.russianOnly) assertEquals(io.github.mesteriis.rune.keyboard.R.string.feature_requires_russian, feature.unavailableReason(english))
            else assertEquals(null, feature.unavailableReason(english))
        }
        val apply = AdditionalFeatures.forKey(SettingsCodec.KEY_DYNAMIC_TOUCH_APPLY)
        assertEquals(io.github.mesteriis.rune.keyboard.R.string.feature_requires_dynamic_touch, apply.unavailableReason(KeyboardSettings.DEFAULT))
        assertEquals(null, apply.unavailableReason(KeyboardSettings.DEFAULT.copy(dynamicTouch = true, candidateStrip = false)))
    }

    @Test fun collectionAndPatternLearningRemainIndependentForAllLanguages() {
        for (language in KeyboardLanguage.entries) for (collect in listOf(false, true)) for (patterns in listOf(false, true)) {
            val settings = KeyboardSettings.DEFAULT.copy(enabledLanguages = listOf(language), candidateStrip = false,
                collectExamples = collect, typoPatterns = patterns)
            for (key in listOf(SettingsCodec.KEY_COLLECT_EXAMPLES, SettingsCodec.KEY_TYPO_PATTERNS)) {
                assertEquals(null, AdditionalFeatures.forKey(key).unavailableReason(settings))
            }
        }
    }

    private class FakeSharedPreferences(initial: Map<String, Any?> = emptyMap()) : SharedPreferences {
        private val values = initial.toMutableMap()
        private val listeners = mutableSetOf<SharedPreferences.OnSharedPreferenceChangeListener>()

        @Volatile var onRead: (() -> Unit)? = null

        override fun getAll(): MutableMap<String, *> {
            val snapshot = values.toMutableMap()
            onRead?.invoke()
            return snapshot
        }

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
