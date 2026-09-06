package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import android.app.Activity
import android.widget.LinearLayout

object DiagnosticsSettingsProvider {
    fun contribute(activity: Activity, container: LinearLayout): AutoCloseable =
        DiagnosticsSettingsContribution(activity, container)
}
