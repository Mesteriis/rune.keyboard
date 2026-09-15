package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import android.content.res.AssetManager
import android.os.Looper

/** Public dictionary mapping and verification runs only on a worker; absent/compressed assets veto. */
object AndroidMorphologyLexiconLoader {
    const val ASSET_PATH = "smarttyping/lexicon/ru.morph"
    const val ASSET_BYTES = 28_591_430L
    const val ASSET_SHA256 = "c1707864a8fbc805aa98bc8307be99f2c9904eec5cc27d26a5220e001d88d28b"

    fun load(assets: AssetManager): MorphologyLexicon {
        if (Looper.myLooper() == Looper.getMainLooper() || Thread.currentThread().isInterrupted)
            return MorphologyLexicon.UNAVAILABLE
        return try {
            assets.openFd(ASSET_PATH).use { descriptor ->
                PackedMorphologyLexicon.open(
                    AndroidPackedLexiconLoader.mapDescriptor(descriptor, ASSET_BYTES), ASSET_SHA256)
            }
        } catch (_: Exception) {
            MorphologyLexicon.UNAVAILABLE
        }
    }
}
