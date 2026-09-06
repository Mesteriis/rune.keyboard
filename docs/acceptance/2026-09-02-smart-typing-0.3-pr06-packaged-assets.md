# Smart Typing 0.3 — PR6 packaged reader checkpoint

Date: 2026-09-02. Base: `00fd271a5a3c642a6b64b89113e34f214699431b`. Packaged dictionary compatibility is PASS on API26, API37 and physical USB Fold API36. Live spelling suggestions and overall PR6/0.3 acceptance remain incomplete; version stays 0.2.0.

## Packaged inputs

The APK includes 28 pinned files: nine orthographic/rank components, 14 original upstream notices and five provenance files. Total raw payload is 77,106,788 bytes; trie/length/rank components account for 76,930,596 bytes. Frequency ranks remain a separate CC-BY-SA component; ES notices and the other original licenses remain byte-identical. Hunspell, source archives, full source wordlists/frequencies and the model are not packaged by this slice. See `tools/lexicon/smart-typing-0.3/PACKAGED_LEXICONS.md` for the source/transformation identities.

Gradle performs no download or dictionary generation. The reviewed offline staging tool validates the complete allowlist and rejects path/symlink/output drift. Its five regression tests pass and are wired into ordinary CI; remote CI has not run. A macOS temp-alias fixture failure is preserved in the evidence, with a fixture-only canonicalization fix; production scope checks were not weakened.

All 28 asset hashes were independently checked inside debug/release/profile APKs. The nine mapped components use ZIP STORE; the compressed negative fixture is actually DEFLATED. Final APK sizes are debug 97,225,551 bytes, release 87,610,860 bytes, profile 87,614,992 bytes. These are whole APK sizes, not an incremental lexicon cost; the earlier asset-only comparison remains separate.

## Android compatibility defect and fix

Initial API26 passed, but API37 and Fold failed before the first dictionary became Ready. Numeric Fold evidence identified ASSET_RANGE: offset 19,591,892, asset length and asset-bounded channel size 4,358,176, whole APK FD size 97,172,842. The loader mixed an absolute APK offset with a region-relative channel size.

The reviewed fix owns a duplicated raw file descriptor and opens a whole-file channel. `PackedAssetMapping` retains its exact absolute range/overflow/declared-length checks. Full manifest, hash, structure and read-only validation remain unchanged; there is no extraction fallback. All descriptors close on success and failure, while read-only mappings remain readable after closure. A tiny actual Android fixture verifies offset 2/length 3, five invalid ranges, read-only write rejection, owner lifetime and absence of leaked duplicate descriptors.

## Actual checks

| Gate | Result |
|---|---|
| Staging host regressions | PASS, 5 tests |
| Existing reader regression suite against adapter proposal | PASS, 15 tests |
| Final lint/build/debug/release/profile/privacy/dependency/native gates | PASS, 298 tasks / 48 executed |
| API26 final packaged reader | PASS, 1 test, 16.900 s |
| API37 final packaged reader | PASS, 1 test, 10.423 s |
| Physical Fold API36 final packaged reader | PASS, 1 test, 14.777 s |
| Full IME/Fold lifecycle, weighted quality, model duty and energy | Not closed by this checkpoint |
| New remote CI and model publication | Not performed |

Each final device test checks all three real dictionary mappings/validation, 24 fixed public exact references, original notices/provenance, missing/compressed/manifest negatives and the FD regression. Tests run off the main thread and use no editor. Fold was updated with install -r, without uninstall or data clearing; the prior APK backup remains private.

The Fold run measured first validation at approximately EN 1.028 s, ES 4.102 s and RU 9.454 s; its final whole-test-process PSS snapshot was 105,625 KiB. These are single debug functional-run observations from sequential loads in one process. Later memory snapshots may include earlier mappings and other process memory; reclamation and cache/thermal state are uncontrolled. They are not release latency distributions, isolated lexicon memory or energy qualification. They support keeping loading off main and allowing immediate Original while unavailable; they do not establish a numerical performance budget.

Content-free logs, exact APK hashes, numeric rows and source/proposal identities are preserved in `tools/lexicon/smart-typing-0.3/results/2026-09-02-packaged/`. Initial failures are retained. Required fresh post-commit JVM results must be recorded against the actual commit separately. Lazy lifetime ownership and the live candidate consumer remain subsequent integration work.
