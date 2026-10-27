package io.github.mesteriis.rune.keyboard.settings

import android.app.AlertDialog
import android.os.Bundle
import android.text.Editable
import android.text.InputFilter
import android.text.TextWatcher
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.view.inputmethod.EditorInfo
import android.widget.BaseAdapter
import android.widget.EditText
import android.widget.ListView
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingModel
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingResources
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalTypingStore
import io.github.mesteriis.rune.keyboard.smarttyping.personalization.PersonalWord
import java.text.Normalizer

/** Explicit management of existing confirmations; no import, spelling retrieval or new learning. */
class ConfirmedWordsActivity : ThemedActivity() {
    private lateinit var store: PersonalTypingStore
    private lateinit var filter: EditText
    private lateinit var list: ListView
    private val adapter = WordsAdapter()
    private var entries = emptyList<PersonalWord>()
    private var busy = false
    private var dialog: AlertDialog? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_confirmed_words)
        setTitle(R.string.confirmed_words_title)
        applySystemBarInsets(findViewById(R.id.confirmed_words_root))
        window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_HIDDEN)
        store = PersonalTypingResources.get(this).personal
        filter = findViewById(R.id.confirmed_words_filter)
        filter.filters = arrayOf(InputFilter.LengthFilter(PersonalTypingModel.MAX_WORD_CHARS))
        filter.imeOptions = EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING or EditorInfo.IME_ACTION_SEARCH
        filter.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) = Unit
            override fun afterTextChanged(s: Editable?) = render()
        })
        list = findViewById(R.id.confirmed_words_entries)
        list.adapter = adapter
        render()
    }

    override fun onResume() {
        super.onResume()
        store.whenReady { runOnUiThread { if (!isFinishing && !isDestroyed) render() } }
    }

    override fun onDestroy() { dialog?.dismiss(); dialog = null; super.onDestroy() }

    private fun render() {
        val all = if (store.isReady) store.model.snapshot().confirmed else emptyList()
        val query = Normalizer.normalize(filter.text.toString().trim(), Normalizer.Form.NFC)
        entries = all.filter { it.word.contains(query, true) || it.language.displayLabel.contains(query, true) }
            .sortedWith(compareBy<PersonalWord>({ it.word }, { it.language.ordinal }))
        filter.isEnabled = !busy && store.isReady
        list.isEnabled = !busy && store.isReady
        findViewById<TextView>(R.id.confirmed_words_status).text = when (store.readiness) {
            PersonalTypingStore.Readiness.LOADING -> getString(R.string.controls_loading)
            PersonalTypingStore.Readiness.FAILED -> getString(R.string.confirmed_words_unavailable)
            PersonalTypingStore.Readiness.READY -> getString(R.string.confirmed_words_count,
                entries.size, all.size, PersonalTypingModel.MAX_CONFIRMED)
        }
        adapter.notifyDataSetChanged()
    }

    private fun confirmRemoval(entry: PersonalWord) {
        if (busy || !store.isReady) return
        dialog = AlertDialog.Builder(this).setTitle(entry.word)
            .setMessage(getString(R.string.confirmed_words_remove_confirm, entry.language.displayLabel))
            .setNegativeButton(android.R.string.cancel, null)
            .setPositiveButton(R.string.controls_remove) { _, _ -> remove(entry) }.show()
    }

    private fun remove(entry: PersonalWord) {
        if (busy) return
        busy = true; render()
        store.removeConfirmedWord(entry) { success -> runOnUiThread {
            if (isFinishing || isDestroyed) return@runOnUiThread
            busy = false; render()
            if (success) KeyboardPreferences(applicationContext).notifyPersonalProfileChanged() else {
                // RAM intent stays applied on storage failure. Retry is idempotent and saves it durably.
                dialog = AlertDialog.Builder(this).setMessage(R.string.confirmed_words_save_failed)
                    .setNegativeButton(android.R.string.cancel, null)
                    .setPositiveButton(R.string.confirmed_words_retry) { _, _ -> remove(entry) }.show()
            }
        } }
    }

    private inner class WordsAdapter : BaseAdapter() {
        override fun getCount() = entries.size
        override fun getItem(position: Int) = entries[position]
        override fun getItemId(position: Int) = position.toLong()
        override fun areAllItemsEnabled() = false
        override fun isEnabled(position: Int) = !busy && store.isReady
        override fun getView(position: Int, convertView: View?, parent: ViewGroup): View {
            val entry = getItem(position)
            return (convertView ?: layoutInflater.inflate(R.layout.view_settings_row, parent, false)).apply {
                findViewById<TextView>(R.id.row_title).text = entry.word
                findViewById<TextView>(R.id.row_summary).apply { text = entry.language.displayLabel; visibility = View.VISIBLE }
                isEnabled = !busy && store.isReady
                isFocusable = true
                contentDescription = getString(R.string.confirmed_words_remove_description, entry.word, entry.language.displayLabel)
                setOnClickListener { confirmRemoval(entry) }
            }
        }
    }
}
