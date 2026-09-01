package io.github.mesteriis.rune.keyboard.intelligence.runtime

import java.io.File
import java.io.IOException
import java.nio.file.Files
import java.nio.file.StandardCopyOption

interface ModelPointerStore {
    fun read(): ActiveModelPointer
    fun write(pointer: ActiveModelPointer)
}

class ModelActivationTransaction(
    private val root: File,
    private val pointerStore: ModelPointerStore,
) : ModelActivationActions {
    private val safeDirectory = Regex("[a-z0-9][a-z0-9._-]{0,126}")

    override fun activate(candidateDirectory: String) {
        requireSafe(candidateDirectory)
        val current = pointerStore.read()
        val candidate = File(root, "candidates/$candidateDirectory")
        val version = File(root, "versions/$candidateDirectory")
        if (current.activeDirectory == candidateDirectory) {
            check(version.isDirectory) { "committed version directory is missing" }
            if (candidate.exists()) deleteCandidate(candidateDirectory)
            deleteUnreferencedVersions(current)
            return
        }
        check(!(candidate.exists() && version.exists())) { "candidate and version both exist" }

        val moveCandidate = candidate.isDirectory && !version.exists()
        check(moveCandidate || (!candidate.exists() && version.isDirectory)) {
            "candidate activation state is missing"
        }
        val plan = ActivationRotation.activate(current, candidateDirectory)
        check(version.parentFile?.mkdirs() == true || version.parentFile?.isDirectory == true) {
            "cannot create versions directory"
        }
        if (moveCandidate) {
            Files.move(candidate.toPath(), version.toPath(), StandardCopyOption.ATOMIC_MOVE)
        }
        try {
            pointerStore.write(plan.pointerAfterCommit)
        } catch (error: Throwable) {
            if (moveCandidate) {
                runCatching { Files.move(version.toPath(), candidate.toPath(), StandardCopyOption.ATOMIC_MOVE) }
            }
            throw error
        }
        plan.deleteAfterCommit?.let(::deleteVersion)
        deleteUnreferencedVersions(plan.pointerAfterCommit)
    }

    fun rollback() {
        val plan = ActivationRotation.rollback(pointerStore.read())
        val promoted = requireNotNull(plan.pointerAfterCommit.activeDirectory)
        requireSafe(promoted)
        require(File(root, "versions/$promoted").isDirectory) { "rollback directory is missing" }
        pointerStore.write(plan.pointerAfterCommit)
        plan.deleteAfterCommit?.let(::deleteVersion)
    }

    override fun resumeRollback(failedDirectory: String) {
        requireSafe(failedDirectory)
        val current = pointerStore.read()
        if (current.activeDirectory == failedDirectory) {
            rollback()
            return
        }
        check(current.rollbackDirectory == null) { "rollback pointer is ambiguous" }
        val active = requireNotNull(current.activeDirectory) { "rolled back active model is missing" }
        requireSafe(active)
        check(File(root, "versions/$active").isDirectory) { "rolled back active directory is missing" }
        deleteVersion(failedDirectory)
        deleteUnreferencedVersions(current)
    }

    override fun clearPointerAndVersions() {
        // The durable pointer is cleared first so a crash or cleanup failure cannot leave it
        // referencing a version that has already been removed. Leftovers are safe to retry.
        pointerStore.write(ActiveModelPointer(null, null))
        val versions = File(root, "versions")
        check(versions.parentFile == root) { "refusing to remove an unscoped path" }
        if (versions.exists() && (!versions.deleteRecursively() || versions.exists())) {
            throw IOException("cannot delete model versions")
        }
    }

    private fun deleteVersion(directory: String) {
        requireSafe(directory)
        val versions = File(root, "versions")
        val target = File(versions, directory)
        check(target.parentFile == versions) { "refusing to remove an unscoped path" }
        if (target.exists() && (!target.deleteRecursively() || target.exists())) {
            throw IOException("cannot delete model version: $directory")
        }
    }

    private fun deleteCandidate(directory: String) {
        requireSafe(directory)
        val candidates = File(root, "candidates")
        val target = File(candidates, directory)
        check(target.parentFile == candidates) { "refusing to remove an unscoped path" }
        if (target.exists() && (!target.deleteRecursively() || target.exists())) {
            throw IOException("cannot delete duplicate model candidate: $directory")
        }
    }

    private fun deleteUnreferencedVersions(pointer: ActiveModelPointer) {
        val retained = setOfNotNull(pointer.activeDirectory, pointer.rollbackDirectory)
        val versions = File(root, "versions")
        if (!versions.exists()) return
        val installed = versions.listFiles() ?: throw IOException("cannot list model versions")
        installed
            .filter { it.isDirectory && safeDirectory.matches(it.name) && it.name !in retained }
            .forEach { directory -> deleteVersion(directory.name) }
    }

    private fun requireSafe(value: String) {
        require(safeDirectory.matches(value)) { "unsafe model directory" }
    }
}
