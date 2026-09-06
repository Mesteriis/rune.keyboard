# Rune Smart Typing 0.3 — consolidated acceptance

Updated 2026-09-06. **IN PROGRESS; not a release approval.** The filename is the
deliverable requested by the original September 2 specification.

Original main: `b5400cbadadd29e8ee915a0fb33fb11ec5bebc79`.
Resumption source: `fd8872f63c0b232ad871f27804b6355840b66bb1`.
Version remains **0.2.0**. Final tested/merged SHA and release APK identity are
not yet available. Pinned upstream llama.cpp remains
`36b10154383b60eb15baac2c7a40d2a5f784faa7`; cancellation patches apply to build
copies and do not change the gitlink.

## Implementation and quality

| Plan slice | Current evidence | Remaining acceptance |
| --- | --- | --- |
| 1 Evaluation | Frozen prepared and product corpora, scorers, numeric caches and per-language reports exist | Historical failures stay immutable; final current-source reproduction remains open |
| 2 Native scoring | Bounded numeric API, tokenizer cancellation, exception guards, exact scalar-oracle checks | Final-head native/Android verification |
| 3 Private process | Production Binder worker, preparation, cancellation, CPU duty and idle unload verified on Fold | Complete editor/process-death matrix and energy |
| 4 Composition | Owned RAM context, invalidation, full-word Backspace reopening, no replay/readback | Physical folding transition and full editor matrix |
| 5 Strip and Undo | Stable keys, explicit Original and single owned correction transaction | Complete final-head physical/accessibility matrix |
| 6 Lexicons | Pinned/licensed RU/EN/ES assets, 3-format/API26 comparison, bounded exact top-N and reproduction receipts | Final product qualification; deterministic-only automatic spelling is unqualified |
| 7 Model ranking | Frozen product point-95 evidence; actual Fold Space correction and immediate Undo | Current-source replay receipt, rapid-typing coverage |
| 8 Mechanical punctuation | Pure exclusions/Undo plus real Binder positive scenarios; API26 numeric/version/hostname exclusions PASS | Full real-editor coverage |
| 9 Contextual punctuation | Bounded explicit suggestions; total-score correction has JVM regressions and API26 controller-to-editor tests | New policy requires freeze and unseen holdout; physical strip tap remains separate |
| 10 Settings/release | Schema3, independent preferences, content-free traces, local gates | Full matrices, current CI, complete reports, final version and main integration |

The user changed the spelling release target from99% to **95% point precision**.
This is a corpus precision policy, not a per-word correctness probability. The
unchanged frozen product model-assisted holdout records EN293/304=96.38%,
RU342/359=95.26% and ES396/408=97.06%; false changes are0/1000,1/1000,0/1000.
All candidate sets retained Original. Counts, coverage, candidate recall and
Wilson95% intervals remain in the [original product report](2026-09-03-smart-typing-0.3-product-spelling-holdout.md)
and [later point-95 policy acceptance](2026-09-04-smart-typing-0.3-autoreplace-95.md).
Its old missing `corpusDirectory` receipt and changed source identities prevent
replay by the current strict verifier; do not relabel that rejection as PASS.

The deterministic branch does not qualify across all languages even at95%:
EN254 and ES265 automatic decisions miss the300-volume gate; RU313/335=93.43%
misses precision. Consequently ordinary deterministic spelling stays suggestions.
Local canonical-case and mechanical rules retain their separate behavior.

Contextual punctuation's [existing holdout](2026-09-03-smart-typing-0.3-contextual-quality.md)
is not accepted. A new calibration-only diagnostic compares total log probability
with token averages and rival margins. The development patch now compares sums,
requires an advantage over Original greater than0.5 and over the next punctuation
candidate of at least4.0, and preserves explicit selection and ownership guards.
The diagnostic does not evaluate held-out decisions or qualify this policy;
a freeze and new unseen holdout remain required. See
`tools/eval/smart-typing-0.3/pipeline/results/2026-09-06-contextual-calibration-diagnostic/`.

The current evaluator now follows that production policy. Its version 2 receipts
bind source/rule/parameters and reject old receipts or orphan score caches.
Actual Kotlin/Python parity passed 79 synthetic cases; all 51 Python pipeline
tests and prescribed local gates passed. This tooling evidence is separate from
fresh model quality: `tools/eval/smart-typing-0.3/pipeline/results/2026-09-06-contextual-tooling/`.

## Required editor matrix

The latest archived API26/API37 runs contain52 tests in five selected classes;
they do **not** establish the complete application suite below. A test name is
coverage evidence, not proof of a final-head run. The amended Space policy also
allows one still-owned spelling result for250ms after ordinary Space; a blanket
“all results after Space are ignored” assertion is superseded by that contract.

| # | Required behavior | Existing coverage / outstanding evidence |
| --- | --- | --- |
| 1 | Display current composing word | SmartTypingComposingInstrumentedTest; inner Fold PASS |
| 2 | Boundary finishes word | Same; inner Fold PASS |
| 3 | Tap replaces owned word | LiveCandidatesInstrumentedTest; inner Fold PASS |
| 4 | High-confidence Space correction | Optional installed-model typing test; inner Fold PASS; ordinary-CI editor path still needed |
| 5 | First Backspace restores Original | Installed-model and canonical-case editor tests; inner Fold PASS |
| 6 | Second Backspace deletes grapheme | Composing/editor tests; include explicit correction-to-second-delete final receipt |
| 7 | External cursor invalidation | Composing tests; inner Fold PASS |
| 8 | Selection replacement | Composing tests; inner Fold PASS |
| 9 | Multiline Enter | EditorActionInstrumentedTest; final full matrix pending |
| 10 | SEND action | EditorActionInstrumentedTest; final full matrix pending |
| 11 | Language swipe preserves text | Composing tests; inner Fold PASS |
| 12 | Cursor mode clears composition before movement | Composing stationary-hold test; inner Fold PASS |
| 13 | Fold/config restart never replays | Restart/detach tests PASS on inner; actual folding transition still pending |
| 14 | Password: no strip/composition/model/readback/content logs | Privacy/live fixtures; aggregate sensitive counters and final matrix pending |
| 15 | NO_PERSONALIZED_LEARNING protections | Composing sensitive counters; inner Fold PASS; aggregate model-request proof pending |
| 16 | Email/URL/number/phone/date-time never corrected | Layout tests exist; correction-specific editor assertions pending |
| 17 | TYPE_NULL raw behavior | QA field exists; direct raw-event instrumentation pending |
| 18 | Model kill preserves text and fallback | Client lifecycle tests exist; combined live-editor kill proof pending |
| 19 | Late results after Space |250ms owned grace plus invalidation unit/Binder-client tests; complete editor proof pending |
| 20 | Late result after editor change | Client/controller tests; final editor matrix pending |
| 21 | Late result after language change | Client/controller tests; final editor matrix pending |
| 22 | Candidate update preserves key instances | Live/settings touch tests; inner Fold PASS |
| 23 | Rapid typing loses/duplicates no characters | Instrumented rapid-touch input and frame/event measurements pending |
| 24 | Held Backspace inside/outside composition | Existing editor coverage; complete final receipt pending |
| 25 | Mechanical URL/version/decimal exclusions | API26 decimal/version/hostname editor cases PASS; URL/email/time full editor cases still separate |
| 26 | Contextual tap changes only allowed segment | API26 controller-to-editor Binder3/3 PASS; physical strip tap path still separate |

## Physical and local receipts

The [September5 Fold report](2026-09-05-smart-typing-0.3-fold-qualified.md) records
release-native2/4/8-candidate timing, cancellation/recovery, load, RSS/PSS,
production service CPU duty and idle unload. Four-candidate p95 is
EN74.848/RU260.200/ES172.555ms; RU can miss the250ms after-Space grace. First
service reply746ms includes loading; the340ms weight-load measurement followed
digest verification and does not measure cold filesystem storage. USB charging
measurements do not qualify unplugged battery use.

September6 fresh resumption JVM: **691/691**, zero failures/errors/skips.
Prescribed lint, debug/release/profile, privacy, dependency and native-symbol
gates: **PASS**. Local logs are in `build/smart-typing-0.3/resume-2026-09-06-*.log`.

After the contextual policy correction, the full JVM rerun passed **707/707**
with zero failures/errors/skips. Scoped regressions failed against the old
arithmetic before passing with the correction. These source-development tests
do not establish real-model quality or the installed APK's behavior. The
post-change prescribed lint/build/privacy/dependency/native-symbol gates and
Android-test APK build also passed (265 tasks).

Physical inner Fold SM-F966B/API36, real `OPENED` state with no override,
1968×2184: composing15 + mechanical3 = **18/18 PASS**,137.854s. Subsequent
live4/settings6/installed-model1 = **10/11 PASS**,144.473s. The failure is the
settings fixture's unconditional “model unavailable” expectation on a Ready
installation. Real-model Space correction/Undo passed. Test corrections and
their subsequent receipts must retain this initial failure.

The corrected settings test and three new contextual Binder editor tests compiled and passed source review. Phone installation of the new test APK failed with `INSTALL_FAILED_UPDATE_INCOMPATIBLE`; the current host debug key differs. No uninstall occurred. A local-only verified model/settings backup is prepared; user confirmation to reinstall/restore has been requested.

API26 was installed locally. The first contextual/settings run passed6/9; its
three setup failures were an invalid lifetime-zero expectation for the resident
IME's existing NORMAL caps-mode lookup. A diagnostic named that counter, and
the corrected tests retain zero payload reads and assert no new calls of any
read API during no-edit scoring actions. Contextual3/settings6/mechanical4 then
passed **13/13**. Full application instrumentation is running separately. The
first API37 image download failed reading its ZIP; a controlled retry is in
progress. Evidence:
`tools/qa/smart-typing-0.3/results/2026-09-06-binder-followup/`.

Both installed APK hashes were checked against the tested local APKs before
these runs. Evidence: `tools/qa/smart-typing-0.3/results/2026-09-06-fold-inner/`.
These are functional probes, not rapid typing, real third-party editors, a
physical fold transition, cold-storage measurements or unplugged energy.

## Named acceptance examples and release decision

Final installed-build examples still require a consolidated per-case record:
RU `автокрекция`, `арфография`, `сообшение`, correct `причём`, `kubectl`, `AIGate`,
mixed RU/EN, valid-word preservation and punctuation; EN `teh`, `recieve`,
`adress`, hostname/camelCase preservation and punctuation; ES `mensage`,
`correcion`, ambiguous accents, ñ, mixed EN/ES and punctuation. Existing corpus
membership or a nearby-word test is not a claim that every named input is
automatically replaced by the installed build. Record actual outcomes and false
positives against the frozen policy, including abstention.

Experimental HF delivery of the exact396704416-byte GGUF is already configured
at immutable revision `c057e37928624d3c3c4bd526d3515f7202395920`; its digest is
`7a97111c917e19117207428971fa1c2583f2d9c2a07a6fda5b6f198b707dd9c4`.
See [publication provenance](2026-09-05-rune-text-v1-hugging-face.md).

| Release gate | Current status |
| --- | --- |
| Fresh JVM and prescribed local gates | PASS at resumption source |
| API26 complete final matrix | OPEN; previous scoped52/52 PASS |
| API37 complete final matrix/stability | OPEN; previous first50/52 FAIL and unchanged repeat52/52 PASS |
| Fold inner named functional probes | PARTIAL PASS; initial settings fixture failure retained |
| Fold transitions/real editors/rapid typing/energy | OPEN |
| Current-source full quality qualification | OPEN; contextual quality not accepted |
| Current external CI | No PR-triggered runs returned for fd8872f by the GitHub connector; remote main remains b5400cb; not a full workflow inventory |
| Model final release / version0.3.0 / main merge | BLOCKED by remaining gates |
