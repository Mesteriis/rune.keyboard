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

Source `239e9f3` passes clean-checkout architecture, release/profile privacy and
APK footprint checks offline, with source-clean verification before/after and no
signing material copied. The source/NOTICE checkers and all 18 new tests also pass
in that clean tree on Python 3.12. Exact sizes and identities are in the receipt.

Actual pinned fdroidserver 2.4.5 `common.prepare_source` and `scanner.scan_source`
pass for this committed source with 29 exact data entries, 11 approved preparation
changes, seven source/qualification probes and zero scanner fatal findings.
The same two historical warnings remain (test calibration gzip and upstream
Keynote file). Scanner networking is blocked; installed SDK/signature cache are
reused. `build_local`, source export, independent build-server and final binary
scanner were not run by this checkpoint.

A real negative scanner probe adds the three experimental inventory-only ctx/gram
files to scanignore after approved deletions. It produces exactly three fatal
`Unused scanignore path` errors; removing those extra suppressions restores zero.
Historical 0.4.1/0.4.2 recipes remain pinned to their published commits. Current
review policy therefore retains exact false-positive suppressions and separately
inventories other data, rather than widening unused historical scanignore lists.

## Updated Fold package

Both coordinating chats yielded the device. An exact rollback APK, private owner
state and model inventory were saved before `adb install --user 0 -r`. Rune was
originally disabled as an IME, with another keyboard selected. The first Chrome
class passed its literal/no-suggestions case, then failed to activate Rune during
the second setup before typing. Recent package-exit records did not show a new
crash; this does not establish the root cause of the activation refusal.

After that instrumentation was terminal, a controlled repeat verified the already
installed app/test APK hashes and ran without reinstalling either. Both complete
native cases and a fresh 113-record independent DOM gate passed: five corrected
words, exact Undo, sixth-word correction and literal no-suggestions/Backspace.
The failed attempt remains in the receipt; no activation-race fix is claimed.

Installed APK SHA matches the committed-source build. Original preference values,
protected existing data, model hashes and IME settings (including original
subtype order and disabled Rune state) are restored/verified. Personal feedback
store snapshots remain unchanged within each final case. Diagnostic streams
rotated during QA; all original bytes are retained in the private pre-run archive,
not claimed unchanged on device. Test tabs are closed, both local servers stopped,
the exact task reverse removed, and both chats notified that Fold is free.

Q2 remains in progress for remaining guide/schema/experiment wording and the full
provenance/README source-path closure, with release/distribution requirements
still separate. Existing pending owner payloads and all 98 original paths remain
preserved. The bounded Fold update/Chrome evidence above does not close the
broader Q8 app/display matrix.
