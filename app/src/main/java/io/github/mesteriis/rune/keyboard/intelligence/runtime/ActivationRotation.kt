package io.github.mesteriis.rune.keyboard.intelligence.runtime

data class ActiveModelPointer(
    val activeDirectory: String?,
    val rollbackDirectory: String?,
)

data class ActivationPlan(
    val pointerAfterCommit: ActiveModelPointer,
    val deleteAfterCommit: String?,
)

object ActivationRotation {
    fun activate(current: ActiveModelPointer, candidateDirectory: String): ActivationPlan {
        require(candidateDirectory.isNotBlank()) { "candidateDirectory must not be blank" }
        return ActivationPlan(
            pointerAfterCommit = ActiveModelPointer(candidateDirectory, current.activeDirectory),
            deleteAfterCommit = current.rollbackDirectory,
        )
    }

    fun rollback(current: ActiveModelPointer): ActivationPlan {
        val rollback = requireNotNull(current.rollbackDirectory) { "rollback is unavailable" }
        return ActivationPlan(
            pointerAfterCommit = ActiveModelPointer(rollback, null),
            deleteAfterCommit = current.activeDirectory,
        )
    }
}
