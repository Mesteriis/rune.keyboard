package io.github.mesteriis.rune.keyboard.smarttyping.diagnostics

import android.content.Context

/** Application singleton; no UI, document-provider, delivery or runtime dependencies. */
object TypingDiagnosticsProvider {
    @Volatile private var recorder: DiagnosticsRecorder? = null
    fun create(context: Context): TypingDiagnostics = recorder ?: synchronized(this) {
        recorder ?: context.applicationContext.let { app ->
            val preferences = DiagnosticsAndroidPreferences(app)
            DiagnosticsRecorder(DiagnosticsStorage.forAppDirectory({ app.noBackupFilesDir },
                preferences::read, preferences::write)).also { recorder = it }
        }
    }
}
