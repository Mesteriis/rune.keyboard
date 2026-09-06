package io.github.mesteriis.rune.keyboard.qa

import androidx.test.ext.junit.runners.AndroidJUnit4
import io.github.mesteriis.rune.keyboard.ime.model.EditorMode
import io.github.mesteriis.rune.keyboard.ime.model.InputPolicy
import org.junit.Test
import org.junit.runner.RunWith

/** Real resident IME and remote editor; model/caps observers have a NORMAL positive control. */
@RunWith(AndroidJUnit4::class)
class NonNormalEditorInstrumentedTest : ImeTestBase() {
    @Test fun passwordKeepsOriginalWithoutSmartTypingOrReads() =
        verify("password", EditorMode.TEXT, InputPolicy.SENSITIVE, "a helllo .  ")

    @Test fun noPersonalizedLearningKeepsOriginalWithoutSmartTypingOrReads() =
        verify("private", EditorMode.TEXT, InputPolicy.SENSITIVE, "a helllo .  ")

    @Test fun emailKeepsOriginalWithoutSmartTypingOrReads() =
        verify("email", EditorMode.EMAIL, InputPolicy.NORMAL, "a helllo .  ")

    @Test fun urlKeepsOriginalWithoutSmartTypingOrReads() =
        verify("url", EditorMode.URI, InputPolicy.NORMAL, "a helllo .  ")

    @Test fun numberKeepsOriginalWithoutSmartTypingOrReads() =
        verify("number", EditorMode.NUMBER, InputPolicy.NORMAL, "12.34")

    @Test fun phoneKeepsOriginalWithoutSmartTypingOrReads() =
        verify("phone", EditorMode.PHONE, InputPolicy.NORMAL, "+123#45")

    @Test fun dateTimeKeepsOriginalWithoutSmartTypingOrReads() =
        verify("date_time", EditorMode.DATE_TIME, InputPolicy.NORMAL, "12:34/56")

    private fun verify(mode: String, editorMode: EditorMode, policy: InputPolicy, publicText: String) {
        LiveFakeModelBinderFixture.install(driver).use { fixture ->
            fixture.proveNormalPipelineObservers()
            fixture.verifyNonNormalEditor(mode, editorMode, policy, publicText)
        }
    }
}
