package io.github.mesteriis.rune.keyboard.intelligence.delivery

import android.content.pm.PackageManager
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ModelDeliveryManifestInstrumentedTest {
    @Test
    fun declaresOnlyInternetAndPrivateWorkerComponents() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        @Suppress("DEPRECATION")
        val info = context.packageManager.getPackageInfo(
            context.packageName,
            PackageManager.GET_PERMISSIONS or PackageManager.GET_SERVICES or PackageManager.GET_RECEIVERS,
        )

        assertEquals(setOf("android.permission.INTERNET"), info.requestedPermissions.orEmpty().toSet())
        val worker = info.services.orEmpty().single { it.name == ModelInstallJobService::class.java.name }
        val receiver = info.receivers.orEmpty().single { it.name == ModelDownloadReceiver::class.java.name }
        assertFalse(worker.exported)
        assertEquals("android.permission.BIND_JOB_SERVICE", worker.permission)
        assertEquals("${context.packageName}:model_worker", worker.processName)
        assertFalse(receiver.exported)
    }
}
