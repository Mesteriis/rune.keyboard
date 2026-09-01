package io.github.mesteriis.rune.keyboard.settings

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.WindowInsets
import android.view.inputmethod.InputMethodManager
import android.widget.Button
import android.widget.ScrollView
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R

class SetupActivity : Activity() {
    private val inputMethodManager: InputMethodManager by lazy {
        getSystemService(InputMethodManager::class.java)
    }

    private lateinit var statusView: TextView

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

        applySystemBarInsets(findViewById(R.id.setup_scroll))
    }

    override fun onResume() {
        super.onResume()
        updateKeyboardStatus()
    }

    private fun openInputMethodSettings() {
        try {
            startActivity(Intent(Settings.ACTION_INPUT_METHOD_SETTINGS))
        } catch (_: ActivityNotFoundException) {
            startActivity(Intent(Settings.ACTION_SETTINGS))
        }
    }

    private fun updateKeyboardStatus() {
        val isEnabled = inputMethodManager.enabledInputMethodList.any { inputMethod ->
            inputMethod.packageName == packageName
        }
        statusView.setText(
            if (isEnabled) R.string.setup_status_enabled else R.string.setup_status_disabled,
        )
        statusView.setTextColor(
            getColor(if (isEnabled) R.color.status_enabled else R.color.status_disabled),
        )
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
}
