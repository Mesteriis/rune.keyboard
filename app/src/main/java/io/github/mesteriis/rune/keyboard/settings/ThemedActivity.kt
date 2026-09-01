package io.github.mesteriis.rune.keyboard.settings

import android.app.Activity
import android.content.Context
import android.os.Build
import android.os.Bundle
import android.view.View
import android.view.WindowInsets
import android.view.WindowInsetsController

/**
 * Applies the stored light/dark override before any resource is resolved, so the qualifier-based
 * palette matches the user's choice instead of the system setting.
 */
abstract class ThemedActivity : Activity() {
    private var nightOverride: Boolean? = null

    override fun attachBaseContext(newBase: Context) {
        val theme = KeyboardPreferences(newBase).readSettings().theme
        val night = ThemeOverride.nightOverride(theme)
        nightOverride = night
        if (night != null) {
            // Must happen before the base context is attached.
            applyOverrideConfiguration(ThemeOverride.overrideConfiguration(newBase, night))
        }
        super.attachBaseContext(newBase)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        applySystemBarAppearance()
    }

    protected fun themePreference(): ThemePreference =
        KeyboardPreferences(this).readSettings().theme

    private fun applySystemBarAppearance() {
        val night = nightOverride ?: return
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return
        val controller = window.insetsController ?: return
        val lightBars = if (night) {
            0
        } else {
            WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS or
                WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS
        }
        controller.setSystemBarsAppearance(
            lightBars,
            WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS or
                WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS,
        )
    }

    /** Shared edge-to-edge padding for the single scrolling container of a settings screen. */
    @Suppress("DEPRECATION")
    protected fun applySystemBarInsets(scrollingContainer: View) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) return

        window.setDecorFitsSystemWindows(false)
        val initialLeft = scrollingContainer.paddingLeft
        val initialTop = scrollingContainer.paddingTop
        val initialRight = scrollingContainer.paddingRight
        val initialBottom = scrollingContainer.paddingBottom
        scrollingContainer.setOnApplyWindowInsetsListener { view, windowInsets ->
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
