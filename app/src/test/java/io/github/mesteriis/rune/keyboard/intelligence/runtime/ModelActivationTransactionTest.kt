package io.github.mesteriis.rune.keyboard.intelligence.runtime

import java.io.File
import java.nio.file.Files
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
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

    @Test
    fun recoversAfterCandidateMoveBeforePointerCommit() {
        val root = Files.createTempDirectory("activation-moved").toFile()
        File(root, "versions/v2/model.gguf").apply { parentFile?.mkdirs(); writeText("new") }
        File(root, "versions/v1/model.gguf").apply { parentFile?.mkdirs(); writeText("active") }
        File(root, "versions/v0/model.gguf").apply { parentFile?.mkdirs(); writeText("old rollback") }
        val store = InMemoryPointerStore(ActiveModelPointer("v1", "v0"))

        ModelActivationTransaction(root, store).activate("v2")

        assertEquals(ActiveModelPointer("v2", "v1"), store.pointer)
        assertTrue(File(root, "versions/v2/model.gguf").isFile)
        assertFalse(File(root, "versions/v0").exists())
    }

    @Test
    fun reentryAfterPointerCommitKeepsRollbackAndCleansOldVersion() {
        val root = Files.createTempDirectory("activation-committed").toFile()
        File(root, "versions/v2/model.gguf").apply { parentFile?.mkdirs(); writeText("new") }
        File(root, "versions/v1/model.gguf").apply { parentFile?.mkdirs(); writeText("rollback") }
        File(root, "versions/v0/model.gguf").apply { parentFile?.mkdirs(); writeText("stale") }
        val store = InMemoryPointerStore(ActiveModelPointer("v2", "v1"))

        ModelActivationTransaction(root, store).activate("v2")

        assertEquals(ActiveModelPointer("v2", "v1"), store.pointer)
        assertTrue(File(root, "versions/v1/model.gguf").isFile)
        assertFalse(File(root, "versions/v0").exists())
    }

    @Test
    fun ambiguousCandidateAndVersionFailsWithoutChangingPointer() {
        val root = Files.createTempDirectory("activation-ambiguous").toFile()
        File(root, "candidates/v2/model.gguf").apply { parentFile?.mkdirs(); writeText("candidate") }
        File(root, "versions/v2/model.gguf").apply { parentFile?.mkdirs(); writeText("version") }
        val store = InMemoryPointerStore(ActiveModelPointer("v1", null))

        assertThrows(IllegalStateException::class.java) {
            ModelActivationTransaction(root, store).activate("v2")
        }

        assertEquals(ActiveModelPointer("v1", null), store.pointer)
        assertTrue(File(root, "candidates/v2/model.gguf").isFile)
        assertTrue(File(root, "versions/v2/model.gguf").isFile)
    }

    @Test
    fun sameActiveDuplicateCandidateIsDiscardedWithoutRotatingRollback() {
        val root = Files.createTempDirectory("activation-duplicate").toFile()
        File(root, "candidates/v2/model.gguf").apply { parentFile?.mkdirs(); writeText("duplicate") }
        File(root, "versions/v2/model.gguf").apply { parentFile?.mkdirs(); writeText("active") }
        File(root, "versions/v1/model.gguf").apply { parentFile?.mkdirs(); writeText("rollback") }
        val store = InMemoryPointerStore(ActiveModelPointer("v2", "v1"))

        ModelActivationTransaction(root, store).activate("v2")

        assertEquals(ActiveModelPointer("v2", "v1"), store.pointer)
        assertFalse(File(root, "candidates/v2").exists())
        assertTrue(File(root, "versions/v2/model.gguf").isFile)
        assertTrue(File(root, "versions/v1/model.gguf").isFile)
    }

    @Test
    fun clearCommitsEmptyPointerBeforeRemovingVersions() {
        val root = Files.createTempDirectory("activation-clear").toFile()
        val active = File(root, "versions/active/model.gguf")
            .apply { parentFile?.mkdirs(); writeText("active") }
        var sawVersionsAtPointerCommit = false
        val store = InMemoryPointerStore(ActiveModelPointer("active", null)) { pointer ->
            if (pointer == ActiveModelPointer(null, null)) {
                sawVersionsAtPointerCommit = active.isFile
            }
        }

        ModelActivationTransaction(root, store).clearPointerAndVersions()

        assertTrue(sawVersionsAtPointerCommit)
        assertEquals(ActiveModelPointer(null, null), store.pointer)
        assertFalse(File(root, "versions").exists())
    }

    @Test
    fun failedPointerClearKeepsVersionsRecoverable() {
        val root = Files.createTempDirectory("activation-clear-failed").toFile()
        val active = File(root, "versions/active/model.gguf")
            .apply { parentFile?.mkdirs(); writeText("active") }
        val store = object : ModelPointerStore {
            override fun read() = ActiveModelPointer("active", null)
            override fun write(pointer: ActiveModelPointer) {
                throw java.io.IOException("pointer commit failed")
            }
        }

        assertThrows(java.io.IOException::class.java) {
            ModelActivationTransaction(root, store).clearPointerAndVersions()
        }

        assertTrue(active.isFile)
    }

    private class InMemoryPointerStore(
        var pointer: ActiveModelPointer,
        private val beforeWrite: (ActiveModelPointer) -> Unit = {},
    ) : ModelPointerStore {
        override fun read() = pointer
        override fun write(pointer: ActiveModelPointer) {
            beforeWrite(pointer)
            this.pointer = pointer
        }
    }
}
