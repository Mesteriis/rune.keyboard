# Optimized Rune Text: physical runtime qualification

2026-09-05. Preparation base: `10e894e8dc9e7bc05e2bce0c826059ec6e53b3c9`.
Original project base: `b5400cbadadd29e8ee915a0fb33fb11ec5bebc79`.
The phone reconnected after the earlier disconnected-device reports. This report
supersedes their runtime-UNRUN status for the observations below, not the full
release gates. Version remains 0.2.0; no push, remote PR or publication occurred.

The shipped Rune Text / optimized CPU backend now enables
`ModelRuntimeQualification.CURRENT` under the unchanged duty/cancellation limits.
No weights, corpus, calibration thresholds or scoring arithmetic changed. The
separate frozen product holdout's user-selected point-95 profile still has
EN293/304, RU342/359 and ES396/408 correct automatic replacements. Deterministic
spelling remains suggestions; canonical case and mechanical rules remain local.

## Release-native measurements

Physical Fold SM-F966B/API36. Exact GGUF: 396704416 bytes, SHA-256
`7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`.
The release instrumentation independently verifies model bytes and installed
native hashes; the native libraries match the actual app release byte for byte.
Pilot27/full180 measured requests passed, with 20 per language/count in full,
plus warmups, cancellation and recovery. Four-candidate p50/p95/max in ms:

| Language | p50 | p95 | Max |
| --- | ---: | ---: | ---: |
| EN | 34.850 | 74.848 | 86.465 |
| RU | 190.009 | 260.200 | 300.370 |
| ES | 124.528 | 172.555 | 197.532 |

Eight-candidate p95: EN148.276/RU400.282/ES295.415 ms. New-runtime load:
340.020 ms wall, 338 ms CPU. Digest verification warms filesystem cache, so this
is not cold-storage latency. All three cancellations returned CANCELLED;
maximum signal-to-end0.946 ms, followed by successful recovery. These samples
are inside the existing3-second active deadline, without establishing a
population percentile or a complete editor latency guarantee.

All 2/4/8 results, conditions, native identities and numeric records are in
`tools/test-native-scoring/runtime-benchmark/results/2026-09-05-fold-optimized/`.
The unrestricted benchmark used116.503 CPU-seconds in38.770 wall seconds;
its continuous rate is not suitable for the IME. The following worker test
provides the evidence for constrained inference.

## Production service and editor

`RealModelServiceInstrumentedTest` checks exact installed bytes and uses the
production client, private Binder, service, adapter and duty worker. It samples
only its own UID's model process, with no diagnostic IPC or fake engine. With an
explicit visible Rune owner:

- First binding through valid reply: **746 ms**, native score228 ms. Obsolete
  input is cancelled and no stale reply delivered. After refill, warm reply
 211 ms/native194 ms preserves exact scores.
- **120 requests in60,000 ms**: 13 completed, 107 UNAVAILABLE. Observed model
  process CPU: **7,850 ms**, including service/native overhead. The test checks
  the conservative `initial capacity + elapsed refill + 500 ms` allowance for
  sampled cancellation and clock granularity; it grants no additional production
  credit and performs no resets/refunds or hidden retry.
- Bound idle65,005 ms: **70 ms CPU**, including eventual unload. RSS remains
 585707520 bytes at50 seconds and falls to158789632 bytes after65 seconds.
  Binder remains available with no replay. This demonstrates page release,
  not absence of all leaks or whole-device energy use.

The first extended probe returned UNAVAILABLE after its pause without an
explicit foreground owner. Its failure and APK/source hashes are retained.
The final fixture supplies a real visible owner instead of bypassing background
or memory suspension. The original suspension cause was not instrumented and
is not claimed as directly proven.

After enabling runtime qualification, the real **IME → `:qa_editor`
InputConnection → installed GGUF service → editor** test passed: `a helllo`
became `a hello ` on Space without a candidate tap; first Backspace restored
`a helllo` as composition with Original selected. All six additional editor
readback counters remained zero. The functional probe allows a normal pause
before Space; it does not measure rapid typing. Temporary test preferences and
IME selection are restored. Separately, all15 composing tests passed on the
cover screen, including full-word reopening, restart and sensitive-field guards.
Evidence: `tools/qa/smart-typing-0.3/results/2026-09-05-fold-qualified/`.

## Remaining scope

Local verification: JVM691/691 and the prescribed lint, debug/release/profile,
privacy, intelligence/dependency and native-symbol gates passed. API26 passed
52/52 in207.509 s. The first API37 run, with two concurrent AVDs, passed50/52:
two live fixtures saw an empty editor with zero composing/commit calls. Its
screenshot was blank despite a populated accessibility tree; no crash log was
present. After restarting the dedicated API37 AVD, isolated live4/4 and the full
unchanged52/52 passed in57.358/198.004 s. No product or test assertion changed
between those runs. The failure, screenshot and full logs remain archived;
its cause is unproven and the intermittent QA result is an open stability item.

| Gate | Actual status |
| --- | --- |
| JVM/local build and privacy gates | PASS |
| API26 scoped matrix | PASS52/52 |
| API37 scoped matrix | PASS52/52 on repeat; initial50/52 FAIL retained |
| Fold runtime/service/cover flow | PASS for the named probes |
| Full Fold / unplugged energy / external CI | BLOCKED: not completed |
| Final0.3.0/model release | BLOCKED: remaining release gates |

After the physical tests, Rune was explicitly enabled and selected through the
system dialogs. The setup screen reported Active. Test preferences remain
restored; the user preference is independent of runtime availability.

This opens the measured runtime, not release0.3.0. A result can still miss a
fast boundary: RU four-candidate p95 exceeds the250-ms post-Space grace; such
late results are discarded and Space never waits. The60-second CPU budget also
limits model coverage. No boundary/debounce/accuracy threshold was relaxed.

Native measurements used USB charging,13–14% battery,35.6–35.7 C and thermal
status1. Unplugged energy, inner-screen/Fold transitions, rapid typing with
missed-frame/event measurements, the complete real-editor/process-death matrix,
and current external CI are separate open gates. No complete Fold or battery
acceptance is claimed.
