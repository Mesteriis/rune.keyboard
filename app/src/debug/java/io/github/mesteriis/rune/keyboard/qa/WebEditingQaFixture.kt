package io.github.mesteriis.rune.keyboard.qa

import android.annotation.SuppressLint
import android.content.Context
import android.os.Build
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.ExtractedText
import android.view.inputmethod.ExtractedTextRequest
import android.view.inputmethod.InputConnection
import android.view.inputmethod.InputConnectionWrapper
import android.view.inputmethod.InputMethodManager
import android.view.inputmethod.SurroundingText
import android.view.inputmethod.TextSnapshot
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.LinearLayout
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R
import java.io.ByteArrayInputStream
import java.util.concurrent.atomic.AtomicInteger

/** Debug-only offline HTML editor. The bridge publishes numeric selection, never editor text. */
@SuppressLint("SetJavaScriptEnabled", "SetTextI18n")
internal class WebEditingQaFixture(private val context: Context) {
    private val counts = listOf("connections", "before", "after", "selected", "extracted", "surrounding", "snapshot")
        .associateWith { AtomicInteger() }
    private var start = 0
    private var end = 0
    private var length = 0
    private var ready = false
    private var disposed = false
    private val status = TextView(context).apply { id = R.id.qa_webview_stats; textSize = 11f }
    private val web = object : WebView(context) {
        override fun onCreateInputConnection(outAttrs: EditorInfo): InputConnection? {
            val connection = super.onCreateInputConnection(outAttrs) ?: return null
            count("connections")
            return when {
                Build.VERSION.SDK_INT >= 33 -> Api33Connection(connection, ::count)
                Build.VERSION.SDK_INT >= 31 -> Api31Connection(connection, ::count)
                else -> ObservedConnection(connection, ::count)
            }
        }
    }
    val content = LinearLayout(context).apply {
        orientation = LinearLayout.VERTICAL
        val padding = (8 * resources.displayMetrics.density).toInt()
        setPadding(padding, padding, padding, padding)
        importantForAutofill = View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS
        addView(status)
        addView(web, LinearLayout.LayoutParams(-1, 0, 1f))
    }

    init {
        web.apply {
            id = R.id.qa_webview
            importantForAutofill = View.IMPORTANT_FOR_AUTOFILL_NO_EXCLUDE_DESCENDANTS
            settings.javaScriptEnabled = true // Only the fixed inline document below is loaded.
            settings.blockNetworkLoads = true
            settings.allowFileAccess = false
            settings.allowContentAccess = false
            settings.domStorageEnabled = false
            settings.cacheMode = android.webkit.WebSettings.LOAD_NO_CACHE
            addJavascriptInterface(object {
                @JavascriptInterface fun selection(from: Int, to: Int, size: Int) {
                    if (size !in 0..10_000 || from !in 0..size || to !in 0..size) return
                    status.post {
                        if (!disposed) {
                            start = from; end = to; length = size; ready = true
                            publish()
                        }
                    }
                }
            }, "RuneQa")
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean = true
                override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse =
                    WebResourceResponse("text/plain", "UTF-8", ByteArrayInputStream(ByteArray(0)))
                override fun onPageFinished(view: WebView, url: String) {
                    if (disposed) return
                    view.evaluateJavascript("document.getElementById('editor').focus(); report();", null)
                    view.requestFocus()
                    view.post { if (!disposed) context.getSystemService(InputMethodManager::class.java).showSoftInput(view, 0) }
                }
            }
            loadDataWithBaseURL("https://rune.invalid/", HTML, "text/html", "UTF-8", null)
        }
        publish()
    }

    fun dispose() {
        disposed = true
        web.stopLoading()
        web.removeJavascriptInterface("RuneQa")
        (web.parent as? ViewGroup)?.removeView(web)
        web.destroy()
    }
    private fun count(name: String) { counts.getValue(name).incrementAndGet(); status.post { if (!disposed) publish() } }
    private fun publish() {
        status.text = (counts.mapValues { it.value.get() } + mapOf("ready" to if (ready) 1 else 0,
            "selectionStart" to start, "selectionEnd" to end, "length" to length))
            .entries.joinToString(" ") { (name, value) -> "$name=$value" }
    }

    private open class ObservedConnection(target: InputConnection, protected val count: (String) -> Unit) : InputConnectionWrapper(target, false) {
        override fun getTextBeforeCursor(length: Int, flags: Int): CharSequence? { count("before"); return super.getTextBeforeCursor(length, flags) }
        override fun getTextAfterCursor(length: Int, flags: Int): CharSequence? { count("after"); return super.getTextAfterCursor(length, flags) }
        override fun getSelectedText(flags: Int): CharSequence? { count("selected"); return super.getSelectedText(flags) }
        override fun getExtractedText(request: ExtractedTextRequest?, flags: Int): ExtractedText? { count("extracted"); return super.getExtractedText(request, flags) }
    }
    private open class Api31Connection(target: InputConnection, count: (String) -> Unit) : ObservedConnection(target, count) {
        override fun getSurroundingText(beforeLength: Int, afterLength: Int, flags: Int): SurroundingText? {
            count("surrounding"); return super.getSurroundingText(beforeLength, afterLength, flags)
        }
    }
    private class Api33Connection(target: InputConnection, count: (String) -> Unit) : Api31Connection(target, count) {
        override fun takeSnapshot(): TextSnapshot? { count("snapshot"); return super.takeSnapshot() }
    }
    private companion object {
        val HTML = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head>
            <body><textarea id="editor" aria-label="Rune WebView QA" rows="3" autocapitalize="off" spellcheck="true"
            style="font:20px monospace;width:95%"></textarea><script>
            const editor=document.getElementById('editor');
            function report(){RuneQa.selection(editor.selectionStart,editor.selectionEnd,editor.value.length);}
            document.addEventListener('selectionchange',report);editor.addEventListener('input',report);
            editor.addEventListener('focus',report);report();
            </script></body></html>""".trimIndent()
    }
}
