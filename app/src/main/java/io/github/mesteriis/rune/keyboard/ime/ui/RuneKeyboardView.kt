package io.github.mesteriis.rune.keyboard.ime.ui

import android.content.Context
import android.graphics.Typeface
import android.graphics.drawable.InsetDrawable
import android.os.Build
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.WindowInsets
import android.widget.LinearLayout
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.layout.KeySpec
import io.github.mesteriis.rune.keyboard.ime.layout.KeyStyle
import io.github.mesteriis.rune.keyboard.ime.layout.KeyboardLayout
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLayer
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState
import io.github.mesteriis.rune.keyboard.ime.model.ShiftMode
import io.github.mesteriis.rune.keyboard.settings.KeyboardViewMetrics

internal class RuneKeyboardView(
    context: Context,
    private val metrics: KeyboardViewMetrics,
) : LinearLayout(context), KeyPopupHost {
    private var actionListener: ((KeyboardAction) -> Unit)? = null
    private var activeTouchCount = 0
    private var pendingRender: PendingRender? = null
    private var previewEnabled = true
    private var inputPolicy = InputPolicy.NORMAL
    private var popupController: KeyPopupController? = null
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

    fun setPopupPolicy(previewEnabled: Boolean, inputPolicy: InputPolicy) {
        this.previewEnabled = previewEnabled
        this.inputPolicy = inputPolicy
    }

    fun render(layout: KeyboardLayout, state: KeyboardState) {
        if (activeTouchCount > 0) {
            pendingRender = PendingRender(layout, state)
            return
        }
        applyRender(layout, state)
    }

    private fun applyRender(layout: KeyboardLayout, state: KeyboardState) {
        // Key views are about to be discarded; a popup anchored to one of them must go first.
        popupController?.dismissAll()
        removeAllViews()
        layout.rows.forEach { rowSpecs -> addView(createRow(rowSpecs, state)) }
    }

    fun cancelActiveTouches() {
        pendingRender = null
        popupController?.dismissAll()
        forEachKey { key -> key.cancelPendingActions() }
        activeTouchCount = 0
    }

    fun showLanguagePreview(label: String) {
        forEachKey { key -> (key as? SpaceKeyView)?.showLanguage(label) }
    }

    override fun onKeyDown(key: KeyboardKeyView, spec: KeySpec) {
        val shouldPreview = PopupGeometry.shouldShowPreview(
            style = spec.style,
            previewEnabled = previewEnabled,
            inputPolicy = inputPolicy,
        )
        if (shouldPreview) {
            controller().showPreview(key, spec.label)
        }
    }

    override fun onKeyLongPress(key: KeyboardKeyView, spec: KeySpec): Boolean =
        controller().showAlternates(key, spec.longPressAlternates)

    override fun onKeyMove(key: KeyboardKeyView, localX: Float, localY: Float) {
        popupController?.onTouchMoved(key, localX, localY)
    }

    override fun onKeyUp(key: KeyboardKeyView): KeyboardAction? =
        popupController?.commitSelection(key)

    override fun onKeyCancel(key: KeyboardKeyView) {
        popupController?.dismissPreview(key)
        popupController?.cancelAlternates(key)
    }

    override fun onDetachedFromWindow() {
        popupController?.dismissAll()
        super.onDetachedFromWindow()
    }

    private fun controller(): KeyPopupController =
        popupController ?: KeyPopupController(this).also { popupController = it }

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
        val keyView = if (spec.style == KeyStyle.SPACE) {
            SpaceKeyView(context, metrics.keyHeightPx).also { view ->
                styleKey(view, spec, state)
                view.configure(
                    actionListener = { action -> actionListener?.invoke(action) },
                    touchStateListener = ::onKeyTouchStateChanged,
                )
            }
        } else {
            KeyboardKeyView(context).also { view ->
                styleKey(view, spec, state)
                view.configure(
                    spec = spec,
                    actionListener = { action -> actionListener?.invoke(action) },
                    touchStateListener = ::onKeyTouchStateChanged,
                    popupHost = this,
                )
            }
        }
        keyView.layoutParams = LayoutParams(0, metrics.keyHeightPx, spec.weight).apply {
            setMargins(0, 0, 0, 0)
        }
        return keyView
    }

    private fun styleKey(view: android.widget.TextView, spec: KeySpec, state: KeyboardState) {
        view.text = spec.label
        view.gravity = Gravity.CENTER
        view.includeFontPadding = false
        view.maxLines = 1
        view.minWidth = 0
        view.setPadding(0, 0, 0, 0)
        view.setTextColor(
            context.getColor(
                if (spec.style == KeyStyle.ACTION) R.color.key_text_accent else R.color.key_text,
            ),
        )
        view.setTextSize(
            TypedValue.COMPLEX_UNIT_PX,
            resources.getDimension(
                if (spec.style == KeyStyle.CHARACTER) {
                    R.dimen.keyboard_key_text_size
                } else {
                    R.dimen.keyboard_action_text_size
                },
            ),
        )
        view.typeface = if (spec.style == KeyStyle.ACTION) Typeface.DEFAULT_BOLD else Typeface.DEFAULT
        view.background = InsetDrawable(
            context.getDrawable(
                when (spec.style) {
                    KeyStyle.CHARACTER -> R.drawable.key_background
                    KeyStyle.ACTION -> R.drawable.key_action_background
                    KeyStyle.SPACE -> R.drawable.key_space_background
                    KeyStyle.SPACER -> android.R.color.transparent
                },
            ),
            metrics.keyGapPx / 2,
        )
        view.isSelected = spec.action == KeyboardAction.Shift && state.shiftMode != ShiftMode.OFF
        view.contentDescription = contentDescriptionFor(spec, state)
        view.importantForAccessibility = if (spec.style == KeyStyle.SPACER) {
            IMPORTANT_FOR_ACCESSIBILITY_NO
        } else {
            IMPORTANT_FOR_ACCESSIBILITY_YES
        }
        view.visibility = if (spec.style == KeyStyle.SPACER) INVISIBLE else VISIBLE
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

    private inline fun forEachKey(action: (CancelableKey) -> Unit) {
        for (rowIndex in 0 until childCount) {
            val row = getChildAt(rowIndex) as? LinearLayout ?: continue
            for (keyIndex in 0 until row.childCount) {
                (row.getChildAt(keyIndex) as? CancelableKey)?.let(action)
            }
        }
    }

    private fun contentDescriptionFor(spec: KeySpec, state: KeyboardState): CharSequence? =
        when (spec.action) {
            is KeyboardAction.CommitLetter,
            is KeyboardAction.CommitText,
            -> spec.label
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
                if (state.layer == KeyboardLayer.LETTERS) R.string.key_symbols else R.string.key_letters,
            )
            KeyboardAction.ToggleSymbolsPage -> context.getString(
                if (state.layer == KeyboardLayer.SYMBOLS) {
                    R.string.key_more_symbols
                } else {
                    R.string.key_fewer_symbols
                },
            )
            KeyboardAction.HideKeyboard -> context.getString(R.string.key_hide_keyboard)
            KeyboardAction.NextInputMethod -> context.getString(R.string.key_next_keyboard)
            is KeyboardAction.SwitchLanguage -> context.getString(R.string.key_language)
            KeyboardAction.DoubleSpaceTap,
            is KeyboardAction.MoveCursor,
            null,
            -> null
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
