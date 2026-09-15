package io.github.mesteriis.rune.keyboard.settings

import android.app.AlertDialog
import android.os.Bundle
import android.text.InputFilter
import android.text.InputType
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.*
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.smarttyping.controls.TypingControlStore
import io.github.mesteriis.rune.keyboard.smarttyping.controls.TypingControlModel
import io.github.mesteriis.rune.keyboard.smarttyping.controls.TypingProfile

abstract class TypingControlsActivity : ThemedActivity() {
    protected lateinit var store: TypingControlStore
    protected lateinit var rows: LinearLayout
    protected var busy = false
    protected abstract val isWords: Boolean
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_typing_controls)
        setTitle(if (isWords) R.string.controls_words_title else R.string.controls_apps_title)
        findViewById<TextView>(R.id.controls_intro).setText(if (isWords) R.string.controls_words_intro else R.string.controls_apps_intro)
        applySystemBarInsets(findViewById(R.id.controls_scroll))
        store = TypingControlStore.get(this)
        rows = findViewById(R.id.controls_entries)
        findViewById<Button>(R.id.controls_add).apply {
            visibility = if (isWords) View.VISIBLE else View.GONE
            setOnClickListener { addWord() }
        }
        findViewById<Button>(R.id.controls_reset).setOnClickListener {
            val recovery = store.readiness == TypingControlStore.Readiness.FAILED
            AlertDialog.Builder(this).setMessage(if (recovery) R.string.controls_recover_confirm else R.string.controls_reset_confirm)
                .setNegativeButton(android.R.string.cancel, null)
                .setPositiveButton(R.string.controls_reset) { _, _ ->
                    busy = true; render()
                    when { recovery -> store.reset(::completed); isWords -> store.resetWords(::completed); else -> store.resetApps(::completed) }
                }.show()
        }
        render()
    }
    override fun onResume() {
        super.onResume()
        store.whenReady { runOnUiThread { if (!isFinishing && !isDestroyed) render() } }
    }
    protected fun completed(result: TypingControlStore.Result) {
        if (result == TypingControlStore.Result.SAVED) KeyboardPreferences(applicationContext).notifyTypingControlsChanged()
        runOnUiThread {
            if (isFinishing || isDestroyed) return@runOnUiThread
            busy = false; render()
            Toast.makeText(this, if (result == TypingControlStore.Result.SAVED) R.string.controls_saved else R.string.controls_save_failed,
                Toast.LENGTH_SHORT).show()
        }
    }
    protected fun row(title: String, summary: String, onClick: () -> Unit) {
        val view = layoutInflater.inflate(R.layout.view_settings_row, rows, false)
        view.findViewById<TextView>(R.id.row_title).text = title
        view.findViewById<TextView>(R.id.row_summary).apply { text = summary; visibility = View.VISIBLE }
        view.isEnabled = !busy && store.isReady
        view.isFocusable = true
        view.setOnClickListener { onClick() }
        rows.addView(view)
    }
    protected fun render() {
        val count = if (isWords) store.snapshot.words.size else store.snapshot.apps.size
        findViewById<TextView>(R.id.controls_status).text = when (store.readiness) {
            TypingControlStore.Readiness.LOADING -> getString(R.string.controls_loading)
            TypingControlStore.Readiness.FAILED -> getString(R.string.controls_failed)
            TypingControlStore.Readiness.READY -> if (count == 0) getString(R.string.controls_empty) else getString(R.string.controls_count, count)
        }
        findViewById<Button>(R.id.controls_add).isEnabled = !busy && store.isReady && count < TypingControlModel.MAX_WORDS
        findViewById<Button>(R.id.controls_reset).apply {
            isEnabled = !busy && store.readiness != TypingControlStore.Readiness.LOADING
            setText(if (store.readiness == TypingControlStore.Readiness.FAILED) R.string.controls_recover else R.string.controls_reset)
        }
        rows.removeAllViews()
        renderEntries()
    }
    protected abstract fun renderEntries()
    private fun addWord() {
        if (busy || !isWords || !store.isReady) return
        val form = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val pad = resources.getDimensionPixelSize(R.dimen.setup_page_padding)
            setPadding(pad, pad, pad, 0)
        }
        val language = Spinner(this).apply {
            adapter = ArrayAdapter(this@TypingControlsActivity, android.R.layout.simple_spinner_dropdown_item,
                KeyboardLanguage.entries.map { it.displayLabel })
            contentDescription = getString(R.string.controls_language)
        }
        val word = EditText(this).apply {
            contentDescription = getString(R.string.controls_word)
            hint = getString(R.string.controls_word)
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS
            imeOptions = EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING
            isSaveEnabled = false
            setSingleLine(true)
            filters = arrayOf(InputFilter.LengthFilter(TypingControlModel.MAX_WORD_CODE_POINTS * 2))
        }
        form.addView(language); form.addView(word)
        val dialog = AlertDialog.Builder(this).setTitle(R.string.controls_add_word).setView(form)
            .setNegativeButton(android.R.string.cancel, null).setPositiveButton(R.string.controls_save, null).create()
        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val value = TypingControlModel.normalize(word.text.toString())
                if (value == null) { word.error = getString(R.string.controls_save_failed); return@setOnClickListener }
                busy = true; render()
                store.protect(value, KeyboardLanguage.entries[language.selectedItemPosition], ::completed)
                dialog.dismiss()
            }
        }
        dialog.show()
    }
}

class ProtectedWordsActivity : TypingControlsActivity() {
    override val isWords = true
    override fun renderEntries() {
        store.snapshot.words.forEach { entry ->
            row(entry.word, entry.language.displayLabel) {
                AlertDialog.Builder(this).setTitle(entry.word).setNegativeButton(android.R.string.cancel, null)
                    .setPositiveButton(R.string.controls_remove) { _, _ ->
                        busy = true; render(); store.removeWord(entry, ::completed)
                    }.show()
            }
        }
    }
}

class AppProfilesActivity : TypingControlsActivity() {
    override val isWords = false
    private val titles = listOf(R.string.controls_profile_default, R.string.controls_profile_chat, R.string.controls_profile_formal)
    private val descriptions = listOf(R.string.controls_profile_default_description, R.string.controls_profile_chat_description,
        R.string.controls_profile_formal_description)
    override fun renderEntries() {
        store.snapshot.apps.forEach { entry ->
            val label = try {
                @Suppress("DEPRECATION")
                packageManager.getApplicationLabel(packageManager.getApplicationInfo(entry.packageName, 0)).toString()
            } catch (_: android.content.pm.PackageManager.NameNotFoundException) { entry.packageName }
            row(label, getString(titles[entry.profile.code]) + "\n" + getString(descriptions[entry.profile.code])) {
                val choices = TypingProfile.entries.map { getString(titles[it.code]) + "\n" + getString(descriptions[it.code]) }
                AlertDialog.Builder(this).setTitle(label)
                    .setSingleChoiceItems(choices.toTypedArray(), entry.profile.code) { dialog, which ->
                        busy = true; render(); store.assign(entry.packageName, TypingProfile.entries[which], ::completed); dialog.dismiss()
                    }.setNegativeButton(android.R.string.cancel, null)
                    .setNeutralButton(R.string.controls_remove) { _, _ ->
                        busy = true; render(); store.removeApp(entry.packageName, ::completed)
                    }.show()
            }
        }
    }
}
