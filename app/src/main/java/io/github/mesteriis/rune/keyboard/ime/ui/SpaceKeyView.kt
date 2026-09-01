package io.github.mesteriis.rune.keyboard.ime.ui

import android.content.Context
import android.os.SystemClock
import android.view.HapticFeedbackConstants
import android.view.MotionEvent
import android.view.ViewConfiguration
import android.widget.Button
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.ime.gesture.SpaceGestureDetector
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.ime.model.LanguageDirection

/**
 * The space bar. It is a separate view from [KeyboardKeyView] on purpose: gestures live only on
 * control keys, so letter keys structurally cannot grow a gesture path (INPUT-002).
 *
 * All arbitration happens in [SpaceGestureDetector]; this view only feeds it touches and turns the
 * resulting gesture events into keyboard actions and local visuals.
 */
internal class SpaceKeyView(
    context: Context,
    keyHeightPx: Int,
) : TextView(context), CancelableKey {
    private val density = resources.displayMetrics.density
    private val holdTimeoutMillis = ViewConfiguration.getLongPressTimeout().toLong()
    private val detector = SpaceGestureDetector(
        SpaceGestureDetector.Config(
            swipeThresholdPx = SpaceGestureDetector.SWIPE_THRESHOLD_DP * density,
            cursorStepPx = SpaceGestureDetector.CURSOR_STEP_DP * density,
            verticalEscapePx = keyHeightPx.toFloat(),
            doubleTapWindowMillis = DOUBLE_TAP_WINDOW_MILLIS,
        ),
    )

    private var actionListener: ((KeyboardAction) -> Unit)? = null
    private var touchStateListener: ((Boolean) -> Unit)? = null
    private var touchActive = false
    private var activePointerId = MotionEvent.INVALID_POINTER_ID
    private var restingLabel: CharSequence = ""

    private val holdRunnable = Runnable {
        handleEvents(detector.onHoldTimeout(SystemClock.uptimeMillis()))
    }

    init {
        isClickable = true
        isFocusable = true
        isSoundEffectsEnabled = false
        // Lets a language switch mid-gesture reach screen readers through the label change.
        accessibilityLiveRegion = ACCESSIBILITY_LIVE_REGION_POLITE
    }

    fun configure(
        actionListener: (KeyboardAction) -> Unit,
        touchStateListener: (Boolean) -> Unit,
    ) {
        cancelPendingActions()
        this.actionListener = actionListener
        this.touchStateListener = touchStateListener
        restingLabel = text ?: ""
    }

    /** Immediate feedback while the finger is still down; the full re-render follows on release. */
    fun showLanguage(label: String) {
        restingLabel = label
        text = label
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        val now = event.eventTime
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                activePointerId = event.getPointerId(0)
                beginTouch()
                isPressed = true
                parent?.requestDisallowInterceptTouchEvent(true)
                handleEvents(detector.onDown(event.x, event.y, now))
                postDelayed(holdRunnable, holdTimeoutMillis)
            }
            MotionEvent.ACTION_MOVE -> {
                val pointerIndex = event.findPointerIndex(activePointerId)
                if (pointerIndex >= 0) {
                    handleEvents(
                        detector.onMove(
                            event.getX(pointerIndex),
                            event.getY(pointerIndex),
                            now,
                        ),
                    )
                }
            }
            MotionEvent.ACTION_UP -> {
                val pointerIndex = event.findPointerIndex(activePointerId)
                val x = if (pointerIndex >= 0) event.getX(pointerIndex) else event.x
                val y = if (pointerIndex >= 0) event.getY(pointerIndex) else event.y
                removeCallbacks(holdRunnable)
                isPressed = false
                activePointerId = MotionEvent.INVALID_POINTER_ID
                val events = detector.onUp(x, y, now)
                // A plain tap goes through performClick so the accessibility path is identical.
                if (SpaceGestureDetector.GestureEvent.Tap in events) performClick()
                handleEvents(events)
                endTouch()
            }
            MotionEvent.ACTION_CANCEL -> cancelPendingActions()
        }
        return true
    }

    override fun performClick(): Boolean {
        super.performClick()
        actionListener?.invoke(KeyboardAction.Space)
        return true
    }

    override fun getAccessibilityClassName(): CharSequence = Button::class.java.name

    override fun onDetachedFromWindow() {
        cancelPendingActions()
        super.onDetachedFromWindow()
    }

    override fun cancelPendingActions() {
        removeCallbacks(holdRunnable)
        activePointerId = MotionEvent.INVALID_POINTER_ID
        isPressed = false
        handleEvents(detector.onCancel())
        endTouch()
    }

    private fun handleEvents(events: List<SpaceGestureDetector.GestureEvent>) {
        events.forEach(::handleEvent)
    }

    private fun handleEvent(event: SpaceGestureDetector.GestureEvent) {
        when (event) {
            // Committed straight from onTouchEvent via performClick.
            SpaceGestureDetector.GestureEvent.Tap -> Unit
            SpaceGestureDetector.GestureEvent.DoubleTap ->
                actionListener?.invoke(KeyboardAction.DoubleSpaceTap)
            is SpaceGestureDetector.GestureEvent.LanguageSwipe -> {
                val direction = when (event.direction) {
                    SpaceGestureDetector.SwipeDirection.LEFT -> LanguageDirection.PREVIOUS
                    SpaceGestureDetector.SwipeDirection.RIGHT -> LanguageDirection.NEXT
                }
                actionListener?.invoke(KeyboardAction.SwitchLanguage(direction))
            }
            SpaceGestureDetector.GestureEvent.CursorModeStarted -> {
                text = CURSOR_MODE_LABEL
                isPressed = true
                performHapticFeedback(HapticFeedbackConstants.LONG_PRESS)
            }
            is SpaceGestureDetector.GestureEvent.CursorMove ->
                actionListener?.invoke(KeyboardAction.MoveCursor(event.steps))
            SpaceGestureDetector.GestureEvent.CursorModeEnded,
            SpaceGestureDetector.GestureEvent.GestureCancelled,
            -> {
                text = restingLabel
                isPressed = false
            }
        }
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

    private companion object {
        const val CURSOR_MODE_LABEL = "◄ ▶"
        const val DOUBLE_TAP_WINDOW_MILLIS = 400L
    }
}
