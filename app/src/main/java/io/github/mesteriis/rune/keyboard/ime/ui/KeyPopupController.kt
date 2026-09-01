package io.github.mesteriis.rune.keyboard.ime.ui

import android.content.Context
import android.graphics.Typeface
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.widget.PopupWindow
import android.widget.TextView
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.RuneTrace
import io.github.mesteriis.rune.keyboard.ime.layout.KeyAlternate
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction

/**
 * Owns the two popup windows above the keyboard: the key preview and the long-press alternates row.
 *
 * Both windows are non-touchable — the pressed key keeps ownership of the whole touch stream and
 * drives the selection through [onTouchMoved]. Both are created once and reused so pressing a key
 * never inflates a view.
 */
internal class KeyPopupController(private val anchorRoot: View) {
    private val context: Context = anchorRoot.context
    private val previewWidth = context.resources.getDimensionPixelSize(R.dimen.keyboard_preview_width)
    private val previewHeight = context.resources.getDimensionPixelSize(R.dimen.keyboard_preview_height)
    private val cellWidth = context.resources.getDimensionPixelSize(R.dimen.keyboard_popup_cell_width)
    private val rowHeight = context.resources.getDimensionPixelSize(R.dimen.keyboard_popup_row_height)
    private val verticalGap = context.resources.getDimensionPixelSize(R.dimen.keyboard_popup_vertical_gap)

    private var previewPopup: PopupWindow? = null
    private var previewLabel: TextView? = null
    private var previewOwner: View? = null

    private var alternatesPopup: PopupWindow? = null
    private var alternatesRow: AlternatesRowView? = null
    private var alternatesOwner: View? = null
    private var alternates: List<KeyAlternate> = emptyList()
    private var alternatesPlacement: PopupPlacement? = null
    private var keyOriginX = 0
    private var keyOriginY = 0
    private var keyHeight = 0
    private var selectionCancelled = false

    private val locationBuffer = IntArray(2)

    val isShowingAlternates: Boolean
        get() = alternatesOwner != null

    fun showPreview(key: View, label: String) {
        RuneTrace.section("Rune#showPreview") {
            if (!anchorRoot.isAttachedToWindow || isShowingAlternates) return@section
            val popup = previewPopup ?: createPreviewPopup().also { previewPopup = it }
            previewLabel?.text = label
            val bounds = keyBounds(key) ?: return@section
            val placement = PopupGeometry.previewPlacement(
                keyLeft = bounds.left,
                keyTop = bounds.top,
                keyWidth = bounds.width,
                previewWidth = previewWidth,
                previewHeight = previewHeight,
                verticalGap = verticalGap,
                containerLeft = bounds.containerLeft,
                containerRight = bounds.containerRight,
            )
            show(popup, placement)
            previewOwner = key
        }
    }

    fun dismissPreview(key: View) {
        if (previewOwner !== key) return
        previewPopup?.dismiss()
        previewOwner = null
    }

    fun showAlternates(key: View, alternates: List<KeyAlternate>): Boolean {
        if (!anchorRoot.isAttachedToWindow || alternates.isEmpty()) return false
        dismissPreview(key)
        val bounds = keyBounds(key) ?: return false
        val popup = alternatesPopup ?: createAlternatesPopup().also { alternatesPopup = it }
        val placement = PopupGeometry.alternatesPlacement(
            keyLeft = bounds.left,
            keyTop = bounds.top,
            keyWidth = bounds.width,
            cellWidth = cellWidth,
            cellCount = alternates.size,
            rowHeight = rowHeight,
            verticalGap = verticalGap,
            containerLeft = bounds.containerLeft,
            containerRight = bounds.containerRight,
        )
        alternatesRow?.setAlternates(alternates)
        this.alternates = alternates
        alternatesPlacement = placement
        keyOriginX = bounds.left
        keyOriginY = bounds.top
        keyHeight = bounds.height
        selectionCancelled = false
        show(popup, placement)
        alternatesOwner = key
        return true
    }

    fun onTouchMoved(key: View, localX: Float, localY: Float) {
        if (alternatesOwner !== key) return
        val placement = alternatesPlacement ?: return
        val row = alternatesRow ?: return
        val touchY = keyOriginY + localY.toInt()
        selectionCancelled = PopupGeometry.isCancelled(
            touchYInWindow = touchY,
            keyBottom = keyOriginY + keyHeight,
            keyHeight = keyHeight,
        )
        row.selectedIndex = if (selectionCancelled) {
            NO_SELECTION
        } else {
            PopupGeometry.selectedAlternateIndex(
                touchXInWindow = keyOriginX + localX.toInt(),
                popupX = placement.x,
                cellWidth = cellWidth,
                cellCount = alternates.size,
            )
        }
    }

    fun commitSelection(key: View): KeyboardAction? {
        if (alternatesOwner !== key) return null
        val index = alternatesRow?.selectedIndex ?: NO_SELECTION
        val action = if (selectionCancelled || index < 0 || index >= alternates.size) {
            null
        } else {
            alternates[index].action
        }
        dismissAlternates()
        return action
    }

    /** Abandons an open alternates row without committing the highlighted cell. */
    fun cancelAlternates(key: View) {
        if (alternatesOwner !== key) return
        dismissAlternates()
    }

    fun dismissAll() {
        previewPopup?.dismiss()
        previewOwner = null
        dismissAlternates()
    }

    private fun dismissAlternates() {
        alternatesPopup?.dismiss()
        alternatesOwner = null
        alternatesPlacement = null
        alternates = emptyList()
        selectionCancelled = false
    }

    private fun show(popup: PopupWindow, placement: PopupPlacement) {
        if (popup.isShowing) {
            popup.update(placement.x, placement.y, placement.width, placement.height)
        } else {
            popup.width = placement.width
            popup.height = placement.height
            popup.showAtLocation(anchorRoot, Gravity.NO_GRAVITY, placement.x, placement.y)
        }
    }

    private fun createPreviewPopup(): PopupWindow {
        return RuneTrace.section("Rune#createPreview") {
            val label = TextView(context).apply {
                gravity = Gravity.CENTER
                includeFontPadding = false
                maxLines = 1
                setTextSize(
                    TypedValue.COMPLEX_UNIT_PX,
                    context.resources.getDimension(R.dimen.keyboard_preview_text_size),
                )
                typeface = Typeface.DEFAULT
                setTextColor(context.getColor(R.color.key_text))
                background = context.getDrawable(R.drawable.key_preview_background)
                importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
            }
            previewLabel = label
            newPopup(label)
        }
    }

    private fun createAlternatesPopup(): PopupWindow {
        val row = AlternatesRowView(context)
        alternatesRow = row
        return newPopup(row)
    }

    private fun newPopup(contentView: View): PopupWindow = PopupWindow(context).apply {
        this.contentView = contentView
        isFocusable = false
        isTouchable = false
        isOutsideTouchable = false
        isClippingEnabled = false
        inputMethodMode = PopupWindow.INPUT_METHOD_NOT_NEEDED
        setBackgroundDrawable(null)
    }

    private fun keyBounds(key: View): KeyBounds? {
        if (!key.isAttachedToWindow || !anchorRoot.isAttachedToWindow) return null
        key.getLocationInWindow(locationBuffer)
        val keyLeft = locationBuffer[0]
        val keyTop = locationBuffer[1]
        anchorRoot.getLocationInWindow(locationBuffer)
        val rootLeft = locationBuffer[0]
        return KeyBounds(
            left = keyLeft,
            top = keyTop,
            width = key.width,
            height = key.height,
            containerLeft = rootLeft + anchorRoot.paddingLeft,
            containerRight = rootLeft + anchorRoot.width - anchorRoot.paddingRight,
        )
    }

    private data class KeyBounds(
        val left: Int,
        val top: Int,
        val width: Int,
        val height: Int,
        val containerLeft: Int,
        val containerRight: Int,
    )

    private companion object {
        const val NO_SELECTION = -1
    }
}
