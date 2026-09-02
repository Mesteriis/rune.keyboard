package io.github.mesteriis.rune.keyboard.qa

import android.app.Instrumentation
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Rect
import android.os.SystemClock
import android.view.InputDevice
import android.view.MotionEvent
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.UiObject2
import androidx.test.uiautomator.UiScrollable
import androidx.test.uiautomator.UiSelector
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import java.io.File
import java.io.FileOutputStream
import org.junit.rules.TestWatcher
import org.junit.runner.Description

class ImeTestDriver {
    private val instrumentation: Instrumentation = InstrumentationRegistry.getInstrumentation()
    val device: UiDevice = UiDevice.getInstance(instrumentation)
    private val targetContext = instrumentation.targetContext
    private var previousIme = ""
    private var previousEnabledImes = ""
    private var runeWasEnabled = false
    private var previousHardKeyboardSetting = "0"
    private var previousPreferences: Map<String, *> = emptyMap<String, Any?>()

    fun setUp() {
        previousIme = shell("settings get secure default_input_method")
        previousEnabledImes = shell("settings get secure enabled_input_methods")
        runeWasEnabled = IME_COMPONENT in previousEnabledImes
        previousHardKeyboardSetting = shell("settings get secure show_ime_with_hard_keyboard")
        val preferences = targetContext.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)
        previousPreferences = HashMap(preferences.all)
        shell("settings put secure show_ime_with_hard_keyboard 1")
        shell("ime enable $IME_COMPONENT")
        shell("ime set $IME_COMPONENT")
        launchQa()
        waitForKeyboard()
        switchToEnglish()
    }

    fun tearDown() {
        device.pressHome()
        restorePreferences()
        // restorePreferences() runs on the instrumentation thread. Its commit makes the values
        // visible immediately, but the IME listener is dispatched on the app's main thread.
        // Drain that queue so the next test cannot inherit a stale keyboard layout.
        instrumentation.waitForIdleSync()
        if (previousIme == IME_COMPONENT) {
            restartRuneIme()
        } else if (previousIme.isNotBlank() && previousIme != "null") {
            shell("ime set $previousIme")
        }
        if (!runeWasEnabled) shell("ime disable $IME_COMPONENT")
        val hardKeyboardSetting = previousHardKeyboardSetting.takeUnless { it.isBlank() || it == "null" } ?: "0"
        shell("settings put secure show_ime_with_hard_keyboard $hardKeyboardSetting")
    }

    fun launchQa() {
        shell("am start -W -f 0x10008000 -n $QA_ACTIVITY")
        awaitQaActivity()
    }

    private fun resumeQa() {
        shell("am start -W -n $QA_ACTIVITY")
        awaitQaActivity()
    }

    fun focusField(idName: String): UiObject2 {
        val selector = By.res(PACKAGE_NAME, idName)
        val visibleField = device.findObject(selector)
        val needsFocus =
            visibleField == null ||
            visibleField.visibleBounds.height() == 0 ||
            !visibleField.isFocused
        val field = if (needsFocus) {
            // Switching editors must happen with the IME hidden: accessibility may expose the
            // target even when its click point is covered. Keep an already-focused editor and its
            // restored IME intact for lifecycle tests.
            prepareQaForScroll()
            device.findObject(selector) ?: scrollToObject(idName)
        } else {
            visibleField
        }
        field.click()
        waitForKeyboard()
        device.waitForIdle()
        // adjustResize may move a low editor outside the accessibility viewport once IME appears;
        // callers only need the focus transition, so keep the node captured before that resize.
        return field
    }

    fun tapQaControl(idName: String) {
        requireObject(idName, scroll = true).click()
        device.waitForIdle()
        SystemClock.sleep(INPUT_CONNECTION_SETTLE_MILLIS)
        waitForKeyboard()
        // The QA editor runs in a separate process. Drain Rune's main thread after its Binder
        // selection/update callbacks before dispatching the next keyboard action.
        instrumentation.waitForIdleSync()
    }

    fun fieldText(idName: String): String = requireObject(idName, scroll = true).text.orEmpty()

    fun tapKey(label: String) {
        keyByText(label).click()
        device.waitForIdle()
    }

    fun tapKey(vararg possibleLabels: String) {
        val key = possibleLabels.firstNotNullOfOrNull(::findKeyByText)
            ?: error("Rune key not found: ${possibleLabels.joinToString()}")
        key.click()
        device.waitForIdle()
    }

    fun tapDelete() = tapKeyByDescription(targetContext.getString(R.string.key_delete))

    fun tapEnter(descriptionResource: Int) = tapKeyByDescription(targetContext.getString(descriptionResource))

    fun tapKeyByDescription(description: String) {
        keyByDescription(description).click()
        device.waitForIdle()
    }

    fun assertKeyVisible(label: String) {
        check(findKeyByText(label) != null) { "Expected Rune key '$label'" }
    }

    fun switchToRussian() {
        switchLanguageUntil("RU")
    }

    private fun switchToEnglish() {
        switchLanguageUntil("EN")
    }

    private fun switchLanguageUntil(expectedKey: String) {
        repeat(5) {
            if (findKeyByText(expectedKey) != null) return
            val space = keyByDescription(targetContext.getString(R.string.key_space))
            val bounds = space.visibleBounds
            // API 37 gesture navigation reserves the bottom strip for system task switching. The
            // upper edge remains part of the space key and exercises Rune's gesture detector.
            val swipeY = (bounds.top + 4).coerceAtMost(bounds.bottom - 1)
            device.swipe(bounds.right - 8, swipeY, bounds.left + 8, swipeY, 24)
            device.waitForIdle()
            eventually(INPUT_CONNECTION_SETTLE_MILLIS * 2) { findKeyByText(expectedKey) != null }
        }
        error("Expected layout key '$expectedKey' did not appear after a bounded language cycle")
    }

    fun awaitFieldText(idName: String, expected: String, timeoutMillis: Long = WAIT_MILLIS) {
        val selector = By.res(PACKAGE_NAME, idName)
        var lastObserved: String? = null
        eventually(timeoutMillis) {
            device.findObject(selector)?.text?.let { observed ->
                lastObserved = observed
                observed == expected
            } ?: false
        }
        check(lastObserved == expected) {
            "Field $idName expected <$expected>, actual <${lastObserved ?: "unavailable"}>"
        }
    }

    fun revealFieldAndAwaitText(idName: String, expected: String) {
        // Lower editors can remain focused but accessibility-invisible behind the API 37 IME.
        // This explicit post-action assertion may hide the IME; passive lifecycle assertions must
        // continue to use awaitFieldText so they cannot add a focus-loss cancellation.
        scrollToObject(idName)
        awaitFieldText(idName, expected)
    }

    fun awaitStatus(expected: String) {
        if (device.findObject(By.res(PACKAGE_NAME, "qa_action_status")) == null) {
            device.pressBack()
            SystemClock.sleep(200)
            scrollToObject("qa_action_status")
        }
        eventually(WAIT_MILLIS) { fieldText("qa_action_status") == expected }
        check(fieldText("qa_action_status") == expected) {
            "Expected action status <$expected>, actual <${fieldText("qa_action_status")}>"
        }
    }

    fun touchDown(key: UiObject2): TouchHandle {
        val bounds = key.visibleBounds
        val downTime = SystemClock.uptimeMillis()
        inject(downTime, downTime, MotionEvent.ACTION_DOWN, bounds.exactCenterX(), bounds.exactCenterY())
        return TouchHandle(downTime, bounds.exactCenterX(), bounds.exactCenterY())
    }

    fun cancelTouch(handle: TouchHandle) {
        inject(handle.downTime, SystemClock.uptimeMillis(), MotionEvent.ACTION_CANCEL, handle.x, handle.y)
    }

    fun releaseTouch(handle: TouchHandle) {
        inject(handle.downTime, SystemClock.uptimeMillis(), MotionEvent.ACTION_UP, handle.x, handle.y)
    }

    fun deleteKey(): UiObject2 = keyByDescription(targetContext.getString(R.string.key_delete))

    fun characterKey(vararg labels: String): UiObject2 =
        labels.firstNotNullOfOrNull(::findKeyByText) ?: error("Character key not found")

    fun captureScreen(): Bitmap = instrumentation.uiAutomation.takeScreenshot()
        ?: error("UiAutomation screenshot is unavailable")

    fun previewCropFor(key: UiObject2, screen: Bitmap = captureScreen()): Bitmap {
        val bounds = key.visibleBounds
        val crop = Rect(
            bounds.left.coerceAtLeast(0),
            (bounds.top - bounds.height() * 2).coerceAtLeast(0),
            bounds.right.coerceAtMost(screen.width),
            bounds.top.coerceAtMost(screen.height),
        )
        return Bitmap.createBitmap(screen, crop.left, crop.top, crop.width(), crop.height())
    }

    fun changedPixels(first: Bitmap, second: Bitmap): Int {
        check(first.width == second.width && first.height == second.height)
        var changed = 0
        for (y in 0 until first.height) {
            for (x in 0 until first.width) {
                if (first.getPixel(x, y) != second.getPixel(x, y)) changed++
            }
        }
        return changed
    }

    fun saveFailureBitmap(name: String, bitmap: Bitmap) {
        val root = targetContext.getExternalFilesDir("instrumentation-failures") ?: return
        root.mkdirs()
        FileOutputStream(File(root, name)).use { output ->
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, output)
        }
    }

    fun shell(command: String): String = device.executeShellCommand(command).trim()

    fun setNumberRowThroughSettings(enabled: Boolean) {
        if ((findKeyByText("1") != null) == enabled) return
        shell("am start -W -n $PACKAGE_NAME/.settings.SettingsActivity")
        val label = targetContext.getString(R.string.settings_number_row)
        var row = device.findObject(By.text(label))
        if (row == null) {
            @Suppress("DEPRECATION")
            UiScrollable(UiSelector().resourceId("$PACKAGE_NAME:id/settings_scroll")).apply {
                setAsVerticalList()
                scrollIntoView(UiSelector().text(label))
            }
            row = device.findObject(By.text(label))
        }
        clickClosestClickable(checkNotNull(row) { "Number-row setting was not found" })
        eventually(WAIT_MILLIS) {
            targetContext.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)
                .getBoolean(KEY_NUMBER_ROW, false) == enabled
        }
        check(
            targetContext.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)
                .getBoolean(KEY_NUMBER_ROW, false) == enabled,
        ) { "Number-row setting was not persisted" }
        // UiAutomator can observe SharedPreferences halfway through the settings click handler.
        // Drain the app's main queue so that handler and the IME preference listener finish before
        // API 26 restores the editor against the next input view.
        instrumentation.waitForIdleSync()
        device.pressBack()
        instrumentation.waitForIdleSync()
        // Detach the current input view without selecting the API 26 vendor IME: the settings
        // listener has already rebuilt Rune's view, and returning from Home starts the next Rune
        // input session against that updated view.
        device.pressHome()
        check(
            device.wait(
                Until.gone(By.desc(targetContext.getString(R.string.key_delete))),
                WAIT_MILLIS,
            ),
        ) { "Rune IME did not detach before the next input session" }
        device.waitForIdle()
        instrumentation.waitForIdleSync()
        resumeQa()
        focusField("qa_plain_text")
        eventually(WAIT_MILLIS) { (findKeyByText("1") != null) == enabled }
        check((findKeyByText("1") != null) == enabled) { "Active IME did not apply number-row setting" }
    }

    fun ensureKeyPreviewEnabled() {
        val wasEnabled = previousPreferences[KEY_PREVIEW] as? Boolean ?: true
        if (wasEnabled) return
        shell("am start -W -n $PACKAGE_NAME/.settings.SettingsActivity")
        val label = targetContext.getString(R.string.settings_key_preview)
        val row = device.findObject(By.text(label)) ?: run {
            @Suppress("DEPRECATION")
            UiScrollable(UiSelector().resourceId("$PACKAGE_NAME:id/settings_scroll")).apply {
                setAsVerticalList()
                scrollIntoView(UiSelector().text(label))
            }
            device.findObject(By.text(label))
        }
        checkNotNull(row) { "Key-preview setting was not found" }.click()
        device.pressBack()
        resumeQa()
        focusField("qa_plain_text")
    }

    fun keyByText(label: String): UiObject2 = findKeyByText(label) ?: error("Rune key '$label' not found")

    private fun restorePreferences() {
        val editor = targetContext.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE).edit().clear()
        previousPreferences.forEach { (key, value) ->
            when (value) {
                is Boolean -> editor.putBoolean(key, value)
                is Float -> editor.putFloat(key, value)
                is Int -> editor.putInt(key, value)
                is Long -> editor.putLong(key, value)
                is String -> editor.putString(key, value)
                is Set<*> -> editor.putStringSet(key, value.filterIsInstance<String>().toSet())
            }
        }
        editor.commit()
    }

    private fun findKeyByText(label: String): UiObject2? = bottomMost(device.findObjects(By.text(label)))

    private fun keyByDescription(description: String): UiObject2 =
        bottomMost(device.findObjects(By.desc(description)))
            ?: error("Rune key with description '$description' not found")

    private fun bottomMost(objects: List<UiObject2>): UiObject2? =
        objects.filter { it.visibleBounds.height() > 0 }.maxByOrNull { it.visibleBounds.centerY() }

    private fun requireObject(idName: String, scroll: Boolean = false): UiObject2 {
        val selector = By.res(PACKAGE_NAME, idName)
        device.findObject(selector)?.let { return it }
        if (device.wait(Until.hasObject(selector), ACCESSIBILITY_SETTLE_MILLIS)) {
            return device.findObject(selector)
        }
        if (scroll) return scrollToObject(idName)
        check(device.wait(Until.hasObject(selector), WAIT_MILLIS)) { "QA object not found: $idName" }
        return device.findObject(selector)
    }

    private fun awaitQaActivity() {
        val selector = By.res(PACKAGE_NAME, "qa_scroll")
        check(device.wait(Until.hasObject(selector), WAIT_MILLIS)) { "QA activity did not become visible" }
    }

    private fun clickClosestClickable(objectNode: UiObject2) {
        var node: UiObject2? = objectNode
        while (node != null && !node.isClickable) node = node.parent
        checkNotNull(node) { "Settings row has no clickable ancestor" }.click()
    }

    private fun scrollToObject(idName: String): UiObject2 {
        prepareQaForScroll()
        @Suppress("DEPRECATION")
        val scrollable = UiScrollable(UiSelector().resourceId("$PACKAGE_NAME:id/qa_scroll")).apply {
            setAsVerticalList()
            scrollToBeginning(12)
            scrollIntoView(UiSelector().resourceId("$PACKAGE_NAME:id/$idName"))
        }
        check(scrollable.exists()) { "QA scroll container is unavailable" }
        val selector = By.res(PACKAGE_NAME, idName)
        check(device.wait(Until.hasObject(selector), WAIT_MILLIS)) { "QA object not found: $idName" }
        return device.findObject(selector)
    }

    private fun prepareQaForScroll() {
        val qaSelector = By.res(PACKAGE_NAME, "qa_scroll")
        val keyboardSelector = By.desc(targetContext.getString(R.string.key_delete))
        if (device.findObject(keyboardSelector) != null) {
            device.pressBack()
            check(device.wait(Until.gone(keyboardSelector), WAIT_MILLIS)) {
                "Rune IME did not hide before scrolling the QA activity"
            }
        }
        // On API 26 accessibility may temporarily expose only the IME window. Hiding it first
        // lets the already-resumed QA root reappear. Do not relaunch from a setup/assertion helper:
        // that could conceal a crashed editor or add another focus-loss cancellation.
        check(device.wait(Until.hasObject(qaSelector), WAIT_MILLIS)) {
            "QA activity did not reappear after hiding Rune IME"
        }
        device.waitForIdle()
    }

    private fun restartRuneIme() {
        val fallback = sequenceOf(previousIme)
            .plus(previousEnabledImes.split(':'))
            .map { it.substringBefore(';').trim() }
            .firstOrNull { candidate ->
                candidate.isNotEmpty() &&
                    candidate != "null" &&
                    candidate != IME_COMPONENT &&
                    candidate.matches(IME_COMPONENT_PATTERN)
        }
        checkNotNull(fallback) { "A second enabled IME is required to restart Rune deterministically" }
        selectImeAndDrain(fallback)
        selectImeAndDrain(IME_COMPONENT)
    }

    private fun selectImeAndDrain(component: String) {
        shell("ime set $component")
        eventually(WAIT_MILLIS) {
            shell("settings get secure default_input_method") == component
        }
        check(shell("settings get secure default_input_method") == component) {
            "Input method did not switch to $component"
        }
        // The shell setting is synchronous, while service unbind/bind callbacks are dispatched on
        // the app main thread. Drain them before selecting the next IME.
        instrumentation.waitForIdleSync()
    }

    private fun waitForKeyboard() {
        check(device.wait(Until.hasObject(By.desc(targetContext.getString(R.string.key_delete))), WAIT_MILLIS)) {
            "Rune IME window did not become visible"
        }
    }

    private fun inject(downTime: Long, eventTime: Long, action: Int, x: Float, y: Float) {
        val pointerProperties = arrayOf(
            MotionEvent.PointerProperties().apply {
                id = 0
                toolType = MotionEvent.TOOL_TYPE_FINGER
            },
        )
        val pointerCoords = arrayOf(
            MotionEvent.PointerCoords().apply {
                this.x = x
                this.y = y
                pressure = 1f
                size = 1f
            },
        )
        val event = MotionEvent.obtain(
            downTime,
            eventTime,
            action,
            1,
            pointerProperties,
            pointerCoords,
            0,
            0,
            1f,
            1f,
            0,
            0,
            InputDevice.SOURCE_TOUCHSCREEN,
            0,
        )
        try {
            check(instrumentation.uiAutomation.injectInputEvent(event, true)) {
                "Failed to inject touch action $action"
            }
        } finally {
            event.recycle()
        }
    }

    private fun eventually(timeoutMillis: Long, condition: () -> Boolean) {
        val deadline = SystemClock.uptimeMillis() + timeoutMillis
        while (SystemClock.uptimeMillis() < deadline && !condition()) SystemClock.sleep(50)
    }

    data class TouchHandle(val downTime: Long, val x: Float, val y: Float)

    companion object {
        const val PACKAGE_NAME = "io.github.mesteriis.rune.keyboard"
        const val IME_COMPONENT = "$PACKAGE_NAME/.ime.RuneInputMethodService"
        const val QA_ACTIVITY = "$PACKAGE_NAME/.qa.ImeQaActivity"
        const val WAIT_MILLIS = 5_000L
        const val ACCESSIBILITY_SETTLE_MILLIS = 1_000L
        const val INPUT_CONNECTION_SETTLE_MILLIS = 250L
        const val PREFERENCES_NAME = "keyboard_preferences"
        const val KEY_NUMBER_ROW = "number_row"
        const val KEY_PREVIEW = "key_preview"
        private val IME_COMPONENT_PATTERN = Regex("[A-Za-z0-9._]+/[A-Za-z0-9._]+")
    }
}

class ImeFailureArtifacts(private val driver: ImeTestDriver) : TestWatcher() {
    override fun failed(error: Throwable?, description: Description) {
        val root = InstrumentationRegistry.getInstrumentation().targetContext
            .getExternalFilesDir("instrumentation-failures") ?: return
        val safeName = description.methodName.replace(Regex("[^A-Za-z0-9_.-]"), "_")
        root.mkdirs()
        driver.device.takeScreenshot(File(root, "$safeName.png"))
        driver.device.dumpWindowHierarchy(File(root, "$safeName.xml"))
    }

    override fun finished(description: Description) {
        driver.tearDown()
    }
}
