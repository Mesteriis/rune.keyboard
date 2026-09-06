package io.github.mesteriis.rune.keyboard.intelligence.storage

data class ActiveModelPointer(
    val activeDirectory: String?,
    val rollbackDirectory: String?,
)

interface ActiveModelPointerReader {
    fun read(): ActiveModelPointer
}
