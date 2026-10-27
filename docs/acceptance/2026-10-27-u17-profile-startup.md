# U17 — verified packed-asset startup on Fold and API 26

U17's requested scope is verified locally. The three earlier receipts cover the
single digest/no-clone fallback, strict validation and packaged lookup, and
disabled-RU/later-enable lifecycle. This final slice makes packaged startup
actually lazy, measures both requested targets, renews replay bindings and
updates the owner's Fold. The full 31-card review remains active.

The first profile probe exposed a remaining startup body walk: reading the
anchor of every block touched almost all mapped asset pages. Packaged headers
now inspect only magic, counts, offsets, exact body end and a minimum byte length
for every block. They leave anchor records for bounded lookup. Strict validate
still checks identity and every record, including malformed/resealed anchors;
lookup checks each accessed anchor/record before decoding. Two added tests cover
lazy publication and refusal on access. The APK/bitrot trust tradeoff remains
documented in ARCHITECTURE; it has not been turned into a full runtime hash claim.

## Measured profile series

Baseline: dcba8ac, before every U17 production change, plus only the four matching
load/ready trace markers in the preserved baseline patch. Candidate: 49740ae plus
the exact three lazy-header reader changes bound in the adjacent JSON. Both
profile APKs use release R8/resource shrinking, debug signing, separate profile
ID and debuggable=false; run-as refusal was verified. All 69 assets and every
packaged native library are identical between the APKs.
The task-owned profile package has no downloaded GGUF or imported personal
profile; the owner's existing model and personal state stay in the main package.

The series has five fresh IME service processes for each version/language
condition on physical Fold/API 37 and the owned ARM64 API 26 emulator with
2,048 MiB configured RAM. All 40 predefined samples are included. The public
empty QA field is in a separate process. Time origin is the framework's Start
proc marker, observed exactly once per sample. PSS is sampled approximately
five seconds after IME selection. Filesystem cache is left intact after
installation/configuration and preceding runs; speed compilation is requested
successfully for each deployed variant.

Medians:

| Device | RU enabled | Version | Dictionary ready, ms | Context ready, ms | PSS at ~5s, MiB |
|---|---|---|---:|---:|---:|
| Fold | yes | baseline | 113.4 | 547.2 | 341.30 |
| Fold | no | baseline | 105.3 | 550.9 | 341.05 |
| Fold | yes | candidate | 61.6 | 67.7 | 33.49 |
| Fold | no | candidate | deferred | deferred | 29.54 |
| API 26 | yes | baseline | 73.1 | 414.8 | 101.05 |
| API 26 | no | baseline | 66.1 | 417.5 | 101.73 |
| API 26 | yes | candidate | 27.5 | 35.1 | 18.89 |
| API 26 | no | candidate | deferred | deferred | 14.93 |

Candidate EN-only has no resource load/ready markers in all ten samples; the
baseline loads the RU resources even in that condition. Fold records native
Perfetto, API 26 records atrace imported by the same Perfetto v58.2 processor.
All 40 traces have zero nonzero error/data_loss importer statistics. Raw traces
stay private under build/perf. The adjacent JSON contains all sample values,
medians/ranges and hashes. The reproducible capture/analysis conditions and
baseline patch are in docs/performance/2026-10-27-u17-protocol.md.

These five-sample medians describe repeated process-cold resource startup in
these conditions. PSS includes resident free/dirty heap pages, not only live
objects. Storage-cold startup, population percentiles, keypress/frame budgets and
battery effects have separate acceptance scopes.

## Regression and deployment

- Final app JVM suite: 1,277 tests, zero failures/errors/skips. Debug lint,
  profile assembly/privacy gates and default owner debug/test builds pass.
- Two fresh ordinary product runs (strict and packaged after full preflight),
  12,000 rows each, match the previous bound packaged run on every projected
  field except the two host timing fields. Projection SHA-256:
  33c3a96fed5b3322601f6b7a0307e3a4b62bfbc9bc7650b82bf644a1afffd8a3.
  This renewal binds all 69 main assets before/after each run, including context,
  grammar, policies and joint/revision models, along with compilation sources,
  source manifest, toolchain manifest, compiler jars, Java executable and Android
  stub. Earlier helper receipts enumerated 18 assets; the Kotlin harness also
  checked frozen identities of the contextual inputs at use. This final receipt
  adds a complete explicit asset inventory. Existing EN/ES quality limitations
  and the ordinary replay's lack of native inference remain unchanged.
- Fold's main debug Rune was updated with the same certificate, no data clear or
  uninstall, a private pre-update backup and exact installed-APK byte verification.
  Version remains 0.4.2/code 8. New app SHA-256:
  14c5f9b1a3eb1aa32298750c0fa3c00c9a97f3618ec3087fdda70b9d7cf3408c.
  The unchanged native runtime identity is
  d48f6df2ed03cd11d3182abe453fb3a5bd126aea92f2bc06ab747b201f84565f.
- Four physical real-touch tests pass, 15 matched cases and no skips: fresh
  reviewed corrections at two paces with exact Undo; extra empty-field
  Backspaces/whole next word; correction preview/Undo followed by another word;
  rapid short-word correction at three paces. The cases cover 50/100/150 ms key
  intervals and assert zero calls to all six editor payload-read APIs.
- Keyboard preferences and three secure IME settings are restored; the inspected
  personal-store files and existing model-store checksums are unchanged. All four
  journal snapshots were retrieved privately. Public evidence includes only
  aggregate results and artifact hashes, not private store contents/checksums.
- Temporary Fold profile/host packages were removed before the owner update;
  the phone window was explicitly released to both coordinated chats. The API 26
  emulator was stopped and its task-owned AVD deleted. The baseline trace patch
  was saved, its two temporary source edits restored, and the clone is clean.
  All 13 original dirty tracked files and all 98 original untracked paths remain.

Earlier probes are retained separately: the initial settings-activity probe
motivated lazy anchors and is excluded from the paired IME series. One Fold
Perfetto probe failed on its output path permissions, then passed with the
standard perfetto-traces path, without root or permission changes. A read-only
package-inventory probe returned work-profile permission output; inventory was
repeated explicitly for user 0 and validated before profile installation.

No active or deferred device commands remain from this slice. This closes U17,
not the remaining review cards or whole-release qualification.
