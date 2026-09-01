package io.github.mesteriis.rune.keyboard.intelligence.delivery

import java.io.File
import java.io.IOException
import java.nio.file.Files
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class ModelFilesCleanerTest {
    @Test
    fun tombstonePrecedesFilesAndIdleFollowsCompleteCleanup() {
        val root = Files.createTempDirectory("model-cleaner").toFile()
        val directories = listOf("candidates", ".installing", "versions")
            .onEach { name -> File(root, "$name/model.bin").apply { parentFile?.mkdirs(); writeText("data") } }
        val actions = mutableListOf<String>()
        var pointerCleared = false

        ModelFilesCleaner(
            root = root,
            markDeleting = { actions += "tombstone" },
            markComplete = { actions += "idle" },
            clearPointer = {
                pointerCleared = true
                actions += "pointer"
            },
            deleteRecursively = { target ->
                if (target.name == "versions") assertTrue(pointerCleared) else assertFalse(pointerCleared)
                actions += target.name
                target.deleteRecursively()
            },
        ).deleteAll()

        assertEquals(listOf("tombstone", "candidates", ".installing", "pointer", "versions", "idle"), actions)
        directories.forEach { name -> assertFalse(File(root, name).exists()) }
    }

    @Test
    fun failedTemporaryCleanupDoesNotProceedToInstalledVersions() {
        val root = Files.createTempDirectory("model-cleaner-failure").toFile()
        File(root, "candidates/model.bin").apply { parentFile?.mkdirs(); writeText("candidate") }
        File(root, "versions/active/model.bin").apply { parentFile?.mkdirs(); writeText("active") }
        val actions = mutableListOf<String>()
        var pointerCleared = false

        assertThrows(IOException::class.java) {
            ModelFilesCleaner(
                root = root,
                markDeleting = { actions += "tombstone" },
                markComplete = { actions += "idle" },
                clearPointer = {
                    pointerCleared = true
                    actions += "pointer"
                },
                deleteRecursively = { target ->
                    actions += target.name
                    target.name != "candidates"
                },
            ).deleteAll()
        }

        assertEquals(listOf("tombstone", "candidates"), actions)
        assertFalse(pointerCleared)
        assertTrue(File(root, "candidates/model.bin").isFile)
        assertTrue(File(root, "versions/active/model.bin").isFile)
    }

    @Test
    fun failedVersionCleanupKeepsTombstoneAfterPointerIsCleared() {
        val root = Files.createTempDirectory("model-cleaner-version-failure").toFile()
        File(root, "versions/active/model.bin").apply { parentFile?.mkdirs(); writeText("active") }
        val actions = mutableListOf<String>()

        assertThrows(IOException::class.java) {
            ModelFilesCleaner(
                root = root,
                markDeleting = { actions += "tombstone" },
                markComplete = { actions += "idle" },
                clearPointer = { actions += "pointer" },
                deleteRecursively = { target ->
                    actions += target.name
                    target.name != "versions"
                },
            ).deleteAll()
        }

        assertEquals(listOf("tombstone", "pointer", "versions"), actions)
        assertTrue(File(root, "versions/active/model.bin").isFile)
    }
}
