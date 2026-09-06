package io.github.mesteriis.rune.keyboard.qa

import android.content.ContextWrapper
import android.inputmethodservice.InputMethodService
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.By
import androidx.test.uiautomator.Until
import io.github.mesteriis.rune.keyboard.R
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class EditorBoundaryInstrumentedTest : ImeTestBase() {
    @Test
    fun distinctEditorResetsManualShiftAndSymbolsThroughBinder() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        driver.configureEnglishStartingLanguage()
        // Visual session reset needs only normal editors. Seed the plain field at an interior
        // cursor position so its caps policy is OFF; do not visit email/URL/password fields.
        driver.tapQaControl("qa_seed_cursor")
        driver.awaitFieldText("qa_plain_text", "leftright")
        assertServedEditor(R.id.qa_plain_text)
        driver.assertKeyVisible("EN")
        driver.assertKeyVisible("c")
        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
        driver.tapKeyByDescription(context.getString(R.string.key_shift))
        InstrumentationRegistry.getInstrumentation().waitForIdleSync()
        driver.device.wait(Until.hasObject(By.pkg(ImeTestDriver.PACKAGE_NAME).text("C")), 5_000L)
        driver.assertKeyVisible("C")
        // The existing multiline field does not request automatic capitalization.
        driver.focusField("qa_multiline_text")
        assertServedEditor(R.id.qa_multiline_text)
        driver.assertKeyVisible("c")
        driver.tapKey("c")
        driver.revealFieldAndAwaitText("qa_multiline_text", "c")

        driver.focusField("qa_multiline_text")
        driver.tapKeyByDescription(context.getString(R.string.key_symbols))
        assertTrue(driver.device.hasObject(By.desc(context.getString(R.string.key_letters))))
        driver.focusField("qa_plain_text")
        assertServedEditor(R.id.qa_plain_text)
        driver.assertKeyVisible("q")
        driver.tapKey("q")
        // Selection is expected to be refreshed by editor focus changes between distinct fields.
        driver.revealFieldAndAwaitText("qa_plain_text", "leftrightq")
    }

    /** Verify actual Binder editor delivery, even if adjustResize hides its accessibility node. */
    private fun assertServedEditor(expectedFieldId: Int) {
        val keyboard = keyboardSnapshot().keyboard
        var result: Result<Unit>? = null
        InstrumentationRegistry.getInstrumentation().runOnMainSync {
            result = runCatching {
                var context = keyboard.context
                while (context is ContextWrapper && context !is InputMethodService) {
                    val base = context.baseContext
                    check(base !== context) { "Keyboard context wrapper cycle" }
                    context = base
                }
                val service = checkNotNull(context as? InputMethodService)
                assertEquals("Rune must serve the intended normal editor", expectedFieldId,
                    service.currentInputEditorInfo?.fieldId)
                assertTrue("Rune input view must be shown for the editor", service.isInputViewShown)
            }
        }
        checkNotNull(result).getOrThrow()
    }

    @Test
    fun injectedDownAndUpCommitExactlyOneKey() {
        driver.tapQaControl("qa_seed_cursor")
        val touch = driver.touchDown(driver.characterKey("a", "A"))
        driver.releaseTouch(touch)
        driver.awaitFieldText("qa_plain_text", "leftaright")
    }

    @Test
    fun commitReplaceDeleteAndCursorBoundariesCrossBinder() {
        driver.tapQaControl("qa_seed_cursor")
        driver.tapKey("a", "A")
        driver.awaitFieldText("qa_plain_text", "leftaright")

        driver.tapQaControl("qa_seed_selection")
        driver.tapKey("a", "A")
        driver.awaitFieldText("qa_plain_text", "beforeaafter")

        driver.tapQaControl("qa_seed_selection")
        driver.tapDelete()
        driver.awaitFieldText("qa_plain_text", "beforeafter")

        driver.tapQaControl("qa_seed_cursor")
        driver.tapDelete()
        driver.awaitFieldText("qa_plain_text", "lefright")

        driver.tapQaControl("qa_seed_start")
        driver.tapDelete()
        driver.awaitFieldText("qa_plain_text", "start")
    }

    @Test
    fun cyrillicSurrogateAndComplexGraphemesAreAtomic() {
        driver.tapQaControl("qa_seed_unicode")
        driver.tapDelete()
        driver.awaitFieldText("qa_plain_text", "Привет")

        driver.switchToRussian()
        driver.tapKey("я", "Я")
        driver.awaitFieldText("qa_plain_text", "Приветя")

        driver.tapQaControl("qa_seed_graphemes")
        val expectedAfterDeletes = listOf(
            "xе́1️⃣🇺🇦👍🏽🧑🏽‍💻👩‍❤️‍💋‍👨",
            "xе́1️⃣🇺🇦👍🏽🧑🏽‍💻",
            "xе́1️⃣🇺🇦👍🏽",
            "xе́1️⃣🇺🇦",
            "xе́1️⃣",
            "xе́",
            "x",
        )
        expectedAfterDeletes.forEach { expected ->
            driver.tapDelete()
            driver.awaitFieldText("qa_plain_text", expected)
        }
    }

    @Test
    fun editorFieldTypesExposeTheirRequiredLayouts() {
        driver.focusField("qa_email")
        driver.assertKeyVisible("@")
        driver.focusField("qa_url")
        driver.assertKeyVisible("/")
        driver.focusField("qa_phone")
        driver.assertKeyVisible("#")
        driver.assertKeyVisible("*")
        driver.focusField("qa_number")
        driver.assertKeyVisible("-")
        driver.assertKeyVisible(".")
        driver.focusField("qa_password")
        driver.assertKeyVisible("?123")
    }
}
