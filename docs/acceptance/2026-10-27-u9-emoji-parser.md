# U9 — single-pass catalog parser; opening budget remains failed

The first traced opening spent 21.390 ms in catalog load/parse, 5.754 ms in panel
construction and 4.313 ms in glyph filtering. Constant trace sections now expose
these phases without editor/user content. Tabs include catalog loading, so their
inclusive duration must not be added to the catalog duration.

The parser now scans delimiters, controls and blank-field evidence once, reusing
six field slots. It avoids a whole-file line list, per-row split lists, a regex
matcher per category ID and repeated Unicode blank scans. UTF-8 REPORT decoding,
byte budget, stream closing, schema/row/order/duplicate checks, localized names
and complete glyph strings retain their existing contract. Catalog assets and
generation did not change. Loading still starts on opening the palette; there is
no startup prewarm or background worker.

Validation passes:

- 1,251 JVM tests, zero failures/errors/skips. Added checks cover every ISO
  control via the independent Character predicate, line separators, Unicode-only
  blanks and field-slot reuse. The complete packaged TSV is reconstructed from
  the parsed catalog and compared field/order-for-field/order using an independent
  line/split reference.
- Fifteen source tests, IME/scoring boundary, release privacy, debug lint and
  debug/test builds pass. Final JVM rerun after the full-data assertion also passes.
- Seven optimized-APK API 26 functional cases pass: font membership for every
  category/name in EN/RU/ES, actual panel insertion/deletion/next-word behavior and
  optional-key settings/editor restrictions. Font results remain 1,545 accepted
  and 353 hidden entries.
- The optimized profile's first catalog span is 6.669 ms. This is a phase
  observation on the updated profiling AVD, not an independent performance win
  or a budget qualification. Baseline APK/source patch and both raw private
  traces/derived spans are bound by the adjacent evidence JSON.

## Predeclared clean-AVD series: target still not met

Three independent clean API 26 AVDs each install the same SHA-bound APK and run
four fresh-view preview observations without tracing. All twelve observations
count. Scope remains native performClick/reducer/render and first window-draw
observation of a visible populated grid, at 958 × 526 px, 420 dpi, font scale 1.0.
It excludes touch injection, IME/Binder work, cold IME/PSS and GPU presentation.

| Clean AVD | Handler ms for palettes 0…3 | Draw-start ms for palettes 0…3 |
| --- | --- | --- |
| 0 | 27.910, 10.695, 18.842, 7.448 | 35.926, 14.873, 37.262, 19.015 |
| 1 | 54.501, 15.876, 14.194, 15.864 | 61.803, 19.445, 17.328, 17.615 |
| 2 | 24.170, 14.468, 7.947, 7.412 | 32.038, 17.547, 15.143, 14.898 |

AVD 1, palette 0 fails both 50 ms limits. The measurement-validity tests pass;
the separate performance gate is false. No late observation is dropped and the
budget is not raised. Remaining cold-path profiling is required.

Two host preparation issues occurred before any measurements: a console-port
bind refusal before AVD creation, then an empty SDK-property read before native
runner dispatch. Both are retained as preparation failures, not passes or timing
observations. The scoped host guard now retries only empty/failed read-only
probes; a nonempty wrong target/API still refuses immediately. Separate explicit
port pairs and three new clean AVDs completed the planned valid series. These
host helpers are private artifacts, not new app retry behavior.

The unchanged 88 spelling replay sources, 18 scoring assets and driver match the
prior accepted identities; its 12,000-row ordinary replay is reused, not rerun.
Existing EN/ES quality limits remain. All owned AVDs are stopped/deleted; no phone
action/update occurred. U9 and the complete review remain open for the failed
opening gate, broader IME/PSS/presentation/Fold checks, modifier insertion and
manual TalkBack.
