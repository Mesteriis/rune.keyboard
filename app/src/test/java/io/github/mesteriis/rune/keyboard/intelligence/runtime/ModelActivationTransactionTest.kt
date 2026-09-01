package io.github.mesteriis.rune.keyboard.intelligence.runtime

import java.io.File
import java.nio.file.Files
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ModelActivationTransactionTest {
    @Test
    fun atomicallyMovesCandidateThenCommitsPointerAndDeletesOldRollback() {
        val root = Files.createTempDirectory("activation").toFile()
        File(root, "candidates/v2/model.gguf").apply { parentFile?.mkdirs(); writeText("new") }
        File(root, "versions/v1/model.gguf").apply { parentFile?.mkdirs(); writeText("active") }
        File(root, "versions/v0/model.gguf").apply { parentFile?.mkdirs(); writeText("old rollback") }
        val store = InMemoryPointerStore(ActiveModelPointer("v1", "v0"))

        ModelActivationTransaction(root, store).activate("v2")

        assertEquals(ActiveModelPointer("v2", "v1"), store.pointer)
        assertTrue(File(root, "versions/v2/model.gguf").isFile)
        assertFalse(File(root, "versions/v0").exists())
    }

    @Test
    fun rollbackCommitsKnownGoodPointerBeforeDeletingFailedActive() {
        val root = Files.createTempDirectory("rollback").toFile()
        File(root, "versions/broken/model.gguf").apply { parentFile?.mkdirs(); writeText("bad") }
        File(root, "versions/good/model.gguf").apply { parentFile?.mkdirs(); writeText("good") }
        val store = InMemoryPointerStore(ActiveModelPointer("broken", "good"))

        ModelActivationTransaction(root, store).rollback()

        assertEquals(ActiveModelPointer("good", null), store.pointer)
        assertFalse(File(root, "versions/broken").exists())
        assertTrue(File(root, "versions/good/model.gguf").isFile)
    }

    private class InMemoryPointerStore(var pointer: ActiveModelPointer) : ModelPointerStore {
        override fun read() = pointer
        override fun write(pointer: ActiveModelPointer) { this.pointer = pointer }
    }
}
