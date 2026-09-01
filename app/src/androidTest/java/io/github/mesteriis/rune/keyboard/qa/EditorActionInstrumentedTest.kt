package io.github.mesteriis.rune.keyboard.qa

import androidx.test.ext.junit.runners.AndroidJUnit4
import io.github.mesteriis.rune.keyboard.R
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class EditorActionInstrumentedTest : ImeTestBase() {
    @Test
    fun standardAndCustomEditorActionsReachTheRemoteEditor() {
        val cases = listOf(
            ActionCase("qa_action_send", R.string.key_send, 4),
            ActionCase("qa_action_search", R.string.key_search, 3),
            ActionCase("qa_action_go", R.string.key_go, 2),
            ActionCase("qa_action_next", R.string.key_next, 5),
            ActionCase("qa_action_done", R.string.key_done, 6),
            ActionCase("qa_custom_action", R.string.qa_custom_action, 0),
        )
        cases.forEachIndexed { index, case ->
            driver.focusField(case.field)
            driver.tapEnter(case.keyDescription)
            driver.awaitStatus("Action received: ${case.actionId}")
            if (index != cases.lastIndex) {
                driver.device.pressBack()
                driver.launchQa()
            }
        }
    }

    @Test
    fun multilineEnterCommitsANewlineInsteadOfSending() {
        driver.focusField("qa_multiline_text")
        driver.tapKey("a", "A")
        driver.tapEnter(R.string.key_enter)
        driver.tapKey("b", "B")
        driver.awaitFieldText("qa_multiline_text", "a\nb")
    }

    private data class ActionCase(val field: String, val keyDescription: Int, val actionId: Int)
}
