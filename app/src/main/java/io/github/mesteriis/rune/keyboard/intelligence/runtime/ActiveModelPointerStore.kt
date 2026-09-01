package io.github.mesteriis.rune.keyboard.intelligence.runtime

import android.util.AtomicFile
import java.io.File
import java.io.RandomAccessFile

object ActiveModelPointerCodec {
    private val json = Regex(
        """\A\{"schemaVersion":1,"active":(null|"[a-z0-9][a-z0-9._-]{0,126}"),"rollback":(null|"[a-z0-9][a-z0-9._-]{0,126}")\}\z""",
    )

    fun encode(pointer: ActiveModelPointer): String =
        "{\"schemaVersion\":1,\"active\":${quoted(pointer.activeDirectory)},\"rollback\":${quoted(pointer.rollbackDirectory)}}"

    fun decode(value: String): ActiveModelPointer {
        val match = requireNotNull(json.matchEntire(value)) { "invalid active model pointer" }
        return ActiveModelPointer(unquote(match.groupValues[1]), unquote(match.groupValues[2]))
    }

    private fun quoted(value: String?) = value?.let { "\"$it\"" } ?: "null"
    private fun unquote(value: String) = value.takeUnless { it == "null" }?.removeSurrounding("\"")
}

class AtomicModelPointerStore(private val root: File) : ModelPointerStore {
    private val pointerFile = File(root, "active-model.json")
    private val lockFile = File(root, "active-model.lock")
    private val atomicFile get() = AtomicFile(pointerFile)

    override fun read(): ActiveModelPointer = locked {
        if (!pointerFile.exists()) ActiveModelPointer(null, null)
        else ActiveModelPointerCodec.decode(atomicFile.readFully().toString(Charsets.UTF_8))
    }

    override fun write(pointer: ActiveModelPointer) = locked {
        val output = atomicFile.startWrite()
        try {
            output.write(ActiveModelPointerCodec.encode(pointer).toByteArray(Charsets.UTF_8))
            atomicFile.finishWrite(output)
        } catch (error: Throwable) {
            atomicFile.failWrite(output)
            throw error
        }
    }

    private fun <T> locked(block: () -> T): T {
        check(root.mkdirs() || root.isDirectory) { "cannot create model root" }
        RandomAccessFile(lockFile, "rw").use { file ->
            file.channel.lock().use { return block() }
        }
    }
}
