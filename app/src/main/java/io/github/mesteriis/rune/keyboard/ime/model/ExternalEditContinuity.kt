package io.github.mesteriis.rune.keyboard.ime.model

/** One RAM-only protective flag for the framework's current editor; never text or ownership. */
internal class ExternalEditContinuity {
    private data class Target(val packageName: String, val fieldId: Int)
    private var target: Target? = null
    private var required = false

    fun observe(controllerEnabled: Boolean, boundaryRequired: Boolean) {
        // A protected/raw editor has no controller ownership from which to infer a cleared flag.
        if (controllerEnabled) required = boundaryRequired
    }

    fun arm() { required = true }

    fun onStart(packageName: String?, fieldId: Int, restarting: Boolean,
        selectionStart: Int, selectionEnd: Int): Boolean {
        val next = packageName?.takeIf { it.isNotBlank() }?.let { Target(it, fieldId) }
        // Every start disowns the old typing context. A nonzero left boundary means unknown
        // preceding text even in a new service, without reading or retaining that text.
        val unknownLeftContext = minOf(selectionStart, selectionEnd) > 0
        required = unknownLeftContext || (required && restarting && next != null && next == target)
        target = next
        return required
    }
}
