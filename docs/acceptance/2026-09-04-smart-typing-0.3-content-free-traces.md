# Smart Typing 0.3 content-free traces

The Android composition root now supplies one Perfetto sink to candidate generation,
ranking, model request/result handling, automatic correction commit/Undo and mechanical
punctuation planning. Host tests retain a no-op sink, so tracing does not add an Android
dependency to the state machines or workers.

The complete Smart Typing vocabulary is a fixed enum containing exactly the nine names
required by the 0.3 specification. No trace API accepts a word, candidate text, prefix,
punctuation value, language content, editor package, model path, session ID or request ID.
All sections close in `finally`, including exceptions and rejected editor operations.

Targeted JVM validation covers the trace vocabulary, balanced failure cleanup, candidate
worker/coordinator lifecycle, model callbacks, correction commit/Undo and mechanical
punctuation. Physical Perfetto latency, RSS/PSS, frame and battery measurements remain a
separate Fold release gate; this slice adds the measurement points and claims no timing
result.
