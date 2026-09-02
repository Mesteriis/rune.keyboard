package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import java.nio.ByteBuffer
import java.nio.channels.FileChannel

/** Absolute asset-region mapping; no mutable channel-position arithmetic or extraction fallback. */
internal object PackedAssetMapping {
    fun map(channel: FileChannel, startOffset: Long, declaredLength: Long, expectedLength: Long): ByteBuffer {
        val fileLength = channel.size()
        packedRequire(startOffset >= 0 && declaredLength == expectedLength && declaredLength in 1..Int.MAX_VALUE.toLong() &&
            startOffset <= fileLength && declaredLength <= fileLength - startOffset, PackedLoadFailure.ASSET_RANGE)
        return channel.map(FileChannel.MapMode.READ_ONLY, startOffset, declaredLength)
    }
}
