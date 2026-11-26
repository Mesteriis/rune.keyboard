package io.github.mesteriis.rune.keyboard.qa

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.content.ContextWrapper
import android.content.res.Configuration
import android.os.Build
import android.os.SystemClock
import android.text.InputType
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsetsController
import android.view.inputmethod.EditorInfo
import android.widget.TextView
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.core.app.ActivityScenario
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences
import io.github.mesteriis.rune.keyboard.settings.KeyboardTheme
import io.github.mesteriis.rune.keyboard.settings.KeyboardPalette
import io.github.mesteriis.rune.keyboard.settings.ThemePreference
import io.github.mesteriis.rune.keyboard.settings.KeyboardViewMetrics
import io.github.mesteriis.rune.keyboard.settings.SetupActivity
import io.github.mesteriis.rune.keyboard.ime.ui.RuneKeyboardView
import io.github.mesteriis.rune.keyboard.ime.RuneInputMethodService
import io.github.mesteriis.rune.keyboard.ime.layout.KeyboardLayoutProvider
import io.github.mesteriis.rune.keyboard.ime.model.EditorContext
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardState
import io.github.mesteriis.rune.keyboard.smarttyping.ui.CandidateUiItem
import io.github.mesteriis.rune.keyboard.smarttyping.ui.SmartTypingViewState
import java.io.File
import org.junit.Assert.*
import org.junit.Test

/** Real settings, persisted selection and live IME rendering; only synthetic text is captured. */
class KeyboardThemesInstrumentedTest : ImeTestBase() {
    private val instrumentation = InstrumentationRegistry.getInstrumentation()
    private val context = instrumentation.targetContext
    private val preferences = KeyboardPreferences(context)

    @Test fun allFiveThemesCanBeSelectedAndTypedWith() {
        driver.configureEnglishStartingLanguage()
        driver.configureSmartTyping(AutocorrectionMode.OFF, true, mechanical = false, doubleSpace = false)
        preferences.writeTheme(ThemePreference.LIGHT)
        val choices = listOf(
            KeyboardTheme.AIR to R.string.keyboard_theme_air,
            KeyboardTheme.SOFT to R.string.keyboard_theme_soft,
            KeyboardTheme.OUTLINE to R.string.keyboard_theme_outline,
            KeyboardTheme.MONOLITH to R.string.keyboard_theme_monolith,
            KeyboardTheme.SILENT to R.string.keyboard_theme_silent,
        )
        for (palette in listOf(KeyboardPalette.DARK, KeyboardPalette.LIGHT)) for ((theme, label) in choices) {
            preferences.writeKeyboardPalette(palette)
            driver.launchSettings()
            driver.chooseSetting(R.string.settings_keyboard_theme, label)
            assertEquals(theme, KeyboardPreferences(context).readSettings().keyboardTheme)
            assertEquals(palette, KeyboardPreferences(context).readSettings().keyboardPalette)
            assertEquals(ThemePreference.LIGHT, preferences.readSettings().theme)
            driver.launchComposingQa()
            for (letter in "hello") driver.tapKey(letter.toString())
            driver.awaitFieldText("qa_composing_text", "hello")
            captureAndCheck(theme, palette)
            driver.tapDelete()
            driver.awaitFieldText("qa_composing_text", "hell")
            driver.tapKeyByDescription(context.getString(R.string.key_space))
            driver.awaitFieldText("qa_composing_text", "hell ")
        }
    }

    @Test fun liveThemeChangeKeepsEditorTextAndRebuildsAppearance() {
        driver.configureEnglishStartingLanguage()
        driver.configureSmartTyping(AutocorrectionMode.OFF, true, mechanical = false, doubleSpace = false)
        driver.launchComposingQa()
        driver.tapKey("h"); driver.tapKey("i")
        driver.awaitFieldText("qa_composing_text", "hi")
        for (theme in KeyboardTheme.entries) {
            val before = keyboardSnapshot()
            preferences.writeKeyboardTheme(theme)
            instrumentation.waitForIdleSync()
            driver.device.waitForIdle()
            if (theme != KeyboardTheme.AIR) assertNotSame(before.keyboard, keyboardSnapshot().keyboard)
            driver.awaitFieldText("qa_composing_text", "hi")
        }
        driver.tapKey("x")
        driver.awaitFieldText("qa_composing_text", "hix")
    }

    @Test fun renderDesignReferencesAtTheMockViewport() {
        var result: Result<Unit>? = null
        instrumentation.runOnMainSync {
            result = runCatching {
                val configuration = Configuration(context.resources.configuration).apply {
                    densityDpi = 480
                    fontScale = 1f
                    screenWidthDp = 390
                    screenHeightDp = 844
                    smallestScreenWidthDp = 390
                    orientation = Configuration.ORIENTATION_PORTRAIT
                }
                val themedContext = context.createConfigurationContext(configuration)
                val state = KeyboardState(KeyboardLanguage.ENGLISH)
                val editor = EditorContext.from(EditorInfo().apply {
                    inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE
                })
                val layout = KeyboardLayoutProvider().layoutFor(state, editor)
                for (theme in KeyboardTheme.entries) for (light in listOf(false, true)) {
                    val view = RuneKeyboardView(themedContext, KeyboardViewMetrics(168, 9), theme, light)
                    view.render(layout, state)
                    view.updateCandidates(SmartTypingViewState(true, listOf(
                        CandidateUiItem.Original("original", "good"),
                        CandidateUiItem.Correction("first", "great"),
                        CandidateUiItem.Correction("second", "thanks"),
                    ), "first"))
                    view.measure(View.MeasureSpec.makeMeasureSpec(1170, View.MeasureSpec.EXACTLY),
                        View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
                    view.layout(0, 0, view.measuredWidth, view.measuredHeight)
                    val bitmap = Bitmap.createBitmap(view.width, view.height, Bitmap.Config.ARGB_8888)
                    view.draw(Canvas(bitmap))
                    val directory = File(context.getExternalFilesDir(null), "theme-qa").apply { mkdirs() }
                    val suffix = if (light) "-light" else ""
                    File(directory, "reference-${theme.name.lowercase()}$suffix.png").outputStream().use {
                        assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it))
                    }
                    bitmap.recycle()
                }
            }
        }
        checkNotNull(result).getOrThrow()
    }

    @Test fun paletteChangesRebuildImeAndKeepItsText() {
        driver.configureEnglishStartingLanguage()
        driver.configureSmartTyping(AutocorrectionMode.OFF, true, mechanical = false, doubleSpace = false)
        driver.launchComposingQa()
        driver.tapKey("h"); driver.tapKey("i")
        driver.awaitFieldText("qa_composing_text", "hi")
        preferences.writeKeyboardTheme(KeyboardTheme.AIR)
        for (palette in listOf(KeyboardPalette.LIGHT, KeyboardPalette.DARK, KeyboardPalette.SYSTEM)) {
            preferences.writeKeyboardPalette(palette)
            instrumentation.waitForIdleSync()
            driver.device.waitForIdle()
            val snapshot = keyboardSnapshot()
            var color = 0
            var navigationColor = 0
            var lightNavigation = false
            instrumentation.runOnMainSync {
                color = (snapshot.keyboard.background as ColorDrawable).color
                var owner = snapshot.keyboard.rootView.context
                while (owner is ContextWrapper && owner !is RuneInputMethodService) {
                    val next = owner.baseContext
                    check(next !== owner)
                    owner = next
                }
                val service = checkNotNull(owner as? RuneInputMethodService)
                @Suppress("DEPRECATION")
                val imeWindow = checkNotNull(service.window?.window)
                navigationColor = imeWindow.navigationBarColor
                @Suppress("DEPRECATION")
                lightNavigation = if (Build.VERSION.SDK_INT >= 30) {
                    checkNotNull(imeWindow.insetsController).systemBarsAppearance and
                        WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS != 0
                } else if (Build.VERSION.SDK_INT >= 27) {
                    imeWindow.decorView.systemUiVisibility and View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR != 0
                } else false
            }
            val night = context.resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES
            val light = palette.isLight(night)
            assertEquals(light, Color.red(color) > 127)
            if (Build.VERSION.SDK_INT < 35)
                assertEquals(if (light && Build.VERSION.SDK_INT >= 27) 0xe8 else 0x18, Color.red(navigationColor))
            assertEquals(light && Build.VERSION.SDK_INT >= 27, lightNavigation)
            val screen = checkNotNull(instrumentation.uiAutomation.takeScreenshot())
            try {
                val pixel = screen.getPixel((screen.width * .05f).toInt(), screen.height - 4)
                if (light && Build.VERSION.SDK_INT >= 27) assertTrue("Light navigation backdrop", Color.red(pixel) >= 128)
                else assertTrue("Dark navigation backdrop", Color.red(pixel) < 100)
            } finally { screen.recycle() }
            driver.awaitFieldText("qa_composing_text", "hi")
        }
        driver.tapKey("x")
        driver.awaitFieldText("qa_composing_text", "hix")
    }

    @Test fun paletteChoicePersistsThroughSettings() {
        driver.launchSettings()
        for ((palette, label) in listOf(
            KeyboardPalette.LIGHT to R.string.keyboard_palette_light,
            KeyboardPalette.SYSTEM to R.string.keyboard_palette_system,
            KeyboardPalette.DARK to R.string.keyboard_palette_dark,
        )) {
            driver.chooseSetting(R.string.settings_keyboard_palette, label)
            assertEquals(palette, KeyboardPreferences(context).readSettings().keyboardPalette)
        }
    }

    @Test fun captureNavigationPalettesForVisualInspection() {
        driver.configureEnglishStartingLanguage()
        driver.configureSmartTyping(AutocorrectionMode.OFF, true, mechanical = false, doubleSpace = false)
        driver.launchComposingQa()
        driver.tapKey("h")
        driver.awaitFieldText("qa_composing_text", "h")
        val directory = File(context.getExternalFilesDir(null), "theme-qa").apply { mkdirs() }
        for (palette in listOf(KeyboardPalette.DARK, KeyboardPalette.LIGHT)) {
            preferences.writeKeyboardPalette(palette)
            instrumentation.waitForIdleSync()
            driver.device.waitForIdle()
            // System navigation may still be animating after the app's view queue is idle.
            SystemClock.sleep(500)
            val bitmap = checkNotNull(instrumentation.uiAutomation.takeScreenshot())
            try {
                File(directory, "navigation-${palette.name.lowercase()}.png").outputStream().use {
                    assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it))
                }
            } finally { bitmap.recycle() }
        }
    }

    @Test fun homePreviewUsesTheKeyboardPalette() {
        preferences.writeTheme(ThemePreference.DARK)
        val night = context.resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK == Configuration.UI_MODE_NIGHT_YES
        for (palette in KeyboardPalette.entries) {
            preferences.writeKeyboardPalette(palette)
            ActivityScenario.launch(SetupActivity::class.java).use { scenario ->
                scenario.onActivity { activity ->
                    val preview = activity.findViewById<ViewGroup>(R.id.menu_preview).getChildAt(0) as RuneKeyboardView
                    assertEquals(palette.isLight(night), Color.red((preview.background as ColorDrawable).color) > 127)
                }
            }
        }
    }

    @Test fun captureLightPaletteOnHomeScreen() {
        preferences.writeKeyboardPalette(KeyboardPalette.LIGHT)
        ActivityScenario.launch(SetupActivity::class.java).use { scenario ->
            instrumentation.waitForIdleSync()
            driver.device.waitForIdle()
            SystemClock.sleep(500)
            scenario.onActivity { activity ->
                val preview = activity.findViewById<ViewGroup>(R.id.menu_preview).getChildAt(0) as RuneKeyboardView
                assertTrue(Color.red((preview.background as ColorDrawable).color) > 127)
            }
            val bitmap = checkNotNull(instrumentation.uiAutomation.takeScreenshot())
            try {
                val directory = File(context.getExternalFilesDir(null), "theme-qa").apply { mkdirs() }
                File(directory, "home-light.png").outputStream().use {
                    assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it))
                }
            } finally { bitmap.recycle() }
        }
    }

    @Test fun systemPaletteFollowsSystemChangesWithoutLosingEditorText() {
        val originalMode = driver.shell("cmd uimode night").substringAfter(": ").trim()
        check(originalMode in setOf("yes", "no", "auto"))
        try {
            driver.configureEnglishStartingLanguage()
            driver.configureSmartTyping(AutocorrectionMode.OFF, true, mechanical = false, doubleSpace = false)
            preferences.writeTheme(ThemePreference.DARK)
            preferences.writeKeyboardPalette(KeyboardPalette.SYSTEM)
            driver.launchComposingQa()
            driver.tapKey("h"); driver.tapKey("i")
            driver.awaitFieldText("qa_composing_text", "hi")
            for ((mode, expectLight) in listOf("yes" to false, "no" to true)) {
                driver.shell("cmd uimode night $mode")
                val deadline = SystemClock.uptimeMillis() + 20_000
                var matched = false
                while (SystemClock.uptimeMillis() < deadline && !matched) {
                    instrumentation.waitForIdleSync()
                    val color = runCatching {
                        var value = 0
                        val snapshot = keyboardSnapshot()
                        instrumentation.runOnMainSync { value = (snapshot.keyboard.background as ColorDrawable).color }
                        value
                    }.getOrNull()
                    matched = color != null && (Color.red(color) > 127) == expectLight
                    if (!matched) SystemClock.sleep(100)
                }
                assertTrue("System palette did not update for $mode", matched)
                driver.awaitFieldText("qa_composing_text", "hi")
            }
        } finally {
            driver.shell("cmd uimode night $originalMode")
            instrumentation.waitForIdleSync()
        }
    }

    @Test fun languageSwipeWorksWithEachThemeAndEnabledLanguages() {
        driver.configureEnglishStartingLanguage()
        preferences.writeEnabledLanguages(listOf(KeyboardLanguage.ENGLISH, KeyboardLanguage.RUSSIAN))
        driver.configureSmartTyping(AutocorrectionMode.OFF, true, mechanical = false, doubleSpace = false)
        for (theme in KeyboardTheme.entries) {
            preferences.writeKeyboardTheme(theme)
            driver.launchComposingQa()
            driver.tapKey("a")
            driver.switchToRussian()
            driver.awaitFieldText("qa_composing_text", "a")
            driver.tapKey("я")
            driver.awaitFieldText("qa_composing_text", "aя")
        }
    }

    private fun captureAndCheck(theme: KeyboardTheme, palette: KeyboardPalette) {
        val snapshot = keyboardSnapshot()
        var result: Result<Unit>? = null
        instrumentation.runOnMainSync {
            result = runCatching {
                val keyboard = snapshot.keyboard
                val color = (keyboard.background as ColorDrawable).color
                assertEquals(Color.red(color), Color.green(color))
                assertEquals(Color.green(color), Color.blue(color))
                val letter = snapshot.keys.filterIsInstance<TextView>().first { it.text.toString() == "h" }
                assertTrue("Height increase missing", letter.height >= 56 * context.resources.displayMetrics.density - 1)
                val pixels = Bitmap.createBitmap(letter.width, letter.height, Bitmap.Config.ARGB_8888)
                letter.background.setBounds(0, 0, letter.width, letter.height)
                letter.background.draw(Canvas(pixels))
                assertEquals("Idle letter must have no keycap", 0, Color.alpha(pixels.getPixel(letter.width / 2, letter.height / 2)))
                letter.isPressed = true
                pixels.eraseColor(Color.TRANSPARENT)
                letter.background.draw(Canvas(pixels))
                assertTrue("Pressed letter needs feedback", Color.alpha(pixels.getPixel(letter.width / 2, letter.height / 2)) > 0)
                letter.isPressed = false
                pixels.recycle()
                val bitmap = Bitmap.createBitmap(keyboard.width, keyboard.height, Bitmap.Config.ARGB_8888)
                keyboard.draw(Canvas(bitmap))
                val directory = File(context.getExternalFilesDir(null), "theme-qa").apply { mkdirs() }
                File(directory, "${theme.name.lowercase()}-${palette.name.lowercase()}.png").outputStream().use {
                    assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it))
                }
                bitmap.recycle()
            }
        }
        checkNotNull(result).getOrThrow()
    }
}
