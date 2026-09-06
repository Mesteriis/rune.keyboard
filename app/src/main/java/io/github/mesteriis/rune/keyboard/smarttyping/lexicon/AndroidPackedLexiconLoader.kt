package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import android.content.res.AssetFileDescriptor
import android.content.res.AssetManager
import android.os.ParcelFileDescriptor
import java.nio.ByteBuffer

/** Off-main-thread APK loader. Compressed/missing assets fail unavailable; never extract or download. */
object AndroidPackedLexiconLoader {
    fun load(assets: AssetManager, trusted: TrustedPackedLexicon): PackedLexiconLoad {
        return try {
            PackedLexiconData.verifyManifest(trusted)
            fun map(asset: PackedAsset): ByteBuffer {
                PackedLexiconData.checkInterrupted()
                return assets.openFd(asset.path).use { descriptor ->
                    mapDescriptor(descriptor, asset.bytes)
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

    /** The mapping helper needs whole-file size and absolute offsets, not an asset-bounded channel. */
    internal fun mapDescriptor(descriptor: AssetFileDescriptor, expectedLength: Long): ByteBuffer {
        // Own a duplicate independently of the caller's AssetFileDescriptor. The outer use also
        // covers stream-construction failure; ParcelFileDescriptor.close is idempotent.
        return ParcelFileDescriptor.dup(descriptor.fileDescriptor).use { duplicate ->
            ParcelFileDescriptor.AutoCloseInputStream(duplicate).use { stream ->
                PackedAssetMapping.map(stream.channel, descriptor.startOffset, descriptor.declaredLength, expectedLength)
            }
        }
    }
}
