package io.github.mesteriis.rune.keyboard.qa

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Context
import android.os.Build
import android.os.Bundle
import android.text.InputType
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

/** Debug-only editor surface for repeatable manual IME acceptance. */
@SuppressLint("SetTextI18n")
class ImeQaActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val padding = dp(24)
            setPadding(padding, padding, padding, padding)
        }
        content.addView(label(getString(R.string.qa_title)))

        val plainText = editor(
            id = R.id.qa_plain_text,
            hint = getString(R.string.qa_plain_hint),
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES,
            imeOptions = EditorInfo.IME_ACTION_DONE,
        )
        content.addView(plainText)
        content.addView(label(getString(R.string.qa_raw_label)))
        content.addView(
            editor(
                id = R.id.qa_raw_text,
                hint = getString(R.string.qa_raw_hint),
                inputType = InputType.TYPE_CLASS_TEXT,
                imeOptions = EditorInfo.IME_ACTION_NONE,
                editText = RawKeyEventEditText(this),
            ),
        )
        content.addView(Button(this).apply {
            id = R.id.qa_seed_unicode
            text = getString(R.string.qa_seed_unicode)
            setOnClickListener {
                plainText.setText(getString(R.string.qa_unicode_sample))
                plainText.setSelection(plainText.text.length)
                plainText.requestFocus()
                getSystemService(InputMethodManager::class.java).showSoftInput(plainText, 0)
            }
        })

        content.addView(label(getString(R.string.qa_multiline_label)))
        content.addView(
            editor(
                id = R.id.qa_multiline_text,
                hint = getString(R.string.qa_multiline_hint),
                inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE,
                imeOptions = EditorInfo.IME_ACTION_SEND or EditorInfo.IME_FLAG_NO_ENTER_ACTION,
            ).apply {
                minLines = 3
                maxLines = 5
                isSingleLine = false
            },
        )

        val actionStatus = label(getString(R.string.qa_custom_waiting)).apply {
            id = R.id.qa_custom_status
        }
        content.addView(label(getString(R.string.qa_custom_label)))
        content.addView(
            editor(
                id = R.id.qa_custom_action,
                hint = getString(R.string.qa_custom_hint),
                inputType = InputType.TYPE_CLASS_TEXT,
                imeOptions = EditorInfo.IME_ACTION_UNSPECIFIED,
            ).apply {
                setImeActionLabel(getString(R.string.qa_custom_action), 0)
                setOnEditorActionListener { _, actionId, _ ->
                    actionStatus.text = getString(R.string.qa_custom_received, actionId)
                    true
                }
            },
        )
        content.addView(actionStatus)

        content.addView(label(getString(R.string.qa_number_label)))
        content.addView(
            editor(
                id = R.id.qa_number,
                hint = getString(R.string.qa_number_hint),
                inputType = InputType.TYPE_CLASS_NUMBER or
                    InputType.TYPE_NUMBER_FLAG_SIGNED or
                    InputType.TYPE_NUMBER_FLAG_DECIMAL,
                imeOptions = EditorInfo.IME_ACTION_DONE,
            ),
        )

        val scrollView = ScrollView(this).apply { addView(content) }
        setContentView(scrollView)
        applySystemBarInsets(scrollView)
        plainText.requestFocus()
        plainText.post {
            getSystemService(InputMethodManager::class.java)
                .showSoftInput(plainText, 0)
        }
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
        layoutParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT,
        ).apply {
            topMargin = dp(8)
            bottomMargin = dp(16)
        }
    }

    private fun label(value: String): TextView = TextView(this).apply {
        text = value
        textSize = 18f
    }

    @Suppress("DEPRECATION")
    private fun applySystemBarInsets(scrollView: ScrollView) {
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

    private class RawKeyEventEditText(context: Context) : EditText(context) {
        override fun onCreateInputConnection(outAttrs: EditorInfo): InputConnection? {
            val inputConnection = super.onCreateInputConnection(outAttrs)
            outAttrs.inputType = InputType.TYPE_NULL
            return inputConnection
        }
    }
}
