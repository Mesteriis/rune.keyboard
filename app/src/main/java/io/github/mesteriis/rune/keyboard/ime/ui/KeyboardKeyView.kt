package io.github.mesteriis.rune.keyboard.ime.ui

import android.content.Context
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.ViewConfiguration
import android.widget.Button
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.ime.gesture.BackspaceRepeatSchedule
import io.github.mesteriis.rune.keyboard.ime.layout.KeySpec
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction

/** Every key view must be able to abandon an in-flight gesture on demand (REL-006). */
internal interface CancelableKey {
    fun cancelPendingActions()
}

/**
 * The keyboard view side of the popup protocol. The key keeps the touch stream; the host only
 * reacts to it.
 */
internal interface KeyPopupHost {
    fun onKeyDown(key: KeyboardKeyView, spec: KeySpec)
    fun onKeyLongPress(key: KeyboardKeyView, spec: KeySpec): Boolean
    fun onKeyMove(key: KeyboardKeyView, localX: Float, localY: Float)
    fun onKeyUp(key: KeyboardKeyView): KeyboardAction?
    fun onKeyCancel(key: KeyboardKeyView)
}

internal class KeyboardKeyView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : TextView(context, attrs), CancelableKey {
    private var spec: KeySpec? = null
    private var actionListener: ((KeyboardAction) -> Unit)? = null
    private var touchStateListener: ((Boolean) -> Unit)? = null
    private var popupHost: KeyPopupHost? = null
    private var repeatable = false
    private var armed = false
    private var longPressTriggered = false
    private var alternatesActive = false
    private var touchActive = false
    private var repeatCount = 0
    private val touchSlop = ViewConfiguration.get(context).scaledTouchSlop

    private val repeatRunnable = object : Runnable {
        override fun run() {
            if (!armed || !repeatable) return
            performClick()
            repeatCount++
            postDelayed(this, BackspaceRepeatSchedule.intervalMillis(repeatCount))
        }
    }

    private val longPressRunnable = Runnable {
        if (!armed) return@Runnable
        val currentSpec = spec
        if (repeatable) {
            longPressTriggered = true
            performClick()
            repeatCount = 1
            postDelayed(repeatRunnable, BackspaceRepeatSchedule.intervalMillis(repeatCount))
        } else if (currentSpec != null && currentSpec.longPressAlternates.isNotEmpty()) {
            alternatesActive = popupHost?.onKeyLongPress(this, currentSpec) ?: false
            longPressTriggered = if (alternatesActive) true else performLongClick()
        }
    }

    init {
        isClickable = true
        isFocusable = true
        isSoundEffectsEnabled = false
    }

    fun configure(
        spec: KeySpec,
        actionListener: (KeyboardAction) -> Unit,
        touchStateListener: (Boolean) -> Unit,
        popupHost: KeyPopupHost?,
    ) {
        cancelPendingActions()
        this.spec = spec
        this.repeatable = spec.action == KeyboardAction.Delete
        this.actionListener = actionListener
        this.touchStateListener = touchStateListener
        this.popupHost = popupHost
        isEnabled = spec.action != null
        isClickable = spec.action != null
        isLongClickable = spec.longPressAlternates.isNotEmpty() || repeatable
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (!isEnabled) return false
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                beginTouch()
                armed = true
                longPressTriggered = false
                alternatesActive = false
                repeatCount = 0
                isPressed = true
                parent?.requestDisallowInterceptTouchEvent(true)
                spec?.let { current -> popupHost?.onKeyDown(this, current) }
                if (repeatable || spec?.longPressAlternates?.isNotEmpty() == true) {
                    postDelayed(longPressRunnable, ViewConfiguration.getLongPressTimeout().toLong())
                }
            }
            MotionEvent.ACTION_MOVE -> {
                if (alternatesActive) {
                    // The finger is expected to leave the key while picking an alternate.
                    popupHost?.onKeyMove(this, event.x, event.y)
                } else if (armed && !isInsideWithSlop(event.x, event.y)) {
                    popupHost?.onKeyCancel(this)
                    finishGesture()
                    endTouch()
                }
            }
            MotionEvent.ACTION_UP -> {
                if (alternatesActive) {
                    val selected = popupHost?.onKeyUp(this)
                    finishGesture()
                    selected?.let { action -> actionListener?.invoke(action) }
                    endTouch()
                } else {
                    val shouldClick = armed && !longPressTriggered
                    popupHost?.onKeyCancel(this)
                    finishGesture()
                    if (shouldClick) performClick()
                    endTouch()
                }
            }
            MotionEvent.ACTION_CANCEL -> {
                popupHost?.onKeyCancel(this)
                cancelPendingActions()
            }
        }
        return true
    }

    override fun performClick(): Boolean {
        val handledBySuper = super.performClick()
        val action = spec?.action ?: return handledBySuper
        actionListener?.invoke(action)
        return true
    }

    /**
     * Reached through the accessibility long-press, where sliding to a popup cell is not possible;
     * the first alternate is the documented default.
     */
    override fun performLongClick(): Boolean {
        val handledBySuper = super.performLongClick()
        val action = spec?.longPressAlternates?.firstOrNull()?.action ?: return handledBySuper
        actionListener?.invoke(action)
        return true
    }

    override fun getAccessibilityClassName(): CharSequence = Button::class.java.name

    override fun onDetachedFromWindow() {
        popupHost?.onKeyCancel(this)
        cancelPendingActions()
        super.onDetachedFromWindow()
    }

    override fun cancelPendingActions() {
        finishGesture()
        endTouch()
    }

    private fun finishGesture() {
        armed = false
        longPressTriggered = false
        alternatesActive = false
        repeatCount = 0
        isPressed = false
        removeCallbacks(longPressRunnable)
        removeCallbacks(repeatRunnable)
    }

    private fun beginTouch() {
        if (touchActive) return
        touchActive = true
        touchStateListener?.invoke(true)
    }

    private fun endTouch() {
        if (!touchActive) return
        touchActive = false
        touchStateListener?.invoke(false)
    }

    private fun isInsideWithSlop(x: Float, y: Float): Boolean =
        x >= -touchSlop && x < width + touchSlop && y >= -touchSlop && y < height + touchSlop
}
