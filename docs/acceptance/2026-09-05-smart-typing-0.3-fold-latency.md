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

Activation exposed a separate lifetime regression after the persistent-context change: allocating
the scoring context during model load made active validation hold it alongside the self-test
context. The runtime now loads only the model for validation and creates the persistent scoring
context lazily on the first candidate request. Local native/JVM gates cover the change; another
physical activation and timing run remains required because the Fold was disconnected.

An experimental candidate-lane batch reduced the same host request from 206 ms warm to 43 ms and
completed the archived calibration/known-holdout diagnostics at p95 66/70 ms. It was rejected:
the scalar oracle delta reached 0.544792, and a calibration-only point-95 fit scored the already
seen holdout at EN 370/398 (92.96%), RU 509/547 (93.05%) and ES 501/534 (93.82%). These figures are
diagnostic, not a new qualification; the holdout was previously revealed. Product inference is
therefore closed for the current model/backend pair even though the exact scalar quality profile
passes the selected point-95 gate. Local deterministic candidates remain available.

The next model milestone is a smaller candidate ranker trained and frozen independently of this
known holdout. Its end-to-end budget includes the measured four-candidate local generation p95 of
51.968 ms. Qualification requires a fresh calibration/holdout and a physical Fold p95 that finishes
before the word boundary; preloading may then remove first-request model load but cannot substitute
for warm inference meeting that budget.

A host-only 262,144-feature hashed linear ranker was also tested against 196,400 pinned public
pairwise rows. It trained in 34.47 s and would require roughly 1 MiB of float weights, but the
point-95 calibration admitted only one replacement per language. On the already seen holdout it
admitted EN 4, RU 2 and ES 0 replacements. This fails coverage by orders of magnitude and is not a
shipping candidate. The next prototype must model nonlinear byte/character context while retaining
bounded candidate-only scoring; its data and thresholds still require a fresh unseen holdout.
