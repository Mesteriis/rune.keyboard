package io.github.mesteriis.rune.keyboard.ime.gesture

/**
 * The single arbiter of every space bar gesture (SPACE-005): tap, double tap, horizontal swipe
 * for language switching, and hold-to-move-cursor.
 *
 * Pure Kotlin by design. Distances arrive already converted to pixels, time arrives with each
 * event, and timeouts are delivered by the caller — nothing here schedules or measures anything,
 * so the whole state machine is unit-testable on the JVM.
 */
class SpaceGestureDetector(private val config: Config) {

    data class Config(
        val swipeThresholdPx: Float,
        val cursorStepPx: Float,
        val verticalEscapePx: Float,
        val doubleTapWindowMillis: Long,
        val maxCursorStepsPerEvent: Int = MAX_CURSOR_STEPS_PER_EVENT,
    ) {
        init {
            require(swipeThresholdPx > 0f) { "Swipe threshold must be positive" }
            require(cursorStepPx > 0f) { "Cursor step must be positive" }
            require(verticalEscapePx > 0f) { "Vertical escape distance must be positive" }
            require(doubleTapWindowMillis > 0L) { "Double tap window must be positive" }
            require(maxCursorStepsPerEvent > 0) { "Cursor step cap must be positive" }
        }
    }

    enum class SwipeDirection {
        LEFT,
        RIGHT,
    }

    sealed interface GestureEvent {
        data object Tap : GestureEvent
        data object DoubleTap : GestureEvent
        data class LanguageSwipe(val direction: SwipeDirection) : GestureEvent
        data object CursorModeStarted : GestureEvent
        data class CursorMove(val steps: Int) : GestureEvent
        data object CursorModeEnded : GestureEvent
        data object GestureCancelled : GestureEvent
    }

    private sealed interface State {
        data object Idle : State
        data class TapCandidate(val lastTapUpMillis: Long) : State
        data class Pressed(val downX: Float, val downY: Float, val lastX: Float) : State
        data class DoubleTapCandidate(val downX: Float, val downY: Float, val lastX: Float) : State
        data object LanguageSwipe : State
        data class CursorMode(val lastEmitX: Float, val accumulatorPx: Float) : State
        data object Cancelled : State
    }

    private var state: State = State.Idle

    val isInCursorMode: Boolean
        get() = state is State.CursorMode

    fun onDown(x: Float, y: Float, timeMillis: Long): List<GestureEvent> {
        val current = state
        val followsRecentTap = current is State.TapCandidate &&
            timeMillis - current.lastTapUpMillis in 0..config.doubleTapWindowMillis
        state = if (followsRecentTap) {
            State.DoubleTapCandidate(downX = x, downY = y, lastX = x)
        } else {
            State.Pressed(downX = x, downY = y, lastX = x)
        }
        return emptyList()
    }

    fun onMove(x: Float, y: Float, timeMillis: Long): List<GestureEvent> = when (val current = state) {
        is State.Pressed -> onUndecidedMove(current.downX, current.downY, x, y, isDoubleTap = false)
        is State.DoubleTapCandidate ->
            onUndecidedMove(current.downX, current.downY, x, y, isDoubleTap = true)
        is State.CursorMode -> onCursorMove(current, x)
        State.Idle,
        State.LanguageSwipe,
        State.Cancelled,
        is State.TapCandidate,
        -> emptyList()
    }

    fun onUp(x: Float, y: Float, timeMillis: Long): List<GestureEvent> = when (state) {
        is State.Pressed -> {
            state = State.TapCandidate(lastTapUpMillis = timeMillis)
            listOf(GestureEvent.Tap)
        }
        is State.DoubleTapCandidate -> {
            // Tap history resets so a third quick tap starts over instead of chaining.
            state = State.Idle
            listOf(GestureEvent.DoubleTap)
        }
        is State.CursorMode -> {
            state = State.Idle
            listOf(GestureEvent.CursorModeEnded)
        }
        State.LanguageSwipe,
        State.Cancelled,
        -> {
            state = State.Idle
            emptyList()
        }
        State.Idle,
        is State.TapCandidate,
        -> emptyList()
    }

    fun onHoldTimeout(timeMillis: Long): List<GestureEvent> = when (val current = state) {
        is State.Pressed -> enterCursorMode(current.lastX)
        is State.DoubleTapCandidate -> enterCursorMode(current.lastX)
        State.Idle,
        State.LanguageSwipe,
        State.Cancelled,
        is State.TapCandidate,
        is State.CursorMode,
        -> emptyList()
    }

    fun onCancel(): List<GestureEvent> {
        val current = state
        state = State.Idle
        return when (current) {
            is State.CursorMode -> listOf(GestureEvent.CursorModeEnded)
            is State.Pressed,
            is State.DoubleTapCandidate,
            State.LanguageSwipe,
            -> listOf(GestureEvent.GestureCancelled)
            State.Idle,
            State.Cancelled,
            is State.TapCandidate,
            -> emptyList()
        }
    }

    private fun onUndecidedMove(
        downX: Float,
        downY: Float,
        x: Float,
        y: Float,
        isDoubleTap: Boolean,
    ): List<GestureEvent> {
        val verticalTravel = y - downY
        if (verticalTravel < -config.verticalEscapePx || verticalTravel > config.verticalEscapePx) {
            state = State.Cancelled
            return listOf(GestureEvent.GestureCancelled)
        }
        val horizontalTravel = x - downX
        val exceededSwipeThreshold = horizontalTravel <= -config.swipeThresholdPx ||
            horizontalTravel >= config.swipeThresholdPx
        if (exceededSwipeThreshold) {
            state = State.LanguageSwipe
            val direction = if (horizontalTravel > 0f) SwipeDirection.RIGHT else SwipeDirection.LEFT
            return listOf(GestureEvent.LanguageSwipe(direction))
        }
        state = if (isDoubleTap) {
            State.DoubleTapCandidate(downX = downX, downY = downY, lastX = x)
        } else {
            State.Pressed(downX = downX, downY = downY, lastX = x)
        }
        return emptyList()
    }

    private fun enterCursorMode(anchorX: Float): List<GestureEvent> {
        state = State.CursorMode(lastEmitX = anchorX, accumulatorPx = 0f)
        return listOf(GestureEvent.CursorModeStarted)
    }

    private fun onCursorMove(current: State.CursorMode, x: Float): List<GestureEvent> {
        val accumulated = current.accumulatorPx + (x - current.lastEmitX)
        val rawSteps = (accumulated / config.cursorStepPx).toInt()
        if (rawSteps == 0) {
            state = current.copy(lastEmitX = x, accumulatorPx = accumulated)
            return emptyList()
        }
        val steps = rawSteps.coerceIn(-config.maxCursorStepsPerEvent, config.maxCursorStepsPerEvent)
        state = State.CursorMode(
            lastEmitX = x,
            accumulatorPx = accumulated - rawSteps * config.cursorStepPx,
        )
        return listOf(GestureEvent.CursorMove(steps))
    }

    companion object {
        const val SWIPE_THRESHOLD_DP = 40f
        const val CURSOR_STEP_DP = 16f
        const val MAX_CURSOR_STEPS_PER_EVENT = 20
    }
}
