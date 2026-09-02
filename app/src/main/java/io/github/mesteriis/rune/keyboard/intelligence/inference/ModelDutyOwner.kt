package io.github.mesteriis.rune.keyboard.intelligence.inference

/** Development trace profile, not a strict CPU ceiling, release threshold or energy qualification. */
internal object ModelDutyProfile {
    const val CAPACITY_CPU_MILLIS = 8000L
    const val MIN_ADMISSION_CPU_MILLIS = 7500L
    const val ACTIVE_MILLIS = 3000L
    const val QUEUE_MILLIS = 3000L
    const val CHECK_MILLIS = 50L
    const val UNITS_PER_CPU_MILLI = 15L
    const val REFILL_UNITS_PER_ELAPSED_MILLI = 2L // 8000 CPU ms / 60000 elapsed ms, exact carry
    const val CAPACITY_UNITS = CAPACITY_CPU_MILLIS * UNITS_PER_CPU_MILLI
}

internal data class ModelDutySample(val elapsedMillis: Long, val processCpuMillis: Long)
internal data class ModelDutyState(val elapsedMillis: Long, val creditUnits: Long,
    val generation: Long, val faulted: Boolean, val suspended: Boolean)
internal data class ModelDutyAdmission(val admitted: Boolean, val state: ModelDutyState)

/**
 * Fixed numeric process state; no Context, Service, callbacks to a worker, or request payload.
 * Only its clock function is retained. Production supplies the real process CPU clock.
 * All samples (admission, monitor and finalization) share this lock and account each CPU interval once.
 */
internal class ModelDutyOwner(private val clock: () -> ModelDutySample) {
    private var elapsed = 0L
    private var cpu = 0L
    private var credit = ModelDutyProfile.CAPACITY_UNITS
    private var faulted = false
    private var suspended = false
    private var generation = 0L
    private var lease = 0L
    private var nextLease = 0L
    private var lifecycle = 0L
    private var bound = false
    private var canRearm = false

    init {
        val initial = try { clock() } catch (_: Exception) { null }
        if (initial == null || initial.elapsedMillis < 0 || initial.processCpuMillis < 0) faulted = true
        else { elapsed = initial.elapsedMillis; cpu = initial.processCpuMillis }
    }

    @Synchronized fun account(): ModelDutyState {
        val sample = try { clock() } catch (_: Exception) { null }
        if (sample == null) faulted = true
        else {
            val validWall = sample.elapsedMillis >= elapsed && sample.elapsedMillis >= 0
            val validCpu = sample.processCpuMillis >= cpu && sample.processCpuMillis >= 0
            if (!validWall || !validCpu) faulted = true
            if (validWall) {
                if (!faulted) credit = minOf(ModelDutyProfile.CAPACITY_UNITS,
                    add(credit, multiply(sample.elapsedMillis - elapsed, ModelDutyProfile.REFILL_UNITS_PER_ELAPSED_MILLI)))
                elapsed = sample.elapsedMillis
            }
            // A permanently faulted clock never refills/rebaselines. Valid later CPU still incurs debt.
            if (validCpu) {
                val delta = sample.processCpuMillis - cpu
                val debit = multiply(delta, ModelDutyProfile.UNITS_PER_CPU_MILLI)
                if (delta > Long.MAX_VALUE / ModelDutyProfile.UNITS_PER_CPU_MILLI || credit < Long.MIN_VALUE + debit) {
                    faulted = true; credit = Long.MIN_VALUE // never refill an unrepresentable debt
                } else credit = subtract(credit, debit)
                cpu = sample.processCpuMillis
            }
        }
        return ModelDutyState(elapsed, credit, generation, faulted, suspended)
    }

    /** Ownership is separate from speculative admission: required close remains possible in debt. */
    @Synchronized fun acquireLease(): Long {
        if (lease != 0L) return 0
        if (nextLease == Long.MAX_VALUE) { faulted = true; return 0 }
        nextLease++; lease = nextLease
        return lease
    }
    @Synchronized fun release(identity: Long) {
        if (identity != 0L && lease == identity) { account(); lease = 0 }
    }
    @Synchronized fun admit(identity: Long): ModelDutyAdmission {
        val state = account()
        return ModelDutyAdmission(identity != 0L && lease == identity && !state.faulted && !state.suspended &&
            state.creditUnits >= ModelDutyProfile.MIN_ADMISSION_CPU_MILLIS * ModelDutyProfile.UNITS_PER_CPU_MILLI, state)
    }
    @Synchronized fun owns(identity: Long) = identity != 0L && lease == identity

    @Synchronized fun registerLifecycle(): Long {
        if (lifecycle == Long.MAX_VALUE) { faulted = true; return 0 }
        lifecycle++; bound = false
        return lifecycle
    }
    @Synchronized fun onBind(identity: Long): Boolean {
        if (identity == 0L || lifecycle != identity) return false
        if (!bound) {
            bound = true
            if (canRearm) { suspended = false; advanceGeneration() }
            canRearm = false
        }
        return true
    }
    @Synchronized fun onUnbind(identity: Long) {
        if (identity != 0L && lifecycle == identity && bound) {
            bound = false; canRearm = true
        }
    }
    /** Linearization point comes before any worker lock, pending removal or cancellation. */
    @Synchronized fun suspendForPressure() { suspended = true; advanceGeneration() }
    private fun advanceGeneration() {
        if (generation == Long.MAX_VALUE) faulted = true else generation++
    }
    private fun multiply(value: Long, multiplier: Long): Long =
        if (value > Long.MAX_VALUE / multiplier) Long.MAX_VALUE else value * multiplier
    private fun add(value: Long, positive: Long): Long =
        if (value > Long.MAX_VALUE - positive) Long.MAX_VALUE else value + positive
    private fun subtract(value: Long, positive: Long): Long =
        if (value < Long.MIN_VALUE + positive) Long.MIN_VALUE else value - positive
}
