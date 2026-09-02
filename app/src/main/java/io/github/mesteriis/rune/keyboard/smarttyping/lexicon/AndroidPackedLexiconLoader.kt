package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import android.content.res.AssetManager
import java.nio.ByteBuffer

/** Off-main-thread APK loader. Compressed/missing assets fail unavailable; never extract or download. */
object AndroidPackedLexiconLoader {
    fun load(assets: AssetManager, trusted: TrustedPackedLexicon): PackedLexiconLoad {
        return try {
            PackedLexiconData.verifyManifest(trusted)
            fun map(asset: PackedAsset): ByteBuffer {
                PackedLexiconData.checkInterrupted()
                return assets.openFd(asset.path).use { descriptor ->
                    descriptor.createInputStream().use { stream ->
                        PackedAssetMapping.map(stream.channel, descriptor.startOffset, descriptor.declaredLength, asset.bytes)
                    }
                }
            }
            val m = trusted.manifest
            PackedLexiconData.validate(trusted, map(m.trie), map(m.lengths), map(m.ranks))
        } catch (failure: PackedValidationException) {
            PackedLexiconLoad.Failed(failure.reason)
        } catch (_: Exception) {
            PackedLexiconLoad.Failed(if (Thread.currentThread().isInterrupted) PackedLoadFailure.CANCELLED else PackedLoadFailure.IO)
        }
        // Closed descriptor/channel references do not unmap pages. No Unsafe/reflection is used.
    }
}
