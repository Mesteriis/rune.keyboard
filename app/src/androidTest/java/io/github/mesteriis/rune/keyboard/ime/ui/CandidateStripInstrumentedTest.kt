package io.github.mesteriis.rune.keyboard.ime.ui

import android.accessibilityservice.AccessibilityServiceInfo
import android.content.Context
import android.os.SystemClock
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.TextView
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.layout.KeyAlternate
import io.github.mesteriis.rune.keyboard.ime.layout.KeySpec
import io.github.mesteriis.rune.keyboard.ime.layout.KeyStyle
import io.github.mesteriis.rune.keyboard.ime.layout.KeyboardLayout
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardAction
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState
import io.github.mesteriis.rune.keyboard.ime.model.ShiftMode
import io.github.mesteriis.rune.keyboard.settings.KeyboardViewMetrics
import io.github.mesteriis.rune.keyboard.settings.SettingsActivity
import io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem
import io.github.mesteriis.rune.keyboard.smarttyping.ui.SmartTypingViewState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotSame
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

/** Uses real child references and the existing key/popup protocol; no production test hooks. */
@RunWith(AndroidJUnit4::class)
class CandidateStripInstrumentedTest {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val original = CandidateUiItem.Original("session:1:original", "teh")
    private val correction = CandidateUiItem.Correction("session:1:correction", "the")
    private val punctuation = CandidateUiItem.Punctuation("session:1:punctuation", ",")
    private val initialState = KeyboardState(KeyboardLanguage.ENGLISH, shiftMode = ShiftMode.LOCKED)
    private val letterSpec = KeySpec("a", KeyboardAction.CommitLetter("a"))
    private val layout = KeyboardLayout(
        listOf(
            listOf(
                letterSpec,
                KeySpec("⇧", KeyboardAction.Shift, style = KeyStyle.ACTION),
                KeySpec("English", KeyboardAction.Space, style = KeyStyle.SPACE),
            ),
        ),
    )

    @Test
    fun candidateUpdatesKeepKeysShiftLanguageAndContainerIdentity() = onMain {
        val keyboard = keyboard(instrumentation.targetContext)
        val before = keys(keyboard)
        val strip = keyboard.getChildAt(0)
        val container = keyboard.getChildAt(1)
        val cells = children(strip as ViewGroup)
        keyboard.showLanguagePreview("Español")
        val labels = before.map { (it as TextView).text.toString() }
        val selected = before.map { it.isSelected }
        val initialHeight = keyboard.measuredHeight
        listOf(
            SmartTypingViewState(true, listOf(original)),
            fullState(),
            SmartTypingViewState.EMPTY,
        ).forEach { state ->
            keyboard.updateCandidates(state)
            measure(keyboard)
            assertIdentical(before, keys(keyboard))
            assertIdentical(cells, children(strip))
            assertSame(strip, keyboard.getChildAt(0))
            assertSame(container, keyboard.getChildAt(1))
            assertEquals(labels, keys(keyboard).map { (it as TextView).text.toString() })
            assertEquals(selected, keys(keyboard).map { it.isSelected })
            assertEquals(initialHeight, keyboard.measuredHeight)
        }
    }

    @Test
    fun updateDuringHeldKeyDoesNotCancelTouchOrFlushPendingRender() = onMain {
        val actions = mutableListOf<KeyboardAction>()
        val keyboard = keyboard(instrumentation.targetContext).apply { setOnActionListener(actions::add) }
        val before = keys(keyboard)
        val held = before.first()
        touch(held, MotionEvent.ACTION_DOWN)
        val nextState = initialState.copy(language = KeyboardLanguage.RUSSIAN, shiftMode = ShiftMode.OFF)
        val nextLayout = KeyboardLayout(listOf(listOf(KeySpec("я", KeyboardAction.CommitLetter("я")))))
        keyboard.render(nextLayout, nextState)
        keyboard.updateCandidates(fullState())
        assertTrue(held.isPressed)
        assertIdentical(before, keys(keyboard))
        assertTrue(before[1].isSelected)
        touch(held, MotionEvent.ACTION_UP)
        assertEquals(listOf(KeyboardAction.CommitLetter("a")), actions)
        assertNotSame(held, keys(keyboard).first())
        assertEquals("я", (keys(keyboard).first() as TextView).text.toString())
        assertFalse(held.isPressed)
    }

    @Test
    fun cancellationStillReachesNestedLetterAndSpaceKeys() = onMain {
        val actions = mutableListOf<KeyboardAction>()
        val keyboard = keyboard(instrumentation.targetContext).apply { setOnActionListener(actions::add) }
        val letter = keys(keyboard).first()
        val space = keys(keyboard).last()
        touch(letter, MotionEvent.ACTION_DOWN)
        touch(space, MotionEvent.ACTION_DOWN)
        keyboard.cancelActiveTouches()
        assertFalse(letter.isPressed)
        assertFalse(space.isPressed)
        touch(letter, MotionEvent.ACTION_UP)
        touch(space, MotionEvent.ACTION_UP)
        assertTrue(actions.isEmpty())
    }

    @Test
    fun candidatesAppearInAccessibilityAfterAnEmptyStripWasQueried() {
        val device = UiDevice.getInstance(instrumentation)
        val description = instrumentation.targetContext.getString(R.string.candidate_original, original.text)
        val wasCompressed = instrumentation.uiAutomation.serviceInfo.flags and
            AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS == 0
        ActivityScenario.launch(SettingsActivity::class.java).use { scenario ->
            lateinit var view: RuneKeyboardView
            scenario.onActivity { activity ->
                view = keyboard(activity)
                activity.setContentView(view)
            }
            try {
                // Check both UiAutomator's full tree and the important-only tree used by readers.
                listOf(false, true).forEach { compressed ->
                    device.setCompressedLayoutHierarchy(compressed)
                    repeat(4) { iteration ->
                        val cleared = if (iteration % 2 == 0) SmartTypingViewState.EMPTY else SmartTypingViewState.HIDDEN
                        scenario.onActivity { view.updateCandidates(cleared) }
                        instrumentation.waitForIdleSync()
                        assertTrue(device.wait(Until.gone(By.desc(description)), 2_000))
                        // Querying the empty hierarchy primes the remote accessibility cache.
                        scenario.onActivity { view.updateCandidates(SmartTypingViewState(true, listOf(original))) }
                        assertTrue(
                            "Populated cells must become discoverable through the public accessibility tree",
                            device.wait(Until.hasObject(By.desc(description)), 2_000),
                        )
                    }
                }
            } finally {
                device.setCompressedLayoutHierarchy(wasCompressed)
            }
        }
    }

    @Test
    fun originalAndCorrectionExposeSelectedStateLabelledActionAndIdCallbacks() {
        ActivityScenario.launch(SettingsActivity::class.java).use { scenario ->
            val chosen = mutableListOf<String>()
            lateinit var view: RuneKeyboardView
            scenario.onActivity { activity ->
                view = keyboard(activity)
                view.setOnCandidateSelectedListener(chosen::add)
                view.updateCandidates(fullState())
                activity.setContentView(view)
            }
            // Accessibility nodes must come from the attached, laid-out view hierarchy.
            instrumentation.waitForIdleSync()
            scenario.onActivity {
                val keyboard = view
                val strip = keyboard.getChildAt(0) as ViewGroup
                val first = strip.getChildAt(0)
                val second = strip.getChildAt(1)
                assertTrue(first.isAttachedToWindow)
                assertTrue(second.isAttachedToWindow)
                assertFalse(first.isSelected)
                assertTrue(second.isSelected)
                val firstInfo = first.createAccessibilityNodeInfo()
                val secondInfo = second.createAccessibilityNodeInfo()
                try {
                    assertTrue(secondInfo.isSelected)
                    assertEquals(
                        keyboard.context.getString(R.string.candidate_original, original.text),
                        firstInfo.contentDescription,
                    )
                    assertEquals(
                        keyboard.context.getString(R.string.candidate_keep_original),
                        firstInfo.actionList.single { it.id == AccessibilityNodeInfo.ACTION_CLICK }.label,
                    )
                    assertTrue(first.performAccessibilityAction(AccessibilityNodeInfo.ACTION_CLICK, null))
                    assertTrue(second.performClick())
                    assertEquals(listOf(original.id, correction.id), chosen)
                } finally {
                    @Suppress("DEPRECATION")
                    firstInfo.recycle()
                    @Suppress("DEPRECATION")
                    secondInfo.recycle()
                }
                keyboard.updateCandidates(SmartTypingViewState(true, listOf(original)))
                assertTrue(first.isSelected)
                keyboard.updateCandidates(SmartTypingViewState.HIDDEN)
                assertEquals(View.GONE, strip.visibility)
                children(strip).forEach { cell ->
                    assertFalse(cell.isEnabled)
                    assertFalse(cell.isSelected)
                    assertEquals("", (cell as TextView).text.toString())
                    assertEquals(null, cell.contentDescription)
                    assertEquals(View.IMPORTANT_FOR_ACCESSIBILITY_NO, cell.importantForAccessibility)
                    cell.performClick()
                }
                assertEquals(listOf(original.id, correction.id), chosen)
            }
        }
    }

    @Test
    fun candidateRefreshBetweenDownAndUpDoesNotSelectReplacementCell() = onMain {
        val chosen = mutableListOf<String>()
        val keyboard = keyboard(instrumentation.targetContext)
        keyboard.setOnCandidateSelectedListener(chosen::add)
        keyboard.updateCandidates(fullState())
        val cell = (keyboard.getChildAt(0) as ViewGroup).getChildAt(1)
        touch(cell, MotionEvent.ACTION_DOWN)
        keyboard.updateCandidates(
            SmartTypingViewState(true, listOf(original, correction.copy(id = "session:2:correction"))),
        )
        touch(cell, MotionEvent.ACTION_UP)
        assertTrue(chosen.isEmpty())
    }

    @Test
    fun candidateUpOutsideWithoutMoveDoesNotSelect() = onMain {
        val chosen = mutableListOf<String>()
        val keyboard = keyboard(instrumentation.targetContext)
        keyboard.setOnCandidateSelectedListener(chosen::add)
        keyboard.updateCandidates(fullState())
        val cell = (keyboard.getChildAt(0) as ViewGroup).getChildAt(1)
        touch(cell, MotionEvent.ACTION_DOWN)
        touch(cell, MotionEvent.ACTION_UP, x = cell.width + 1f)
        assertTrue(chosen.isEmpty())
        assertFalse(cell.isPressed)
    }

    @Test
    fun sameIdWithChangedTextOrTypeCancelsPendingCandidateTap() = onMain {
        val chosen = mutableListOf<String>()
        val keyboard = keyboard(instrumentation.targetContext)
        keyboard.setOnCandidateSelectedListener(chosen::add)
        val cell = (keyboard.getChildAt(0) as ViewGroup).getChildAt(1)
        listOf(
            correction.copy(text = "they"),
            CandidateUiItem.Punctuation(correction.id, correction.text),
        ).forEach { changed ->
            keyboard.updateCandidates(fullState())
            touch(cell, MotionEvent.ACTION_DOWN)
            keyboard.updateCandidates(SmartTypingViewState(true, listOf(original, changed)))
            touch(cell, MotionEvent.ACTION_UP)
            assertTrue(chosen.isEmpty())
            assertFalse(cell.isPressed)
        }
    }

    @Test
    fun secondaryPointerIsIgnoredAndCannotTakeOverReleasedOwner() = onMain {
        val chosen = mutableListOf<String>()
        val keyboard = keyboard(instrumentation.targetContext)
        keyboard.setOnCandidateSelectedListener(chosen::add)
        keyboard.updateCandidates(fullState())
        val cell = (keyboard.getChildAt(0) as ViewGroup).getChildAt(1)
        pointerTouch(cell, MotionEvent.ACTION_DOWN, intArrayOf(4))
        pointerTouch(cell, MotionEvent.ACTION_POINTER_DOWN, intArrayOf(4, 9), actionIndex = 1)
        pointerTouch(cell, MotionEvent.ACTION_POINTER_UP, intArrayOf(4, 9), actionIndex = 1)
        pointerTouch(cell, MotionEvent.ACTION_UP, intArrayOf(4))
        assertEquals(listOf(correction.id), chosen)
        chosen.clear()

        pointerTouch(cell, MotionEvent.ACTION_DOWN, intArrayOf(4))
        pointerTouch(cell, MotionEvent.ACTION_POINTER_DOWN, intArrayOf(4, 9), actionIndex = 1)
        pointerTouch(cell, MotionEvent.ACTION_POINTER_UP, intArrayOf(4, 9), actionIndex = 0)
        pointerTouch(cell, MotionEvent.ACTION_UP, intArrayOf(9))
        assertTrue(chosen.isEmpty())
        assertFalse(cell.isPressed)
    }

    @Test
    fun missingOwnerPointerCancelsCandidateTap() = onMain {
        val chosen = mutableListOf<String>()
        val keyboard = keyboard(instrumentation.targetContext)
        keyboard.setOnCandidateSelectedListener(chosen::add)
        keyboard.updateCandidates(fullState())
        val cell = (keyboard.getChildAt(0) as ViewGroup).getChildAt(1)
        pointerTouch(cell, MotionEvent.ACTION_DOWN, intArrayOf(4))
        pointerTouch(cell, MotionEvent.ACTION_MOVE, intArrayOf(9))
        pointerTouch(cell, MotionEvent.ACTION_UP, intArrayOf(4))
        assertTrue(chosen.isEmpty())
        assertFalse(cell.isPressed)
    }

    @Test
    fun candidateUpdateKeepsAttachedAlternatePopupSelectionAlive() {
        ActivityScenario.launch(SettingsActivity::class.java).use { scenario ->
            lateinit var keyboard: RuneKeyboardView
            val alternate = KeyAlternate("é", KeyboardAction.CommitLetter("é"))
            val spec = letterSpec.copy(longPressAlternates = listOf(alternate))
            scenario.onActivity { activity ->
                keyboard = keyboard(activity)
                keyboard.render(KeyboardLayout(listOf(listOf(spec))), initialState)
                activity.setContentView(keyboard)
            }
            instrumentation.waitForIdleSync()
            scenario.onActivity {
                assertTrue(keyboard.isAttachedToWindow)
                val key = keys(keyboard).single() as KeyboardKeyView
                assertTrue(keyboard.onKeyLongPress(key, spec))
                keyboard.updateCandidates(fullState())
                assertSame(key, keys(keyboard).single())
                assertEquals(alternate.action, keyboard.onKeyUp(key))
            }
        }
    }

    private fun keyboard(context: Context): RuneKeyboardView = RuneKeyboardView(
        context,
        KeyboardViewMetrics(
            context.resources.getDimensionPixelSize(R.dimen.keyboard_key_height),
            context.resources.getDimensionPixelSize(R.dimen.keyboard_key_gap),
        ),
    ).apply {
        setPopupPolicy(previewEnabled = false, inputPolicy = InputPolicy.NORMAL)
        render(layout, initialState)
        updateCandidates(SmartTypingViewState.EMPTY)
        measure(this)
    }

    private fun fullState() = SmartTypingViewState(
        true,
        listOf(original, correction, punctuation),
        correction.id,
    )

    private fun measure(view: View) {
        val width = (360 * view.resources.displayMetrics.density).toInt()
        view.measure(
            View.MeasureSpec.makeMeasureSpec(width, View.MeasureSpec.EXACTLY),
            View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED),
        )
        view.layout(0, 0, width, view.measuredHeight)
    }

    private fun children(view: ViewGroup): List<View> = (0 until view.childCount).map(view::getChildAt)

    private fun keys(view: ViewGroup): List<View> = children(view).flatMap { child ->
        when {
            child is CancelableKey -> listOf(child)
            child is ViewGroup -> keys(child)
            else -> emptyList()
        }
    }

    private fun assertIdentical(before: List<View>, after: List<View>) {
        assertEquals(before.size, after.size)
        before.zip(after).forEach { (first, second) -> assertSame(first, second) }
    }

    private fun touch(
        view: View,
        action: Int,
        x: Float = view.width / 2f,
        y: Float = view.height / 2f,
    ) {
        val now = SystemClock.uptimeMillis()
        val event = MotionEvent.obtain(now, now, action, x, y, 0)
        try {
            view.onTouchEvent(event)
        } finally {
            event.recycle()
        }
    }

    private fun pointerTouch(view: View, action: Int, ids: IntArray, actionIndex: Int = 0) {
        val now = SystemClock.uptimeMillis()
        val event = MotionEvent.obtain(
            now,
            now,
            action or (actionIndex shl MotionEvent.ACTION_POINTER_INDEX_SHIFT),
            ids.size,
            ids.map { pointerId ->
                MotionEvent.PointerProperties().apply {
                    id = pointerId
                    toolType = MotionEvent.TOOL_TYPE_FINGER
                }
            }.toTypedArray(),
            ids.map {
                MotionEvent.PointerCoords().apply {
                    x = view.width / 2f
                    y = view.height / 2f
                    pressure = 1f
                    size = 1f
                }
            }.toTypedArray(),
            0,
            0,
            1f,
            1f,
            0,
            0,
            android.view.InputDevice.SOURCE_TOUCHSCREEN,
            0,
        )
        try {
            view.onTouchEvent(event)
        } finally {
            event.recycle()
        }
    }

    private fun onMain(block: () -> Unit) = instrumentation.runOnMainSync(block)
}
