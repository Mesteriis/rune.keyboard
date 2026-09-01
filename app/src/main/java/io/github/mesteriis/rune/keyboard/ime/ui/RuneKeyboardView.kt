package io.github.mesteriis.rune.keyboard.ime.ui

import android.content.Context
import android.graphics.Typeface
import android.graphics.drawable.InsetDrawable
import android.os.Build
import android.util.AttributeSet
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.WindowInsets
import android.widget.LinearLayout
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.layout.KeySpec
import io.github.mesteriis.rune.keyboard.ime.layout.KeyStyle
import io.github.mesteriis.rune.keyboard.ime.layout.KeyboardLayout
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLayer
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState
import io.github.mesteriis.rune.keyboard.ime.model.ShiftMode

class RuneKeyboardView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null,
) : LinearLayout(context, attrs) {
    private var actionListener: ((KeyboardAction) -> Unit)? = null
    private var activeTouchCount = 0
    private var pendingRender: PendingRender? = null
    private val keyGap = resources.getDimensionPixelSize(R.dimen.keyboard_key_gap)
    private val keyHeight = resources.getDimensionPixelSize(R.dimen.keyboard_key_height)
    private val keyboardPadding = resources.getDimensionPixelSize(R.dimen.keyboard_padding)

    init {
        orientation = VERTICAL
        layoutDirection = LAYOUT_DIRECTION_LTR
        gravity = Gravity.CENTER_HORIZONTAL
        setPadding(
            keyboardPadding,
            keyboardPadding,
            keyboardPadding,
            keyboardPadding,
        )
        setOnApplyWindowInsetsListener { _, insets ->
            val navigationBars = navigationBarInsets(insets)
            val leftPadding = keyboardPadding + navigationBars.left
            val rightPadding = keyboardPadding + navigationBars.right
            val bottomPadding = keyboardPadding + navigationBars.bottom
            if (
                paddingLeft != leftPadding ||
                paddingRight != rightPadding ||
                paddingBottom != bottomPadding
            ) {
                setPadding(leftPadding, keyboardPadding, rightPadding, bottomPadding)
            }
            insets
        }
        setBackgroundColor(context.getColor(R.color.keyboard_background))
    }

    fun setOnActionListener(listener: (KeyboardAction) -> Unit) {
        actionListener = listener
    }

    fun render(layout: KeyboardLayout, state: KeyboardState) {
        if (activeTouchCount > 0) {
            pendingRender = PendingRender(layout, state)
            return
        }
        applyRender(layout, state)
    }

    private fun applyRender(layout: KeyboardLayout, state: KeyboardState) {
        removeAllViews()
        layout.rows.forEach { rowSpecs -> addView(createRow(rowSpecs, state)) }
    }

    fun cancelActiveTouches() {
        pendingRender = null
        for (rowIndex in 0 until childCount) {
            val row = getChildAt(rowIndex) as? LinearLayout ?: continue
            for (keyIndex in 0 until row.childCount) {
                (row.getChildAt(keyIndex) as? KeyboardKeyView)?.cancelPendingActions()
            }
        }
        activeTouchCount = 0
    }

    private fun createRow(specs: List<KeySpec>, state: KeyboardState): LinearLayout =
        LinearLayout(context).apply {
            orientation = HORIZONTAL
            layoutDirection = LAYOUT_DIRECTION_LTR
            gravity = Gravity.CENTER
            isBaselineAligned = false
            layoutParams = LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT)
            specs.forEach { spec -> addView(createKey(spec, state)) }
        }

    private fun createKey(spec: KeySpec, state: KeyboardState): View {
        val keyView = KeyboardKeyView(context).apply {
            text = spec.label
            gravity = Gravity.CENTER
            includeFontPadding = false
            maxLines = 1
            minWidth = 0
            setPadding(0, 0, 0, 0)
            setTextColor(
                context.getColor(
                    if (spec.style == KeyStyle.ACTION) R.color.key_text_accent else R.color.key_text,
                ),
            )
            setTextSize(
                TypedValue.COMPLEX_UNIT_PX,
                resources.getDimension(
                    if (spec.style == KeyStyle.CHARACTER) {
                        R.dimen.keyboard_key_text_size
                    } else {
                        R.dimen.keyboard_action_text_size
                    },
                ),
            )
            typeface = if (spec.style == KeyStyle.ACTION) Typeface.DEFAULT_BOLD else Typeface.DEFAULT
            background = InsetDrawable(
                context.getDrawable(
                    when (spec.style) {
                        KeyStyle.CHARACTER -> R.drawable.key_background
                        KeyStyle.ACTION -> R.drawable.key_action_background
                        KeyStyle.SPACE -> R.drawable.key_space_background
                        KeyStyle.SPACER -> android.R.color.transparent
                    },
                ),
                keyGap / 2,
            )
            isSelected = spec.action == KeyboardAction.Shift && state.shiftMode != ShiftMode.OFF
            contentDescription = contentDescriptionFor(spec, state)
            importantForAccessibility = if (spec.style == KeyStyle.SPACER) {
                IMPORTANT_FOR_ACCESSIBILITY_NO
            } else {
                IMPORTANT_FOR_ACCESSIBILITY_YES
            }
            visibility = if (spec.style == KeyStyle.SPACER) INVISIBLE else VISIBLE
            configure(
                primaryAction = spec.action,
                longPressAction = spec.longPressAction,
                repeatable = spec.action == KeyboardAction.Delete,
                actionListener = { action -> actionListener?.invoke(action) },
                touchStateListener = ::onKeyTouchStateChanged,
            )
        }
        keyView.layoutParams = LayoutParams(0, keyHeight, spec.weight).apply {
            setMargins(0, 0, 0, 0)
        }
        return keyView
    }

    private fun onKeyTouchStateChanged(isActive: Boolean) {
        activeTouchCount = if (isActive) {
            activeTouchCount + 1
        } else {
            (activeTouchCount - 1).coerceAtLeast(0)
        }
        if (activeTouchCount != 0) return

        val render = pendingRender ?: return
        pendingRender = null
        applyRender(render.layout, render.state)
    }

    private fun contentDescriptionFor(spec: KeySpec, state: KeyboardState): CharSequence? =
        when (spec.action) {
            is KeyboardAction.CommitLetter,
            is KeyboardAction.CommitText -> spec.label
            KeyboardAction.Shift -> context.getString(
                when (state.shiftMode) {
                    ShiftMode.LOCKED -> R.string.key_caps_lock
                    ShiftMode.AUTO,
                    ShiftMode.ONCE,
                    -> R.string.key_shift_on
                    ShiftMode.OFF -> R.string.key_shift
                },
            )
            KeyboardAction.Delete -> context.getString(R.string.key_delete)
            KeyboardAction.Space -> context.getString(R.string.key_space)
            KeyboardAction.Enter -> spec.accessibilityLabel ?: context.getString(
                when (spec.label) {
                    "→" -> R.string.key_go
                    "⌕" -> R.string.key_search
                    "➤" -> R.string.key_send
                    "›" -> R.string.key_next
                    "✓" -> R.string.key_done
                    "‹" -> R.string.key_previous
                    else -> R.string.key_enter
                },
            )
            KeyboardAction.ToggleSymbols -> context.getString(
                if (state.layer == KeyboardLayer.SYMBOLS) R.string.key_letters else R.string.key_symbols,
            )
            KeyboardAction.ToggleLanguage -> context.getString(R.string.key_language)
            KeyboardAction.NextInputMethod -> context.getString(R.string.key_next_keyboard)
            null -> null
    }

    @Suppress("DEPRECATION")
    private fun navigationBarInsets(insets: WindowInsets): NavigationBarInsets =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            insets.getInsets(
                WindowInsets.Type.navigationBars() or WindowInsets.Type.displayCutout(),
            ).let { safeInsets ->
                NavigationBarInsets(
                    left = safeInsets.left,
                    right = safeInsets.right,
                    bottom = safeInsets.bottom,
                )
            }
        } else {
            NavigationBarInsets(
                left = insets.systemWindowInsetLeft,
                right = insets.systemWindowInsetRight,
                bottom = insets.systemWindowInsetBottom,
            )
        }

    private data class NavigationBarInsets(
        val left: Int,
        val right: Int,
        val bottom: Int,
    )

    private data class PendingRender(
        val layout: KeyboardLayout,
        val state: KeyboardState,
    )
}
