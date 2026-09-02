package io.github.mesteriis.rune.keyboard.intelligence.inference

import org.junit.Assert.*
import org.junit.Test

internal class DutyClock {
    var elapsed = 0L
    var cpu = 0L
    var fail = false
    fun sample(): ModelDutySample {
        if (fail) throw IllegalStateException()
        return ModelDutySample(elapsed, cpu)
    }
}

class ModelDutyOwnerTest {
    @Test fun idleRefillThenCpuDebitHasExactAdmissionBoundary() {
        for (debit in listOf(499L, 500L, 501L)) {
            val clock = DutyClock(); val owner = ModelDutyOwner(clock::sample)
            val lease = owner.acquireLease()
            clock.elapsed = 600_000; clock.cpu = debit
            assertEquals(debit <= 500, owner.admit(lease).admitted)
            assertEquals((8000 - debit) * 15, owner.account().creditUnits)
        }
    }
    @Test fun fractionalRefillDoesNotDependOnFiftyMillisecondSubdivisions() {
        fun scenario(step: Long): Long {
            val clock = DutyClock(); val owner = ModelDutyOwner(clock::sample)
            clock.cpu = 4000; owner.account()
            while (clock.elapsed < 10_000) { clock.elapsed += step; owner.account() }
            return owner.account().creditUnits
        }
        assertEquals(80_000L, scenario(10_000))
        assertEquals(scenario(10_000), scenario(50))
        assertEquals(scenario(10_000), scenario(1))
    }
    @Test fun debtIsNotForgivenAndRefillNeverExceedsCapacity() {
        val clock = DutyClock(); val owner = ModelDutyOwner(clock::sample)
        val lease = owner.acquireLease()
        clock.cpu = 10_000
        assertEquals(-30_000L, owner.account().creditUnits)
        assertFalse(owner.admit(lease).admitted)
        clock.elapsed = 60_000
        assertEquals(90_000L, owner.account().creditUnits)
        clock.elapsed = 600_000
        assertEquals(120_000L, owner.account().creditUnits)
    }
    @Test fun backwardNegativeAndThrowingSamplesPermanentlyFaultWithoutNewBaseline() {
        for (mode in 0..4) {
            val clock = DutyClock(); val owner = ModelDutyOwner(clock::sample)
            val lease = owner.acquireLease()
            clock.elapsed = 100; clock.cpu = 100; owner.account()
            when (mode) {
                0 -> clock.elapsed = 99
                1 -> clock.cpu = 99
                2 -> clock.elapsed = -1
                3 -> clock.cpu = -1
                else -> clock.fail = true
            }
            assertTrue(owner.account().faulted)
            clock.fail = false; clock.elapsed = 100_000; clock.cpu = 200
            assertFalse(owner.admit(lease).admitted)
            assertTrue(owner.account().creditUnits < 120_000)
            owner.onUnbind(1); owner.onBind(1)
            assertTrue(owner.account().faulted)
        }
    }
    @Test fun initialClockFailureDoesNotGrantANewBaselineOnRecovery() {
        val clock = DutyClock().also { it.fail = true }
        val owner = ModelDutyOwner(clock::sample)
        val lease = owner.acquireLease()
        clock.fail = false; clock.elapsed = 60_000; clock.cpu = 10_000
        assertFalse(owner.admit(lease).admitted)
        assertEquals(-30_000L, owner.account().creditUnits)
        val lifecycle = owner.registerLifecycle()
        owner.onBind(lifecycle); owner.onUnbind(lifecycle); owner.onBind(lifecycle)
        assertTrue(owner.account().faulted)
    }
    @Test fun overflowSaturatesWithoutWrappingOrGrantingCredit() {
        val clock = DutyClock(); val owner = ModelDutyOwner(clock::sample)
        val lease = owner.acquireLease()
        clock.cpu = Long.MAX_VALUE
        val debt = owner.account().creditUnits
        assertTrue(debt < 0)
        assertFalse(owner.admit(lease).admitted)
        clock.elapsed = Long.MAX_VALUE
        val balance = owner.account().creditUnits
        assertTrue(balance <= 120_000)
        assertEquals(balance, owner.account().creditUnits)
    }
    @Test fun leaseSpansWarmIdleAndRecreationWithoutResettingCredit() {
        val clock = DutyClock(); val owner = ModelDutyOwner(clock::sample)
        val first = owner.acquireLease(); assertTrue(first > 0)
        clock.cpu = 2000; owner.account()
        assertEquals(0L, owner.acquireLease())
        owner.release(first)
        val second = owner.acquireLease(); assertTrue(second > first)
        assertEquals(90_000L, owner.account().creditUnits)
        owner.release(first) // obsolete release cannot free the successor
        assertEquals(0L, owner.acquireLease())
        owner.release(second)
    }
    @Test fun pressureRequiresRealUnbindBindAndLaterPressureWins() {
        val clock = DutyClock(); val owner = ModelDutyOwner(clock::sample)
        val lifecycle = owner.registerLifecycle(); val lease = owner.acquireLease()
        owner.onBind(lifecycle); owner.suspendForPressure()
        assertFalse(owner.admit(lease).admitted)
        owner.onBind(lifecycle)
        assertFalse(owner.admit(lease).admitted)
        owner.onUnbind(lifecycle); owner.onBind(lifecycle)
        assertTrue(owner.admit(lease).admitted)
        owner.suspendForPressure()
        assertFalse(owner.admit(lease).admitted)
        val successor = owner.registerLifecycle()
        owner.onBind(successor) // recreation without an unbind cannot clear pressure
        assertFalse(owner.admit(lease).admitted)
        owner.onUnbind(lifecycle); owner.onBind(successor) // retired lifecycle has no authority
        assertFalse(owner.admit(lease).admitted)
    }
}
