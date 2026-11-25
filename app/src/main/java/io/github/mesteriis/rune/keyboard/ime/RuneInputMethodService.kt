package io.github.mesteriis.rune.keyboard.ime

import android.content.SharedPreferences
import android.content.res.Configuration
import android.inputmethodservice.InputMethodService
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.text.InputType
import android.view.KeyEvent
import android.view.View
import android.view.WindowInsetsController
import android.view.WindowManager
import android.graphics.Color
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.view.inputmethod.InputMethodSubtype
import io.github.mesteriis.rune.keyboard.BuildConfig
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.editor.EditorCommandExecutor
import io.github.mesteriis.rune.keyboard.ime.editor.EditorCallbackTrace
import io.github.mesteriis.rune.keyboard.ime.editor.DeleteMode
import io.github.mesteriis.rune.keyboard.ime.feedback.CommandOutcome
import io.github.mesteriis.rune.keyboard.ime.feedback.FeedbackController
import io.github.mesteriis.rune.keyboard.ime.feedback.FeedbackPolicy
import io.github.mesteriis.rune.keyboard.ime.layout.KeyboardLayoutProvider
import io.github.mesteriis.rune.keyboard.ime.layout.LayoutOptions
import io.github.mesteriis.rune.keyboard.ime.model.EditorCommand
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLayer
import io.github.mesteriis.rune.keyboard.ime.model.ExternalEditContinuity
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
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.MorphologyLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.lexicon.RareWordLexicon
import io.github.mesteriis.rune.keyboard.smarttyping.learning.LearningJobScheduler

class RuneInputMethodService : InputMethodService() {
    private val layoutProvider = KeyboardLayoutProvider()
    private lateinit var feedbackController: FeedbackController
    private lateinit var keyboardPreferences: KeyboardPreferences
    private var voiceTarget: Pair<String, InputMethodSubtype>? = null
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
    private val typingSession = TypingSessionController(RuneTrace, BuildConfig.MODEL_PREFIX_WINDOW)
    private val externalEditContinuity = ExternalEditContinuity()
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
        LearningJobScheduler.sync(this, globalSettings.collectExamples && globalSettings.typoPatterns)
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
        personalization = AndroidTypingPersonalization(personalResources) {
            Handler(Looper.getMainLooper()).post {
                if (!serviceDestroyed) android.widget.Toast.makeText(this,
                    getString(R.string.confirmed_words_full,
                        io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingModel.MAX_CONFIRMED),
                    android.widget.Toast.LENGTH_SHORT).show()
            }
        }
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
            MorphologyLexicon { language, key -> personalResources.lexicon.lookup(language, key) },
            RareWordLexicon { key -> personalResources.rareWords.lookup(key) },
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
            val systemNight = resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES
            val light = settings.keyboardPalette.isLight(systemNight)
            applyKeyboardNavigation(light)
            RuneKeyboardView(themedContext, buildMetrics(themedContext), settings.keyboardTheme, light).also { view ->
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
                view.setOnCandidateExpandListener {
                    updatePersonalizationPolicy()
                    val expanded = candidates.openExpandedCandidates()
                    if (expanded != null && !view.showExpandedCandidates(expanded.candidates, { id ->
                            updatePersonalizationPolicy()
                            candidates.selectExpandedCandidate(expanded, id, ::executeTypingEdit)
                            renderCandidates()
                        }, { candidates.closeExpandedCandidates() })) {
                        candidates.closeExpandedCandidates()
                    }
                }
                renderKeyboard()
                view.requestApplyInsets()
            }
        }
    }

    @Suppress("DEPRECATION")
    private fun applyKeyboardNavigation(light: Boolean) {
        val imeWindow = window?.window ?: return
        val lightNavigation = light && Build.VERSION.SDK_INT >= 27
        imeWindow.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
        imeWindow.navigationBarColor = if (lightNavigation) Color.rgb(0xe8, 0xe8, 0xe8) else Color.rgb(0x18, 0x18, 0x18)
        if (Build.VERSION.SDK_INT >= 30) {
            imeWindow.insetsController?.setSystemBarsAppearance(
                if (lightNavigation) WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS else 0,
                WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS,
            )
        } else if (Build.VERSION.SDK_INT >= 27) {
            val flags = imeWindow.decorView.systemUiVisibility
            imeWindow.decorView.systemUiVisibility = if (lightNavigation) flags or View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
                else flags and View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR.inv()
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
        externalEditContinuity.observe(typingSession.state.enabled, typingSession.requiresExternalWordBoundary)
        val requireExternalBoundary = externalEditContinuity.onStart(editorInfo.packageName, editorInfo.fieldId, restarting,
            editorInfo.initialSelStart, editorInfo.initialSelEnd)
        editorContext = EditorContext.from(editorInfo)
        activePackage = editorInfo.packageName
        resolveTypingProfile()
        if (globalSettings.appProfiles && editorContext.allowsPersonalization)
            activePackage?.let(personalResources.controls::observePackage)
        hasSelection = editorInfo.initialSelStart >= 0 &&
            editorInfo.initialSelEnd >= 0 &&
            editorInfo.initialSelStart != editorInfo.initialSelEnd
        // Every callback starts fresh typing ownership. Visual-only continuation must not change
        // the framework restart flag used by typing or diagnostics admission.
        typingSession.configureFeatures(DiagnosticFeatures.configured(globalSettings), 0, activeProfile.code)
        typingSession.startSession(editorContext, editorInfo.initialSelStart, editorInfo.initialSelEnd,
            diagnosticsFresh = !restarting, requireExternalBoundary = requireExternalBoundary)
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
        if (editorContext.inputPolicy == InputPolicy.SENSITIVE && state.layer == KeyboardLayer.EDITING)
            state = state.toggleSymbols()
        selectedLanguage = state.language
        renderCandidates()
    }

    override fun onStartInputView(info: EditorInfo?, restarting: Boolean) {
        super.onStartInputView(info, restarting)
        if (info != null) editorContext = EditorContext.from(info)
        inputViewActive = true
        voiceTarget = findVoiceInput()
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
        val wasEnabled = typingSession.state.enabled
        val externalChange = typingSession.updateSelection(
            newSelStart, newSelEnd, candidatesStart, candidatesEnd, ::executeTypingEdit,
        )
        var callback = 0
        if (oldSelStart == newSelStart && oldSelEnd == newSelEnd) callback = callback or EditorCallbackTrace.STATIONARY_CURSOR
        if (candidatesStart >= 0 && candidatesEnd >= candidatesStart) callback = callback or EditorCallbackTrace.COMPOSING_SPAN
        if (externalChange && wasEnabled && !typingSession.state.enabled) callback = callback or EditorCallbackTrace.SESSION_DISABLED_EXTERNALLY
        if (typingSession.state.enabled) callback = callback or EditorCallbackTrace.SESSION_ENABLED
        if (externalChange) callback = callback or EditorCallbackTrace.EXTERNAL_CHANGE
        if (newSelStart < 0 || newSelEnd < 0) callback = callback or EditorCallbackTrace.INVALID_SELECTION
        if (currentInputEditorInfo?.packageName == packageName) EditorCallbackTrace.record(callback)
        if (externalChange) candidates.invalidate()
        externalEditContinuity.observe(typingSession.state.enabled, typingSession.requiresExternalWordBoundary)
        renderCandidates()
        refreshAutomaticCapitalization()
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK && keyboardView?.hasExpandedCandidates == true) {
            if (event.repeatCount == 0) event.startTracking()
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onKeyUp(keyCode: Int, event: KeyEvent): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK && event.isTracking && !event.isCanceled &&
            keyboardView?.dismissExpandedCandidates() == true
        ) return true
        return super.onKeyUp(keyCode, event)
    }

    override fun onFinishInputView(finishingInput: Boolean) {
        externalEditContinuity.observe(typingSession.state.enabled, typingSession.requiresExternalWordBoundary)
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
        externalEditContinuity.observe(typingSession.state.enabled, typingSession.requiresExternalWordBoundary)
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
            val leavingEditing = previousState.layer == KeyboardLayer.EDITING && action == KeyboardAction.ToggleSymbols
            val leavingEmoji = previousState.layer == KeyboardLayer.EMOJI && action == KeyboardAction.ToggleSymbols
            // Keep the owned word only while entering the first symbols page, so ':' can
            // consume a ready correction. Any other symbol still ends that ownership.
            val enteringSymbolsWithOwnedWord = action == KeyboardAction.ToggleSymbols &&
                previousState.layer == KeyboardLayer.LETTERS && transition.state.layer == KeyboardLayer.SYMBOLS &&
                typingSession.canRequestCandidates
            val returningFromOwnedColon = action == KeyboardAction.ToggleSymbols &&
                previousState.layer == KeyboardLayer.SYMBOLS && transition.state.layer == KeyboardLayer.LETTERS &&
                previousState.language == KeyboardLanguage.RUSSIAN && !hasSelection &&
                editorContext.inputPolicy == InputPolicy.NORMAL && editorContext.supportsSmartTyping &&
                settings.mechanicalPunctuation && typingSession.ownsCyrillicColonContinuation()
            val editingCursor = previousState.layer == KeyboardLayer.EDITING &&
                (action is KeyboardAction.MoveCursor || action == KeyboardAction.CursorModeStarted)
            val externalEdit = action == KeyboardAction.OpenEditing && transition.state.layer == KeyboardLayer.EDITING ||
                transition.command is EditorCommand.NavigateCursor || transition.command is EditorCommand.ContextMenu || editingCursor
            if (externalEdit) {
                candidates.invalidate()
                val await = transition.command is EditorCommand.NavigateCursor || transition.command is EditorCommand.ContextMenu ||
                    action is KeyboardAction.MoveCursor
                if (!typingSession.prepareExternalEdit(await, ::executeTypingEdit)) return@section
                externalEditContinuity.arm()
            } else if (returningFromOwnedColon) {
                // The punctuation planner still decides on the actual next key.
                candidates.invalidate()
                typingSession.closeDiagnosticsAdmission()
            } else if (!leavingEditing && !leavingEmoji && !ownedEnter && !enteringSymbolsWithOwnedWord && invalidatesTyping(action)) {
                candidates.invalidate()
                if (action is KeyboardAction.MoveCursor || action == KeyboardAction.Enter) {
                    typingSession.awaitEditorSelection(::executeTypingEdit)
                } else {
                    val finished = typingSession.invalidate(::executeTypingEdit)
                    if (action == KeyboardAction.OpenEmoji && !finished) return@section
                }
            }
            state = transition.state
            if (externalEdit || leavingEditing || action == KeyboardAction.OpenEmoji) updatePersonalizationPolicy()
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
            if (outcome == CommandOutcome.DELIVERED && previousState.layer == KeyboardLayer.EMOJI && editorContext.inputPolicy == InputPolicy.NORMAL &&
                action is KeyboardAction.CommitText) keyboardView?.recordEmojiCommitted(action.value)
            externalEditContinuity.observe(typingSession.state.enabled, typingSession.requiresExternalWordBoundary)
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
        KeyboardAction.OpenEmoji,
        KeyboardAction.CursorModeStarted,
        KeyboardAction.HideKeyboard,
        KeyboardAction.NextInputMethod,
        KeyboardAction.VoiceInput,
        is KeyboardAction.SwitchLanguage,
        is KeyboardAction.MoveCursor,
        -> true
        else -> false
    }

    private fun executeTypingOrEditorCommand(command: EditorCommand, beforeAction: KeyboardState): CommandOutcome {
        if (beforeAction.layer == KeyboardLayer.SYMBOLS && command is EditorCommand.CommitText &&
            command.value != ":" && typingSession.state.composing?.typedWord?.isNotEmpty() == true) {
            candidates.invalidate()
            if (!typingSession.invalidate(::executeTypingEdit)) return CommandOutcome.DROPPED
        }
        when (command) {
            is EditorCommand.CommitText -> typingSession.recordInput(command.value,
                allowFreshDiagnostics = inputViewActive && editorContext.supportsSmartTyping &&
                    state.layer == KeyboardLayer.LETTERS && !hasSelection)
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
                ::executeTypingEdit else null, retainReadySymbolBoundary = beforeAction.layer == KeyboardLayer.SYMBOLS &&
                command is EditorCommand.CommitText && command.value == ":" && typingSession.canRequestCandidates) {
                when (command) {
                    is EditorCommand.CommitText -> if (beforeAction.layer == KeyboardLayer.EMOJI && command.value != " ")
                        typingSession.typeIsolatedText(command.value, ::executeTypingEdit)
                    else typingSession.typeText(command.value, punctuation, beforeAction,
                        autocorrectionMode = settings.autocorrectionMode, execute = ::executeTypingEdit)
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
            EditorCommand.SwitchToVoiceInput -> {
                switchToVoiceInputOrShowPicker()
                return CommandOutcome.DELIVERED
            }
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
                    !editorContext.inputPolicy.allowsEditorReads -> {
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
        is EditorCommand.ContextMenu -> command.action == io.github.mesteriis.rune.keyboard.ime.model.EditorContextAction.CUT ||
            command.action == io.github.mesteriis.rune.keyboard.ime.model.EditorContextAction.PASTE
        else -> false
    }

    private fun onSettingsChanged() {
        visualContinuity.invalidate()
        RuneTrace.section("Rune#applySettings") {
            val previous = settings
            val previousProfile = activeProfile
            val previousControls = appliedControls
            globalSettings = keyboardPreferences.readSettings()
            LearningJobScheduler.sync(this, globalSettings.collectExamples && globalSettings.typoPatterns)
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
            suppressSentenceCaps = {
                settings.mechanicalPunctuation && candidate.language == KeyboardLanguage.RUSSIAN &&
                    typingSession.awaitsRussianAbbreviationContinuation()
            },
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
                options = LayoutOptions(showNumberRow = settings.numberRow, keyFlicks = settings.keyFlicks, emojiKey = settings.emojiKey, voiceInput = voiceTarget != null),
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
        appliedControls = if (editorContext.allowsPersonalization && personalResources.controls.isReady)
            personalResources.controls.snapshot else null
        // Incognito uses global typing settings, never a personal package profile or its loading fallback.
        val profileSettings = if (editorContext.allowsPersonalization) globalSettings else globalSettings.copy(appProfiles = false)
        val resolved = TypingProfileResolver.resolve(profileSettings, activePackage, appliedControls)
        activeProfile = resolved.first
        settings = resolved.second
    }

    private fun handleCandidateProtection(id: String): Boolean {
        updatePersonalizationPolicy()
        if (!settings.protectedWords || !inputViewActive || !editorContext.allowsPersonalization) return false
        val word = typingSession.wordForProtection(id) ?: return false
        personalResources.controls.protect(word, state.language) { result ->
            if (result == TypingControlStore.Result.SAVED) keyboardPreferences.notifyTypingControlsChanged()
            Handler(Looper.getMainLooper()).post {
                if (!serviceDestroyed) android.widget.Toast.makeText(this,
                    when (result) {
                        TypingControlStore.Result.SAVED -> getString(R.string.controls_saved)
                        TypingControlStore.Result.INVALID_OR_FULL -> getString(R.string.controls_invalid_or_full,
                            io.github.mesteriis.rune.keyboard.smarttyping.controls.TypingControlModel.MAX_WORDS)
                        TypingControlStore.Result.NOT_READY -> getString(R.string.controls_loading)
                        TypingControlStore.Result.IO_FAILURE -> getString(R.string.controls_io_failure)
                    },
                    android.widget.Toast.LENGTH_SHORT).show()
            }
        }
        return true
    }

    private fun candidateOwnerState() = CandidateOwnerState(
        editorAllowsSmartTyping = editorContext.supportsSmartTyping,
        editorAllowsSuggestions = editorContext.editorAllowsSuggestions,
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
        val retainedSymbolWord = state.layer == KeyboardLayer.SYMBOLS && typingSession.canRequestCandidates
        val eligible = inputViewActive && editorContext.allowsPersonalization && !hasSelection &&
            (state.layer == KeyboardLayer.LETTERS || retainedSymbolWord)
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
        val featureOwner = candidateOwnerState().let { if (retainedSymbolWord) it.copy(layer = KeyboardLayer.LETTERS) else it }
        val effective = TypingFeaturePolicy.effective(DiagnosticFeatures.configured(settings), featureOwner,
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
        val enabled = inputViewActive && editorContext.allowsPersonalization && !hasSelection &&
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
        view.updateCandidates(snapshot, candidates.hasExpandedCandidates())
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

    private fun findVoiceInput(): Pair<String, InputMethodSubtype>? {
        val manager = getSystemService(InputMethodManager::class.java)
        return try {
            manager.enabledInputMethodList.asSequence().flatMap { method ->
                manager.getEnabledInputMethodSubtypeList(method, true).asSequence()
                    .filter { it.mode.equals("voice", ignoreCase = true) }
                    .map { method.id to it }
            }.firstOrNull()
        } catch (_: SecurityException) {
            null
        }
    }

    @Suppress("DEPRECATION")
    private fun switchToVoiceInputOrShowPicker() {
        val manager = getSystemService(InputMethodManager::class.java)
        val target = findVoiceInput()
        if (target != null) {
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                    switchInputMethod(target.first, target.second)
                } else {
                    val token = window?.window?.attributes?.token
                    if (token == null) { manager.showInputMethodPicker(); return }
                    manager.setInputMethodAndSubtype(token, target.first, target.second)
                }
                return
            } catch (_: IllegalArgumentException) {
                // The enabled or visible IME can change while the popup is open.
            } catch (_: SecurityException) {
                // Fall back to the system chooser if Android rejects direct switching.
            }
        }
        manager.showInputMethodPicker()
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
        if (action is KeyboardAction.MoveCursor || action is KeyboardAction.Navigate || action == KeyboardAction.CursorModeStarted) return
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
