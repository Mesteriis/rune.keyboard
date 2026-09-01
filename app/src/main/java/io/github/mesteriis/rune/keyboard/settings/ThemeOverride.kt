package io.github.mesteriis.rune.keyboard.settings

import android.content.Context
import android.content.res.Configuration

/**
 * Forces light or dark independently of the system setting.
 *
 * The palette lives in `values`/`values-night` qualifier resources, so the override has to happen
 * at the configuration level — a theme overlay cannot re-resolve qualifier colors.
 */
object ThemeOverride {
    /** null means "follow the system". */
    fun nightOverride(theme: ThemePreference): Boolean? = when (theme) {
        ThemePreference.SYSTEM -> null
        ThemePreference.LIGHT -> false
        ThemePreference.DARK -> true
    }

    fun themedContext(base: Context, theme: ThemePreference): Context {
        val night = nightOverride(theme) ?: return base
        return base.createConfigurationContext(overrideConfiguration(base, night))
    }

    fun overrideConfiguration(base: Context, night: Boolean): Configuration =
        Configuration(base.resources.configuration).apply {
            uiMode = (uiMode and Configuration.UI_MODE_NIGHT_MASK.inv()) or
                if (night) Configuration.UI_MODE_NIGHT_YES else Configuration.UI_MODE_NIGHT_NO
        }
}
