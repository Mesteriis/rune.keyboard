# Q6 refinement promotion admission

The current refinement promoter previously used assertions for selection/model
checks and immediately overwrote bundled models before computing parity and
provenance. It did not inspect durable exclusion coverage or distinguish
disclosed data. Assertions are removed by `python -O`.

Default promotion now checks the permanent registries before optional model
libraries or source artifacts are opened. It also requires a bound independent
data-evaluation receipt, matching corpus/registry snapshots and final new-family
row checks. Current incomplete coverage refuses packaged promotion.

Historical review requires both `--historical-reproduction` and a fresh output
under `build/`. It validates the frozen selection, evaluation binding, public
manifest, safe model names, exact model bytes and supported model format/window
with explicit runtime checks. Parity/provenance are computed before output
creation. All input bytes and the baseline are rechecked before writing; the
packaged branch also rechecks registry identity. Historical output is explicitly
non-independent and not production-qualified. It never writes APK sources or
assets.

The original promoter's complete bytes and digest remain archived; packaged
provenance retains its original digest through an explicit exact archive map.
Existing tests reject a corrupted archive rather than rehashing old evidence.

Actual checks:

- Six promotion tests pass on Python 3.12 and 3.14, including real default and
  malformed-receipt refusal under `python -O`, runtime-compatible tree payload validation, destination restrictions,
  model/hash/name checks and final input drift.
- Full stdlib: 115 modules / 609 tests, zero failures/errors/skips. The final
  registry recheck was followed by focused reruns.
- Packaged provenance unit tests: 12 pass.
- A controlled host-export fixture uses published frozen weights and original
  public corpus metadata with an explicitly synthetic evaluation binding. It
  runs with optimized Python and writes six files and four numeric parity rows. All inspected packaged asset,
  provenance, Kotlin-identity and parity bytes remain unchanged. This verifies
  export isolation and serialization, not original training/test qualification.

See the [source/evidence receipt](2026-10-28-q6-refinement-promotion-evidence.json).
The current evaluation driver still needs independent-data receipt integration;
no new independent promotion is claimed. Other evaluation/promotion paths,
historical lineage, canonical families and full Q6 qualification remain open.
