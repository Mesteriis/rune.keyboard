package io.github.mesteriis.rune.keyboard.ime.gesture

import kotlin.math.abs

/** A downward flick chooses a secondary symbol only on release; a rejected flick cannot recover. */
internal class KeyFlickGesture(
    private val downX: Float,
    private val downY: Float,
    private val threshold: Float,
    private val horizontalLimit: Float,
    private val upwardLimit: Float,
    private val downwardLimit: Float,
) {
    enum class State { PENDING, SELECTED, REJECTED, CANCELLED }
    var state = State.PENDING
        private set
    var movedBeyondTap = false
        private set

    init {
        require(threshold > 0 && horizontalLimit > 0 && upwardLimit > 0 && downwardLimit >= threshold)
    }

    fun move(x: Float, y: Float): State {
        if (state == State.REJECTED || state == State.CANCELLED) return state
        val dx = x - downX
        val dy = y - downY
        state = when {
            !x.isFinite() || !y.isFinite() -> State.CANCELLED
            abs(dx) > horizontalLimit || dy < -upwardLimit || dy > downwardLimit -> State.REJECTED
            dy >= threshold && dy > abs(dx) * 1.25f -> State.SELECTED
            state == State.SELECTED && dy >= threshold * .55f -> State.SELECTED
            else -> State.PENDING
        }
        if (state != State.PENDING) movedBeyondTap = true
        return state
    }
}
