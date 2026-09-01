package io.github.mesteriis.rune.keyboard.intelligence.runtime

import java.io.File
import java.nio.file.Files
import java.nio.file.StandardCopyOption

interface ModelPointerStore {
    fun read(): ActiveModelPointer
    fun write(pointer: ActiveModelPointer)
}

class ModelActivationTransaction(
    private val root: File,
    private val pointerStore: ModelPointerStore,
) {
    private val safeDirectory = Regex("[a-z0-9][a-z0-9._-]{0,126}")

    fun activate(candidateDirectory: String) {
        requireSafe(candidateDirectory)
        val current = pointerStore.read()
        val plan = ActivationRotation.activate(current, candidateDirectory)
        val candidate = File(root, "candidates/$candidateDirectory")
        val version = File(root, "versions/$candidateDirectory")
        require(candidate.isDirectory) { "candidate directory is missing" }
        check(!version.exists()) { "version directory already exists" }
        check(version.parentFile?.mkdirs() == true || version.parentFile?.isDirectory == true) {
            "cannot create versions directory"
        }
        Files.move(candidate.toPath(), version.toPath(), StandardCopyOption.ATOMIC_MOVE)
        try {
            pointerStore.write(plan.pointerAfterCommit)
        } catch (error: Throwable) {
            runCatching { Files.move(version.toPath(), candidate.toPath(), StandardCopyOption.ATOMIC_MOVE) }
            throw error
        }
        plan.deleteAfterCommit?.let(::deleteVersion)
    }

    fun rollback() {
        val plan = ActivationRotation.rollback(pointerStore.read())
        val promoted = requireNotNull(plan.pointerAfterCommit.activeDirectory)
        requireSafe(promoted)
        require(File(root, "versions/$promoted").isDirectory) { "rollback directory is missing" }
        pointerStore.write(plan.pointerAfterCommit)
        plan.deleteAfterCommit?.let(::deleteVersion)
    }

    private fun deleteVersion(directory: String) {
        requireSafe(directory)
        val versions = File(root, "versions")
        val target = File(versions, directory)
        check(target.parentFile == versions) { "refusing to remove an unscoped path" }
        target.deleteRecursively()
    }

    private fun requireSafe(value: String) {
        require(safeDirectory.matches(value)) { "unsafe model directory" }
    }
}
