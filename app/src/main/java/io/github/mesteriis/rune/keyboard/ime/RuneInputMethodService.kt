package io.github.mesteriis.rune.keyboard.ime

import android.content.SharedPreferences
import android.content.res.Configuration
import android.inputmethodservice.InputMethodService
import android.os.Build
import android.os.SystemClock
import android.text.InputType
import android.view.View
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.editor.EditorCommandExecutor
import io.github.mesteriis.rune.keyboard.ime.feedback.CommandOutcome
import io.github.mesteriis.rune.keyboard.ime.feedback.FeedbackController
import io.github.mesteriis.rune.keyboard.ime.feedback.FeedbackPolicy
import io.github.mesteriis.rune.keyboard.ime.layout.KeyboardLayoutProvider
import io.github.mesteriis.rune.keyboard.ime.layout.LayoutOptions
import io.github.mesteriis.rune.keyboard.ime.model.EditorCommand
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLayer
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardReducer
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardSessionPolicy
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState
import io.github.mesteriis.rune.keyboard.ime.ui.RuneKeyboardView
import io.github.mesteriis.rune.keyboard.settings.GapPreset
import io.github.mesteriis.rune.keyboard.settings.KeyboardMetrics
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences
import io.github.mesteriis.rune.keyboard.settings.KeyboardSettings
import io.github.mesteriis.rune.keyboard.settings.KeyboardViewMetrics
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import io.github.mesteriis.rune.keyboard.settings.SizeBucket
import io.github.mesteriis.rune.keyboard.settings.ThemeOverride

class RuneInputMethodService : InputMethodService() {
    private val layoutProvider = KeyboardLayoutProvider()
    private lateinit var feedbackController: FeedbackController
    private lateinit var keyboardPreferences: KeyboardPreferences
    private var keyboardView: RuneKeyboardView? = null
    private var editorContext = EditorContext.from(InputType.TYPE_CLASS_TEXT, EditorInfo.IME_ACTION_NONE)
    private var settings = KeyboardSettings.DEFAULT
    private var state = KeyboardState.initial(KeyboardLanguage.ENGLISH, automaticCapitalization = false)
    private var selectedLanguage = KeyboardLanguage.ENGLISH
    private var hasSelection = false

    // Held in a field on purpose: SharedPreferences keeps registered listeners weakly.
    private val preferencesListener = SharedPreferences.OnSharedPreferenceChangeListener { _, key ->
        // The last-used language and the schema stamp are written by the keyboard itself; reacting
        // to them would re-enter handleAction on every language swipe.
        if (key != SettingsCodec.KEY_LANGUAGE && key != SettingsCodec.KEY_SCHEMA_VERSION) {
            onSettingsChanged()
        }
    }

    override fun onCreate() {
        super.onCreate()
        feedbackController = FeedbackController(this)
        keyboardPreferences = KeyboardPreferences(this)
        settings = keyboardPreferences.readSettings()
        selectedLanguage = KeyboardSessionPolicy.resolveStartLanguage(
            settings = settings,
            lastUsedLanguage = keyboardPreferences.readLanguage(),
        )
        state = KeyboardState.initial(
            language = selectedLanguage,
            automaticCapitalization = false,
            enabledLanguages = settings.enabledLanguages,
            doubleSpacePeriodEnabled = settings.doubleSpacePeriod,
        )
        keyboardPreferences.registerListener(preferencesListener)
    }

    override fun onDestroy() {
        keyboardPreferences.unregisterListener(preferencesListener)
        keyboardView = null
        super.onDestroy()
    }

    override fun onCreateInputView(): View {
        val themedContext = ThemeOverride.themedContext(this, settings.theme)
        return RuneKeyboardView(themedContext, buildMetrics(themedContext)).also { view ->
            keyboardView = view
            view.setOnActionListener(::handleAction)
            renderKeyboard()
        }
    }

    override fun onStartInput(attribute: EditorInfo?, restarting: Boolean) {
        keyboardView?.cancelActiveTouches()
        super.onStartInput(attribute, restarting)
        val editorInfo = attribute ?: EditorInfo()
        editorContext = EditorContext.from(editorInfo)
        hasSelection = editorInfo.initialSelStart >= 0 &&
            editorInfo.initialSelEnd >= 0 &&
            editorInfo.initialSelStart != editorInfo.initialSelEnd
        state = KeyboardSessionPolicy.onStartInput(
            previous = state,
            restarting = restarting,
            settings = settings,
            lastUsedLanguage = selectedLanguage,
        )
        selectedLanguage = state.language
    }

    override fun onStartInputView(info: EditorInfo?, restarting: Boolean) {
        super.onStartInputView(info, restarting)
        if (info != null) editorContext = EditorContext.from(info)
        state = withAutomaticCapitalization(state)
        renderKeyboard()
    }

    override fun onUpdateSelection(
        oldSelStart: Int,
        oldSelEnd: Int,
        newSelStart: Int,
        newSelEnd: Int,
        candidatesStart: Int,
        candidatesEnd: Int,
    ) {
        super.onUpdateSelection(
            oldSelStart,
            oldSelEnd,
            newSelStart,
            newSelEnd,
            candidatesStart,
            candidatesEnd,
        )
        hasSelection = newSelStart >= 0 && newSelEnd >= 0 && newSelStart != newSelEnd
        refreshAutomaticCapitalization()
    }

    override fun onFinishInputView(finishingInput: Boolean) {
        keyboardView?.cancelActiveTouches()
        super.onFinishInputView(finishingInput)
    }

    /**
     * State is deliberately not reset here. A fold, unfold or rotation can interleave
     * onFinishInput with a restarting onStartInput for the same editor; making
     * `onStartInput(restarting = false)` the only reset point is what preserves shift, caps lock
     * and the active layer across those transitions (FOLD-003).
     */
    override fun onFinishInput() {
        keyboardView?.cancelActiveTouches()
        hasSelection = false
        super.onFinishInput()
    }

    override fun onEvaluateFullscreenMode(): Boolean = false

    private fun handleAction(action: KeyboardAction) {
        val previousState = state
        val transition = KeyboardReducer.reduce(
            state = state,
            action = action,
            editorContext = editorContext,
            nowMillis = SystemClock.uptimeMillis(),
        )
        state = transition.state
        if (action is KeyboardAction.SwitchLanguage) {
            if (state.language != previousState.language) {
                selectedLanguage = state.language
                keyboardPreferences.writeLanguage(selectedLanguage)
                keyboardView?.showLanguagePreview(state.language.displayLabel)
            }
            state = withAutomaticCapitalization(state)
        } else if (action == KeyboardAction.ToggleSymbols && state.layer == KeyboardLayer.LETTERS) {
            state = withAutomaticCapitalization(state)
        }

        val outcome = transition.command?.let(::executeCommand) ?: CommandOutcome.NO_COMMAND
        val stateChanged = state != previousState
        provideFeedback(action, stateChanged, outcome)
        if (stateChanged) renderKeyboard()

        if (mutatesText(transition.command)) {
            keyboardView?.post(::refreshAutomaticCapitalization)
        }
    }

    private fun executeCommand(command: EditorCommand): CommandOutcome {
        when (command) {
            EditorCommand.SwitchToNextInputMethod -> {
                switchToNextInputMethodOrShowPicker()
                return CommandOutcome.DELIVERED
            }
            EditorCommand.HideKeyboard -> {
                requestHideSelf(0)
                return CommandOutcome.DELIVERED
            }
            else -> Unit
        }
        val connection = currentInputConnection ?: return CommandOutcome.DROPPED
        val result = EditorCommandExecutor.execute(
            command = command,
            inputConnection = connection,
            hasSelection = hasSelection,
            requiresRawKeyEvents = editorContext.requiresRawKeyEvents,
        )
        if (result.clearsSelection) {
            hasSelection = false
        }
        return if (result.handled) CommandOutcome.DELIVERED else CommandOutcome.DROPPED
    }

    private fun mutatesText(command: EditorCommand?): Boolean = when (command) {
        is EditorCommand.CommitText,
        EditorCommand.DeletePreviousCodePoint,
        EditorCommand.InsertNewline,
        EditorCommand.ConvertPrecedingSpaceToPeriod,
        EditorCommand.RevertDoubleSpacePeriod,
        -> true
        else -> false
    }

    private fun onSettingsChanged() {
        val previous = settings
        settings = keyboardPreferences.readSettings()
        state = state
            .withEnabledLanguages(settings.enabledLanguages)
            .copy(doubleSpacePeriodEnabled = settings.doubleSpacePeriod)
        if (state.language != selectedLanguage) {
            selectedLanguage = state.language
            keyboardPreferences.writeLanguage(selectedLanguage)
        }
        if (settings.affectsKeyboardView(previous)) {
            recreateInputView()
        } else {
            renderKeyboard()
        }
    }

    private fun recreateInputView() {
        if (keyboardView == null) return
        keyboardView?.cancelActiveTouches()
        setInputView(onCreateInputView())
    }

    private fun refreshAutomaticCapitalization() {
        val updatedState = withAutomaticCapitalization(state)
        if (updatedState != state) {
            state = updatedState
            renderKeyboard()
        }
    }

    private fun withAutomaticCapitalization(candidate: KeyboardState): KeyboardState {
        if (!editorContext.supportsAutomaticCapitalization || candidate.layer != KeyboardLayer.LETTERS) {
            return candidate
        }
        val connection = currentInputConnection ?: return candidate
        val shouldCapitalize = connection.getCursorCapsMode(editorContext.inputType) != 0
        return candidate.withAutomaticCapitalization(shouldCapitalize)
    }

    private fun renderKeyboard() {
        val view = keyboardView ?: return
        view.setPopupPolicy(
            previewEnabled = settings.keyPreview,
            inputPolicy = editorContext.inputPolicy,
        )
        view.render(
            layoutProvider.layoutFor(
                state = state,
                editorContext = editorContext,
                options = LayoutOptions(showNumberRow = settings.numberRow),
            ),
            state,
        )
    }

    private fun buildMetrics(themedContext: android.content.Context): KeyboardViewMetrics {
        val resources = themedContext.resources
        val configuration = resources.configuration
        val bucket = SizeBucket.resolve(
            smallestScreenWidthDp = configuration.smallestScreenWidthDp,
            isLandscape = configuration.orientation == Configuration.ORIENTATION_LANDSCAPE,
        )
        val baseHeightPx = resources.getDimensionPixelSize(R.dimen.keyboard_key_height)
        val gapResource = when (settings.keyGap) {
            GapPreset.TIGHT -> R.dimen.keyboard_key_gap_tight
            GapPreset.NORMAL -> R.dimen.keyboard_key_gap
            GapPreset.WIDE -> R.dimen.keyboard_key_gap_wide
        }
        return KeyboardViewMetrics(
            keyHeightPx = KeyboardMetrics.keyHeightPx(baseHeightPx, settings.heightPreset(bucket)),
            keyGapPx = resources.getDimensionPixelSize(gapResource),
        )
    }

    private fun switchToNextInputMethodOrShowPicker() {
        val switched = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P &&
            shouldOfferSwitchingToNextInputMethod()
        ) {
            switchToNextInputMethod(false)
        } else {
            false
        }
        if (!switched) {
            getSystemService(InputMethodManager::class.java).showInputMethodPicker()
        }
    }

    private fun provideFeedback(
        action: KeyboardAction,
        stateChanged: Boolean,
        outcome: CommandOutcome,
    ) {
        // Cursor mode emits a step per movement; the space key gives one buzz when it engages.
        if (action is KeyboardAction.MoveCursor) return
        val view = keyboardView ?: return
        if (!FeedbackPolicy.shouldProvide(stateChanged, outcome)) return
        feedbackController.provide(
            view = view,
            action = action,
            hapticMode = settings.hapticMode,
            soundMode = settings.soundMode,
        )
    }
}
