package io.github.mesteriis.rune.keyboard.intelligence.delivery

import java.io.InputStream
import java.io.OutputStream

object ModelFileExporter {
    fun copy(
        input: InputStream,
        output: OutputStream,
        deletePartial: () -> Unit = {},
    ) {
        try {
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                if (count > 0) output.write(buffer, 0, count)
            }
            output.flush()
        } catch (error: Exception) {
            runCatching(deletePartial)
            throw error
        }
    }
}
