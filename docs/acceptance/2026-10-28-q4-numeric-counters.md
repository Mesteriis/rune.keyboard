# Q4 — numeric model and storage foundation

The model now contains a separate fixed 14-source × four-outcome numeric table,
with no addition to the existing eight QualityEvent counters. Model refinement
is excluded; canonical-case changes have their own source. Two new recorder
methods accept only fixed enums and an integer duration. Existing shadow text
comparison remains ephemeral and does not enter the persisted snapshot.

Five engine-response buckets use exact 50/100/250/500 ms edges and avoid integer
overflow for large durations. The existing candidate-latency buckets are retained.
An observed explicit Undo fraction is available at 100 source applications;
below that, or with an invalid numerator, it is unavailable. It never supplies
a correctness label, enables/disables a source or changes admission.

The strict RUNE_QUALITY_3 codec stores 81 bounded decimal counters and a fixed
header, capped at 2,048 bytes. Versions 1 and 2 retain every legacy field; new
source/model arrays are zero rather than inferred from old aggregate counts.
The atomic no-backup filename remains unchanged. Counts saturate at 10^12 and
reset/restore cover all arrays. The developer storage contract is documented in
`docs/quality-source-counters.md`.

Actual validation: 1313 app JVM tests pass, with zero failures/errors/
skips; 31 belong to the quality model/repository suites. Debug
lint, profile privacy/R8 packaging and the Android-test APK build also pass.
New regressions cover the fixed identities and non-String API, all 56 distinct
counter positions, privacy/toggle gates, exact model timing boundaries, 99/100/
101 application reporting, v2 migration, v1 preservation, maximum-size numeric
round trip, saturation, malformed input, load/save failure and durable reset.

This is the storage foundation, not completed Q4. Controller/Undo/window and
model-time hooks, dashboard/reset instrumentation, debug export and final
replay/release/device integration remain separate. No owner installation or real
owner-use observation period is claimed here. The required two weeks of actual
use cannot be replaced by synthetic tests. The complete review remains open.
