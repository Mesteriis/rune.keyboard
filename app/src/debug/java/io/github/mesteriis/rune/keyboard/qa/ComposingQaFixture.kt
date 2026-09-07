package io.github.mesteriis.rune.keyboard.qa

import android.annotation.SuppressLint
import android.content.Context
import android.os.Build
import android.text.InputType
import android.view.KeyEvent
import android.view.inputmethod.BaseInputConnection
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.ExtractedText
import android.view.inputmethod.ExtractedTextRequest
import android.view.inputmethod.InputConnection
import android.view.inputmethod.InputConnectionWrapper
import android.view.inputmethod.InputMethodManager
import android.view.inputmethod.SurroundingText
import android.view.inputmethod.TextAttribute
import android.view.inputmethod.TextSnapshot
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R

/** A compact, debug-only editor in :qa_editor. No product state or user text enters its stats. */
@SuppressLint("SetTextI18n")
internal class ComposingQaFixture(context: Context, mode: String) {
    private val passwordFixture = mode == "password"
    private val counts = linkedMapOf(
        "connections" to 0, "compose" to 0, "region" to 0, "finish" to 0, "commit" to 0,
        "before" to 0, "after" to 0, "selected" to 0, "extracted" to 0, "caps" to 0,
        "surrounding" to 0, "snapshot" to 0, "callbacks" to 0,
        "keyDown" to 0, "keyUp" to 0, "deleteKeyDown" to 0,
    )
    private val status = TextView(context).apply {
        id = R.id.qa_composing_stats
        textSize = 11f
    }
    val editor = ObservedEditText(context, mode).apply {
        id = R.id.qa_composing_text
        setHint(R.string.qa_composing_hint)
        inputType = when (mode) {
            "password" -> InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            "email" -> InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS
            "url" -> InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            "number" -> InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_DECIMAL
            "phone" -> InputType.TYPE_CLASS_PHONE
            "date_time" -> InputType.TYPE_CLASS_DATETIME
            else -> InputType.TYPE_CLASS_TEXT
        }
        imeOptions = EditorInfo.IME_ACTION_DONE or
            if (mode == "private") EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING else 0
        isSingleLine = true
        importantForAutofill = View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS
        setAutofillHints(*emptyArray())
    }
    val content = LinearLayout(context).apply {
        orientation = LinearLayout.VERTICAL
        val padding = (8 * resources.displayMetrics.density).toInt()
        setPadding(padding, padding, padding, padding)
        addView(status)
        addView(editor)
        addView(LinearLayout(context).apply {
            addView(button(R.id.qa_composing_rewrite, R.string.qa_composing_rewrite) {
                // Mutate the active Editable rather than setText(), which can restartInput and
                // legitimately enable a new composition session on some Android versions.
                editor.text.replace(0, editor.length(), "editor")
                BaseInputConnection.removeComposingSpans(editor.text)
                editor.setSelection(editor.length())
                editor.notifySelection()
            })
            addView(button(R.id.qa_composing_cursor, R.string.qa_composing_cursor) {
                editor.setSelection(0)
                editor.notifySelection()
            })
            addView(button(R.id.qa_composing_select, R.string.qa_composing_select) {
                editor.selectAll()
                editor.notifySelection()
            })
        })
        addView(LinearLayout(context).apply {
            addView(button(R.id.qa_composing_drop, R.string.qa_composing_drop) {
                BaseInputConnection.removeComposingSpans(editor.text)
                editor.notifySelection()
            })
            addView(button(R.id.qa_composing_restart, R.string.qa_composing_restart) {
                context.getSystemService(InputMethodManager::class.java).restartInput(editor)
            })
        })
    }

    init {
        editor.onChange = ::publish
        editor.onCall = { name ->
            counts[name] = counts.getValue(name) + 1
            editor.post(::publish)
        }
        publish()
    }

    private fun button(id: Int, label: Int, action: () -> Unit): Button = Button(editor.context).apply {
        this.id = id
        setText(label)
        textSize = 11f
        minWidth = 0
        minimumWidth = 0
        setOnClickListener {
            action()
            editor.requestFocus()
            editor.context.getSystemService(InputMethodManager::class.java).showSoftInput(editor, 0)
            publish()
        }
    }

    private fun publish() {
        val spans = editor.text
        status.text = (counts + mapOf(
            "start" to BaseInputConnection.getComposingSpanStart(spans),
            "end" to BaseInputConnection.getComposingSpanEnd(spans),
            "selectionStart" to editor.selectionStart,
            "selectionEnd" to editor.selectionEnd,
            "length" to editor.length(),
        ) + if (passwordFixture) {
            // The real password editor stays masked. Only an exact-prefix index for this fixed
            // public test input is exposed; arbitrary editor content is never copied into stats.
            val publicInput = "a helllo .  "
            mapOf("publicPrefix" to if (spans.length <= publicInput.length &&
                spans.toString() == publicInput.take(spans.length)) spans.length else -1)
        } else emptyMap()).entries.joinToString(" ") { (name, value) -> "$name=$value" }
    }

    class ObservedEditText(context: Context, private val mode: String) : EditText(context) {
        var onChange: (() -> Unit)? = null
        var onCall: ((String) -> Unit)? = null

        override fun onSelectionChanged(selStart: Int, selEnd: Int) {
            super.onSelectionChanged(selStart, selEnd)
            onChange?.invoke()
        }

        override fun onCreateInputConnection(outAttrs: EditorInfo): InputConnection? {
            val target = super.onCreateInputConnection(outAttrs) ?: return null
            if (mode == "raw") outAttrs.inputType = InputType.TYPE_NULL
            onCall?.invoke("connections")
            val count: (String) -> Unit = { onCall?.invoke(it) }
            return when {
                Build.VERSION.SDK_INT >= 33 -> Api33Connection(target, this, mode, count)
                Build.VERSION.SDK_INT >= 31 -> Api31Connection(target, this, mode, count)
                else -> ObservedConnection(target, this, mode, count)
            }
        }

        fun notifySelection() {
            onCall?.invoke("callbacks")
            context.getSystemService(InputMethodManager::class.java).updateSelection(
                this, selectionStart, selectionEnd,
                BaseInputConnection.getComposingSpanStart(text),
                BaseInputConnection.getComposingSpanEnd(text),
            )
            onChange?.invoke()
        }
    }

    private open class ObservedConnection(
        target: InputConnection,
        private val editor: ObservedEditText,
        private val mode: String,
        protected val count: (String) -> Unit,
    ) : InputConnectionWrapper(target, false) {
        override fun sendKeyEvent(event: KeyEvent): Boolean {
            when (event.action) {
                KeyEvent.ACTION_DOWN -> {
                    count("keyDown")
                    if (event.keyCode == KeyEvent.KEYCODE_DEL) count("deleteKeyDown")
                }
                KeyEvent.ACTION_UP -> count("keyUp")
            }
            return super.sendKeyEvent(event)
        }

        override fun setComposingText(text: CharSequence?, newCursorPosition: Int): Boolean {
            count("compose")
            if (mode == "reject" || mode == "drop") {
                // Some remote editors insert the text but cannot retain spans. Binder can hide
                // their false return value, so these fixtures explicitly report missing spans.
                // Deliberately silent editors without callbacks are outside this guarantee.
                super.commitText(text, newCursorPosition)
                editor.post { editor.notifySelection() }
                return mode == "drop"
            }
            return super.setComposingText(text, newCursorPosition)
        }

        override fun setComposingRegion(start: Int, end: Int): Boolean {
            count("region")
            return super.setComposingRegion(start, end)
        }

        override fun finishComposingText(): Boolean {
            count("finish")
            return super.finishComposingText()
        }

        override fun commitText(text: CharSequence?, newCursorPosition: Int): Boolean {
            count("commit")
            return super.commitText(text, newCursorPosition)
        }

        override fun getTextBeforeCursor(length: Int, flags: Int): CharSequence? {
            count("before")
            return super.getTextBeforeCursor(length, flags)
        }

        override fun getTextAfterCursor(length: Int, flags: Int): CharSequence? {
            count("after")
            return super.getTextAfterCursor(length, flags)
        }

        override fun getSelectedText(flags: Int): CharSequence? {
            count("selected")
            return super.getSelectedText(flags)
        }

        override fun getExtractedText(request: ExtractedTextRequest?, flags: Int): ExtractedText? {
            count("extracted")
            return super.getExtractedText(request, flags)
        }

        override fun getCursorCapsMode(reqModes: Int): Int {
            count("caps")
            return super.getCursorCapsMode(reqModes)
        }
    }

    private open class Api31Connection(
        target: InputConnection, editor: ObservedEditText, mode: String, count: (String) -> Unit,
    ) : ObservedConnection(target, editor, mode, count) {
        override fun getSurroundingText(beforeLength: Int, afterLength: Int, flags: Int): SurroundingText? {
            count("surrounding")
            return if (Build.VERSION.SDK_INT >= 31) {
                super.getSurroundingText(beforeLength, afterLength, flags)
            } else {
                null
            }
        }
    }

    private class Api33Connection(
        target: InputConnection, editor: ObservedEditText, mode: String, count: (String) -> Unit,
    ) : Api31Connection(target, editor, mode, count) {
        override fun setComposingText(text: CharSequence, newCursorPosition: Int, textAttribute: TextAttribute?): Boolean =
            setComposingText(text, newCursorPosition)

        override fun setComposingRegion(start: Int, end: Int, textAttribute: TextAttribute?): Boolean =
            setComposingRegion(start, end)

        override fun commitText(text: CharSequence, newCursorPosition: Int, textAttribute: TextAttribute?): Boolean =
            commitText(text, newCursorPosition)

        override fun takeSnapshot(): TextSnapshot? {
            count("snapshot")
            return if (Build.VERSION.SDK_INT >= 33) super.takeSnapshot() else null
        }
    }
}
