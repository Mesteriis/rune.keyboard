package io.github.mesteriis.rune.keyboard.intelligence.delivery

import io.github.mesteriis.rune.keyboard.intelligence.model.ModelDescriptor
import io.github.mesteriis.rune.keyboard.intelligence.model.VerifiedCandidate
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.InputStream
import java.nio.file.AtomicMoveNotSupportedException
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.MessageDigest

class CandidateInstallException(
    val failureCode: ModelFailureCode,
    message: String,
    cause: Throwable? = null,
) : Exception(message, cause)

class CandidateInstaller(private val root: File) {
    fun install(
        input: InputStream,
        descriptor: ModelDescriptor,
        beforePublish: () -> Unit = {},
    ): VerifiedCandidate {
        val staging = File(root, ".installing")
        val candidateName = "${descriptor.id}-${descriptor.version}"
        val candidates = File(root, "candidates")
        val destination = File(candidates, candidateName)
        if (destination.exists()) {
            throw CandidateInstallException(ModelFailureCode.IO_ERROR, "candidate already exists")
        }
        removePrivatePartial(staging)
        if (!staging.mkdirs()) {
            throw CandidateInstallException(ModelFailureCode.IO_ERROR, "cannot create private staging directory")
        }
        val stagedModel = File(staging, descriptor.fileName)
        try {
            val result = FileOutputStream(stagedModel).use { output ->
                VerifiedStreamCopier.copy(input, output, descriptor.sizeBytes).also { output.fd.sync() }
            }
            if (!MessageDigest.isEqual(result.sha256.toByteArray(), descriptor.sha256.toByteArray())) {
                throw CandidateInstallException(ModelFailureCode.HASH_MISMATCH, "model digest does not match descriptor")
            }
            FileInputStream(stagedModel).use(GgufMetadataReader::read)
            beforePublish()
            if (!candidates.mkdirs() && !candidates.isDirectory) {
                throw CandidateInstallException(ModelFailureCode.IO_ERROR, "cannot create candidate directory")
            }
            try {
                Files.move(staging.toPath(), destination.toPath(), StandardCopyOption.ATOMIC_MOVE)
            } catch (error: AtomicMoveNotSupportedException) {
                throw CandidateInstallException(ModelFailureCode.IO_ERROR, "atomic candidate publish is unsupported", error)
            }
            return VerifiedCandidate(descriptor, candidateName)
        } catch (error: CandidateInstallException) {
            removePrivatePartial(staging)
            throw error
        } catch (error: StreamSizeException) {
            removePrivatePartial(staging)
            throw CandidateInstallException(ModelFailureCode.SIZE_MISMATCH, "model size does not match descriptor", error)
        } catch (error: GgufValidationException) {
            removePrivatePartial(staging)
            throw CandidateInstallException(ModelFailureCode.INVALID_GGUF, "model GGUF metadata is incompatible", error)
        } catch (error: Exception) {
            removePrivatePartial(staging)
            throw CandidateInstallException(ModelFailureCode.IO_ERROR, "candidate install failed", error)
        }
    }

    private fun removePrivatePartial(staging: File) {
        if (!staging.exists()) return
        check(staging.parentFile == root) { "refusing to remove an unscoped path" }
        staging.deleteRecursively()
    }
}
