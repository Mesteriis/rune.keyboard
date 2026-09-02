package io.github.mesteriis.rune.keyboard.intelligence.client

import org.junit.Assert.assertEquals
import org.junit.Test

class ModelDemandTest {
    @Test fun demandRequiresEverySessionGateReadyAndAnImplementedConsumer() {
        for (session in listOf(null, -1L, 0L, 1L))
            for (active in listOf(false, true))
                for (visible in listOf(false, true))
                    for (normalText in listOf(false, true))
                        for (ready in ModelReadinessHint.entries)
                            for (spelling in ModelConsumerDemand.entries)
                                for (contextual in ModelConsumerDemand.entries) {
                                    val demand = ModelDemand.derive(session, active, visible, normalText,
                                        ready, spelling, contextual)
                                    assertEquals(session?.takeIf { it > 0 }, demand.sessionId)
                                    assertEquals(session != null && session > 0 && active && visible && normalText &&
                                        ready == ModelReadinessHint.READY &&
                                        (spelling == ModelConsumerDemand.ENABLED_IMPLEMENTED ||
                                            contextual == ModelConsumerDemand.ENABLED_IMPLEMENTED), demand.shouldBind)
                                }
    }

    @Test fun readyAndStoredPreferencesWithoutImplementedConsumersRemainDisabled() {
        assertEquals(false, ModelDemand.derive(1, true, true, true, ModelReadinessHint.READY).shouldBind)
        assertEquals(false, ModelDemand.derive(1, true, true, true, ModelReadinessHint.READY,
            ModelConsumerDemand.UNIMPLEMENTED, ModelConsumerDemand.UNIMPLEMENTED).shouldBind)
    }
}
