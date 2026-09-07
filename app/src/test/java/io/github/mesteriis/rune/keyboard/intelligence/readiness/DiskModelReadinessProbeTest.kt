package io.github.mesteriis.rune.keyboard.intelligence.readiness

import io.github.mesteriis.rune.keyboard.intelligence.client.ModelReadinessHint
import io.github.mesteriis.rune.keyboard.intelligence.storage.ModelOperationGate
import io.github.mesteriis.rune.keyboard.intelligence.storage.ActiveModelPointer
import io.github.mesteriis.rune.keyboard.intelligence.storage.ActiveModelPointerCodec
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

class DiskModelReadinessProbeTest {
    @get:Rule val temp = TemporaryFolder()

    @Test fun missingStoreAndCancelledDemandDoNotCreateOrReadStorage() {
        val missing = File(temp.root, "absent")
        assertEquals(ModelReadinessHint.MISSING, DiskModelReadinessProbe { missing }.read { false })
        assertFalse(missing.exists())
        assertEquals(ModelReadinessHint.UNKNOWN, DiskModelReadinessProbe { error("must not access root") }.read { true })
    }

    @Test fun lockContentionReturnsUnknownWithoutWaitingForInstall() {
        val root = temp.newFolder(); val gate = ModelOperationGate(root)
        val entered = CountDownLatch(1); val release = CountDownLatch(1)
        val owner = Thread {
            gate.withLock { entered.countDown(); assertTrue(release.await(3, TimeUnit.SECONDS)) }
        }.apply { start() }
        try {
            assertTrue(entered.await(3, TimeUnit.SECONDS))
            assertEquals(ModelReadinessHint.UNKNOWN, DiskModelReadinessProbe { root }.read { false })
            assertEquals(1L, release.count)
        } finally { release.countDown(); owner.join(3000) }
        assertEquals(ModelReadinessHint.MISSING, DiskModelReadinessProbe { root }.read { false })
    }

    @Test fun sameProcessOverlappingFileLockReturnsUnknownAndReleasesLocalLock() {
        val root = temp.newFolder(); val gate = ModelOperationGate(root)
        gate.withLock {
            assertNull(gate.tryWithReadLock { error("exclusive OS lock must win") })
        }
        assertEquals(7, gate.tryWithReadLock { 7 })
        assertEquals(ModelReadinessHint.MISSING, DiskModelReadinessProbe { root }.read { false })
    }

    @Test fun readyIsOnlyMetadataAndBadOrDeletedActiveVersionFailsClosed() {
        val root = temp.newFolder(); val gate = ModelOperationGate(root)
        val version = File(root, "versions/fixture-1.0.0")
        gate.withLock {
            check(version.mkdirs())
            File(root, "active-model.json").writeText(ActiveModelPointerCodec.encode(ActiveModelPointer("fixture-1.0.0", null)))
            File(version, "fixture.gguf").writeBytes(byteArrayOf(0)) // intentionally not a valid GGUF
            File(version, "model-manifest.json").writeText("""{"schemaVersion":1,"modelId":"fixture","version":"1.0.0","displayName":"Fixture","fileName":"fixture.gguf","url":"https://github.com/Mesteriis/rune.keyboard/releases/download/fixture/fixture.gguf","sha256":"${"0".repeat(64)}","sizeBytes":1,"runtimeApi":1,"minimumRuneVersionCode":2,"ggufVersion":3,"architecture":"qwen3","fileType":15}""")
        }
        val probe = DiskModelReadinessProbe { root }
        assertEquals(ModelReadinessHint.BROKEN, probe.read { false })
        val manifest = File(version, "model-manifest.json")
        manifest.writeText(manifest.readText().replace("0".repeat(64),
            "7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4"))
        assertEquals(ModelReadinessHint.READY, probe.read { false })
        gate.withLock { File(version, "fixture.gguf").delete() }
        assertEquals(ModelReadinessHint.BROKEN, probe.read { false })
        gate.withLock { File(root, "active-model.json").writeText("malformed") }
        assertEquals(ModelReadinessHint.BROKEN, probe.read { false })
    }
}
