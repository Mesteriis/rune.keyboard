package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import android.content.res.AssetManager
import android.os.Looper

/** Public dictionary mapping and verification runs only on a worker; absent/compressed assets veto. */
object AndroidMorphologyLexiconLoader {
    const val ASSET_PATH = FrozenMorphologyLexicon.ASSET_PATH
    const val ASSET_BYTES = FrozenMorphologyLexicon.ASSET_BYTES
    const val ASSET_SHA256 = FrozenMorphologyLexicon.ASSET_SHA256

    fun load(assets: AssetManager): MorphologyLexicon {
        if (Looper.myLooper() == Looper.getMainLooper() || Thread.currentThread().isInterrupted)
            return MorphologyLexicon.UNAVAILABLE
        return try {
            assets.openFd(ASSET_PATH).use { descriptor ->
                PackedMorphologyLexicon.openPackaged(
                    AndroidPackedLexiconLoader.mapDescriptor(descriptor, ASSET_BYTES), ASSET_BYTES)
            }
        } catch (_: Exception) {
            MorphologyLexicon.UNAVAILABLE
        }
    }
}
