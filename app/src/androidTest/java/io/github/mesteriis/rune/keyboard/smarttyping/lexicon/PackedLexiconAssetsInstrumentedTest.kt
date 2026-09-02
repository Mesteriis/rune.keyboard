package io.github.mesteriis.rune.keyboard.smarttyping.lexicon

import android.content.res.AssetFileDescriptor
import android.content.res.AssetManager
import android.os.Bundle
import android.os.Debug
import android.os.Looper
import android.os.ParcelFileDescriptor
import android.os.SystemClock
import android.system.Os
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import java.nio.ReadOnlyBufferException
import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicReference
import java.util.zip.ZipEntry
import java.util.zip.ZipFile
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

/** Actual APK contract only: one validated load per language, no forced GC, no latency threshold. */
@RunWith(AndroidJUnit4::class)
class PackedLexiconAssetsInstrumentedTest {
    @Test
    fun packagedMappingsNoticesAndExactReferencesAreAvailableOffMainThread() {
        val failure = AtomicReference<String>()
        val stage = AtomicInteger(0)
        val loadFailure = AtomicReference<PackedLoadFailure>()
        val worker = Thread({
            try { exerciseAssets(stage, loadFailure) } catch (error: Throwable) {
                // Never pass an exception payload/cause (or a query) into instrumentation diagnostics.
                failure.set("stage=${stage.get()} load_failure=${loadFailure.get()?.name ?: "NONE"} class=${error.javaClass.simpleName}")
            }
        }, "packed-lexicon-contract").apply { isDaemon = true }
        worker.start()
        worker.join(120_000)
        if (worker.isAlive) {
            worker.interrupt()
            worker.join(5_000)
            fail("PACKED_CONTRACT_TIMEOUT_STAGE_${stage.get()}")
        }
        assertNull("PACKED_CONTRACT_FAILED_CLASS", failure.get())
    }

    private fun exerciseAssets(stage: AtomicInteger, loadFailure: AtomicReference<PackedLoadFailure>) {
        stage.set(1)
        assertNotSame(Looper.getMainLooper(), Looper.myLooper())
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val assets = instrumentation.targetContext.assets
        val trusted = listOf(FrozenPackedLexicons.ENGLISH, FrozenPackedLexicons.SPANISH, FrozenPackedLexicons.RUSSIAN)
        val base = trusted[0]
        stage.set(2)
        assertEquals(PackedLexiconLoad.Failed(PackedLoadFailure.MANIFEST),
            AndroidPackedLexiconLoader.load(assets, base.copy(expectedSha256 = "0".repeat(64))))
        stage.set(3)
        assertEquals(PackedLexiconLoad.Failed(PackedLoadFailure.MANIFEST),
            AndroidPackedLexiconLoader.load(assets, base.copy(language = trusted[1].language)))
        stage.set(4)
        assertEquals(PackedLexiconLoad.Failed(PackedLoadFailure.IO),
            AndroidPackedLexiconLoader.load(assets, withTriePath(base, "smarttyping/lexicon/missing.trie")))
        val fixture = "packed-reader-fixtures/compressed.txt"
        // Explicitly prove the negative fixture is compressed in the test APK.
        stage.set(5)
        ZipFile(instrumentation.context.applicationInfo.sourceDir).use { apk ->
            assertEquals(ZipEntry.DEFLATED, apk.getEntry("assets/" + fixture).method)
        }
        stage.set(6)
        assertEquals(PackedLexiconLoad.Failed(PackedLoadFailure.IO),
            AndroidPackedLexiconLoader.load(instrumentation.context.assets, withTriePath(base, fixture)))

        stage.set(8)
        exerciseEmbeddedRegion(instrumentation.targetContext.cacheDir)
        stage.set(7)
        val notices = base.manifest.notices
        assertEquals(14, notices.size)
        for ((index, notice) in notices.withIndex()) {
            stage.set(20 + index)
            verifyFile(assets, notice.path, notice.bytes, notice.sha256)
        }
        stage.set(40)
        verifyFile(assets, "smarttyping/lexicon/provenance/source-lock.json", null,
            "28750e183ef99ea33da58b20036e2f0dcb3f7e1f76e8528c21074ac7d6615b70")
        stage.set(41)
        verifyFile(assets, "smarttyping/lexicon/provenance/frozen-output-manifest.json", null,
            "ec26c80edd28f2b42008a844c8b0ce83c11759386ccc9de591cb038a7a4f3c48")
        stage.set(42)
        verifyFile(assets, "smarttyping/lexicon/provenance/packed-asset-manifest.json", null,
            "7ce207ab7d05b8800a1d8921f6e55fe81f429f8158bf8ebcebf581cbee7255f0")

        for ((index, identity) in trusted.withIndex()) {
            val languageStage = 100 * (index + 1)
            stage.set(languageStage)
            var openNanos = 0L
            var mappedBytes = 0L
            for (component in listOf(identity.manifest.trie, identity.manifest.lengths, identity.manifest.ranks)) {
                stage.incrementAndGet()
                val start = SystemClock.elapsedRealtimeNanos()
                assets.openFd(component.path).use { descriptor ->
                    assertTrue(descriptor.startOffset >= 0)
                    assertEquals(component.bytes, descriptor.declaredLength)
                }
                openNanos += SystemClock.elapsedRealtimeNanos() - start
                mappedBytes += component.bytes
            }
            stage.set(languageStage + 10)
            val before = memory()
            val cpuStart = Debug.threadCpuTimeNanos()
            val start = SystemClock.elapsedRealtimeNanos()
            val loaded = AndroidPackedLexiconLoader.load(assets, identity)
            loadFailure.set((loaded as? PackedLexiconLoad.Failed)?.reason)
            val loadNanos = SystemClock.elapsedRealtimeNanos() - start
            val cpuNanos = Debug.threadCpuTimeNanos() - cpuStart
            assertTrue("PACKED_LOAD_LANGUAGE_$index", loaded is PackedLexiconLoad.Ready)
            val handle = (loaded as PackedLexiconLoad.Ready).lexicon
            assertEquals(identity.manifest.wordCount, handle.wordCount)
            assertEquals(identity.manifest.nodeCount, handle.nodeCount)
            // Success requires the core's read-only buffer validation; exact queries happen after FD closure.
            val reader = PackedCandidateLexicon(listOf(handle))
            for ((slot, reference) in references[index].withIndex()) {
                stage.set(languageStage + 20 + slot)
                assertEquals("PACKED_REFERENCE_ID_" + reference.id, reference.expected,
                    reader.exact(identity.language, reference.key, CandidateSearchControl { false }))
            }
            stage.set(languageStage + 40)
            val after = memory()
            assertTrue(openNanos >= 0 && loadNanos >= 0 && cpuNanos >= 0)
            val values = "v1 language=$index open_ns=$openNanos load_ns=$loadNanos cpu_ns=$cpuNanos " +
                "mapped_bytes=$mappedBytes words=${handle.wordCount} nodes=${handle.nodeCount} " +
                "references=${references[index].size} java_before=${before.first} java_after=${after.first} " +
                "pss_kib_before=${before.second} pss_kib_after=${after.second}"
            instrumentation.sendStatus(0, Bundle().apply { putString("packed_reader_contract", values) })
        }
    }

    /** Actual Android FD ownership and positive-offset regression, without full dictionary reloads. */
    private fun exerciseEmbeddedRegion(cacheDirectory: File) {
        val file = File.createTempFile("packed-region-", ".bin", cacheDirectory)
        try {
            file.writeBytes(byteArrayOf(99, 98, 1, 2, 3, 97))
            val (mapped, originalFd, target) = AssetFileDescriptor(
                ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY), 2, 3,
            ).use { descriptor ->
                val originalFd = descriptor.fileDescriptor
                val target = Os.readlink("/proc/self/fd/${descriptor.parcelFileDescriptor.fd}")
                assertEquals(1, countDescriptors(target))
                val buffer = AndroidPackedLexiconLoader.mapDescriptor(descriptor, 3)
                assertTrue(originalFd.valid())
                assertEquals(6L, Os.fstat(originalFd).st_size)
                assertEquals(1, countDescriptors(target)) // Mapping duplicate closed; original still open.
                for ((offset, length, expected) in listOf(Triple(-1L, 3L, 3L), Triple(Long.MAX_VALUE, 3L, 3L),
                    Triple(2L, Long.MAX_VALUE, Long.MAX_VALUE), Triple(2L, 3L, 2L), Triple(4L, 3L, 3L))) {
                    AssetFileDescriptor(ParcelFileDescriptor.dup(originalFd), offset, length).use { invalid ->
                        val failure = assertThrows(PackedValidationException::class.java) {
                            AndroidPackedLexiconLoader.mapDescriptor(invalid, expected)
                        }
                        assertEquals(PackedLoadFailure.ASSET_RANGE, failure.reason)
                        assertEquals(2, countDescriptors(target)) // No leaked duplicate on failure either.
                    }
                    assertEquals(1, countDescriptors(target))
                }
                Triple(buffer, originalFd, target)
            }
            assertFalse(originalFd.valid())
            assertEquals(0, countDescriptors(target))
            assertTrue(mapped.isReadOnly)
            assertEquals(3, mapped.capacity())
            assertEquals(listOf<Byte>(1, 2, 3), (0..2).map { mapped.get(it) })
            assertThrows(ReadOnlyBufferException::class.java) { mapped.put(0, 7.toByte()) }
        } finally { assertTrue(file.delete()) }
    }

    private fun countDescriptors(target: String): Int = File("/proc/self/fd").list().orEmpty().count { name ->
        try { Os.readlink("/proc/self/fd/$name") == target } catch (_: android.system.ErrnoException) { false }
    }

    private fun memory(): Pair<Long, Int> {
        val runtime = Runtime.getRuntime()
        val info = Debug.MemoryInfo()
        Debug.getMemoryInfo(info)
        return (runtime.totalMemory() - runtime.freeMemory()) to info.totalPss
    }

    private fun verifyFile(assets: AssetManager, path: String, expectedBytes: Long?, expectedSha: String) {
        val digest = MessageDigest.getInstance("SHA-256")
        val buffer = ByteArray(4096)
        var count = 0L
        assets.open(path).use { stream ->
            while (true) {
                val size = stream.read(buffer)
                if (size < 0) break
                digest.update(buffer, 0, size)
                count += size
            }
        }
        if (expectedBytes != null) assertEquals(expectedBytes, count)
        assertEquals(expectedSha, PackedLexiconManifest.hex(digest.digest()))
    }

    private fun withTriePath(base: TrustedPackedLexicon, path: String): TrustedPackedLexicon {
        val m = base.manifest
        val changed = PackedLexiconManifest(m.language, m.wordCount, m.nodeCount, m.trie.copy(path = path),
            m.lengths, m.ranks, m.canonicalWordsSha256, m.provenanceSha256, m.notices,
            m.normalization, m.maximumFrequencyRank)
        return TrustedPackedLexicon(base.language, changed.identity(), changed)
    }

    private class Reference(val id: Int, val key: String, val expected: ExactMembership) {
        override fun toString(): String = "Reference(id=$id)"
    }

    companion object {
        // Fixed public reference IDs from benchmark/fixtures/exact/{en,es,ru}.tsv; no holdout inputs.
        private val references = listOf(
            listOf(
                Reference(0, "cheerig", ExactMembership.ABSENT),
                Reference(1, "joh", ExactMembership.ABSENT),
                Reference(2, "slution", ExactMembership.ABSENT),
                Reference(240, "crystals", ExactMembership.PRESENT),
                Reference(241, "jump", ExactMembership.PRESENT),
                Reference(242, "hatchets", ExactMembership.PRESENT),
                Reference(258, "crystals􏿿", ExactMembership.ABSENT),
                Reference(276, "", ExactMembership.UNAVAILABLE),
            ),
            listOf(
                Reference(1000, "sl", ExactMembership.ABSENT),
                Reference(1001, "indi", ExactMembership.ABSENT),
                Reference(1002, "uo", ExactMembership.ABSENT),
                Reference(1240, "haciéndolos", ExactMembership.PRESENT),
                Reference(1241, "tipos", ExactMembership.PRESENT),
                Reference(1242, "migra", ExactMembership.PRESENT),
                Reference(1258, "haciéndolos􏿿", ExactMembership.ABSENT),
                Reference(1276, "", ExactMembership.UNAVAILABLE),
            ),
            listOf(
                Reference(2000, "полици", ExactMembership.ABSENT),
                Reference(2001, "засавило", ExactMembership.ABSENT),
                Reference(2002, "ерет", ExactMembership.ABSENT),
                Reference(2240, "шума", ExactMembership.PRESENT),
                Reference(2241, "одному", ExactMembership.PRESENT),
                Reference(2242, "загрязненному", ExactMembership.PRESENT),
                Reference(2258, "шума􏿿", ExactMembership.ABSENT),
                Reference(2276, "", ExactMembership.UNAVAILABLE),
            ),
        )
    }
}
