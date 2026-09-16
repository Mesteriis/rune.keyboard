package io.github.mesteriis.rune.keyboard.ime.ui

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.os.Bundle
import android.view.accessibility.AccessibilityNodeInfo
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.gesture.KeyFlickGesture
import android.graphics.drawable.Drawable
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
    var keyIcon: Drawable? = null
    var secondaryTextColor: Int = android.graphics.Color.GRAY
    private val flickPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { textAlign = Paint.Align.CENTER }
    private var flickGesture: KeyFlickGesture? = null


    override fun onDraw(canvas: Canvas) {
        val icon = keyIcon
        if (icon == null) {
            val alternate = spec?.flickDown
            if (alternate == null) {
                super.onDraw(canvas)
            } else if (flickGesture?.state == KeyFlickGesture.State.SELECTED) {
                flickPaint.typeface = typeface
                flickPaint.textSize = textSize
                flickPaint.color = currentTextColor
                val metrics = flickPaint.fontMetrics
                canvas.drawText(alternate.label, width / 2f, height / 2f - (metrics.ascent + metrics.descent) / 2, flickPaint)
            } else {
                val saved = canvas.save()
                canvas.translate(0f, 4f * resources.displayMetrics.density)
                super.onDraw(canvas)
                canvas.restoreToCount(saved)
                flickPaint.typeface = typeface
                flickPaint.textSize = minOf(10f * resources.displayMetrics.scaledDensity, height * .2f)
                flickPaint.color = secondaryTextColor
                canvas.drawText(alternate.label, width / 2f, -flickPaint.fontMetrics.ascent + 2f * resources.displayMetrics.density, flickPaint)
            }
        } else {
            // Keep the original TextView label and content description for accessibility.
            val size = minOf((24f * resources.displayMetrics.density).toInt(), width, height)
            val left = (width - size) / 2
            val top = (height - size) / 2
            icon.setBounds(left, top, left + size, top + size)
            icon.setTint(currentTextColor)
            icon.draw(canvas)
        }
    }
    private var spec: KeySpec? = null
    private var actionListener: ((KeyboardAction) -> Unit)? = null
    private var physicalTouchListener: ((Float, Float) -> Unit)? = null
    private var physicalTouchAllowed: (() -> Boolean)? = null
    private var physicalTapEligible = false
    private var physicalTapStamp: (() -> Long)? = null
    private var physicalTapResolver: ((Float, Float, Long) -> KeyboardAction?)? = null
    private var downStamp = 0L
    private var downTime = 0L
    private var touchDownX = 0f
    private var touchDownY = 0f
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
        physicalTouchListener: ((Float, Float) -> Unit)? = null,
        physicalTouchAllowed: (() -> Boolean)? = null,
        physicalTapStamp: (() -> Long)? = null,
        physicalTapResolver: ((Float, Float, Long) -> KeyboardAction?)? = null,
    ) {
        cancelPendingActions()
        this.spec = spec
        this.repeatable = spec.action == KeyboardAction.Delete
        this.actionListener = actionListener
        this.touchStateListener = touchStateListener
        this.popupHost = popupHost
        this.physicalTouchListener = physicalTouchListener
        this.physicalTouchAllowed = physicalTouchAllowed
        this.physicalTapStamp = physicalTapStamp
        this.physicalTapResolver = physicalTapResolver
        isEnabled = spec.action != null
        isClickable = spec.action != null
        isLongClickable = spec.longPressAlternates.isNotEmpty() || repeatable
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (!isEnabled) return false
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                beginTouch()
                physicalTapEligible = event.pointerCount == 1 && physicalTouchListener != null &&
                    (physicalTouchAllowed?.invoke() != false)
                downStamp = if (physicalTapEligible) physicalTapStamp?.invoke() ?: 0L else 0L
                downTime = event.eventTime
                touchDownX = event.x
                touchDownY = event.y
                flickGesture = if (spec?.flickDown != null) KeyFlickGesture(
                    downX = event.x,
                    downY = event.y,
                    threshold = maxOf(18f * resources.displayMetrics.density, height * .32f),
                    horizontalLimit = maxOf(touchSlop.toFloat(), width * .65f),
                    upwardLimit = touchSlop.toFloat(),
                    downwardLimit = maxOf(36f * resources.displayMetrics.density, height * 1.8f),
                ) else null
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
            MotionEvent.ACTION_POINTER_DOWN -> {
                physicalTapEligible = false
                if (flickGesture != null && !alternatesActive) {
                    popupHost?.onKeyCancel(this)
                    cancelPendingActions()
                }
            }
            MotionEvent.ACTION_MOVE -> {
                if (event.pointerCount != 1) physicalTapEligible = false
                if (event.pointerCount != 1 && flickGesture != null && !alternatesActive) {
                    popupHost?.onKeyCancel(this)
                    cancelPendingActions()
                    return true
                }
                if (updateFlick(event)) return true
                if (alternatesActive) {
                    // The finger is expected to leave the key while picking an alternate.
                    popupHost?.onKeyMove(this, event.x, event.y)
                } else if (armed && flickGesture == null && !isInsideWithSlop(event.x, event.y)) {
                    popupHost?.onKeyCancel(this)
                    finishGesture()
                    endTouch()
                }
            }
            MotionEvent.ACTION_UP -> {
                if (updateFlick(event)) return true
                if (armed && !longPressTriggered && flickGesture?.state == KeyFlickGesture.State.SELECTED) {
                    val action = spec?.flickDown?.action
                    popupHost?.onKeyCancel(this)
                    finishGesture()
                    action?.let { actionListener?.invoke(it) }
                    endTouch()
                } else if (alternatesActive) {
                    val selected = popupHost?.onKeyUp(this)
                    finishGesture()
                    selected?.let { action -> actionListener?.invoke(action) }
                    endTouch()
                } else {
                    val shouldClick = armed && !longPressTriggered
                    val capturePhysicalTap = shouldClick && physicalTapEligible && event.pointerCount == 1 &&
                        touchDownX >= 0f && touchDownX < width && touchDownY >= 0f && touchDownY < height &&
                        event.x >= 0f && event.x < width && event.y >= 0f && event.y < height
                    val stamp = downStamp
                    val shortTap = event.eventTime - downTime in 0 until ViewConfiguration.getLongPressTimeout().toLong()
                    val contactX = touchDownX
                    val contactY = touchDownY
                    popupHost?.onKeyCancel(this)
                    finishGesture()
                    if (shouldClick) {
                        // Report the original contact before dispatching the acknowledged action.
                        // Accessibility performClick, repeats, cancels, and alternates never enter here.
                        val replacement = if (capturePhysicalTap && shortTap && stamp != 0L &&
                            physicalTapStamp?.invoke() == stamp) {
                            physicalTapResolver?.invoke(contactX, contactY, stamp)
                        } else null
                        if (replacement == null && capturePhysicalTap) physicalTouchListener?.invoke(contactX, contactY)
                        if (replacement == null) performClick() else {
                            // No temporary action can leak into accessibility or a subsequent click.
                            super.performClick()
                            actionListener?.invoke(replacement)
                        }
                    }
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

    /** Returns true only after the entire key interaction, rather than just flick recognition, ends. */
    private fun updateFlick(event: MotionEvent): Boolean {
        val gesture = flickGesture ?: return false
        if (!armed || alternatesActive || longPressTriggered) return false
        val previous = gesture.state
        val next = gesture.move(event.x, event.y)
        if (gesture.movedBeyondTap) {
            physicalTapEligible = false
            removeCallbacks(longPressRunnable)
        }
        if (next == KeyFlickGesture.State.CANCELLED) {
            popupHost?.onKeyCancel(this)
            cancelPendingActions()
            return true
        }
        if (next == KeyFlickGesture.State.REJECTED) {
            if (!isInsideWithSlop(event.x, event.y)) {
                popupHost?.onKeyCancel(this)
                cancelPendingActions()
                return true
            }
        }
        if (next != previous) {
            popupHost?.onKeyCancel(this)
            invalidate()
        }
        return false
    }

    override fun onInitializeAccessibilityNodeInfo(info: AccessibilityNodeInfo) {
        super.onInitializeAccessibilityNodeInfo(info)
        spec?.flickDown?.let { alternate ->
            if (isEnabled) info.addAction(AccessibilityNodeInfo.AccessibilityAction(
                R.id.action_key_flick, context.getString(R.string.key_flick_action, alternate.label),
            ))
        }
    }

    override fun performAccessibilityAction(action: Int, arguments: Bundle?): Boolean {
        if (action == R.id.action_key_flick && isEnabled) {
            val alternate = spec?.flickDown ?: return false
            actionListener?.invoke(alternate.action)
            return true
        }
        return super.performAccessibilityAction(action, arguments)
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
        flickGesture = null
        invalidate()
        physicalTapEligible = false
        downStamp = 0L
        downTime = 0L
        touchDownX = 0f
        touchDownY = 0f
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
