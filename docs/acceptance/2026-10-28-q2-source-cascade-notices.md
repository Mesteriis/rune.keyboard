# Q2: source cascade, diagnostic namespaces and numeric-asset NOTICE

Architecture now enumerates all 13 SpellingSource and 14 DiagnosticSource values,
with separate descriptions of qualification, candidate selection, admission and
event attribution. It records baseline ranking priority, joint/rescue behavior,
conditional finite-context supplementation, contextual/infinitive/noun-case
revision order, and both admission dispatchers. Canonical case is a separate
boundary gate; model refinement remains disabled by MODEL_QUALIFIED=false.

The event map preserves actual route-dependent behavior: main joint RANKING uses
JOINT, a plain synchronous joint boundary write uses LOCAL_POLICY, and the late
local joint route uses JOINT. CONTEXTUAL means the separate contextual-punctuation
consumer; the statistical local contextual spelling model uses CONTEXTUAL_RANKER.
There is no assumed one-to-one mapping or universal linear source cascade.

`tools/check_typing_sources.py` checks separate namespace tables, the named
orchestration orders and the current refinement flag. Nine mutation tests pass
on Python 3.12/3.14: another namespace cannot cover an omitted row; a new source,
wrong order/dispatcher/status or missing source/marker fails. The check binds the
named orchestration points, not every inner policy condition. Those conditions
were reviewed directly against current source; Kotlin symbolic navigation was
unavailable. No runtime code, threshold, model, candidate order or admission
window was changed.

## Packaged attribution inventory

NOTICE now explicitly names every one of the 13 packaged experimental `.bin`,
`.ctx` and `.gram` files. Six filenames were absent from the original explicit
text. Each row names its declared attribution/license and exact provenance file;
existing contributor credits and license text remain. This is declared source
inventory, not proof of complete training reconstruction or fresh qualification.

`tools/check_typing_asset_notice.py` reuses the authoritative 29-entry F-Droid
review-data policy for exact path, bytes, digest, provenance digest, action and
prefix-collision checks, then verifies NOTICE coverage and the binary's declared
digest in its bound provenance. It refuses duplicate/stale rows, wrong provenance,
changed/unregistered data, inventory-to-ignore changes and external NOTICE
symlinks. Nine fixture tests pass on Python 3.12/3.14, and the ten existing direct
data-policy tests pass. Both new checkers/tests are wired into the stdlib CI job;
the workflow parses. Hosted CI was not run.

Both prior replay receipts became stale because NOTICE is a bound input. The
actual two-profile CI replay was rerun: 2,160 + 12,000 = 14,160 rows, two fresh JVM
projections per profile, all 69 assets bound and no model calls. Both existing
projection/baseline hashes match; no baseline was renewed or weakened. Debug/test
APK compilation, debug lint, architecture boundaries and all 1,355 JVM tests pass
with zero failures/errors/skips.

## Integration boundary and remaining Q2 scope

Current source preparation/scanner and clean release/profile/footprint results
are recorded after the source commit in the adjacent receipt. Historical 0.4.1
and 0.4.2 recipes remain pinned to their published commits. The current review
policy separates scanner false-positive suppressions from inventory-only data;
blanket scanignore is not treated as inventory acceptance. fdroidserver 2.4.5
counts an unused scanignore/scandelete path as a fatal finding.

Q2 remains in progress for remaining guide/schema/experiment wording and the full
provenance/README source-path closure, with release/distribution requirements
still separate. Existing pending owner payloads and all 98 original paths remain
preserved. No Fold operation has been performed for this source/NOTICE slice yet.
