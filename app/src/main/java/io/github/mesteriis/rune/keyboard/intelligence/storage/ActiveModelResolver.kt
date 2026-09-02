package io.github.mesteriis.rune.keyboard.intelligence.storage

import io.github.mesteriis.rune.keyboard.intelligence.model.ModelDescriptor
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelManifestParser
import java.io.File
import java.io.FileInputStream

/** Metadata reads only; caller holds ModelOperationGate.withReadLock for each operation. */
class DiskActiveModelPointerReader(root: File) : ActiveModelPointerReader {
    private val root = root.canonicalFile
    override fun read(): ActiveModelPointer {
        // AtomicFile compatibility: .bak is the committed state until install-owned recovery.
        val backup = File(root, "active-model.json.bak")
        val selected = if (backup.exists()) backup else File(root, "active-model.json")
        if (!selected.exists()) return ActiveModelPointer(null, null)
        require(selected.canonicalFile == selected.absoluteFile)
        return ActiveModelPointerCodec.decode(readBounded(selected, 1024))
    }
}

data class ResolvedActiveModel(val directory: String, val file: File, val descriptor: ModelDescriptor,
    val fileSize: Long, val modifiedMillis: Long)

class ActiveModelResolver(root: File,
    private val pointer: ActiveModelPointerReader = DiskActiveModelPointerReader(root)) {
    private val root = root.canonicalFile
    fun resolve(): ResolvedActiveModel? {
        val directory = pointer.read().activeDirectory ?: return null
        require(Regex("[a-z0-9][a-z0-9._-]{0,126}").matches(directory))
        val versions = File(root, "versions")
        val version = File(versions, directory)
        require(versions.canonicalFile == versions.absoluteFile && version.canonicalFile == version.absoluteFile)
        val manifest = File(version, "model-manifest.json")
        require(manifest.canonicalFile == manifest.absoluteFile)
        val descriptor = ModelManifestParser.parse(readBounded(manifest, 16384))
        require(directory == "${descriptor.id}-${descriptor.version}")
        val file = File(version, descriptor.fileName)
        require(file.canonicalFile == file.absoluteFile && file.isFile && file.length() == descriptor.sizeBytes)
        return ResolvedActiveModel(directory, file, descriptor, file.length(), file.lastModified())
    }
}

private fun readBounded(file: File, maximum: Int): String {
    require(file.isFile && file.length() in 1..maximum.toLong())
    val buffer = ByteArray(maximum + 1)
    val size = FileInputStream(file).use { input ->
        var total = 0
        while (total < buffer.size) {
            val count = input.read(buffer, total, buffer.size - total)
            if (count < 0) break
            total += count
        }
        total
    }
    require(size in 1..maximum)
    return buffer.copyOf(size).toString(Charsets.UTF_8)
}
