package io.github.mesteriis.rune.keyboard.ime.model

import android.text.InputType
import android.view.inputmethod.EditorInfo
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class EditorContextTest {
    @Test
    fun `email variation selects email mode`() {
        val context = EditorContext.from(
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS,
            imeOptions = EditorInfo.IME_ACTION_NEXT,
        )

        assertEquals(EditorMode.EMAIL, context.mode)
        assertFalse(context.isPassword)
    }

    @Test
    fun `password disables automatic capitalization`() {
        val context = EditorContext.from(
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD,
            imeOptions = EditorInfo.IME_ACTION_DONE,
        )

        assertTrue(context.isPassword)
        assertFalse(context.supportsAutomaticCapitalization)
    }

    @Test
    fun `number flags are retained`() {
        val context = EditorContext.from(
            inputType = InputType.TYPE_CLASS_NUMBER or
                InputType.TYPE_NUMBER_FLAG_DECIMAL or
                InputType.TYPE_NUMBER_FLAG_SIGNED,
            imeOptions = EditorInfo.IME_ACTION_DONE,
        )

        assertEquals(EditorMode.NUMBER, context.mode)
        assertTrue(context.allowsDecimalNumber)
        assertTrue(context.allowsSignedNumber)
    }

    @Test
    fun `null input type requires raw key events`() {
        val context = EditorContext.from(
            inputType = InputType.TYPE_NULL,
            imeOptions = EditorInfo.IME_ACTION_NONE,
        )

        assertTrue(context.requiresRawKeyEvents)
    }

    @Test
    fun `multi-line flag is detected only for text editors`() {
        val multiLine = EditorContext.from(
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE,
            imeOptions = EditorInfo.IME_ACTION_DONE,
        )
        val imeMultiLineOnly = EditorContext.from(
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_IME_MULTI_LINE,
            imeOptions = EditorInfo.IME_ACTION_DONE,
        )
        val numberWithSameBit = EditorContext.from(
            inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_TEXT_FLAG_MULTI_LINE,
            imeOptions = EditorInfo.IME_ACTION_DONE,
        )

        assertTrue(multiLine.isMultiLine)
        assertFalse(imeMultiLineOnly.isMultiLine)
        assertFalse(numberWithSameBit.isMultiLine)
    }

    @Test
    fun `double space period is limited to plain text editors`() {
        val eligible = EditorContext.from(
            inputType = InputType.TYPE_CLASS_TEXT,
            imeOptions = EditorInfo.IME_ACTION_NONE,
        )
        val password = EditorContext.from(
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD,
            imeOptions = EditorInfo.IME_ACTION_DONE,
        )
        val email = EditorContext.from(
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS,
            imeOptions = EditorInfo.IME_ACTION_NEXT,
        )
        val rawKeyEvents = EditorContext.from(
            inputType = InputType.TYPE_NULL,
            imeOptions = EditorInfo.IME_ACTION_NONE,
        )

        assertTrue(eligible.supportsDoubleSpacePeriod)
        assertFalse(password.supportsDoubleSpacePeriod)
        assertFalse(email.supportsDoubleSpacePeriod)
        assertFalse(rawKeyEvents.supportsDoubleSpacePeriod)
    }

    @Test
    fun `sensitive input policy covers passwords and no-personalized-learning`() {
        val plain = EditorContext.from(
            inputType = InputType.TYPE_CLASS_TEXT,
            imeOptions = EditorInfo.IME_ACTION_NONE,
        )
        val password = EditorContext.from(
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD,
            imeOptions = EditorInfo.IME_ACTION_DONE,
        )
        val noLearning = EditorContext.from(
            inputType = InputType.TYPE_CLASS_TEXT,
            imeOptions = EditorInfo.IME_ACTION_NONE or EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING,
        )

        assertEquals(InputPolicy.NORMAL, plain.inputPolicy)
        assertEquals(InputPolicy.SENSITIVE, password.inputPolicy)
        assertEquals(InputPolicy.SENSITIVE, noLearning.inputPolicy)
    }

    @Test
    fun `custom action label retains zero action id`() {
        val editorInfo = EditorInfo().apply {
            inputType = InputType.TYPE_CLASS_TEXT
            imeOptions = EditorInfo.IME_ACTION_NONE
            actionId = 0
            actionLabel = "Apply"
        }

        val context = EditorContext.from(editorInfo)

        assertEquals(0, context.customActionId)
        assertEquals("Apply", context.customActionLabel)
    }
}
