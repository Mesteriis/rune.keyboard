package io.github.mesteriis.rune.keyboard.settings.quality

import android.app.Activity
import android.content.Intent
import android.widget.Button
import android.widget.LinearLayout
import io.github.mesteriis.rune.keyboard.R

internal object QualityDashboardExtras {
    fun contribute(activity: Activity, container: LinearLayout) {
        container.addView(Button(activity).apply {
            id = R.id.quality_export_manage
            setText(R.string.quality_export_title)
            minHeight = (48 * resources.displayMetrics.density).toInt()
            setOnClickListener { activity.startActivity(Intent(activity, QualityExportActivity::class.java)) }
        })
    }
}
