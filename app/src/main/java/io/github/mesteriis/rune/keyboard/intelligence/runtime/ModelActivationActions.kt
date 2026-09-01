package io.github.mesteriis.rune.keyboard.intelligence.runtime

internal interface ModelActivationActions {
    fun activate(candidateDirectory: String)
    fun resumeRollback(failedDirectory: String)
    fun clearPointerAndVersions()
}
