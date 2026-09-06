package io.github.mesteriis.rune.keyboard.intelligence.client

/** Cached model-state hint, not Binder connectivity or proof of a loaded inference engine. */
enum class ModelReadinessHint { UNKNOWN, MISSING, LOADING, BROKEN, READY }

/** A saved setting alone is UNIMPLEMENTED until its model consumer actually exists. */
enum class ModelConsumerDemand { DISABLED, UNIMPLEMENTED, ENABLED_IMPLEMENTED }

/** No editor/model I/O. Only an enabled, implemented model consumer can request transport. */
class ModelDemand private constructor(val sessionId: Long?, val shouldBind: Boolean) {
    companion object {
        /**
         * normalTextEligible is the owner's cached NORMAL plain-text, non-raw eligibility.
         * Lexicon-only suggestions, strip visibility, mechanical punctuation and double-space
         * are not model consumers. Spelling and contextual consumers are independent.
         */
        fun derive(
            sessionId: Long?,
            sessionActive: Boolean,
            inputViewVisible: Boolean,
            normalTextEligible: Boolean,
            readiness: ModelReadinessHint,
            spelling: ModelConsumerDemand = ModelConsumerDemand.DISABLED,
            contextual: ModelConsumerDemand = ModelConsumerDemand.DISABLED,
        ): ModelDemand {
            val session = sessionId?.takeIf { it > 0 }
            val consumer = spelling == ModelConsumerDemand.ENABLED_IMPLEMENTED ||
                contextual == ModelConsumerDemand.ENABLED_IMPLEMENTED
            return ModelDemand(session, session != null && sessionActive && inputViewVisible &&
                normalTextEligible && readiness == ModelReadinessHint.READY && consumer)
        }
    }
}
