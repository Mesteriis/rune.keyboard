# Smart Typing 0.3 Fold latency investigation — 2026-09-05

The exact published Rune Text 0.1 GGUF (`7a97111c…dd9c4`, 396704416 bytes) was measured on the
physical Fold with the public synthetic request `Пекарь готовит ` and four bounded candidates.
The instrumentation verifies the complete model SHA-256 before loading and records content-free
timings only.

| Runtime path | Load wall | Score wall | Process CPU | Result |
| --- | ---: | ---: | ---: | --- |
| Original, full prefix per candidate | 0.874 s | 11.638 s | not captured | FAIL |
| Original, repeated thermal run | 1.322 s | 13.621 s | 51.795 s | FAIL |
| Shared prefix once per set | 1.120 s | 4.869 s | 18.569 s | FAIL |
| Persistent context plus incremental KV, cold score | 1.397 s | 5.855 s | 21.698 s | FAIL |
| Persistent context plus incremental KV, warm score | included above | 4.480 s | 16.994 s | FAIL |

Shared-prefix and incremental-KV results match the independent token-at-a-time scalar oracle with
zero sum-log-probability delta. The cache retains token IDs/KV in the private model process only,
clears on cancellation failure, session unbind, memory pressure, idle unload, model replacement or
process death, and never reads editor text.

Two rejected experiments establish practical bounds. Eight scoring threads increased wall time to
37.628 s and CPU to 192.869 s on the Fold. A 64-token microbatch left warm wall time at 4.376 s and
changed calibrated scores by up to 0.407125 in the exact-model oracle, so it was not adopted.

The production watchdog remains 3 seconds and 8 CPU-seconds per minute. Raising it cannot make this
model interactive: even the warm optimized request exceeds both limits, and a larger allowance
would permit only sparse corrections while consuming an unacceptable typing-time CPU budget.
Rune Text 0.1 therefore remains a suggestion/evaluation model on this device. Automatic ordinary
typo correction still requires a smaller specialized ranker or a newly qualified batched model
whose measured p95 completes before the word boundary.

Backspace ownership was corrected independently: deleting a pending Rune-owned space now reopens
the complete preceding Rune-owned word and requests candidates for that word. A word whose left
boundary predates the bounded session context is not claimed. This preserves the no-readback rule.
