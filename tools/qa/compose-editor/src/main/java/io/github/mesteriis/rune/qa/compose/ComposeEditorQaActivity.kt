package io.github.mesteriis.rune.qa.compose

import android.annotation.SuppressLint
import android.os.Build
import android.os.Bundle
import android.view.View
import android.view.WindowInsets
import android.view.inputmethod.ExtractedText
import android.view.inputmethod.ExtractedTextRequest
import android.view.inputmethod.InputConnection
import android.view.inputmethod.InputConnectionWrapper
import android.view.inputmethod.SurroundingText
import android.view.inputmethod.TextSnapshot
import android.widget.LinearLayout
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.text.input.TextFieldLineLimits
import androidx.compose.foundation.text.input.rememberTextFieldState
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.platform.InterceptPlatformTextInput
import androidx.compose.ui.platform.PlatformTextInputInterceptor
import androidx.compose.ui.platform.PlatformTextInputMethodRequest
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.util.concurrent.atomic.AtomicInteger

/** Independent network-free QA app. Only numeric state is exported by its status view. */
@SuppressLint("SetTextI18n")
class ComposeEditorQaActivity : ComponentActivity() {
    private val counts = listOf("connections", "before", "after", "selected", "extracted", "surrounding", "snapshot")
        .associateWith { AtomicInteger() }
    private lateinit var status: TextView
    private var editor: ComposeView? = null
    private var start = 0
    private var end = 0
    private var length = 0
    private var disposed = false

    @Suppress("DEPRECATION")
    @OptIn(ExperimentalComposeUiApi::class)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        status = TextView(this).apply { id = R.id.qa_compose_stats; textSize = 11f }
        val view = ComposeView(this).apply {
            importantForAutofill = View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS
            setContent {
                val state = rememberTextFieldState()
                // Stable identity avoids restarting the native session on every recomposition.
                val interceptor = remember {
                    PlatformTextInputInterceptor { request, next ->
                        next.startInputMethod(PlatformTextInputMethodRequest { attrs ->
                            wrap(request.createInputConnection(attrs))
                        })
                    }
                }
                LaunchedEffect(state) {
                    snapshotFlow { Triple(state.selection.start, state.selection.end, state.text.length) }
                        .collect { (from, to, size) -> start = from; end = to; length = size; publish() }
                }
                InterceptPlatformTextInput(interceptor) {
                    BasicTextField(
                        state = state,
                        modifier = Modifier.fillMaxWidth().height(140.dp).background(Color.White).padding(12.dp)
                            .semantics { contentDescription = "Rune Compose QA" },
                        textStyle = TextStyle(color = Color.Black, fontFamily = FontFamily.Monospace, fontSize = 20.sp),
                        lineLimits = TextFieldLineLimits.MultiLine(minHeightInLines = 3, maxHeightInLines = 3),
                        keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.None, autoCorrectEnabled = true),
                    )
                }
            }
        }
        editor = view
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            importantForAutofill = View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS
            addView(status)
            addView(view, LinearLayout.LayoutParams(-1, 0, 1f))
        }
        setContentView(root)
        if (Build.VERSION.SDK_INT >= 30) {
            window.setDecorFitsSystemWindows(false)
            root.setOnApplyWindowInsetsListener { target, insets ->
                val safe = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
                target.setPadding(safe.left, safe.top, safe.right, safe.bottom)
                insets
            }
        }
        publish()
    }

    override fun onDestroy() {
        disposed = true
        editor?.disposeComposition()
        editor = null
        super.onDestroy()
    }
    private fun wrap(connection: InputConnection): InputConnection {
        count("connections")
        return when {
            Build.VERSION.SDK_INT >= 33 -> Api33Connection(connection, ::count)
            Build.VERSION.SDK_INT >= 31 -> Api31Connection(connection, ::count)
            else -> ObservedConnection(connection, ::count)
        }
    }
    private fun count(name: String) { counts.getValue(name).incrementAndGet(); status.post { if (!disposed) publish() } }
    private fun publish() {
        status.text = (counts.mapValues { it.value.get() } + mapOf("selectionStart" to start,
            "selectionEnd" to end, "length" to length)).entries.joinToString(" ") { (name, value) -> "$name=$value" }
    }
    private open class ObservedConnection(target: InputConnection, protected val count: (String) -> Unit) : InputConnectionWrapper(target, false) {
        override fun getTextBeforeCursor(length: Int, flags: Int): CharSequence? { count("before"); return super.getTextBeforeCursor(length, flags) }
        override fun getTextAfterCursor(length: Int, flags: Int): CharSequence? { count("after"); return super.getTextAfterCursor(length, flags) }
        override fun getSelectedText(flags: Int): CharSequence? { count("selected"); return super.getSelectedText(flags) }
        override fun getExtractedText(request: ExtractedTextRequest?, flags: Int): ExtractedText? { count("extracted"); return super.getExtractedText(request, flags) }
    }
    private open class Api31Connection(target: InputConnection, count: (String) -> Unit) : ObservedConnection(target, count) {
        override fun getSurroundingText(beforeLength: Int, afterLength: Int, flags: Int): SurroundingText? { count("surrounding"); return super.getSurroundingText(beforeLength, afterLength, flags) }
    }
    private class Api33Connection(target: InputConnection, count: (String) -> Unit) : Api31Connection(target, count) {
        override fun takeSnapshot(): TextSnapshot? { count("snapshot"); return super.takeSnapshot() }
    }
}
