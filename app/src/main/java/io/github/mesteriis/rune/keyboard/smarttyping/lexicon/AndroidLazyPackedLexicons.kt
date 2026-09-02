package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import android.content.res.AssetManager
import io.github.mesteriis.rune.keyboard.ime.model.KeyboardLanguage

/** Supply application assets; this source retains neither Context/service nor completion callbacks. */
object AndroidLazyPackedLexicons {
    fun create(assets: AssetManager): LazyPackedLexicons = LazyPackedLexicons(AssetSource(assets))

    private class AssetSource(private val assets: AssetManager) : PackedLanguageSource {
        override fun load(language: KeyboardLanguage): PackedLexiconLoad = AndroidPackedLexiconLoader.load(assets, when (language) {
            KeyboardLanguage.ENGLISH -> FrozenPackedLexicons.ENGLISH
            KeyboardLanguage.SPANISH -> FrozenPackedLexicons.SPANISH
            KeyboardLanguage.RUSSIAN -> FrozenPackedLexicons.RUSSIAN
        })
    }
}
