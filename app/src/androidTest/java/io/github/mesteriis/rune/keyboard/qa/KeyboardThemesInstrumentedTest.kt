package io.github.mesteriis.rune.keyboard.qa

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.drawable.ColorDrawable
import android.content.res.Configuration
import android.text.InputType
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.TextView
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.R
import io.github.mesteriis.rune.keyboard.settings.AutocorrectionMode
import io.github.mesteriis.rune.keyboard.settings.KeyboardPreferences
import io.github.mesteriis.rune.keyboard.settings.KeyboardTheme
import io.github.mesteriis.rune.keyboard.settings.ThemePreference
import io.github.mesteriis.rune.keyboard.settings.KeyboardViewMetrics
import io.github.mesteriis.rune.keyboard.ime.ui.RuneKeyboardView
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
        for ((theme, label) in choices) {
            driver.launchSettings()
            driver.chooseSetting(R.string.settings_keyboard_theme, label)
            assertEquals(theme, KeyboardPreferences(context).readSettings().keyboardTheme)
            assertEquals(ThemePreference.LIGHT, preferences.readSettings().theme)
            driver.launchComposingQa()
            for (letter in "hello") driver.tapKey(letter.toString())
            driver.awaitFieldText("qa_composing_text", "hello")
            captureAndCheck(theme)
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
                for (theme in KeyboardTheme.entries) {
                    val view = RuneKeyboardView(themedContext, KeyboardViewMetrics(168, 9), theme)
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
                    File(directory, "reference-${theme.name.lowercase()}.png").outputStream().use {
                        assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it))
                    }
                    bitmap.recycle()
                }
            }
        }
        checkNotNull(result).getOrThrow()
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

    private fun captureAndCheck(theme: KeyboardTheme) {
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
                File(directory, "${theme.name.lowercase()}.png").outputStream().use {
                    assertTrue(bitmap.compress(Bitmap.CompressFormat.PNG, 100, it))
                }
                bitmap.recycle()
            }
        }
        checkNotNull(result).getOrThrow()
    }
}
