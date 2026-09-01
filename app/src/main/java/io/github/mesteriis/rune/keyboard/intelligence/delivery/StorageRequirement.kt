package io.github.mesteriis.rune.keyboard.intelligence.delivery

object StorageRequirement {
    private const val MIB = 1024L * 1024L

    fun sameVolume(modelSize: Long): Long {
        require(modelSize > 0) { "modelSize must be positive" }
        return Math.addExact(Math.multiplyExact(modelSize, 2L), 64L * MIB)
    }

    fun eachDifferentVolume(modelSize: Long): Long {
        require(modelSize > 0) { "modelSize must be positive" }
        return Math.addExact(modelSize, 32L * MIB)
    }
}
