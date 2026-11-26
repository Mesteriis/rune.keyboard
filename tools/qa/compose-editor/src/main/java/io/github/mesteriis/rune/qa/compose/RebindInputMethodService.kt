package io.github.mesteriis.rune.qa.compose

import android.inputmethodservice.InputMethodService

/** Allows a real service unbind and rebind without launching a system keyboard. */
class RebindInputMethodService : InputMethodService()
