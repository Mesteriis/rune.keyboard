package io.github.mesteriis.rune.keyboard.ime

import android.content.SharedPreferences
import android.content.res.Configuration
import android.inputmethodservice.InputMethodService
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.text.InputType
import android.view.View
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.editor.EditorCommandExecutor
import io.github.mesteriis.rune.keyboard.ime.editor.DeleteMode
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
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingEdit
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.AndroidLazyPackedLexicons
import io.github.mesteriis.rune.keyboard.smarttyping.session.CandidateOwnerState
import io.github.mesteriis.rune.keyboard.smarttyping.session.LocalCandidateCoordinator
import io.github.mesteriis.rune.keyboard.smarttyping.android.AndroidModelCandidates
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingSessionController
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingTextResult
import io.github.mesteriis.rune.keyboard.smarttyping.ui.SmartTypingViewState
import java.util.concurrent.Executor

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
    private val typingSession = TypingSessionController()
    private lateinit var candidates: LocalCandidateCoordinator
    private var inputViewActive = false

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
        val mainHandler = Handler(Looper.getMainLooper())
        candidates = LocalCandidateCoordinator(
            typingSession,
            AndroidLazyPackedLexicons.create(applicationContext.assets),
            Executor { action -> check(mainHandler.post(action)) { "Candidate owner dispatcher stopped" } },
            ::candidateOwnerState,
            ::renderCandidates,
            AndroidModelCandidates.create(applicationContext, typingSession, ::candidateOwnerState, ::renderCandidates),
        )
        keyboardPreferences.registerListener(preferencesListener)
    }

    override fun onDestroy() {
        inputViewActive = false
        candidates.close()
        typingSession.endSession()
        keyboardView?.updateCandidates(SmartTypingViewState.HIDDEN)
        keyboardPreferences.unregisterListener(preferencesListener)
        keyboardView = null
        super.onDestroy()
    }

    override fun onCreateInputView(): View {
        return RuneTrace.section("Rune#createInputView") {
            val themedContext = ThemeOverride.themedContext(this, settings.theme)
            RuneKeyboardView(themedContext, buildMetrics(themedContext)).also { view ->
                keyboardView = view
                view.setOnActionListener(::handleAction)
                view.setOnCandidateSelectedListener(::handleCandidateSelection)
                renderKeyboard()
            }
        }
    }

    override fun onStartInput(attribute: EditorInfo?, restarting: Boolean) {
        keyboardView?.cancelActiveTouches()
        inputViewActive = false
        candidates.invalidate()
        super.onStartInput(attribute, restarting)
        val editorInfo = attribute ?: EditorInfo()
        editorContext = EditorContext.from(editorInfo)
        hasSelection = editorInfo.initialSelStart >= 0 &&
            editorInfo.initialSelEnd >= 0 &&
            editorInfo.initialSelStart != editorInfo.initialSelEnd
        // Restart preserves displayed editor text and visual state, never an old composing buffer.
        typingSession.startSession(editorContext, editorInfo.initialSelStart, editorInfo.initialSelEnd)
        state = KeyboardSessionPolicy.onStartInput(
            previous = state,
            restarting = restarting,
            settings = settings,
            lastUsedLanguage = selectedLanguage,
        )
        selectedLanguage = state.language
        renderCandidates()
    }

    override fun onStartInputView(info: EditorInfo?, restarting: Boolean) {
        super.onStartInputView(info, restarting)
        if (info != null) editorContext = EditorContext.from(info)
        inputViewActive = true
        candidates.invalidate()
        if (!editorContext.supportsSmartTyping) typingSession.endSession()
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
        val externalChange = typingSession.updateSelection(
            newSelStart, newSelEnd, candidatesStart, candidatesEnd, ::executeTypingEdit,
        )
        if (externalChange) candidates.invalidate()
        renderCandidates()
        refreshAutomaticCapitalization()
    }

    override fun onFinishInputView(finishingInput: Boolean) {
        keyboardView?.cancelActiveTouches()
        inputViewActive = false
        candidates.invalidate()
        typingSession.invalidate(::executeTypingEdit)
        if (finishingInput) typingSession.endSession()
        renderCandidates()
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
        inputViewActive = false
        candidates.invalidate()
        typingSession.finishComposition(::executeTypingEdit)
        typingSession.endSession()
        renderCandidates()
        hasSelection = false
        super.onFinishInput()
    }

    override fun onEvaluateFullscreenMode(): Boolean = false

    override fun onConfigurationChanged(newConfig: Configuration) {
        candidates.invalidate()
        typingSession.invalidate(::executeTypingEdit)
        super.onConfigurationChanged(newConfig)
    }

    private fun handleAction(action: KeyboardAction) {
        RuneTrace.section("Rune#touchUpDispatch") {
            val previousState = state
            if (invalidatesTyping(action)) candidates.invalidate()
            if (action is KeyboardAction.MoveCursor || action == KeyboardAction.Enter) {
                typingSession.awaitEditorSelection(::executeTypingEdit)
            } else if (invalidatesTyping(action)) {
                typingSession.invalidate(::executeTypingEdit)
            }
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

            val outcome = transition.command?.let { executeTypingOrEditorCommand(it, previousState) }
                ?: CommandOutcome.NO_COMMAND
            if (outcome == CommandOutcome.DELIVERED && typingSession.sentenceCapitalizationPending) {
                // The gesture consumed this action. Prime the next key from the post-action state.
                state = state.withAutomaticCapitalization(editorContext.supportsAutomaticCapitalization &&
                    state.layer == KeyboardLayer.LETTERS)
            }
            val stateChanged = state != previousState
            provideFeedback(action, stateChanged, outcome)
            if (stateChanged) renderKeyboard() else renderCandidates()

            if (mutatesText(transition.command)) {
                keyboardView?.post(::refreshAutomaticCapitalization)
            }
        }
    }

    private fun invalidatesTyping(action: KeyboardAction): Boolean = when (action) {
        KeyboardAction.Enter,
        KeyboardAction.ToggleSymbols,
        KeyboardAction.ToggleSymbolsPage,
        KeyboardAction.CursorModeStarted,
        KeyboardAction.HideKeyboard,
        KeyboardAction.NextInputMethod,
        is KeyboardAction.SwitchLanguage,
        is KeyboardAction.MoveCursor,
        -> true
        else -> false
    }

    private fun executeTypingOrEditorCommand(command: EditorCommand, beforeAction: KeyboardState): CommandOutcome {
        val punctuation = MechanicalPunctuationPolicy(editorContext.inputPolicy, editorContext.mode,
            editorContext.requiresRawKeyEvents, settings.mechanicalPunctuation, settings.doubleSpacePeriod)
        val result = if (command is EditorCommand.CommitText || command == EditorCommand.DeletePreviousCodePoint ||
            command == EditorCommand.ConvertPrecedingSpaceToPeriod) {
            candidates.edit {
                when (command) {
                    is EditorCommand.CommitText -> typingSession.typeText(command.value, punctuation, beforeAction,
                        execute = ::executeTypingEdit)
                    EditorCommand.DeletePreviousCodePoint -> typingSession.deletePrevious(::executeTypingEdit)
                    EditorCommand.ConvertPrecedingSpaceToPeriod -> typingSession.typeText(" ", punctuation,
                        beforeAction, doubleSpaceGesture = true, execute = ::executeTypingEdit)
                    else -> TypingTextResult.BYPASS
                }
            }
        } else TypingTextResult.BYPASS
        return when (result) {
            TypingTextResult.HANDLED -> CommandOutcome.DELIVERED
            TypingTextResult.REJECTED -> CommandOutcome.DROPPED
            TypingTextResult.BYPASS -> executeCommand(
                if (command == EditorCommand.ConvertPrecedingSpaceToPeriod) EditorCommand.CommitText(" ") else command,
            )
        }
    }

    private fun executeTypingEdit(edit: TypingEdit): Boolean = RuneTrace.section("Rune#composeUpdate") {
        executeCommand(
            when (edit) {
                is TypingEdit.SetComposingText -> EditorCommand.SetComposingText(edit.value)
                is TypingEdit.CommitText -> EditorCommand.CommitText(edit.value)
                TypingEdit.FinishComposingText -> EditorCommand.FinishComposingText
            },
        ) == CommandOutcome.DELIVERED
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
        val result = RuneTrace.section("Rune#editorCommand") {
            EditorCommandExecutor.execute(
                command = command,
                inputConnection = connection,
                hasSelection = hasSelection,
                inputPolicy = editorContext.inputPolicy,
                deleteMode = when {
                    editorContext.requiresRawKeyEvents -> DeleteMode.RAW_KEY_EVENT
                    editorContext.inputPolicy == io.github.mesteriis.rune.keyboard.ime.model.InputPolicy.SENSITIVE -> {
                        DeleteMode.CODE_POINT
                    }
                    else -> DeleteMode.GRAPHEME_AWARE
                },
            )
        }
        if (result.clearsSelection) {
            hasSelection = false
        }
        return if (result.handled) CommandOutcome.DELIVERED else CommandOutcome.DROPPED
    }

    private fun mutatesText(command: EditorCommand?): Boolean = when (command) {
        is EditorCommand.CommitText,
        is EditorCommand.SetComposingText,
        EditorCommand.DeletePreviousCodePoint,
        EditorCommand.InsertNewline,
        EditorCommand.ConvertPrecedingSpaceToPeriod,
        -> true
        else -> false
    }

    private fun onSettingsChanged() {
        RuneTrace.section("Rune#applySettings") {
            val previous = settings
            settings = keyboardPreferences.readSettings()
            state = state
                .withEnabledLanguages(settings.enabledLanguages)
                .copy(doubleSpacePeriodEnabled = settings.doubleSpacePeriod)
            if (settings.mechanicalPunctuation != previous.mechanicalPunctuation ||
                settings.doubleSpacePeriod != previous.doubleSpacePeriod
            ) {
                typingSession.discardUndo()
                candidates.invalidate()
            }
            if (settings.autocorrectionMode != previous.autocorrectionMode ||
                settings.candidateStrip != previous.candidateStrip
            ) candidates.invalidate()
            if (settings.enabledLanguages != previous.enabledLanguages) candidates.invalidate()
            if (state.language != selectedLanguage) {
                candidates.invalidate()
                typingSession.invalidate(::executeTypingEdit)
                selectedLanguage = state.language
                keyboardPreferences.writeLanguage(selectedLanguage)
            }
            if (settings.affectsKeyboardView(previous)) {
                recreateInputView()
            } else if (settings.enabledLanguages != previous.enabledLanguages) {
                renderKeyboard()
            } else {
                // Nonvisual settings update the cached action policy, not existing key views.
                renderCandidates()
            }
        }
    }

    private fun recreateInputView() {
        if (keyboardView == null) return
        RuneTrace.section("Rune#recreateInputView") {
            keyboardView?.cancelActiveTouches()
            setInputView(onCreateInputView())
        }
    }

    private fun refreshAutomaticCapitalization() {
        val updatedState = withAutomaticCapitalization(state)
        if (updatedState != state) {
            state = updatedState
            renderKeyboard()
        }
    }

    private fun withAutomaticCapitalization(candidate: KeyboardState): KeyboardState =
        KeyboardSessionPolicy.withAutomaticCapitalization(
            state = candidate,
            editor = editorContext,
            hasComposingWord = !typingSession.state.composing?.typedWord.isNullOrEmpty(),
            ownedSentenceBoundary = typingSession.sentenceCapitalizationPending,
        ) { currentInputConnection?.getCursorCapsMode(editorContext.inputType) }

    private fun renderKeyboard() {
        val view = keyboardView ?: return
        view.setPopupPolicy(
            previewEnabled = settings.keyPreview,
            inputPolicy = editorContext.inputPolicy,
        )
        val layout = RuneTrace.section("Rune#layoutFor") {
            layoutProvider.layoutFor(
                state = state,
                editorContext = editorContext,
                options = LayoutOptions(showNumberRow = settings.numberRow),
            )
        }
        view.render(layout, state)
        renderCandidates()
    }

    private fun handleCandidateSelection(id: String) {
        candidates.selectCandidate(id, ::executeTypingEdit)
        renderCandidates()
    }

    private fun candidateOwnerState() = CandidateOwnerState(
        editorAllowsSmartTyping = editorContext.supportsSmartTyping,
        inputViewActive = inputViewActive,
        layer = state.layer,
        language = state.language,
        hasSelection = hasSelection,
        autocorrectionMode = settings.autocorrectionMode,
        candidateStripEnabled = settings.candidateStrip,
    )

    private fun renderCandidates() {
        val view = keyboardView ?: return
        view.updateCandidates(candidates.viewState)
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
        if (action is KeyboardAction.MoveCursor || action == KeyboardAction.CursorModeStarted) return
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
