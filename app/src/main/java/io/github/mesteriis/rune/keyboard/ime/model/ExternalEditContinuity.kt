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

    fun onStart(packageName: String?, fieldId: Int, restarting: Boolean): Boolean {
        val next = packageName?.takeIf { it.isNotBlank() }?.let { Target(it, fieldId) }
        required = required && restarting && next != null && next == target
        target = next
        return required
    }
}
