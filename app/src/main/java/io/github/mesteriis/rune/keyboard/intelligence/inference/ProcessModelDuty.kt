package io.github.mesteriis.rune.keyboard.intelligence.inference

import android.os.Process
import android.os.SystemClock

/** One numeric owner for the lifetime of :model_runtime, never scoped to a Service or worker. */
internal object ProcessModelDuty {
    val owner = ModelDutyOwner { ModelDutySample(SystemClock.elapsedRealtime(), Process.getElapsedCpuTime()) }
}
