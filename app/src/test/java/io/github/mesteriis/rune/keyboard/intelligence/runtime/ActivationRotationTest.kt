package io.github.mesteriis.rune.keyboard.intelligence.runtime

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ActivationRotationTest {
    @Test
    fun newCandidateKeepsExactlyPreviousActiveAsRollback() {
        val plan = ActivationRotation.activate(
            current = ActiveModelPointer(activeDirectory = "v1", rollbackDirectory = "v0"),
            candidateDirectory = "v2",
        )

        assertEquals(ActiveModelPointer("v2", "v1"), plan.pointerAfterCommit)
        assertEquals("v0", plan.deleteAfterCommit)
    }

    @Test
    fun firstActivationHasNoRollback() {
        val plan = ActivationRotation.activate(ActiveModelPointer(null, null), "v1")

        assertEquals(ActiveModelPointer("v1", null), plan.pointerAfterCommit)
        assertNull(plan.deleteAfterCommit)
    }

    @Test
    fun rollbackPromotesOnlyKnownGoodSlotAndDeletesFailedActiveAfterCommit() {
        val plan = ActivationRotation.rollback(ActiveModelPointer("broken", "known-good"))

        assertEquals(ActiveModelPointer("known-good", null), plan.pointerAfterCommit)
        assertEquals("broken", plan.deleteAfterCommit)
    }
}
