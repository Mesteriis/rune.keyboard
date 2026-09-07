package io.github.mesteriis.rune.keyboard.ime.ui

import android.content.Context
import android.graphics.Typeface
import android.text.TextUtils
import android.util.TypedValue
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.ViewConfiguration
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityManager
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.RuneTrace
import io.github.mesteriis.rune.keyboard.smarttyping.telemetry.SmartTypingTraceSection
import io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem
import io.github.mesteriis.rune.keyboard.smarttyping.ui.SmartTypingViewState

/** Three permanent cells: candidate updates have no reference to keys, popups or keyboard state. */
internal class CandidateStripView(context: Context) : LinearLayout(context) {
    private var candidateListener: ((String) -> Unit)? = null
    private val cells = List(SmartTypingViewState.MAX_VISIBLE_CANDIDATES) {
        CandidateCell(context) { id -> candidateListener?.invoke(id) }
    }

    init {
        orientation = HORIZONTAL
        layoutDirection = LAYOUT_DIRECTION_LTR
        gravity = Gravity.CENTER
        isBaselineAligned = false
        importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_NO
        cells.forEach { cell ->
            addView(cell, LayoutParams(0, LayoutParams.MATCH_PARENT, 1f))
        }
        render(SmartTypingViewState.HIDDEN)
    }

    fun setOnCandidateSelectedListener(listener: (String) -> Unit) {
        candidateListener = listener
    }

    fun render(state: SmartTypingViewState) {
        RuneTrace.section(SmartTypingTraceSection.CANDIDATE_RENDER) {
            val childrenChanged = cells.count { it.visibility == VISIBLE } != state.candidates.size
            cells.forEachIndexed { index, cell ->
                val item = state.candidates.getOrNull(index)
                cell.bind(item, item != null && item.id == state.selectedCandidateId)
            }
            visibility = if (state.enabled) VISIBLE else GONE
            if (childrenChanged && isShown &&
                context.getSystemService(AccessibilityManager::class.java).isEnabled
            ) {
                // API 26 can retain the empty parent's child list when individual cells become
                // visible. The strip itself is excluded from TalkBack's tree, so publish the
                // completed structural update from its nearest exposed ancestor.
                val source = parentForAccessibility as? View ?: this
                source.sendAccessibilityEventUnchecked(
                    AccessibilityEvent.obtain(AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED).apply {
                        contentChangeTypes = AccessibilityEvent.CONTENT_CHANGE_TYPE_SUBTREE
                    },
                )
            }
        }
    }

    private class CandidateCell(
        context: Context,
        onSelected: (String) -> Unit,
    ) : TextView(context) {
        private var item: CandidateUiItem? = null
        private var pressedCandidate: CandidateUiItem? = null
        private var activePointerId = MotionEvent.INVALID_POINTER_ID
        private val touchSlop = ViewConfiguration.get(context).scaledTouchSlop

        init {
            gravity = Gravity.CENTER
            includeFontPadding = false
            maxLines = 1
            ellipsize = TextUtils.TruncateAt.END
            minWidth = 0
            minHeight = resources.getDimensionPixelSize(R.dimen.candidate_strip_height)
            val horizontalPadding = resources.getDimensionPixelSize(R.dimen.candidate_horizontal_padding)
            setPadding(horizontalPadding, 0, horizontalPadding, 0)
            setTextSize(TypedValue.COMPLEX_UNIT_PX, resources.getDimension(R.dimen.candidate_text_size))
            background = context.getDrawable(R.drawable.candidate_background)
            isSoundEffectsEnabled = false
            setOnClickListener { item?.let { current -> onSelected(current.id) } }
        }

        fun bind(item: CandidateUiItem?, selected: Boolean) {
            if (this.item != item) cancelTouch()
            this.item = item
            val label = item?.text.orEmpty()
            if (text.toString() != label) text = label
            isSelected = selected
            typeface = if (selected) Typeface.DEFAULT_BOLD else Typeface.DEFAULT
            setTextColor(context.getColor(if (selected) R.color.key_text_accent else R.color.key_text))
            contentDescription = item?.let {
                context.getString(
                    when (it) {
                        is CandidateUiItem.Original -> R.string.candidate_original
                        is CandidateUiItem.Correction -> R.string.candidate_correction
                        is CandidateUiItem.Punctuation -> R.string.candidate_punctuation
                    },
                    it.text,
                )
            }
            isEnabled = item != null
            isClickable = item != null
            isFocusable = item != null
            importantForAccessibility = if (item != null) {
                IMPORTANT_FOR_ACCESSIBILITY_YES
            } else {
                IMPORTANT_FOR_ACCESSIBILITY_NO
            }
            // A slot's size never depends on candidate length or candidate count.
            visibility = if (item != null) VISIBLE else INVISIBLE
        }

        override fun getAccessibilityClassName(): CharSequence = Button::class.java.name

        override fun onTouchEvent(event: MotionEvent): Boolean {
            if (!isEnabled) {
                cancelTouch()
                return false
            }
            val pointerIndex = event.findPointerIndex(activePointerId)
            if (event.actionMasked != MotionEvent.ACTION_DOWN && pointerIndex < 0) {
                cancelTouch()
                return true
            }
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    cancelTouch()
                    if (isInside(event, event.actionIndex)) {
                        activePointerId = event.getPointerId(event.actionIndex)
                        pressedCandidate = item
                        isPressed = true
                        parent?.requestDisallowInterceptTouchEvent(true)
                    }
                }
                MotionEvent.ACTION_MOVE -> {
                    if (!isInside(event, pointerIndex, touchSlop)) cancelTouch()
                }
                MotionEvent.ACTION_POINTER_UP -> {
                    if (event.getPointerId(event.actionIndex) == activePointerId) cancelTouch()
                }
                MotionEvent.ACTION_UP -> {
                    val shouldClick = event.getPointerId(event.actionIndex) == activePointerId &&
                        isInside(event, pointerIndex) && pressedCandidate != null && pressedCandidate == item
                    cancelTouch()
                    if (shouldClick) performClick()
                }
                MotionEvent.ACTION_CANCEL -> cancelTouch()
            }
            return true
        }

        override fun performClick(): Boolean = super.performClick()

        override fun onDetachedFromWindow() {
            cancelTouch()
            super.onDetachedFromWindow()
        }

        private fun cancelTouch() {
            activePointerId = MotionEvent.INVALID_POINTER_ID
            pressedCandidate = null
            isPressed = false
        }

        private fun isInside(event: MotionEvent, index: Int, slop: Int = 0): Boolean =
            event.getX(index) >= -slop && event.getX(index) < width + slop &&
                event.getY(index) >= -slop && event.getY(index) < height + slop

        override fun onInitializeAccessibilityNodeInfo(info: AccessibilityNodeInfo) {
            super.onInitializeAccessibilityNodeInfo(info)
            val current = item ?: return
            val action = when (current) {
                is CandidateUiItem.Original -> R.string.candidate_keep_original
                is CandidateUiItem.Correction -> R.string.candidate_apply_correction
                is CandidateUiItem.Punctuation -> R.string.candidate_apply_punctuation
            }
            info.removeAction(AccessibilityNodeInfo.AccessibilityAction.ACTION_CLICK)
            info.addAction(
                AccessibilityNodeInfo.AccessibilityAction(
                    AccessibilityNodeInfo.ACTION_CLICK,
                    context.getString(action),
                ),
            )
        }
    }
}
