package io.github.mesteriis.rune.keyboard.intelligence.inference

import android.content.Context
import android.app.ActivityManager
import android.os.Bundle
import android.os.SystemClock
import android.system.Os
import android.system.OsConstants
import androidx.test.core.app.ApplicationProvider
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import io.github.mesteriis.rune.keyboard.intelligence.client.BoundModelScoringClient
import io.github.mesteriis.rune.keyboard.intelligence.client.ModelScoringListener
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringCode
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringInput
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringReply
import io.github.mesteriis.rune.keyboard.intelligence.ipc.ScoringToken
import io.github.mesteriis.rune.keyboard.intelligence.storage.ActiveModelResolver
import io.github.mesteriis.rune.keyboard.intelligence.storage.ModelOperationGate
import io.github.mesteriis.rune.keyboard.settings.SettingsActivity
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File
import java.security.MessageDigest
import java.util.concurrent.Callable
import java.util.concurrent.CountDownLatch
import java.util.concurrent.FutureTask
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit

/** Explicit physical probe of the production service/duty policy; fixed public text only. */
class RealModelServiceInstrumentedTest {
    @Test(timeout = 180_000) fun exactInstalledModelPreparesAndScoresThroughPrivateBinder() {
        assumeTrue("Explicit installed-model service probe only",
            InstrumentationRegistry.getArguments().getString("runeRealService") == "true")
        // A hidden/background app is deliberately suspended by the production memory policy.
        // Keep an actual foreground owner for this active-session probe; never bypass that policy.
        ActivityScenario.launch(SettingsActivity::class.java).use { exerciseService() }
    }

    private fun exerciseService() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val root = File(context.noBackupFilesDir, "model-delivery")
        ModelOperationGate(root).withReadLock {
            val active = ActiveModelResolver(root).resolve()
            assertNotNull("Exact installed model is required", active)
            assertEquals(396704416L, active!!.file.length())
            val digest = MessageDigest.getInstance("SHA-256")
            active.file.inputStream().buffered().use { input ->
                val bytes = ByteArray(64 * 1024)
                while (true) {
                    val count = input.read(bytes)
                    if (count < 0) break
                    digest.update(bytes, 0, count)
                }
            }
            assertEquals("7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4",
                digest.digest().joinToString("") { "%02x".format(it.toInt() and 0xff) })
        }
        // Digest verification warms filesystem cache. This is a cold binding, not cold storage.
        val session = SystemClock.elapsedRealtimeNanos()
        val connected = CountDownLatch(1)
        val replies = LinkedBlockingQueue<ScoringReply>()
        var current: ScoringToken? = null // main thread only
        val client = onMain { BoundModelScoringClient(context, object : ModelScoringListener {
            override fun currentCompositionRevision() = current?.revision ?: 0L
            override fun isCurrentRequest(token: ScoringToken) = token == current
            override fun onAvailabilityChanged(available: Boolean) { if (available) connected.countDown() }
            override fun onReply(reply: ScoringReply) { replies.add(reply) }
        }) }
        fun submit(id: Long) = onMain {
            val token = ScoringToken(session, id, id, listOf(0, 1, 2, 3))
            current = token
            client.score(ScoringInput(token, "Пекарь готовит ", listOf("ттесто", "тесто", "место", "тесть")))
        }
        fun reply(id: Long): ScoringReply {
            val result = replies.poll(4, TimeUnit.SECONDS)
            assertNotNull("Bounded model reply timed out", result)
            assertEquals(id, result!!.token.requestId)
            assertEquals(session, result.token.sessionId)
            return result
        }
        fun success(result: ScoringReply) {
            assertEquals("Service request ${result.token.requestId} code", ScoringCode.OK, result.code)
            assertEquals(listOf(0, 1, 2, 3), result.scores.map { it.candidateId })
            assertTrue(result.scores.all { it.sumLogProbability.isFinite() && it.tokenCount in 1..255 })
        }
        try {
            val started = SystemClock.elapsedRealtime()
            onMain { client.attachSession(session, true) }
            assertTrue("Private service binding timed out", connected.await(5, TimeUnit.SECONDS))
            onMain {
                // The serial Binder sender cancels obsolete input before admitting its successor.
                // This does not assert which native stage happened to be active at cancellation.
                val old = ScoringToken(session, 1, 1, listOf(0, 1))
                current = old
                client.score(ScoringInput(old, "Public", listOf(" fixture", " fixtures")))
                client.cancel()
            }
            submit(2)
            val first = reply(2); success(first)
            val firstWall = SystemClock.elapsedRealtime() - started
            submit(3)
            val immediate = reply(3)
            assertTrue("Unexpected duty result", immediate.code in listOf(ScoringCode.OK, ScoringCode.UNAVAILABLE))
            if (immediate.code == ScoringCode.OK) success(immediate)
            // Refill the existing process budget with no rebind/reset or hidden retry.
            SystemClock.sleep(9_000)
            assertTrue(replies.isEmpty())
            val warmStart = SystemClock.elapsedRealtime()
            submit(4)
            val warm = reply(4); success(warm)
            assertEquals(first.scores, warm.scores)
            assertTrue(replies.isEmpty())
            InstrumentationRegistry.getInstrumentation().sendStatus(0, Bundle().apply {
                putLong("serviceFirstWallMillis", firstWall)
                putLong("serviceFirstNativeMillis", first.elapsedMillis)
                putInt("serviceImmediateCode", immediate.code)
                putLong("serviceWarmWallMillis", SystemClock.elapsedRealtime() - warmStart)
                putLong("serviceWarmNativeMillis", warm.elapsedMillis)
                putInt("serviceSuccessfulRequests", if (immediate.code == ScoringCode.OK) 3 else 2)
            })
            if (InstrumentationRegistry.getArguments().getString("runeRealServiceDuty") == "true") {
                val manager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
                val process = manager.runningAppProcesses.single { it.processName == context.packageName + ":model_runtime" }
                assertEquals(android.os.Process.myUid(), process.uid)
                fun cpuMillis(): Long {
                    val fields = File("/proc/${process.pid}/stat").readText().substringAfterLast(") ").trim().split(Regex("\\s+"))
                    return (fields[11].toLong() + fields[12].toLong()) * 1000 / Os.sysconf(OsConstants._SC_CLK_TCK)
                }
                fun rssBytes(): Long {
                    val status = File("/proc/${process.pid}/status").readText()
                    return Regex("(?m)^VmRSS:\\s+(\\d+) kB$").find(status)!!.groupValues[1].toLong() * 1024
                }
                // Sampling our own UID's model process only; never emit its PID/name or /proc text.
                val dutyCpuStart = cpuMillis()
                val dutyStart = SystemClock.elapsedRealtime()
                var completed = 0; var denied = 0
                repeat(120) { index ->
                    submit(5L + index)
                    val result = reply(5L + index)
                    when (result.code) {
                        ScoringCode.OK -> { success(result); completed++ }
                        ScoringCode.UNAVAILABLE -> denied++
                        else -> fail("Unexpected sustained duty result code ${result.code}")
                    }
                    val remaining = dutyStart + (index + 1) * 500 - SystemClock.elapsedRealtime()
                    if (remaining > 0) SystemClock.sleep(remaining)
                }
                val dutyElapsed = SystemClock.elapsedRealtime() - dutyStart
                val dutyCpu = cpuMillis() - dutyCpuStart
                val creditBound = ModelDutyProfile.CAPACITY_CPU_MILLIS +
                    dutyElapsed * ModelDutyProfile.REFILL_UNITS_PER_ELAPSED_MILLI / ModelDutyProfile.UNITS_PER_CPU_MILLI
                assertTrue("No successful sustained service requests", completed > 0)
                assertTrue("Duty limiter never denied the public burst", denied > 0)
                // One cooperative cancellation/check interval and clock granularity may overshoot.
                assertTrue("Measured service CPU exceeded accounted allowance", dutyCpu <= creditBound + 500)
                InstrumentationRegistry.getInstrumentation().sendStatus(0, Bundle().apply {
                    putLong("dutyElapsedMillis", dutyElapsed); putLong("dutyProcessCpuMillis", dutyCpu)
                    putLong("dutyCreditBoundCpuMillis", creditBound)
                    putInt("dutyCompleted", completed); putInt("dutyDenied", denied)
                })
                val idleStart = SystemClock.elapsedRealtime()
                val idleCpuStart = cpuMillis()
                val loadedRss = rssBytes()
                SystemClock.sleep(50_000)
                val beforeUnloadRss = rssBytes()
                assertTrue("Model was unloaded before the idle window", beforeUnloadRss > loadedRss - 100 * 1024 * 1024)
                SystemClock.sleep(15_000)
                val unloadedRss = rssBytes()
                assertTrue("Expected model pages to leave RSS after idle unload", unloadedRss + 200 * 1024 * 1024 < beforeUnloadRss)
                assertTrue(onMain { client.available })
                assertTrue(replies.isEmpty())
                InstrumentationRegistry.getInstrumentation().sendStatus(0, Bundle().apply {
                    putLong("idleElapsedMillis", SystemClock.elapsedRealtime() - idleStart)
                    putLong("idleProcessCpuMillis", cpuMillis() - idleCpuStart)
                    putLong("loadedRssBytes", loadedRss); putLong("beforeUnloadRssBytes", beforeUnloadRss)
                    putLong("unloadedRssBytes", unloadedRss)
                })
            }
        } finally {
            onMain { current = null; client.close() }
        }
    }

    private fun <T> onMain(action: () -> T): T {
        val task = FutureTask(Callable(action))
        InstrumentationRegistry.getInstrumentation().runOnMainSync(task)
        return task.get(6, TimeUnit.SECONDS)
    }
}
