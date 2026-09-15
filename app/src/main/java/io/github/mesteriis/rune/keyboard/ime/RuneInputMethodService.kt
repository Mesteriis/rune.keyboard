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
import io.github.mesteriis.rune.keyboard.ime.model.ConfigurationSize
import io.github.mesteriis.rune.keyboard.ime.model.ConfigurationVisualContinuity
import io.github.mesteriis.rune.keyboard.ime.model.ConfigurationVisualContinuityStore
import io.github.mesteriis.rune.keyboard.ime.model.VisualEditorIdentity
import io.github.mesteriis.rune.keyboard.ime.ui.RuneKeyboardView
import io.github.mesteriis.rune.keyboard.settings.GapPreset
import io.github.mesteriis.rune.keyboard.settings.KeyboardMetrics
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences
import io.github.mesteriis.rune.keyboard.settings.KeyboardSettings
import io.github.mesteriis.rune.keyboard.settings.KeyboardViewMetrics
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import io.github.mesteriis.rune.keyboard.settings.SizeBucket
import io.github.mesteriis.rune.keyboard.settings.ThemeOverride
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessHint
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingEdit
import io.github.mesteriis.rune.keyboard.smarttyping.punctuation.MechanicalPunctuationPolicy
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.AndroidLazyPackedLexicons
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.AndroidCanonicalCaseLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.session.CandidateOwnerState
import io.github.mesteriis.rune.keyboard.smarttyping.session.LocalCandidateCoordinator
import io.github.mesteriis.rune.keyboard.smarttyping.android.AndroidModelCandidates
import io.github.mesteriis.rune.keyboard.smarttyping.correction.ModelRuntimeQualification
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingSessionController
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingTextResult
import io.github.mesteriis.rune.keyboard.smarttyping.ui.SmartTypingViewState
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.SmartTypingTraceSection
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.TypingDiagnosticsProvider
import java.util.concurrent.Executor
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingFeaturePolicy
import io.github.mesteriis.rune.keyboard.smarttyping.session.AndroidTypingTools
import io.github.mesteriis.rune.keyboard.smarttyping.abbreviations.AbbreviationStore
import io.github.mesteriis.rune.keyboard.smarttyping.quality.QualityStore
import io.github.mesteriis.rune.keyboard.smarttyping.diagnostics.DiagnosticFeatures
import io.github.mesteriis.rune.keyboard.smarttyping.experiments.AndroidExperimentResources
import io.github.mesteriis.rune.keyboard.smarttyping.touch.DynamicTouchContext
import io.github.mesteriis.rune.keyboard.smarttyping.touch.DynamicTouchResolver
import io.github.mesteriis.rune.keyboard.smarttyping.touch.PhysicalTouchSample
import io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem
import io.github.mesteriis.rune.keyboard.smarttyping.controls.TypingProfile
import io.github.mesteriis.rune.keyboard.smarttyping.controls.TypingProfileResolver
import io.github.mesteriis.rune.keyboard.smarttyping.controls.TypingControlSnapshot
import io.github.mesteriis.rune.keyboard.smarttyping.controls.TypingControlStore
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingResources
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.AndroidTypingPersonalization

class RuneInputMethodService : InputMethodService() {
    private val layoutProvider = KeyboardLayoutProvider()
    private lateinit var feedbackController: FeedbackController
    private lateinit var keyboardPreferences: KeyboardPreferences
    private var keyboardView: RuneKeyboardView? = null
    private var editorContext = EditorContext.from(InputType.TYPE_CLASS_TEXT, EditorInfo.IME_ACTION_NONE)
    private var settings = KeyboardSettings.DEFAULT
    private var globalSettings = KeyboardSettings.DEFAULT
    private var activePackage: String? = null
    private var activeProfile = TypingProfile.DEFAULT
    private var appliedControls: TypingControlSnapshot? = null
    private var serviceDestroyed = false
    private var state = KeyboardState.initial(KeyboardLanguage.ENGLISH, automaticCapitalization = false)
    private var selectedLanguage = KeyboardLanguage.ENGLISH
    private var hasSelection = false
    private val typingSession = TypingSessionController(RuneTrace)
    private lateinit var personalResources: PersonalTypingResources
    private lateinit var personalization: AndroidTypingPersonalization
    private lateinit var typingTools: AndroidTypingTools
    private lateinit var abbreviationStore: AbbreviationStore
    private lateinit var qualityStore: QualityStore
    private var timedUndoId: String? = null
    private var physicalLetterPending = false
    private val dynamicTouchContext = DynamicTouchContext()
    private var experimentReadySubscription: java.io.Closeable? = null
    private lateinit var candidates: LocalCandidateCoordinator
    private var inputViewActive = false
    private lateinit var visualContinuity: ConfigurationVisualContinuity

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
        visualContinuity = visualContinuityStore.attach(configurationSize(resources.configuration))
        try { typingSession.setDiagnostics(TypingDiagnosticsProvider.create(this)) } catch (_: Throwable) { }
        feedbackController = FeedbackController(this)
        keyboardPreferences = KeyboardPreferences(this)
        globalSettings = keyboardPreferences.readSettings()
        settings = globalSettings
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
        personalResources = PersonalTypingResources.get(this)
        personalization = AndroidTypingPersonalization(personalResources)
        typingSession.setPersonalization(personalization, state.language)
        abbreviationStore = AbbreviationStore.get(this)
        qualityStore = QualityStore.get(this)
        typingTools = AndroidTypingTools(personalResources, abbreviationStore)
        typingSession.setTypingTools(typingTools)
        typingSession.setQualityRecorder(qualityStore)
        typingSession.configureFeatures(DiagnosticFeatures.configured(globalSettings), 0, activeProfile.code)
        val mainHandler = Handler(Looper.getMainLooper())
        candidates = LocalCandidateCoordinator(
            typingSession,
            AndroidLazyPackedLexicons.create(applicationContext.assets),
            Executor { action -> check(mainHandler.post(action)) { "Candidate owner dispatcher stopped" } },
            ::candidateOwnerState,
            ::renderCandidates,
            AndroidModelCandidates.create(applicationContext, typingSession, ::candidateOwnerState, ::renderCandidates,
                RuneTrace),
            RuneTrace,
            AndroidCanonicalCaseLexicon(applicationContext.assets),
        )
        experimentReadySubscription = AndroidExperimentResources.whenReady {
            if (!serviceDestroyed) { candidates.invalidate(); renderCandidates() }
        }
        keyboardPreferences.registerListener(preferencesListener)
        personalResources.controls.whenReady { mainHandler.post { if (!serviceDestroyed) onSettingsChanged() } }
    }

    override fun onDestroy() {
        serviceDestroyed = true
        dynamicTouchContext.reset()
        experimentReadySubscription?.close()
        experimentReadySubscription = null
        personalResources.learning.configure(false, false, false)
        visualContinuityStore.detach(visualContinuity)
        typingSession.closeDiagnosticsAdmission()
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
                view.setOnPhysicalTouchListener { sample ->
                    updatePersonalizationPolicy()
                    if (personalization.touchEnabled && personalResources.touch.isReady) {
                        personalResources.touch.model.observe(sample)
                        physicalLetterPending = true
                    }
                }
                view.setOnTouchGeometryChangedListener {
                    personalization.clearPending()
                    dynamicTouchContext.invalidate()
                }
                view.setDynamicTouchResolver(::dynamicTouchStamp, ::resolveDynamicTouch)
                view.setOnActionListener(::handleAction)
                view.setOnCandidateSelectedListener(::handleCandidateSelection)
                renderKeyboard()
                view.requestApplyInsets()
            }
        }
    }

    override fun onStartInput(attribute: EditorInfo?, restarting: Boolean) {
        typingSession.closeDiagnosticsAdmission()
        dynamicTouchContext.reset()
        keyboardView?.cancelActiveTouches()
        inputViewActive = false
        candidates.invalidate()
        super.onStartInput(attribute, restarting)
        val editorInfo = attribute ?: EditorInfo()
        editorContext = EditorContext.from(editorInfo)
        activePackage = editorInfo.packageName
        resolveTypingProfile()
        if (globalSettings.appProfiles && editorContext.supportsSmartTyping)
            activePackage?.let(personalResources.controls::observePackage)
        hasSelection = editorInfo.initialSelStart >= 0 &&
            editorInfo.initialSelEnd >= 0 &&
            editorInfo.initialSelStart != editorInfo.initialSelEnd
        // Every callback starts fresh typing ownership. Visual-only continuation must not change
        // the framework restart flag used by typing or diagnostics admission.
        typingSession.configureFeatures(DiagnosticFeatures.configured(globalSettings), 0, activeProfile.code)
        typingSession.startSession(editorContext, editorInfo.initialSelStart, editorInfo.initialSelEnd,
            diagnosticsFresh = !restarting)
        state = visualContinuity.onStartInput(
            previous = state,
            restarting = restarting,
            settings = settings,
            lastUsedLanguage = selectedLanguage,
            editor = attribute?.let {
                VisualEditorIdentity(it.packageName.orEmpty(), it.fieldId, it.inputType, it.imeOptions)
            },
            configuration = configurationSize(resources.configuration),
            nowMillis = SystemClock.uptimeMillis(),
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
        candidates.warmCurrentLanguage()
        state = withAutomaticCapitalization(state)
        renderKeyboard()
        keyboardView?.requestApplyInsets()
    }

    override fun onWindowShown() {
        super.onWindowShown()
        keyboardView?.requestApplyInsets()
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
     * Do not reset visual state or discard its configuration handoff here: Android can finish
     * input while recreating the same editor. onStartInput decides whether its visual state can
     * continue, independently of the old typing session which always ends here.
     */
    override fun onFinishInput() {
        typingSession.closeDiagnosticsAdmission()
        dynamicTouchContext.reset()
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
        // On some Fold firmware the focused editor survives the size change but the framework does
        // not invoke onStartInputView again. Keep the active IME window attached by replacing its
        // view after the framework consumes the configuration; no editor refocus or text replay.
        val wasInputViewActive = inputViewActive
        // Capture before super can synchronously redeliver input callbacks/rebuild the view.
        visualContinuity.onConfigurationChanged(configurationSize(newConfig), state, SystemClock.uptimeMillis())
        candidates.invalidate()
        typingSession.invalidate(::executeTypingEdit)
        super.onConfigurationChanged(newConfig)
        if (wasInputViewActive) recreateInputView()
        keyboardView?.requestApplyInsets()
    }

    private fun handleAction(action: KeyboardAction) {
        updatePersonalizationPolicy()
        if (action == KeyboardAction.Delete) dynamicTouchContext.afterDelete()
        if (action == KeyboardAction.Space || action == KeyboardAction.DoubleSpaceTap || action == KeyboardAction.Enter)
            dynamicTouchContext.afterBoundary()
        if (action !is KeyboardAction.CommitLetter || !physicalLetterPending) personalization.clearPending()
        physicalLetterPending = false
        visualContinuity.invalidate()
        RuneTrace.section("Rune#touchUpDispatch") {
            val previousState = state
            val transition = KeyboardReducer.reduce(
                state = state,
                action = action,
                editorContext = editorContext,
                nowMillis = SystemClock.uptimeMillis(),
            )
            val ownedEnter = action == KeyboardAction.Enter && editorContext.supportsSmartTyping &&
                (transition.command == EditorCommand.InsertNewline || transition.command is EditorCommand.PerformEditorAction)
            if (!ownedEnter && invalidatesTyping(action)) {
                candidates.invalidate()
                if (action is KeyboardAction.MoveCursor || action == KeyboardAction.Enter) {
                    typingSession.awaitEditorSelection(::executeTypingEdit)
                } else {
                    typingSession.invalidate(::executeTypingEdit)
                }
            }
            state = transition.state
            if (action is KeyboardAction.SwitchLanguage || action == KeyboardAction.ToggleSymbols ||
                action == KeyboardAction.ToggleSymbolsPage) {
                typingSession.reopenDiagnosticsForLetters(inputViewActive && editorContext.supportsSmartTyping &&
                    state.layer == KeyboardLayer.LETTERS && !hasSelection)
            }
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
            if ((action is KeyboardAction.SwitchLanguage || action == KeyboardAction.ToggleSymbols) &&
                state.layer == KeyboardLayer.LETTERS) candidates.warmCurrentLanguage()

            val outcome = transition.command?.let { executeTypingOrEditorCommand(it, previousState) }
                ?: CommandOutcome.NO_COMMAND
            if (outcome == CommandOutcome.DELIVERED && typingSession.sentenceCapitalizationPending) {
                // The gesture consumed this action. Prime the next key from the post-action state.
                state = state.withAutomaticCapitalization(editorContext.supportsAutomaticCapitalization &&
                    state.layer == KeyboardLayer.LETTERS)
            }
            if (outcome == CommandOutcome.DROPPED || action !is KeyboardAction.CommitLetter) personalization.clearPending()
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
        when (command) {
            is EditorCommand.CommitText -> typingSession.recordInput(command.value)
            EditorCommand.ConvertPrecedingSpaceToPeriod -> typingSession.recordInput(" ")
            EditorCommand.InsertNewline -> typingSession.recordInput("\n")
            EditorCommand.DeletePreviousCodePoint -> typingSession.recordBackspace()
            else -> Unit
        }
        val punctuation = MechanicalPunctuationPolicy(editorContext.inputPolicy, editorContext.mode,
            editorContext.requiresRawKeyEvents, settings.mechanicalPunctuation, settings.doubleSpacePeriod)
        if (command is EditorCommand.PerformEditorAction && editorContext.supportsSmartTyping) {
            val prepared = candidates.edit { typingSession.prepareEditorAction(punctuation, beforeAction,
                settings.autocorrectionMode, ::executeTypingEdit) }
            if (prepared == TypingTextResult.REJECTED) return CommandOutcome.DROPPED
            return when (executeEditorActionOnly(command.actionId)) {
                EditorCommandExecutor.EditorActionResult.ACCEPTED -> CommandOutcome.DELIVERED
                EditorCommandExecutor.EditorActionResult.REFUSED -> when (candidates.edit {
                    typingSession.appendEditorActionFallbackNewline(::executeTypingEdit)
                }) {
                    TypingTextResult.HANDLED -> CommandOutcome.DELIVERED
                    else -> CommandOutcome.DROPPED
                }
                EditorCommandExecutor.EditorActionResult.UNKNOWN -> {
                    candidates.invalidate()
                    typingSession.awaitEditorSelection(::executeTypingEdit)
                    CommandOutcome.DROPPED
                }
            }
        }
        val result = if (command is EditorCommand.CommitText || command == EditorCommand.DeletePreviousCodePoint ||
            command == EditorCommand.ConvertPrecedingSpaceToPeriod || command == EditorCommand.InsertNewline) {
            candidates.edit(spaceCorrection = if (command is EditorCommand.CommitText && command.value == " ")
                ::executeTypingEdit else null) {
                when (command) {
                    is EditorCommand.CommitText -> typingSession.typeText(command.value, punctuation, beforeAction,
                        autocorrectionMode = settings.autocorrectionMode,
                        execute = ::executeTypingEdit)
                    EditorCommand.DeletePreviousCodePoint -> typingSession.deletePrevious(::executeTypingEdit)
                    EditorCommand.ConvertPrecedingSpaceToPeriod -> typingSession.typeText(" ", punctuation,
                        beforeAction, doubleSpaceGesture = true, autocorrectionMode = settings.autocorrectionMode,
                        execute = ::executeTypingEdit)
                    EditorCommand.InsertNewline -> typingSession.typeText("\n", punctuation, beforeAction,
                        autocorrectionMode = settings.autocorrectionMode, execute = ::executeTypingEdit)
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

    private fun executeTypingEdit(edit: TypingEdit): Boolean = RuneTrace.section(SmartTypingTraceSection.COMPOSE_UPDATE) {
        executeCommand(editorCommand(edit)) == CommandOutcome.DELIVERED
    }

    private fun executeEditorActionOnly(actionId: Int): EditorCommandExecutor.EditorActionResult =
        RuneTrace.section("Rune#editorCommand") {
            currentInputConnection?.let { EditorCommandExecutor.performEditorActionOnly(it, actionId) }
                ?: EditorCommandExecutor.EditorActionResult.UNKNOWN
    }

    private fun editorCommand(edit: TypingEdit): EditorCommand =
            when (edit) {
                is TypingEdit.SetComposingText -> EditorCommand.SetComposingText(edit.value)
                is TypingEdit.CommitText -> EditorCommand.CommitText(edit.value)
                TypingEdit.FinishComposingText -> EditorCommand.FinishComposingText
                is TypingEdit.SetComposingRegion -> EditorCommand.SetComposingRegion(edit.start, edit.end)
                is TypingEdit.Batch -> EditorCommand.Batch(edit.edits.map(::editorCommand), edit.isCurrent)
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
        is EditorCommand.Batch,
        EditorCommand.DeletePreviousCodePoint,
        EditorCommand.InsertNewline,
        EditorCommand.ConvertPrecedingSpaceToPeriod,
        -> true
        else -> false
    }

    private fun onSettingsChanged() {
        visualContinuity.invalidate()
        RuneTrace.section("Rune#applySettings") {
            val previous = settings
            val previousProfile = activeProfile
            val previousControls = appliedControls
            globalSettings = keyboardPreferences.readSettings()
            resolveTypingProfile()
            if (previousProfile != activeProfile || previousControls !== appliedControls ||
                previous.protectedWords != settings.protectedWords || previous.appProfiles != settings.appProfiles ||
                previous.collectExamples != settings.collectExamples || previous.typoPatterns != settings.typoPatterns) {
                typingSession.invalidate(::executeTypingEdit)
                candidates.invalidate()
            }
            typingSession.updatePersonalLearningPolicy(previous.personalLearning, settings.personalLearning,
                ::executeTypingEdit)
            personalization.clearPending()
            qualityStore.invalidatePending()
            updatePersonalizationPolicy()
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
                settings.candidateStrip != previous.candidateStrip ||
                settings.contextualPunctuationMode != previous.contextualPunctuationMode ||
                settings.personalLearning != previous.personalLearning ||
                settings.touchPersonalization != previous.touchPersonalization ||
                settings.phraseSuggestions != previous.phraseSuggestions ||
                settings.learnedRanking != previous.learnedRanking ||
                settings.manualCandidateExpansion != previous.manualCandidateExpansion ||
                settings.compactContext != previous.compactContext
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
            keyboardView?.requestApplyInsets()
        }
    }

    private fun configurationSize(configuration: Configuration) = ConfigurationSize(
        configuration.screenWidthDp,
        configuration.screenHeightDp,
        configuration.smallestScreenWidthDp,
    )

    private companion object {
        /** Process-local only; it survives the old/new service overlap of a configuration change. */
        val visualContinuityStore = ConfigurationVisualContinuityStore()
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
        updatePersonalizationPolicy()
        candidates.selectCandidate(id, ::executeTypingEdit)
        renderCandidates()
    }

    private fun resolveTypingProfile() {
        appliedControls = personalResources.controls.snapshot.takeIf { personalResources.controls.isReady }
        val resolved = TypingProfileResolver.resolve(globalSettings, activePackage, appliedControls)
        activeProfile = resolved.first
        settings = resolved.second
    }

    private fun handleCandidateProtection(id: String): Boolean {
        updatePersonalizationPolicy()
        if (!settings.protectedWords || !inputViewActive || !editorContext.supportsSmartTyping) return false
        val word = typingSession.wordForProtection(id) ?: return false
        personalResources.controls.protect(word, state.language) { result ->
            if (result == TypingControlStore.Result.SAVED) keyboardPreferences.notifyTypingControlsChanged()
            Handler(Looper.getMainLooper()).post {
                if (!serviceDestroyed) android.widget.Toast.makeText(this,
                    if (result == TypingControlStore.Result.SAVED) R.string.controls_saved else R.string.controls_save_failed,
                    android.widget.Toast.LENGTH_SHORT).show()
            }
        }
        return true
    }

    private fun candidateOwnerState() = CandidateOwnerState(
        editorAllowsSmartTyping = editorContext.supportsSmartTyping,
        inputViewActive = inputViewActive,
        layer = state.layer,
        language = state.language,
        hasSelection = hasSelection,
        autocorrectionMode = settings.autocorrectionMode,
        candidateStripEnabled = settings.candidateStrip,
        manualCandidateExpansion = settings.manualCandidateExpansion,
        deterministicAutoReplaceQualified = typingSession.isLocalSpellingQualified(state.language),
        modelAutoReplaceQualified = typingSession.isModelSpellingQualified(state.language),
        modelRuntimeQualified = ModelRuntimeQualification.CURRENT,
        contextualPunctuationEnabled = settings.contextualPunctuationMode == ContextualPunctuationMode.SUGGESTIONS,
        contextualModelReady = candidates.modelReadinessHint == ModelReadinessHint.READY,
    )

    private fun updatePersonalizationPolicy() {
        if (!::personalization.isInitialized) return
        val eligible = inputViewActive && editorContext.supportsSmartTyping && !hasSelection &&
            state.layer == KeyboardLayer.LETTERS
        val visible = eligible && settings.candidateStrip
        typingTools.boundariesEnabled = visible && settings.wordBoundarySuggestions
        typingTools.abbreviationsEnabled = visible && settings.abbreviations
        typingTools.reviewEnabled = visible && settings.phraseReview
        qualityStore.configure(settings.qualityMetrics, settings.shadowComparison, eligible)
        personalization.learnedRankingEnabled = visible && settings.learnedRanking
        personalization.compactContextEnabled = visible && settings.compactContext
        personalization.protectionEnabled = eligible && settings.protectedWords
        personalResources.learning.configure(settings.collectExamples, settings.typoPatterns, eligible)
        keyboardView?.setOnCandidateLongPressedListener(if (visible && settings.protectedWords && personalResources.controls.isReady)
            ::handleCandidateProtection else null)
        val configured = DiagnosticFeatures.configured(globalSettings)
        val effective = TypingFeaturePolicy.effective(DiagnosticFeatures.configured(settings), candidateOwnerState(),
            personalResources.dictionaryLoaded, abbreviationStore.isReady, personalResources.personal.isReady,
            personalResources.touch.isReady, qualityStore.isReady, personalResources.controls.isReady, personalResources.learning.isReady,
            personalResources.experiments.learnedReady, personalResources.experiments.contextReady, personalResources.experiments.tapReady)
        typingSession.configureFeatures(configured, effective, activeProfile.code)
        personalization.learningEnabled = eligible && settings.personalLearning
        personalization.touchEnabled = eligible && settings.touchPersonalization
        personalization.phrasesEnabled = eligible && settings.phraseSuggestions
        personalResources.touch.model.setEnabled(personalization.touchEnabled)
        keyboardView?.setTouchLearningEnabled(personalization.touchEnabled)
        typingSession.setPersonalizationLanguage(state.language)
        if (!eligible || !settings.dynamicTouch) dynamicTouchContext.invalidate()
        if (!eligible) {
            physicalLetterPending = false
            personalization.clearPending()
        }
    }

    private fun dynamicTouchStamp(): Long {
        val enabled = inputViewActive && editorContext.supportsSmartTyping && !hasSelection &&
            state.layer == KeyboardLayer.LETTERS && settings.dynamicTouch && personalResources.experiments.tapReady
        return dynamicTouchContext.update(typingSession.state.sessionId, typingSession.state.revision,
            state.language, if (enabled) typingSession.experimentalInput() else null, enabled, settings.dynamicTouchApply)
    }

    private fun resolveDynamicTouch(sample: PhysicalTouchSample): Char {
        if (dynamicTouchStamp() == 0L) return sample.observedKey
        val probabilities = dynamicTouchContext.probabilities(personalResources.experiments::nextLetters)
        val proposed = DynamicTouchResolver.propose(sample, probabilities)
        val apply = dynamicTouchContext.applies
        typingSession.recordDynamicTouch(proposed != sample.observedKey, apply)
        // A model-selected character must not become a new physical calibration label.
        if (apply && proposed != sample.observedKey) {
            physicalLetterPending = false
            personalization.clearPending()
        }
        return if (apply) proposed else sample.observedKey
    }

    private fun renderCandidates() {
        updatePersonalizationPolicy()
        val view = keyboardView ?: return
        val snapshot = candidates.viewState
        view.updateCandidates(snapshot)
        val undoId = snapshot.candidates.filterIsInstance<CandidateUiItem.Undo>().firstOrNull()?.id
        if (undoId != null && undoId != timedUndoId) {
            timedUndoId = undoId
            view.postDelayed({ if (keyboardView === view && timedUndoId == undoId) renderCandidates() }, 8_050)
        } else if (undoId == null) timedUndoId = null
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
