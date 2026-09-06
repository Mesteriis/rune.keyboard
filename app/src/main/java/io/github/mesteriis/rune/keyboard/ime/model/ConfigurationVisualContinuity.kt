package io.github.mesteriis.rune.keyboard.ime.model

import io.github.mesteriis.rune.keyboard.settings.KeyboardSettings

internal data class ConfigurationSize(val widthDp: Int, val heightDp: Int, val smallestWidthDp: Int)

internal data class VisualEditorIdentity(
    val packageName: String,
    val fieldId: Int,
    val inputType: Int,
    val imeOptions: Int,
)

/**
 * One bounded, memory-only visual handoff for an editor recreated by configuration change.
 * Metadata is not a universal logical-editor ID: screens reusing identical metadata can collide.
 * Never retain text, candidates, composing ownership, selection, or gesture timing here.
 */
internal class ConfigurationVisualContinuity(initialConfiguration: ConfigurationSize) {
    private var lastConfiguration = initialConfiguration
    private var lastEditor: VisualEditorIdentity? = null
    private var pending: Pending? = null

    fun onConfigurationChanged(configuration: ConfigurationSize, previous: KeyboardState, nowMillis: Long) {
        if (configuration == lastConfiguration) return
        lastConfiguration = configuration
        pending = lastEditor?.takeIf {
            it.fieldId > 0 && configuration.widthDp > 0 && configuration.heightDp > 0
        }?.let {
            // Capture explicit OFF intent through the state's side-effect-free caps policy.
            // The original KeyboardState (including its private tap timestamp) is not retained.
            val manualOff = previous.shiftMode == ShiftMode.OFF &&
                previous.withAutomaticCapitalization(true).shiftMode == ShiftMode.OFF
            Pending(it, VisualState(previous.language, previous.layer, previous.shiftMode, manualOff), nowMillis)
        }
    }

    /** User actions/settings changes end the handoff, without changing generation deduplication. */
    fun invalidate() {
        pending = null
    }

    internal fun hasPendingHandoff(): Boolean = pending != null

    fun onStartInput(
        previous: KeyboardState,
        restarting: Boolean,
        settings: KeyboardSettings,
        lastUsedLanguage: KeyboardLanguage?,
        editor: VisualEditorIdentity?,
        configuration: ConfigurationSize,
        nowMillis: Long,
    ): KeyboardState {
        // Resources may already have changed when start arrives before onConfigurationChanged.
        // Observing the same generation later must not rearm a consumed visual handoff.
        onConfigurationChanged(configuration, previous, nowMillis)
        val identity = editor?.takeIf { it.packageName.isNotBlank() && it.fieldId > 0 }
        val candidate = pending
        val matches = candidate != null && identity != null &&
            identity.packageName == candidate.editor.packageName &&
            identity.fieldId == candidate.editor.fieldId &&
            nowMillis >= candidate.armedAtMillis && nowMillis - candidate.armedAtMillis < 5_000L
        if (!matches || !restarting) pending = null
        lastEditor = identity
        if (matches && !restarting) {
            val visual = checkNotNull(candidate).visual
            return KeyboardState(
                language = visual.language.takeIf { it in settings.enabledLanguages }
                    ?: settings.enabledLanguages.first(),
                enabledLanguages = settings.enabledLanguages,
                layer = if (visual.language in settings.enabledLanguages) visual.layer else KeyboardLayer.LETTERS,
                // AUTO belongs to the new editor's caps policy; manual state is visual intent.
                shiftMode = visual.shiftMode.takeUnless { it == ShiftMode.AUTO } ?: ShiftMode.OFF,
                doubleSpacePeriodEnabled = settings.doubleSpacePeriod,
                automaticCapitalizationSuppressed = visual.manualOff &&
                    visual.language in settings.enabledLanguages,
            )
        }
        return KeyboardSessionPolicy.onStartInput(previous, restarting, settings, lastUsedLanguage)
    }

    private data class VisualState(
        val language: KeyboardLanguage,
        val layer: KeyboardLayer,
        val shiftMode: ShiftMode,
        val manualOff: Boolean,
    )

    private data class Pending(
        val editor: VisualEditorIdentity,
        val visual: VisualState,
        val armedAtMillis: Long,
    )
}

/**
 * Holds one already-armed visual-only handoff while Android replaces an IME service for a
 * configuration transition. It contains no editor text, composing state, selection, candidates
 * or timing from keystrokes. A normal service destroy clears the retained tracker immediately.
 */
internal class ConfigurationVisualContinuityStore {
    private var tracker: ConfigurationVisualContinuity? = null

    fun attach(initialConfiguration: ConfigurationSize): ConfigurationVisualContinuity =
        tracker ?: ConfigurationVisualContinuity(initialConfiguration).also { tracker = it }

    fun detach(instance: ConfigurationVisualContinuity) {
        if (tracker === instance && !instance.hasPendingHandoff()) tracker = null
    }
}
