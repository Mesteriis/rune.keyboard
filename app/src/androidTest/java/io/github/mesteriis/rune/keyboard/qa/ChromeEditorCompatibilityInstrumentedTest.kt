package io.github.mesteriis.rune.keyboard.qa

import android.content.Context
import android.content.ContextWrapper
import android.inputmethodservice.InputMethodService
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.view.KeyEvent
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.smarttyping.session.TypingSessionController
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.ContextualPunctuationMode
import io.github.mesteriis.rune.keyboard.settings.SettingsCodec
import org.junit.After
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Rule
import org.junit.rules.TestName
import org.junit.Before
import org.junit.Test

/** Explicit physical test of a fixed loopback page; never reads other browser fields. */
class ChromeEditorCompatibilityInstrumentedTest {
    private val driver = ImeTestDriver()
    private val instrumentation get() = InstrumentationRegistry.getInstrumentation()
    private val context get() = instrumentation.targetContext
    private var prepared = false
    private var stores = emptyMap<String, Map<String, String>>()
    private var captured = false
    private var pageOwned = false
    private var port = 0
    @get:Rule val testName = TestName()
    private val browser = "com.android.chrome"

    @Before fun prepare() {
        val args = InstrumentationRegistry.getArguments()
        assumeTrue("Explicit physical Chrome run required", Build.MODEL.startsWith("SM-F") &&
            args.getString("allowPhysicalDevice") == "true")
        check(args.getString("runeFailureArtifacts") == "false")
        port = checkNotNull(args.getString("runeLoopbackPort")).toInt()
        check(port in 1024..65535)
        prepared = true
        driver.setUp(privateQa = true)
        val edit = context.getSharedPreferences(ImeTestDriver.PREFERENCES_NAME, Context.MODE_PRIVATE).edit()
        for (key in listOf(SettingsCodec.KEY_PERSONAL_LEARNING, SettingsCodec.KEY_TOUCH_PERSONALIZATION,
            SettingsCodec.KEY_COLLECT_EXAMPLES, SettingsCodec.KEY_TYPO_PATTERNS, SettingsCodec.KEY_DYNAMIC_TOUCH,
            SettingsCodec.KEY_DYNAMIC_TOUCH_APPLY, SettingsCodec.KEY_QUALITY_METRICS,
            SettingsCodec.KEY_SHADOW_COMPARISON, SettingsCodec.KEY_APP_PROFILES)) edit.putBoolean(key, false)
        check(edit.commit())
        driver.prepareLiveCorrection(mode = "private")
        driver.configureSmartTyping(AutocorrectionMode.HIGH_CONFIDENCE, true,
            mechanical = false, doubleSpace = false, contextual = ContextualPunctuationMode.OFF)
        stores = personalStoreSnapshot(context).filterKeys { it != "typing-diagnostics" }
        captured = true
        val route = if (testName.methodName.startsWith("noSuggestions")) "rune-q8-no-suggestions" else "rune-q8"
        driver.device.executeShellCommand("am start -W -a android.intent.action.VIEW -d http://127.0.0.1:$port/$route --ez create_new_tab true -p $browser")
        assertTrue("Fixed local QA page missing", driver.device.wait(Until.hasObject(By.pkg(browser).text("Rune Q8 local editor")), 10000))
        pageOwned = true
        val field = checkNotNull(driver.device.wait(Until.findObject(By.pkg(browser).res("rune-qa").clazz("android.widget.EditText")), 5000))
        assertEquals("", field.text.orEmpty())
        field.click()
        assertTrue("Rune keyboard missing", driver.device.wait(Until.hasObject(By.pkg(context.packageName)
            .desc(context.getString(R.string.key_delete))), 5000))
    }

    @After fun restore() {
        try {
            if (captured) assertEquals("External QA must preserve personal feedback stores", stores,
                personalStoreSnapshot(context).filterKeys { it != "typing-diagnostics" })
        } finally {
            try {
                if (pageOwned) {
                    assertEquals(browser, driver.device.currentPackageName)
                    assertTrue(driver.device.hasObject(By.res(browser, "url_bar")
                        .textContains("127.0.0.1:$port")))
                    driver.device.pressKeyCode(KeyEvent.KEYCODE_W, KeyEvent.META_CTRL_ON)
                    assertTrue("Owned Chrome tab did not close", driver.device.wait(
                        Until.gone(By.res(browser, "url_bar").textContains("127.0.0.1:$port")), 5000))
                }
            } finally { if (prepared) driver.tearDown() }
        }
    }

    private fun checkEditor() {
        assertEquals(browser, driver.device.currentPackageName)
        var owner: Context = keyboardSnapshot().keyboard.rootView.context
        while (owner !is InputMethodService && owner is ContextWrapper) owner = owner.baseContext
        assertEquals(browser, (owner as InputMethodService).currentInputEditorInfo?.packageName)
        assertTrue("Fixed local page lost foreground", driver.device.hasObject(
            By.res(browser, "url_bar").textContains("127.0.0.1:$port")))
    }
    private fun reportState(word: Int) {
        checkEditor()
        var owner: Context = keyboardSnapshot().keyboard.rootView.context
        while (owner !is InputMethodService && owner is ContextWrapper) owner = owner.baseContext
        val service = owner as InputMethodService
        val state = Bundle()
        instrumentation.runOnMainSync {
            val info = checkNotNull(service.currentInputEditorInfo)
            val policy = EditorContext.from(info)
            val field = service.javaClass.getDeclaredField("typingSession").apply { isAccessible = true }
            val controller = field.get(service) as TypingSessionController
            state.putBoolean("session_enabled", controller.state.enabled)
            state.putBoolean("suggestions_allowed", policy.editorAllowsSuggestions)
            state.putBoolean("supports_smart_typing", policy.supportsSmartTyping)
            state.putInt("editor_input_type", info.inputType); state.putInt("editor_ime_options", info.imeOptions)
        }
        val noSuggestions = testName.methodName.startsWith("noSuggestions")
        assertEquals(!noSuggestions, state.getBoolean("suggestions_allowed"))
        assertTrue(state.getBoolean("session_enabled"))
        instrumentation.sendStatus(2, state.apply { putInt("word", word) })
    }
    private fun type(value: String) = value.forEach { checkEditor(); driver.tapKey(it.toString()) }
    private fun space() { checkEditor(); driver.tapKeyByDescription(context.getString(R.string.key_space)) }
    @Test fun noSuggestionsPreservesFiveLiteralWordsAndBackspace() {
        repeat(5) { type("teh"); space(); reportState(it + 1) }
        SystemClock.sleep(250)
        checkEditor(); driver.tapDelete()
        SystemClock.sleep(250)
        instrumentation.sendStatus(2, Bundle().apply { putString("dom_checkpoint", "literal_backspace") })
    }

    @Test fun correctionRemainsAvailableAfterFiveWordsAndExactUndo() {
        repeat(5) { type("teh"); space(); reportState(it + 1) }
        SystemClock.sleep(250)
        checkEditor(); driver.tapDelete()
        SystemClock.sleep(250)
        space(); type("teh"); space()
        SystemClock.sleep(250)
        reportState(6)
        instrumentation.sendStatus(2, Bundle().apply { putString("dom_checkpoint", "sixth_after_undo") })
    }
}
