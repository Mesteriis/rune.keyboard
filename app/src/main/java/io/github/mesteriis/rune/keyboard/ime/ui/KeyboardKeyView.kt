package io.github.mesteriis.rune.keyboard.ime.ui

import android.content.Context
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.ViewConfiguration
import android.widget.Button
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction

internal class KeyboardKeyView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : TextView(context, attrs) {
    private var primaryAction: KeyboardAction? = null
    private var longPressAction: KeyboardAction? = null
    private var actionListener: ((KeyboardAction) -> Unit)? = null
    private var touchStateListener: ((Boolean) -> Unit)? = null
    private var repeatable = false
    private var armed = false
    private var longPressTriggered = false
    private var touchActive = false
    private val touchSlop = ViewConfiguration.get(context).scaledTouchSlop

    private val repeatRunnable = object : Runnable {
        override fun run() {
            if (!armed || !repeatable) return
            performClick()
            postDelayed(this, REPEAT_INTERVAL_MILLIS)
        }
    }

    private val longPressRunnable = Runnable {
        if (!armed) return@Runnable
        if (repeatable) {
            longPressTriggered = true
            performClick()
            postDelayed(repeatRunnable, REPEAT_INTERVAL_MILLIS)
        } else if (longPressAction != null) {
            longPressTriggered = performLongClick()
        }
    }

    init {
        isClickable = true
        isFocusable = true
        isSoundEffectsEnabled = false
    }

    fun configure(
        primaryAction: KeyboardAction?,
        longPressAction: KeyboardAction?,
        repeatable: Boolean,
        actionListener: (KeyboardAction) -> Unit,
        touchStateListener: (Boolean) -> Unit,
    ) {
        cancelPendingActions()
        this.primaryAction = primaryAction
        this.longPressAction = longPressAction
        this.repeatable = repeatable
        this.actionListener = actionListener
        this.touchStateListener = touchStateListener
        isEnabled = primaryAction != null
        isClickable = primaryAction != null
        isLongClickable = longPressAction != null || repeatable
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (!isEnabled) return false
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                beginTouch()
                armed = true
                longPressTriggered = false
                isPressed = true
                parent?.requestDisallowInterceptTouchEvent(true)
                if (repeatable || longPressAction != null) {
                    postDelayed(longPressRunnable, ViewConfiguration.getLongPressTimeout().toLong())
                }
            }
            MotionEvent.ACTION_MOVE -> {
                if (armed && !isInsideWithSlop(event.x, event.y)) {
                    finishGesture()
                    endTouch()
                }
            }
            MotionEvent.ACTION_UP -> {
                val shouldClick = armed && !longPressTriggered
                finishGesture()
                if (shouldClick) performClick()
                endTouch()
            }
            MotionEvent.ACTION_CANCEL -> cancelPendingActions()
        }
        return true
    }

    override fun performClick(): Boolean {
        val handledBySuper = super.performClick()
        val action = primaryAction ?: return handledBySuper
        actionListener?.invoke(action)
        return true
    }

    override fun performLongClick(): Boolean {
        val handledBySuper = super.performLongClick()
        val action = longPressAction ?: return handledBySuper
        actionListener?.invoke(action)
        return true
    }

    override fun getAccessibilityClassName(): CharSequence = Button::class.java.name

    override fun onDetachedFromWindow() {
        cancelPendingActions()
        super.onDetachedFromWindow()
    }

    fun cancelPendingActions() {
        finishGesture()
        endTouch()
    }

    private fun finishGesture() {
        armed = false
        longPressTriggered = false
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

    private companion object {
        const val REPEAT_INTERVAL_MILLIS = 55L
    }
}
