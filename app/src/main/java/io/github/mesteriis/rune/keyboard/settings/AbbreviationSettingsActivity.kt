package io.github.mesteriis.rune.keyboard.settings

import android.app.AlertDialog
import android.os.Bundle
import android.text.InputFilter
import android.text.InputType
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.abbreviations.Abbreviation
import io.github.mesteriis.rune.keyboard.smarttyping.abbreviations.AbbreviationModel
import io.github.mesteriis.rune.keyboard.smarttyping.abbreviations.AbbreviationResult
import io.github.mesteriis.rune.keyboard.smarttyping.abbreviations.AbbreviationStore

class AbbreviationSettingsActivity : ThemedActivity() {
    private lateinit var store: AbbreviationStore
    private lateinit var rows: LinearLayout
    private lateinit var status: TextView
    private lateinit var add: Button
    private lateinit var reset: Button
    private var busy = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_abbreviations)
        setTitle(R.string.abbreviations_title)
        applySystemBarInsets(findViewById<View>(R.id.abbreviations_scroll))
        store = AbbreviationStore.get(this)
        rows = findViewById(R.id.abbreviations_entries)
        status = findViewById(R.id.abbreviations_status)
        add = findViewById(R.id.abbreviations_add)
        reset = findViewById(R.id.abbreviations_reset)
        add.setOnClickListener { showEditor(null) }
        reset.setOnClickListener {
            AlertDialog.Builder(this).setTitle(R.string.abbreviations_reset)
                .setMessage(R.string.abbreviations_reset_confirm)
                .setNegativeButton(android.R.string.cancel, null)
                .setPositiveButton(R.string.abbreviations_reset) { _, _ ->
                    busy = true
                    render()
                    store.reset { result -> onResult(result) }
                }.show()
        }
        render()
    }

    override fun onResume() {
        super.onResume()
        store.whenReady { runOnUiThread { if (!isFinishing && !isDestroyed) render() } }
    }

    private fun render() {
        val entries = store.model.snapshot()
        add.isEnabled = store.isReady && !busy && entries.size < AbbreviationModel.MAX_ENTRIES
        reset.isEnabled = !busy && store.readiness != AbbreviationStore.Readiness.LOADING
        status.text = when (store.readiness) {
            AbbreviationStore.Readiness.LOADING -> getString(R.string.abbreviations_loading)
            AbbreviationStore.Readiness.FAILED -> getString(R.string.abbreviations_load_failed)
            AbbreviationStore.Readiness.READY -> if (entries.isEmpty()) getString(R.string.abbreviations_empty)
                else getString(R.string.abbreviations_count, entries.size)
        }
        rows.removeAllViews()
        entries.forEach { entry ->
            val row = layoutInflater.inflate(R.layout.view_settings_row, rows, false)
            row.findViewById<TextView>(R.id.row_title).text = getString(R.string.abbreviations_entry, entry.key, entry.expansion)
            row.findViewById<TextView>(R.id.row_summary).apply {
                text = entry.language.displayLabel
                visibility = View.VISIBLE
            }
            row.isEnabled = !busy
            row.isFocusable = true
            row.setOnClickListener { showEditor(entry) }
            rows.addView(row)
        }
    }

    private fun showEditor(original: Abbreviation?) {
        if (busy || !store.isReady) return
        val padding = resources.getDimensionPixelSize(R.dimen.setup_page_padding)
        val form = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(padding, padding, padding, 0) }
        fun label(text: Int) { form.addView(TextView(this).apply { setText(text) }) }
        label(R.string.abbreviations_language)
        val language = Spinner(this).apply {
            adapter = ArrayAdapter(this@AbbreviationSettingsActivity, android.R.layout.simple_spinner_dropdown_item,
                KeyboardLanguage.entries.map { it.displayLabel })
            setSelection(KeyboardLanguage.entries.indexOf(original?.language ?: KeyboardLanguage.RUSSIAN))
            contentDescription = getString(R.string.abbreviations_language)
        }
        form.addView(language)
        fun input(title: Int, value: String, limit: Int): EditText {
            label(title)
            return EditText(this).apply {
                inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
                imeOptions = EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING
                setSingleLine(true)
                filters = arrayOf(InputFilter.LengthFilter(limit * 2))
                contentDescription = getString(title)
                // Settings entries are persisted only by Save, never by automatic view state.
                isSaveEnabled = false
                setText(value)
                form.addView(this)
            }
        }
        val key = input(R.string.abbreviations_key, original?.key.orEmpty(), AbbreviationModel.MAX_KEY_CODE_POINTS)
        val expansion = input(R.string.abbreviations_expansion, original?.expansion.orEmpty(), AbbreviationModel.MAX_EXPANSION_CODE_POINTS)
        val dialog = AlertDialog.Builder(this)
            .setTitle(if (original == null) R.string.abbreviations_add else R.string.abbreviations_edit)
            .setView(form).setNegativeButton(android.R.string.cancel, null)
            .setPositiveButton(R.string.abbreviations_save, null)
            .apply { if (original != null) setNeutralButton(R.string.abbreviations_delete, null) }.create()
        dialog.setOnShowListener {
            fun submit(operation: ((AbbreviationResult) -> Unit) -> Unit) {
                if (busy) return
                busy = true
                dialog.setCancelable(false)
                listOf(AlertDialog.BUTTON_POSITIVE, AlertDialog.BUTTON_NEGATIVE, AlertDialog.BUTTON_NEUTRAL)
                    .forEach { dialog.getButton(it)?.isEnabled = false }
                key.isEnabled = false
                expansion.isEnabled = false
                language.isEnabled = false
                render()
                operation { result ->
                    onResult(result) {
                        dialog.setCancelable(true)
                        listOf(AlertDialog.BUTTON_POSITIVE, AlertDialog.BUTTON_NEGATIVE, AlertDialog.BUTTON_NEUTRAL)
                            .forEach { dialog.getButton(it)?.isEnabled = true }
                        key.isEnabled = true
                        expansion.isEnabled = true
                        language.isEnabled = true
                        if (result == AbbreviationResult.SAVED) dialog.dismiss()
                    }
                }
            }
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val selected = KeyboardLanguage.entries[language.selectedItemPosition]
                val enteredKey = key.text.toString()
                val enteredExpansion = expansion.text.toString()
                submit { store.save(selected, enteredKey, enteredExpansion, original, it) }
            }
            if (original != null) dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener {
                submit { store.delete(original, it) }
            }
        }
        dialog.show()
    }

    private fun onResult(result: AbbreviationResult, after: () -> Unit = {}) {
        runOnUiThread {
            busy = false
            if (isFinishing || isDestroyed) return@runOnUiThread
            if (result != AbbreviationResult.SAVED) {
                val message = when (result) {
                    AbbreviationResult.INVALID -> R.string.abbreviations_invalid
                    AbbreviationResult.DUPLICATE -> R.string.abbreviations_duplicate
                    AbbreviationResult.LIMIT -> R.string.abbreviations_limit
                    AbbreviationResult.NOT_FOUND -> R.string.abbreviations_not_found
                    AbbreviationResult.NOT_READY -> R.string.abbreviations_load_failed
                    else -> R.string.abbreviations_io_failed
                }
                Toast.makeText(this, message, Toast.LENGTH_LONG).show()
            }
            render()
            after()
        }
    }
}
