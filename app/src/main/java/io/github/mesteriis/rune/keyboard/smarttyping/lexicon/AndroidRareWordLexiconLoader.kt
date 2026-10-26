package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import android.content.res.AssetManager
import android.os.Looper

object AndroidRareWordLexiconLoader {
    fun load(assets: AssetManager): RareWordLexicon {
        if (Looper.myLooper() == Looper.getMainLooper() || Thread.currentThread().isInterrupted)
            return RareWordLexicon.UNAVAILABLE
        return try {
            assets.openFd(FrozenRareWordLexicon.ASSET_PATH).use { descriptor ->
                PackedRareWordLexicon.open(AndroidPackedLexiconLoader.mapDescriptor(
                    descriptor, FrozenRareWordLexicon.ASSET_BYTES), FrozenRareWordLexicon.ASSET_SHA256)
            }
        } catch (_: Exception) {
            RareWordLexicon.UNAVAILABLE
        }
    }
}
