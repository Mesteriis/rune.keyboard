package io.github.mesteriis.rune.keyboard.intelligence.delivery

import android.os.StatFs
import android.system.Os
import io.github.mesteriis.rune.keyboard.intelligence.model.ModelDescriptor
import java.io.File

class ModelStorageSpace(
    private val externalStaging: File,
    private val privateRoot: File,
) {
    fun requireCapacity(descriptor: ModelDescriptor) {
        check(externalStaging.mkdirs() || externalStaging.isDirectory) { "Cannot create external model staging" }
        check(privateRoot.mkdirs() || privateRoot.isDirectory) { "Cannot create private model root" }
        val sameVolume = Os.stat(externalStaging.absolutePath).st_dev == Os.stat(privateRoot.absolutePath).st_dev
        if (sameVolume) {
            requireAvailable(privateRoot, StorageRequirement.sameVolume(descriptor.sizeBytes))
        } else {
            val required = StorageRequirement.eachDifferentVolume(descriptor.sizeBytes)
            requireAvailable(externalStaging, required)
            requireAvailable(privateRoot, required)
        }
    }

    fun requirePrivateCopyCapacity(descriptor: ModelDescriptor) {
        check(privateRoot.mkdirs() || privateRoot.isDirectory) { "Cannot create private model root" }
        requireAvailable(privateRoot, StorageRequirement.eachDifferentVolume(descriptor.sizeBytes))
    }

    private fun requireAvailable(directory: File, requiredBytes: Long) {
        if (StatFs(directory.absolutePath).availableBytes < requiredBytes) {
            throw CandidateInstallException(ModelFailureCode.INSUFFICIENT_SPACE, "insufficient model storage")
        }
    }
}
