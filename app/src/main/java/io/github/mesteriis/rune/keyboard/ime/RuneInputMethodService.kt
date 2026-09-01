package io.github.mesteriis.rune.keyboard.ime

import android.inputmethodservice.InputMethodService
import android.media.AudioManager
import android.os.Build
import android.os.SystemClock
import android.text.InputType
import android.view.HapticFeedbackConstants
import android.view.View
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import io.github.mesteriis.rune.keyboard.ime.editor.EditorCommandExecutor
import io.github.mesteriis.rune.keyboard.ime.layout.KeyboardLayoutProvider
import io.github.mesteriis.rune.keyboard.ime.model.EditorCommand
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLayer
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardReducer
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState
import io.github.mesteriis.rune.keyboard.ime.ui.RuneKeyboardView
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences

class RuneInputMethodService : InputMethodService() {
    private val layoutProvider = KeyboardLayoutProvider()
    private lateinit var audioManager: AudioManager
    private lateinit var keyboardPreferences: KeyboardPreferences
    private var keyboardView: RuneKeyboardView? = null
    private var editorContext = EditorContext.from(InputType.TYPE_CLASS_TEXT, EditorInfo.IME_ACTION_NONE)
    private var state = KeyboardState.initial(KeyboardLanguage.ENGLISH, automaticCapitalization = false)
    private var selectedLanguage = KeyboardLanguage.ENGLISH
    private var hasSelection = false

    override fun onCreate() {
        super.onCreate()
        audioManager = getSystemService(AudioManager::class.java)
        keyboardPreferences = KeyboardPreferences(this)
        selectedLanguage = keyboardPreferences.readLanguage()
            ?: KeyboardLanguage.ENGLISH
    }

    override fun onCreateInputView(): View = RuneKeyboardView(this).also { view ->
        keyboardView = view
        view.setOnActionListener(::handleAction)
        renderKeyboard()
    }

    override fun onStartInput(attribute: EditorInfo?, restarting: Boolean) {
        keyboardView?.cancelActiveTouches()
        super.onStartInput(attribute, restarting)
        val editorInfo = attribute ?: EditorInfo()
        editorContext = EditorContext.from(editorInfo)
        hasSelection = editorInfo.initialSelStart >= 0 &&
            editorInfo.initialSelEnd >= 0 &&
            editorInfo.initialSelStart != editorInfo.initialSelEnd
        state = KeyboardState.initial(
            language = selectedLanguage,
            automaticCapitalization = false,
        )
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

    override fun onFinishInput() {
        keyboardView?.cancelActiveTouches()
        hasSelection = false
        state = KeyboardState.initial(selectedLanguage, automaticCapitalization = false)
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
        if (action == KeyboardAction.ToggleLanguage) {
            selectedLanguage = state.language
            keyboardPreferences.writeLanguage(selectedLanguage)
            state = withAutomaticCapitalization(state)
        } else if (action == KeyboardAction.ToggleSymbols && state.layer == KeyboardLayer.LETTERS) {
            state = withAutomaticCapitalization(state)
        }
        provideFeedback(action)
        transition.command?.let(::executeCommand)
        if (state != previousState) renderKeyboard()

        if (transition.command is EditorCommand.CommitText ||
            transition.command is EditorCommand.DeletePreviousCodePoint
        ) {
            keyboardView?.post(::refreshAutomaticCapitalization)
        }
    }

    private fun executeCommand(command: EditorCommand) {
        if (command == EditorCommand.SwitchToNextInputMethod) {
            switchToNextInputMethodOrShowPicker()
            return
        }
        val connection = currentInputConnection ?: return
        val result = EditorCommandExecutor.execute(
            command = command,
            inputConnection = connection,
            hasSelection = hasSelection,
            requiresRawKeyEvents = editorContext.requiresRawKeyEvents,
        )
        if (result.clearsSelection) {
            hasSelection = false
        }
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
        view.render(layoutProvider.layoutFor(state, editorContext), state)
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

    private fun provideFeedback(action: KeyboardAction) {
        val view = keyboardView ?: return
        val hapticEffect = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            HapticFeedbackConstants.KEYBOARD_TAP
        } else {
            HapticFeedbackConstants.VIRTUAL_KEY
        }
        view.performHapticFeedback(hapticEffect)
        audioManager.playSoundEffect(
            when (action) {
                KeyboardAction.Delete -> AudioManager.FX_KEYPRESS_DELETE
                KeyboardAction.Space -> AudioManager.FX_KEYPRESS_SPACEBAR
                KeyboardAction.Enter -> AudioManager.FX_KEYPRESS_RETURN
                else -> AudioManager.FX_KEYPRESS_STANDARD
            },
        )
    }
}
