package io.github.mesteriis.rune.keyboard.settings

import android.content.ActivityNotFoundException
import android.content.ComponentName
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.view.inputmethod.InputMethodManager
import android.widget.Button
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R

class SetupActivity : ThemedActivity() {
    private val inputMethodManager: InputMethodManager by lazy {
        getSystemService(InputMethodManager::class.java)
    }

    private lateinit var statusView: TextView
    private var appliedTheme = ThemePreference.SYSTEM

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_setup)

        statusView = findViewById(R.id.keyboard_status)
        findViewById<Button>(R.id.enable_keyboard_button).setOnClickListener {
            openInputMethodSettings()
        }
        findViewById<Button>(R.id.select_keyboard_button).setOnClickListener {
            inputMethodManager.showInputMethodPicker()
        }
        findViewById<Button>(R.id.languages_button).setOnClickListener {
            startActivity(Intent(this, LanguageSettingsActivity::class.java))
        }
        findViewById<Button>(R.id.open_settings_button).setOnClickListener {
            startActivity(Intent(this, SettingsActivity::class.java))
        }

        applySystemBarInsets(findViewById<View>(R.id.setup_scroll))
        appliedTheme = themePreference()
    }

    override fun onResume() {
        super.onResume()
        if (themePreference() != appliedTheme) {
            recreate()
            return
        }
        updateKeyboardStatus()
    }

    /** The keyboard picker is a system dialog that never pauses this activity. */
    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) updateKeyboardStatus()
    }

    private fun openInputMethodSettings() {
        try {
            startActivity(Intent(Settings.ACTION_INPUT_METHOD_SETTINGS))
        } catch (_: ActivityNotFoundException) {
            startActivity(Intent(Settings.ACTION_SETTINGS))
        }
    }

    private fun updateKeyboardStatus() {
        val status = resolveStatus()
        statusView.setText(
            when (status) {
                SetupStatus.ACTIVE -> R.string.setup_status_active
                SetupStatus.ENABLED -> R.string.setup_status_enabled
                SetupStatus.DISABLED -> R.string.setup_status_disabled
            },
        )
        statusView.setTextColor(
            getColor(
                when (status) {
                    SetupStatus.ACTIVE -> R.color.status_enabled
                    SetupStatus.ENABLED -> R.color.rune_primary
                    SetupStatus.DISABLED -> R.color.status_disabled
                },
            ),
        )
    }

    private fun resolveStatus(): SetupStatus {
        val isEnabled = inputMethodManager.enabledInputMethodList.any { inputMethod ->
            inputMethod.packageName == packageName
        }
        if (!isEnabled) return SetupStatus.DISABLED
        return if (isDefaultInputMethod()) SetupStatus.ACTIVE else SetupStatus.ENABLED
    }

    private fun isDefaultInputMethod(): Boolean {
        val current = Settings.Secure.getString(
            contentResolver,
            Settings.Secure.DEFAULT_INPUT_METHOD,
        ) ?: return false
        return ComponentName.unflattenFromString(current)?.packageName == packageName
    }

    private enum class SetupStatus {
        DISABLED,
        ENABLED,
        ACTIVE,
    }
}
