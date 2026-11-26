package io.github.mesteriis.rune.keyboard.qa

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Context
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.text.Editable
import android.text.Spanned
import android.text.TextWatcher
import android.os.SystemClock
import android.text.style.SuggestionSpan
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsets
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputConnection
import android.view.inputmethod.InputMethodManager
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R

/** Debug-only, cross-process editor surface for repeatable IME boundary tests. */
@SuppressLint("SetTextI18n")
class ImeQaActivity : Activity() {
    private lateinit var plainText: EditText
    private var webEditingFixture: WebEditingQaFixture? = null
    private var detachLength: TextView? = null
    private var pauseLength = -1
    private var stopLength = -1
    private var lastEditAt = 0L

    private fun updateDetachStats() {
        detachLength?.text = "pause=$pauseLength stop=$stopLength lastEditAt=$lastEditAt"
    }

    override fun onPause() {
        if (::plainText.isInitialized && detachLength != null && pauseLength < 0) {
            pauseLength = plainText.length()
            updateDetachStats()
        }
        super.onPause()
    }

    override fun onStop() {
        if (::plainText.isInitialized && detachLength != null && stopLength < 0) {
            stopLength = plainText.length()
            updateDetachStats()
        }
        super.onStop()
    }

    override fun onDestroy() {
        webEditingFixture?.dispose()
        webEditingFixture = null
        super.onDestroy()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (intent.getBooleanExtra("qa_webview_fixture", false)) {
            val fixture = WebEditingQaFixture(this, intent.getBooleanExtra("qa_callback_trace", false))
            webEditingFixture = fixture
            setContentView(fixture.content)
            applySystemBarInsets(fixture.content)
            return
        }
        intent.getStringExtra("qa_composing_fixture")?.let { mode ->
            val fixture = ComposingQaFixture(this, mode)
            val scrollView = ScrollView(this).apply {
                id = R.id.qa_scroll
                // Fixed public QA editors must not summon a user's password-manager overlay.
                importantForAutofill = View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS
                addView(fixture.content)
            }
            setContentView(scrollView)
            applySystemBarInsets(scrollView)
            showKeyboardOnLaunch(fixture.editor)
            return
        }
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val padding = dp(24)
            setPadding(padding, padding, padding, padding)
        }
        val actionStatus = label(getString(R.string.qa_action_waiting)).apply {
            id = R.id.qa_action_status
        }
        val recordEditorAction = TextView.OnEditorActionListener { _, actionId, _ ->
            actionStatus.text = getString(R.string.qa_action_received, actionId)
            true
        }
        fun addNumberEditor() {
            addEditor(
                content, getString(R.string.qa_number_label), R.id.qa_number,
                getString(R.string.qa_number_hint),
                InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_SIGNED or
                    InputType.TYPE_NUMBER_FLAG_DECIMAL,
                EditorInfo.IME_ACTION_DONE,
            ).setOnEditorActionListener(recordEditorAction)
        }
        val numberFirst = intent.getBooleanExtra("qa_number_first", false)
        content.addView(label(getString(R.string.qa_title)))
        if (numberFirst) {
            addNumberEditor()
            content.addView(actionStatus)
        }
        if (intent.getBooleanExtra("qa_observe_detach_length", false)) {
            detachLength = TextView(this).apply { id = R.id.qa_detach_length }
            updateDetachStats()
            content.addView(detachLength)
        }

        plainText = addEditor(
            content, getString(R.string.qa_plain_label), R.id.qa_plain_text,
            getString(R.string.qa_plain_hint),
            InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES,
            EditorInfo.IME_ACTION_DONE,
        )
        if (detachLength != null) plainText.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) = Unit
            override fun afterTextChanged(s: Editable?) { lastEditAt = SystemClock.uptimeMillis(); updateDetachStats() }
        })
        content.addView(actionButton(R.id.qa_seed_selection, R.string.qa_seed_selection) {
            seed(plainText, "beforeSELECTEDafter", 6, 14)
        })
        content.addView(actionButton(R.id.qa_seed_cursor, R.string.qa_seed_cursor) {
            seed(plainText, "leftright", 4, 4)
            if (intent.getBooleanExtra("qa_misspelling_fixture", false)) {
                plainText.text.setSpan(
                    SuggestionSpan(this, arrayOf("left right"),
                        SuggestionSpan.FLAG_EASY_CORRECT or SuggestionSpan.FLAG_MISSPELLED),
                    0, plainText.text.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE,
                )
            }
        })
        content.addView(actionButton(R.id.qa_seed_start, R.string.qa_seed_start) {
            seed(plainText, "start", 0, 0)
        })
        content.addView(actionButton(R.id.qa_seed_unicode, R.string.qa_seed_unicode) {
            seed(plainText, getString(R.string.qa_unicode_sample))
        })
        content.addView(actionButton(R.id.qa_seed_graphemes, R.string.qa_seed_graphemes) {
            seed(plainText, getString(R.string.qa_grapheme_sample))
        })
        content.addView(actionButton(R.id.qa_seed_canary, R.string.qa_seed_canary) {
            seed(plainText, getString(R.string.qa_canary))
        })

        addEditor(
            content, getString(R.string.qa_raw_label), R.id.qa_raw_text,
            getString(R.string.qa_raw_hint), InputType.TYPE_CLASS_TEXT, EditorInfo.IME_ACTION_NONE,
            RawKeyEventEditText(this),
        )
        addEditor(
            content, getString(R.string.qa_multiline_label), R.id.qa_multiline_text,
            getString(R.string.qa_multiline_hint),
            InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE,
            EditorInfo.IME_ACTION_SEND or EditorInfo.IME_FLAG_NO_ENTER_ACTION,
        ).apply {
            minLines = 3
            maxLines = 5
            isSingleLine = false
        }
        addEditor(
            content, getString(R.string.qa_email_label), R.id.qa_email,
            getString(R.string.qa_email_hint),
            InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS,
            EditorInfo.IME_ACTION_NEXT,
        )
        addEditor(
            content, getString(R.string.qa_url_label), R.id.qa_url,
            getString(R.string.qa_url_hint),
            InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI,
            EditorInfo.IME_ACTION_GO,
        )
        addEditor(
            content, getString(R.string.qa_phone_label), R.id.qa_phone,
            getString(R.string.qa_phone_hint), InputType.TYPE_CLASS_PHONE, EditorInfo.IME_ACTION_DONE,
        )
        if (!numberFirst) addNumberEditor()
        addEditor(
            content, getString(R.string.qa_password_label), R.id.qa_password,
            getString(R.string.qa_password_hint),
            InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD,
            EditorInfo.IME_ACTION_DONE,
        )

        content.addView(label(getString(R.string.qa_actions_label)))
        listOf(
            ActionField(R.id.qa_action_send, R.string.qa_send_hint, EditorInfo.IME_ACTION_SEND),
            ActionField(R.id.qa_action_search, R.string.qa_search_hint, EditorInfo.IME_ACTION_SEARCH),
            ActionField(R.id.qa_action_go, R.string.qa_go_hint, EditorInfo.IME_ACTION_GO),
            ActionField(R.id.qa_action_next, R.string.qa_next_hint, EditorInfo.IME_ACTION_NEXT),
            ActionField(R.id.qa_action_done, R.string.qa_done_hint, EditorInfo.IME_ACTION_DONE),
        ).forEach { field ->
            content.addView(
                editor(field.id, getString(field.hint), InputType.TYPE_CLASS_TEXT, field.actionId).apply {
                    setOnEditorActionListener(recordEditorAction)
                },
            )
        }
        content.addView(
            editor(
                R.id.qa_custom_action, getString(R.string.qa_custom_hint),
                InputType.TYPE_CLASS_TEXT, EditorInfo.IME_ACTION_UNSPECIFIED,
            ).apply {
                setImeActionLabel(getString(R.string.qa_custom_action), 0)
                setOnEditorActionListener(recordEditorAction)
            },
        )
        if (!numberFirst) content.addView(actionStatus)

        // Keep QA navigation free of residual fling/stretch interception. The following real
        // editor-focus tap belongs to the Binder test, not to stopping a ScrollView animation.
        val scrollView = object : ScrollView(this) {
            override fun fling(velocityY: Int) = Unit
        }.apply {
            overScrollMode = android.view.View.OVER_SCROLL_NEVER
            id = R.id.qa_scroll
            // Exclude this debug-only hierarchy; never alter the device's autofill settings.
            importantForAutofill = View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS
            addView(content)
        }
        setContentView(scrollView)
        applySystemBarInsets(scrollView)
        showKeyboardOnLaunch(plainText)
    }

    private fun addEditor(
        content: LinearLayout,
        label: String,
        id: Int,
        hint: String,
        inputType: Int,
        imeOptions: Int,
        editText: EditText = EditText(this),
    ): EditText {
        content.addView(label(label))
        return editor(id, hint, inputType, imeOptions, editText).also(content::addView)
    }

    private fun editor(
        id: Int,
        hint: String,
        inputType: Int,
        imeOptions: Int,
        editText: EditText = EditText(this),
    ): EditText = editText.apply {
        this.id = id
        this.hint = hint
        this.inputType = inputType
        this.imeOptions = imeOptions
        this.importantForAutofill = View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS
        this.setAutofillHints(*emptyArray())
        // API 26 may keep a field focused while hiding the IME after a sibling Activity closes.
        // Make a deliberate tap restore the keyboard even when focus itself does not change.
        setOnClickListener { showKeyboard(this) }
        layoutParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT,
        ).apply {
            topMargin = dp(8)
            bottomMargin = dp(16)
        }
    }

    private fun actionButton(id: Int, textResource: Int, action: () -> Unit): Button =
        Button(this).apply {
            this.id = id
            setText(textResource)
            setOnClickListener { action() }
        }

    private fun seed(
        editor: EditText,
        text: String,
        selectionStart: Int = text.length,
        selectionEnd: Int = selectionStart,
    ) {
        editor.setText(text)
        editor.setSelection(selectionStart, selectionEnd)
        editor.requestFocus()
        // TextView coalesces selection notifications on API 26 after replacing all text. Send the
        // public editor-to-IME update explicitly so the test still exercises Rune's live
        // onUpdateSelection path instead of hiding it behind restartInput/EditorInfo.
        getSystemService(InputMethodManager::class.java).updateSelection(
            editor,
            selectionStart,
            selectionEnd,
            -1,
            -1,
        )
        showKeyboard(editor)
    }

    private fun showKeyboardOnLaunch(editor: EditText) {
        editor.requestFocus()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            window.insetsController?.let {
                it.show(WindowInsets.Type.ime())
                return
            }
        }
        editor.post { showKeyboard(editor) }
    }

    private fun showKeyboard(editor: EditText) {
        getSystemService(InputMethodManager::class.java).showSoftInput(editor, 0)
    }

    private fun label(value: String): TextView = TextView(this).apply {
        text = value
        textSize = 18f
    }

    @Suppress("DEPRECATION")
    private fun applySystemBarInsets(scrollView: View) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return
        window.setDecorFitsSystemWindows(false)
        val initialLeft = scrollView.paddingLeft
        val initialTop = scrollView.paddingTop
        val initialRight = scrollView.paddingRight
        val initialBottom = scrollView.paddingBottom
        scrollView.setOnApplyWindowInsetsListener { view, windowInsets ->
            val safeInsets = windowInsets.getInsets(
                WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout(),
            )
            view.setPadding(
                initialLeft + safeInsets.left,
                initialTop + safeInsets.top,
                initialRight + safeInsets.right,
                initialBottom + safeInsets.bottom,
            )
            windowInsets
        }
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private data class ActionField(val id: Int, val hint: Int, val actionId: Int)

    private class RawKeyEventEditText(context: Context) : EditText(context) {
        override fun onCreateInputConnection(outAttrs: EditorInfo): InputConnection? {
            val inputConnection = super.onCreateInputConnection(outAttrs)
            outAttrs.inputType = InputType.TYPE_NULL
            return inputConnection
        }
    }
}
