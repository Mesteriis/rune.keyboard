# U9 — defer category names; preview performance gate still fails

The catalog validates every field before returning, preserving strict UTF-8,
byte budget, controls/blank-name checks, schema, order and duplicate detection.
Each category retains glyphs and name offsets into the validated immutable text.
Its EmojiEntry/EmojiNames objects and localized strings are created once on first
entry access, with synchronized publication. Category counts and invalid indices
do not materialize names. Public list behavior, source order, packaged TSV,
manifest and generator remain unchanged. The input stream is already closed when
materialization starts. There is no prewarm or worker.

The full decoded text and offsets remain reachable until their lazy initializers
are released. No PSS reduction is claimed. Recent-commit lookup still scans in
source order and can materialize preceding categories; that latency needs separate
profiling. This patch establishes deferred allocation, not a demonstrated speedup.

Two clean API 26 scheduler profiles of the preceding single-pass parser motivated
this change. First clicks were 29.825/32.850 ms, with 21.708/21.946 ms marked
scheduled-running; catalog spans accounted for 11.348/9.088 scheduled-running ms.
These samples did not reproduce the prior 54 ms outlier and cannot explain that
specific observation. Scheduled-running includes interrupts and is not measured
thread CPU time. Tabs includes catalog; phase spans must not be added. Optional
`runeEmojiTrace=true` adds the constant measured-click marker only in the native
measurement test. It defaults off and was off for the candidate acceptance series.
Raw scheduler traces remain private; the evidence publishes durations and hashes.

Validation:

- 1,254 JVM tests, zero failures/errors/skips. Added coverage proves lazy counts,
  index guards, one-time concurrent publication and rejection of invalid names in
  an unopened category. Existing complete TSV reconstruction still passes.
- Fifteen source tests; IME/scoring boundary, release privacy, debug lint and
  debug/test builds pass. The adjacent JSON binds the exact Gradle command/log.
- Seven API 26 functional cases pass, after timing on the first clean AVD:
  font coverage/names, native emoji panel/editor behavior and key settings.
- All 88 ordinary replay sources, 18 scoring assets and driver hashes match the
  prior emoji-key replay. Its 12,000-row projection remains reusable by identity;
  no fresh replay was run. This does not resolve the existing EN qualification
  volume/precision failures or ES aggregate false change.

## Predeclared candidate series

Three clean API 26 AVDs, four fresh preview keyboards each; all 12 count. The same
SHA-bound main/test APKs were used throughout. Budget is 50 ms for both click
handler and first window-draw start with a visible populated grid. Geometry is
958 × 526 px, density 420 dpi, font scale 1.0. Native performClick exercises the
preview reducer/render; it does not measure touch delivery, IME Binder, cold IME,
GPU presentation, release performance or physical Fold behavior.

| Clean AVD | Handler ms, palettes 0…3 | Draw-start ms, palettes 0…3 |
| --- | --- | --- |
| 0 | 38.073, 16.025, 9.422, 8.201 | 47.211, 19.484, 15.544, 16.386 |
| 1 | 44.103, 16.631, 33.245, 17.401 | 56.895, 31.329, 40.500, 20.997 |
| 2 | 49.973, 17.771, 34.910, 32.938 | 60.401, 30.994, 52.982, 50.230 |

Every handler meets 50 ms, but four draw starts exceed it. Measurement-validity
tests pass; the separate performance gate is false. Neither the budget nor the
sample set changed after results. This series does not demonstrate improvement
over the previous candidate. All three measurement AVDs and both profiling AVDs
were stopped/deleted; cleanup receipts are bound in the JSON.

A new owner availability signal prompted a fresh saved-phone check. Device info
and capabilities were unavailable; the read-only diagnostic returned
TRANSPORT_FAILURE. No phone UI was read, no gesture dispatched, and no update was
installed. Physical/Fold checks, manual TalkBack, modifier insertion, remaining
opening/startup/PSS and presented-frame budgets leave U9 open.
