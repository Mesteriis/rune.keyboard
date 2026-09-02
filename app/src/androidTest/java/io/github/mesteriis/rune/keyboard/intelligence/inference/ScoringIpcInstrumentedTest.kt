package io.github.mesteriis.rune.keyboard.intelligence.inference

import android.content.ComponentName
import android.content.pm.PackageManager
import android.os.BadParcelableException
import android.os.Parcel
import androidx.test.core.app.ApplicationProvider
import android.content.Context
import io.github.mesteriis.rune.keyboard.intelligence.ipc.*
import org.junit.Assert.*
import org.junit.Test
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

class ScoringIpcInstrumentedTest {
    @Test fun privateManifestContract() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        @Suppress("DEPRECATION")
        val info = context.packageManager.getServiceInfo(ComponentName(context, ModelInferenceService::class.java), 0)
        assertFalse(info.exported)
        assertEquals(context.packageName + ":model_runtime", info.processName)
        assertNull(info.permission)
    }
    @Test fun boundedRequestAndNumericReplyRoundTrip() {
        val request = ScoringInput(ScoringToken(1,2,3,listOf(4)), "test", listOf(" word"))
        val parcel = Parcel.obtain()
        try {
            ScoreRequestParcel(request).writeToParcel(parcel,0); parcel.setDataPosition(0)
            val restored = ScoreRequestParcel.CREATOR.createFromParcel(parcel).value
            assertEquals(request.token, restored.token); assertEquals(request.prefix, restored.prefix)
            assertEquals(request.continuations, restored.continuations)
            parcel.setDataSize(0); parcel.setDataPosition(0)
            val result = ScoringReply(request.token,0,7,listOf(NumericScore(4,-1.5,2)))
            ScoreReplyParcel(result).writeToParcel(parcel,0); parcel.setDataPosition(0)
            val reply = ScoreReplyParcel.CREATOR.createFromParcel(parcel).value
            assertEquals(result.token,reply.token);assertEquals(result.scores,reply.scores)
        } finally { parcel.recycle() }
    }
    @Test fun oversizedCountAndTextRejectBeforeAllocation() {
        listOf(true,false).forEach { badCount ->
            val parcel=Parcel.obtain()
            try {
                parcel.writeInt(1);parcel.writeLong(1);parcel.writeLong(0);parcel.writeLong(1)
                parcel.writeInt(if (badCount) Int.MAX_VALUE else 1)
                if (!badCount) { parcel.writeInt(1);parcel.writeInt(Int.MAX_VALUE) }
                parcel.setDataPosition(0)
                try { ScoreRequestParcel.CREATOR.createFromParcel(parcel);fail("malformed wire accepted") }
                catch (_: BadParcelableException) { }
            } finally { parcel.recycle() }
        }
    }
    @Test fun observerConfirmsRegistrationThenInvalidatesOnPointerChange() {
        val context=ApplicationProvider.getApplicationContext<Context>()
        val root=File(context.cacheDir,"scoring-observer-fixture")
        root.deleteRecursively();File(root,"versions/model-1.0.0").mkdirs()
        val changed=CountDownLatch(1);val watch=ActiveModelWatch(root) { changed.countDown() }
        try {
            assertTrue(watch.start("model-1.0.0"))
            File(root,"active-model.json").writeText("synthetic fixture")
            assertTrue(changed.await(2,TimeUnit.SECONDS))
        } finally { watch.close();root.deleteRecursively() }
    }
}
