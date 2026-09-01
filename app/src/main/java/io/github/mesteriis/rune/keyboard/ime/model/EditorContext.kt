package io.github.mesteriis.rune.keyboard.ime.model

import android.text.InputType
import android.view.inputmethod.EditorInfo

enum class EditorMode {
    TEXT,
    EMAIL,
    URI,
    NUMBER,
    PHONE,
    DATE_TIME,
}

/**
 * Runtime input policy every text-touching component must consult.
 * SENSITIVE forbids anything beyond plain committing: no preview popups, no text reads,
 * no learning. An INCOGNITO value joins this enum once learning subsystems exist.
 */
enum class InputPolicy {
    NORMAL,
    SENSITIVE,
}

data class EditorContext(
    val inputType: Int,
    val imeOptions: Int,
    val mode: EditorMode,
    val isPassword: Boolean,
    val allowsSignedNumber: Boolean,
    val allowsDecimalNumber: Boolean,
    val requiresRawKeyEvents: Boolean,
    val isMultiLine: Boolean = false,
    val noPersonalizedLearning: Boolean = false,
    val customActionId: Int? = null,
    val customActionLabel: String? = null,
) {
    val inputPolicy: InputPolicy
        get() = if (isPassword || noPersonalizedLearning) InputPolicy.SENSITIVE else InputPolicy.NORMAL

    val supportsAutomaticCapitalization: Boolean
        get() = mode == EditorMode.TEXT && !isPassword

    /**
     * Double space converts to ". " only where a sentence separator makes sense and where the
     * bounded two-character guard read is acceptable: plain text, never passwords, never TYPE_NULL.
     */
    val supportsDoubleSpacePeriod: Boolean
        get() = mode == EditorMode.TEXT && !isPassword && !requiresRawKeyEvents

    companion object {
        fun from(editorInfo: EditorInfo): EditorContext = from(
            inputType = editorInfo.inputType,
            imeOptions = editorInfo.imeOptions,
        ).copy(
            customActionId = editorInfo.actionId.takeIf {
                editorInfo.actionLabel != null
            },
            customActionLabel = editorInfo.actionLabel?.toString(),
        )

        fun from(inputType: Int, imeOptions: Int): EditorContext {
            val inputClass = inputType and InputType.TYPE_MASK_CLASS
            val variation = inputType and InputType.TYPE_MASK_VARIATION
            val mode = when (inputClass) {
                InputType.TYPE_CLASS_NUMBER -> EditorMode.NUMBER
                InputType.TYPE_CLASS_PHONE -> EditorMode.PHONE
                InputType.TYPE_CLASS_DATETIME -> EditorMode.DATE_TIME
                InputType.TYPE_CLASS_TEXT -> when (variation) {
                    InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS,
                    InputType.TYPE_TEXT_VARIATION_WEB_EMAIL_ADDRESS,
                    -> EditorMode.EMAIL
                    InputType.TYPE_TEXT_VARIATION_URI -> EditorMode.URI
                    else -> EditorMode.TEXT
                }
                else -> EditorMode.TEXT
            }
            return EditorContext(
                inputType = inputType,
                imeOptions = imeOptions,
                mode = mode,
                isPassword = isPasswordVariation(inputClass, variation),
                allowsSignedNumber = inputType and InputType.TYPE_NUMBER_FLAG_SIGNED != 0,
                allowsDecimalNumber = inputType and InputType.TYPE_NUMBER_FLAG_DECIMAL != 0,
                requiresRawKeyEvents = inputType == InputType.TYPE_NULL,
                isMultiLine = inputClass == InputType.TYPE_CLASS_TEXT &&
                    inputType and InputType.TYPE_TEXT_FLAG_MULTI_LINE != 0,
                noPersonalizedLearning = imeOptions and
                    EditorInfo.IME_FLAG_NO_PERSONALIZED_LEARNING != 0,
            )
        }

        private fun isPasswordVariation(inputClass: Int, variation: Int): Boolean = when (inputClass) {
            InputType.TYPE_CLASS_NUMBER -> variation == InputType.TYPE_NUMBER_VARIATION_PASSWORD
            InputType.TYPE_CLASS_TEXT -> variation in setOf(
                InputType.TYPE_TEXT_VARIATION_PASSWORD,
                InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD,
                InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD,
            )
            else -> false
        }
    }
}
