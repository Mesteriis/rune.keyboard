package io.github.mesteriis.rune.keyboard.qa

import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class EditorBoundaryInstrumentedTest : ImeTestBase() {
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
