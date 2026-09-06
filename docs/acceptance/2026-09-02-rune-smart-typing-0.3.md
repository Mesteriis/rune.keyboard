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
| 1 Evaluation | Frozen prepared and product corpora; current controller reproduction completed5956 responses and24000 observations; state-based Original annotation reviewed | Contextual controller attribution; historical failures stay immutable |
| 2 Native scoring | Fresh current-source host7/7 PASS, including exact model oracle/equivalence/abort; ordinary Android JNI6/6 on each API with source/APK continuity | Physical runtime/energy acceptance is separate |
| 3 Private process | Production Binder worker, preparation, cancellation, CPU duty and idle unload verified on Fold | Complete editor/process-death matrix and energy |
| 4 Composition | Owned RAM context, invalidation, full-word Backspace reopening, no replay/readback | Physical folding transition and full editor matrix |
| 5 Strip and Undo | Stable keys, explicit Original and single owned correction transaction | Complete final-head physical/accessibility matrix |
| 6 Lexicons | Pinned/licensed RU/EN/ES assets, 3-format/API26 comparison, bounded exact top-N and reproduction receipts | Final product qualification; deterministic-only automatic spelling is unqualified |
| 7 Model ranking | Current controller holdout EN293/304, RU341/358, ES396/408; reviewed Original annotation; actual Fold Space correction and immediate Undo | Physical rapid-typing coverage |
| 8 Mechanical punctuation | Pure exclusions/Undo plus real Binder positive scenarios; API26 numeric/version/hostname exclusions PASS | Full real-editor coverage |
| 9 Contextual punctuation | Current fixed policy has source-bound v5 calibration/freeze/holdout and per-language reports; actual Kotlin parity79/79 | Source agreement is not semantic precision; physical strip tap remains separate |
| 10 Settings/release | Schema3, independent preferences, content-free traces, local gates | Full matrices, current CI, complete reports, final version and main integration |

The user changed the spelling release target from99% to **95% point precision**.
This is a corpus precision policy, not a per-word correctness probability. The
historical September3 product model-assisted holdout records EN293/304=96.38%,
RU342/359=95.26% and ES396/408=97.06%; false changes are0/1000,1/1000,0/1000.
All candidate sets retained Original. Counts, coverage, candidate recall and
Wilson95% intervals remain in the [original product report](2026-09-03-smart-typing-0.3-product-spelling-holdout.md)
and [later point-95 policy acceptance](2026-09-04-smart-typing-0.3-autoreplace-95.md).
Its old missing `corpusDirectory` receipt and changed source identities prevent
replay by the current strict verifier; do not relabel that rejection as PASS.
The September 6 compatibility diagnostic freshly reproduced all ordinary generator
outputs (6000 rows per split) and all 2940 native responses: identical numeric
scores/counts and the same 14 refusals, maximum sum delta 0. It leaves the strict
verifier intact and does not qualify canonical-case or current controller
eligibility. Evidence: `tools/eval/smart-typing-0.3/pipeline/results/2026-09-06-current-native-compatibility/`.

Current actual-controller replay found additional casing and mechanical edits absent
from that ordinary-score report. Commit `93b92f6` now requires unambiguous and
consistent casing evidence across the routed dictionaries. It removed 34 incorrect
canonical changes on correct/protected rows, while retaining automatic
`Paris`, `London`, `Москва` and exact Undo. The then-current full final-text replay
was EN293/305, RU341/359=94.9861%, ES396/410; RU remained below95%.
All initial failures, row-level outputs and exact source/model-response bindings
are preserved in `tools/eval/smart-typing-0.3/pipeline/results/2026-09-06-canonical-safety/`.
This is development evidence on already revealed data, not unseen qualification.
Commit `55195f2` subsequently protects the standalone dot argument of bounded known
commands. The new full-text replay is EN293/304=96.38%, RU341/358=95.25%,
ES396/409=96.82%, with correct/protected false changes0/1000,1/1000,0/1000.
Exactly the three command-dot outcomes changed; all1071 automatic boundary edits
have exact Undo. The ES canonical-case error and RU spelling false change remain
visible. See `tools/eval/smart-typing-0.3/pipeline/results/2026-09-06-command-dot-safety/`.
This is still revealed-data development evidence; historical failures remain intact.

The final fixed-policy reproduction is now complete and committed in `1a5826e`.
It includes the current controller payloads, including33 fragment requests that
the older command-dot run correctly refused. All2983 calibration and2973 holdout
requests have exact retained responses;9/14 native errors remain explicit, with
zero retries, missing responses or payload refusals. All24000 observations across
both splits and ready/unavailable modes are retained. The current holdout ordinary
spelling counts are EN293/304=96.3816%, RU341/358=95.2514%, ES396/408=97.0588%.
Integer point95, volume300, aggregate false changes0/1/0 per1000 and exact immediate
restoration6000/6000 pass. All5703 owned candidate sets contain Original;297
no-word states preserve text and have no stale candidates. The frozen stricter
all-row Original statistic remains FAIL, alongside a separately reviewed
state-based contract annotation that accounts for every row. Detailed counts,
coverage, Wilson intervals, unchanged coefficients and exact source/cache hashes
are in `tools/eval/smart-typing-0.3/results/2026-09-06-final-controller-replay/`.
This is reproduction on revealed rows, not unseen generalization. No product rule,
corpus or threshold was changed to resolve the empty-state reporting distinction.
Changing model/coefficients or selecting another policy from revealed outcomes
would require a new protocol.

The exact historical prepared selector remains FAIL under the revised point95
target: RU162/172, EN7/7, ES239/243, all below300; RU also misses precision.
The separate unchanged-decision comparison is in
`tools/eval/smart-typing-0.3/results/2026-09-06-prepared-fixed-point95/`.
It preserves original report/config/cache identities and performs no calibration
or model call. The later authorized combined product branch has separate gates;
neither its authorization nor this comparison establishes a prepared PASS.

The deterministic branch does not qualify across all languages even at95%:
EN254 and ES265 automatic decisions miss the300-volume gate; RU313/335=93.43%
misses precision. Consequently ordinary deterministic spelling stays suggestions.
Local canonical-case and mechanical rules retain their separate behavior.

Contextual punctuation's [existing holdout](2026-09-03-smart-typing-0.3-contextual-quality.md)
is not accepted. A new calibration-only diagnostic compares total log probability
with token averages and rival margins. The development patch now compares sums,
requires an advantage over Original greater than0.5 and over the next punctuation
candidate of at least4.0, and preserves explicit selection and ownership guards.
The diagnostic itself does not evaluate held-out decisions or qualify this policy. See
`tools/eval/smart-typing-0.3/pipeline/results/2026-09-06-contextual-calibration-diagnostic/`.

The current evaluator now follows that production policy. Its version 2 receipts
bind source/rule/parameters and reject old receipts or orphan score caches.
Actual Kotlin/Python parity passed 79 synthetic cases; all 51 Python pipeline
tests and prescribed local gates passed. This tooling evidence is separate from
fresh model quality: `tools/eval/smart-typing-0.3/pipeline/results/2026-09-06-contextual-tooling/`.

The separately reviewed v5 source-observation corpus and adapter are committed in
`03b06b9`. Before real scoring, a protocol receipt bound all corpus/source/backend
and policy hashes. Complete calibration preceded configuration freeze; the fresh
holdout followed it without parameter changes. Of600 holdout rows,517 were scored
and83 production exclusions retained; errors and missing responses were zero.
EN/RU/ES produced38/37/27 suggestions, with37/36/26 matching source punctuation,
and0/50 insertions at observed spaces in each language. Full-source agreement is
87/200,86/200,76/200; abstention is included. All per-boundary counts, Wilson95%
row-descriptive intervals, decisions and attribution are in
`tools/eval/smart-typing-0.3/pipeline/results/2026-09-06-contextual-v5/`.
These are source-boundary observations, not unique semantic labels or an automatic
punctuation quality gate. Balanced Wikipedia strata do not establish chat precision;
no source question/exclamation/semicolon strata or unknown-pretraining exclusion is
claimed. Corpus20/20, current adapter35/35 and actual policy parity79/79 PASS.
Those counts come from the actual contextual engine. Full-controller valid-word,
spelling-precedence and canonical eligibility still need attribution over all1200
rows before reporting displayed-suggestion coverage. No numeric semantic-precision
floor was specified for suggestions; do not invent one or label source agreement
as semantic accuracy.

## Required editor matrix

The earlier134-test full run passed API26 with131 PASS, three optional-model
assumptions and no failures. API37 had130 PASS, three assumptions and one focus
failure before a custom editor action. Both new TYPE_NULL and75-character rapid
input tests passed. The prior131-test failures remain archived separately.
A dedicated reproduction showed ScrollView intercepting the following focus tap;
the default debug QA surface now disables fling and overscroll stretch. Final
trace-free API37 navigation/action scope passed4/4, including all six action IDs,
offscreen focus and focused-editor restoration. The subsequent complete139-test runs
finished with136 PASS, three optional-model assumptions and zero failures on each
API (26:764.511s,37:720.627s); exact source/APK receipts and changed-source
snapshots are in `2026-09-06-editor-matrix-139`.
The ordinary-CI live fake model/editor Binder matrix passed3/3 on both APIs: numeric
Original control, model Space correction/Undo, stale Original-tap reply rejection,
and actual remote process death with unchanged editor state and no replay.
This uses the resident controller, production coordinators and real bound client;
fixed lexical input/readiness and numeric model responses are explicit test seams,
not production factory, packaged lexicon, JNI or model quality qualification.

The reviewed diagnostic build subsequently completes152 cases: API37 has149 PASS,
three optional-model assumptions and no failures; API26 has148 PASS, three assumptions
and one preview-target readiness failure. All five strengthened diagnostic cases
pass on both APIs. A reviewed test-only wait for the actual b/B target passes the
changed case on both; the full API26 rerun subsequently passes149+3 assumptions
in1171.451s. API37's full152
uses the preceding test APK, with the changed case verified separately. Exact
receipts, original failures, final focused JVM147/147 and actual complete local
gates are archived in `2026-09-06-diagnostics-reviewed-matrix`.

The amended Space policy also
allows one still-owned spelling result for250ms after ordinary Space; a blanket
“all results after Space are ignored” assertion is superseded by that contract.

| # | Required behavior | Existing coverage / outstanding evidence |
| --- | --- | --- |
| 1 | Display current composing word | SmartTypingComposingInstrumentedTest; inner Fold PASS |
| 2 | Boundary finishes word | Same; inner Fold PASS |
| 3 | Tap replaces owned word | LiveCandidatesInstrumentedTest; inner Fold PASS |
| 4 | High-confidence Space correction | LiveFakeModelBinder original control and correction pass both full152 runs through actual model/editor Binder; exact-GGUF phone evidence is separate |
| 5 | First Backspace restores Original | Installed-model and canonical-case editor tests; inner Fold PASS |
| 6 | Second Backspace deletes grapheme | New spelling/canonical Undo→next Delete delta2/2 PASS on each API, exact spans/commands/no readback; mechanical two-Backspace and separate complex-grapheme editor tests also pass |
| 7 | External cursor invalidation | Composing tests; inner Fold PASS |
| 8 | Selection replacement | Composing tests; inner Fold PASS |
| 9 | Multiline Enter | EditorActionInstrumentedTest.multilineEnterCommitsANewlineInsteadOfSending passes both full152 runs with exact a/newline/b text |
| 10 | SEND action | Standard/custom action test passes both full152 runs for SEND/SEARCH/GO/NEXT/DONE/custom IDs; repaired offscreen custom action also passes |
| 11 | Language swipe preserves text | Composing tests; inner Fold PASS |
| 12 | Cursor mode clears composition before movement | Composing stationary-hold test; inner Fold PASS |
| 13 | Fold/config restart never replays | Restart/detach tests PASS on inner; actual folding transition still pending |
| 14 | Password: no strip/composition/model/readback/content logs | Positive-controlled NonNormalEditor password test passes both full152 runs with inactive owners and unchanged binding/request/engine/reply activity; diagnostics files unchanged; popup/canary checks retain sampled/window limits |
| 15 | NO_PERSONALIZED_LEARNING protections | Private-flag NonNormalEditor and composing tests pass both full152 runs with zero reads/composition/model activity; diagnostics streams unchanged |
| 16 | Email/URL/number/phone/date-time never corrected | Five explicit NonNormalEditor mode tests pass both full152 runs, with normal correction positive controls, exact prefixes and zero Smart Typing/read activity |
| 17 | TYPE_NULL raw behavior | New raw fixture passes API26/API37: balanced down/up, exact Delete, no composing/strip/readback |
| 18 | Model kill preserves text and fallback | Live fake real-Binder process death/reconnect test passes both full152 runs; unchanged text/keys, no replay, subsequent typing works |
| 19 | Late results after Space | Actual expired reply refusal PASS both APIs. Allowed late reply also PASS both APIs: observed Original+Space before release, certified ownership and real callback elapsed<250ms, exact correction commands and immediate Undo. Next-text invalidation also PASS both APIs: actual next key and exact old remote release before250ms, unchanged original word, current selected Original, no stale correction writes |
| 20 | Late result after editor change | Live switch to another real QA editor/task/session PASS both APIs: exact old request released, new text/span/caret and candidate contents/IDs/selection unchanged, returning old text has no payload writes; no editor payload reads. Same-Activity field variant and already-dispatched callback are not claimed |
| 21 | Late result after language change | Held exact remote numeric reply across actual Russian language swipe PASS both APIs: old English text/span preserved/finished, unchanged editor commands and strip after release, no stale accepted callback, fresh Russian typing works |
| 22 | Candidate update preserves key instances | Live/settings touch tests; inner Fold PASS |
| 23 | Rapid typing loses/duplicates no characters |75-character bounded touch burst and exact deletion pass API26/API37; physical frame/event/energy measurements remain |
| 24 | Held Backspace inside/outside composition | Focused4/4 PASS on each API: positive repeated deletion on unowned seeded text with cancel/detach; exact owned prefix/span/caret and command counts with release/cancel; one hold consumes model Undo then deletes normally; no payload reads in owned paths. Bounded correctness, not physical performance |
| 25 | Mechanical URL/version/decimal exclusions | Numeric/version/hostname and URL/email/time public fixtures pass both full152 runs, with same-session cleanup/Undo controls; reviewed number-row navigation delta separately passes both APIs/Fold |
| 26 | Contextual tap changes only allowed segment | Independent controller→real editor Binder3/3 passes both full152 runs; actual resident contextual strip tap path remains missing |

Exact test names, terminal log anchors and source/APK deltas are in the
`editor-matrix-audit.md` and `review.md` files under
`tools/qa/smart-typing-0.3/results/2026-09-06-undo-second-delete/`.
The audit's row6 cutoff precedes the separately verified two-test delta. These
ordinary-CI proofs do not substitute for physical Fold or arbitrary editor checks.

Row24's subsequent four-test delta, exact sources/APK identities and complete logs
are in `tools/qa/smart-typing-0.3/results/2026-09-06-held-delete/`.
Rows19/21's live late-reply deltas, initial test-expectation failure and corrected
focused runs are in `tools/qa/smart-typing-0.3/results/2026-09-06-live-late-replies/`.
Row20's two-real-editor proof and preserved fixture failures are in
`tools/qa/smart-typing-0.3/results/2026-09-06-live-editor-switch/`.
Row19's within-grace positive and API26 observer diagnosis are in
`tools/qa/smart-typing-0.3/results/2026-09-06-live-space-grace/`.
Its subsequent positive-plus-next-text pair passes2/2 on each API; exact source/APK
identities and logs are in `tools/qa/smart-typing-0.3/results/2026-09-06-live-space-next-text/`.

## Physical and local receipts

2026-09-06 update: the user took the phone and explicitly requested continued
emulator work. Remaining physical Fold transition, current real-editor/rapid-input
and performance checks are BLOCKED on device availability. The prepared cover
composition is historical setup only and must not be reused as a valid transition
baseline after the user's intervening phone use. API26/API37 work continues; no
physical completion or release qualification is inferred from those emulator runs.

Current-source native correctness at `1a5826e`: fresh Release configure/build and
all7 CTest cases PASS (8.24s), including the three exact-GGUF cases. Token output
matches the independently frozen pristine tokenizer digest. All eight real abort
stages, inside-loop checkpoints, recovery and per-call isolation pass. Native
sources remain unchanged since `c0b0280`; the current app APK matches the complete
API26/API37 matrices byte-for-byte. Source/compiler/patch/binary receipts are in
`tools/test-native-scoring/results/2026-09-06-final-native/`. This establishes host
correctness and continuity, not new Android exact-model or physical performance
measurements.

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

The corrected settings test and three new contextual Binder editor tests compiled and passed source review. Phone installation initially failed with `INSTALL_FAILED_UPDATE_INCOMPATIBLE` because the host debug key differed. After the user's explicit permission to uninstall/reinstall, the reviewed app and test APK were installed and all nine model/settings files restored and hash-verified from a local-only backup. The initial signature failure remains historical evidence.

API26 was installed locally. The first contextual/settings run passed6/9; its
three setup failures were an invalid lifetime-zero expectation for the resident
IME's existing NORMAL caps-mode lookup. A diagnostic named that counter, and
the corrected tests retain zero payload reads and assert no new calls of any
read API during no-edit scoring actions. Contextual3/settings6/mechanical4 then
passed **13/13**. Full API26 instrumentation subsequently passed128 of131 with
three optional-model assumptions and no failures; JNI6/6 passed. The first API37
image download failed reading its ZIP; the controlled retry installed revision6.
Its full suite passed127 of131 with three assumptions and one failed popup
positive control; unchanged isolated privacy2/2 and JNI6/6 passed afterward.
The original A-key/150ms rendering cause remains unproven. Later numeric and
PixelCopy probes retained both failures and passes. The replacement test uses a
no-alternate B key, frozen touch/crop geometry, a current-setting and actual-view
assertion, and a full nominal1s sampled window for normal-enabled, normal-disabled
and password-enabled modes. Isolated API37 passed2/2; the complete suite for this
new test subsequently completed in the152-case matrices described above. It verifies eventual sampled visual policy, not latency
or continuous absence. All earlier failure receipts remain unchanged.
Evidence:
`tools/qa/smart-typing-0.3/results/2026-09-06-binder-followup/`.
Full logs/APK attestations: `2026-09-06-api26-full/` and `2026-09-06-api37-full/`
under the same results parent.

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
| Fresh JVM and prescribed local gates | Current1a5826e: mandatory postcommit whole JVM743/743 PASS, zero failures/errors/skips; prescribed240-task gates PASS. Earlier diagnostics Python32/32 and complete emulator matrices retained with exact receipts |
| API26 complete final matrix | Complete rerun152:149 PASS +3 assumptions, zero failures; all five diagnostic cases PASS. Ordinary JNI6/6 PASS. Initial preview and overbroad missing-model command failures retained |
| API37 complete final matrix/stability | Full152:149 PASS +3 assumptions, zero failures; subsequent test-only preview case1/1 and JNI6/6 PASS; prior failures retained |
| Fold inner named functional probes | PARTIAL PASS; initial settings fixture failure retained |
| Fold transitions/real editors/rapid typing/energy | OPEN. Earlier cover13:6 PASS,5 diagnostic assumptions preserving logs,2 initial failures.75-touch exact text PASS. Exact-model Binder1/1 PASS (899ms first/166ms warm). Read-only admission observation shows model correction/Undo PASS; initial timing miss unresolved. Subsequent cover27:26 PASS + number-row navigation failure; unchanged isolated PASS and class reproduction FAIL retained. Reviewed quarter-height navigation27c3df2 passes mechanical5/5 on Fold and affected case1/1 on each API. Actual unfold is prepared with owned `тест` span0..4, awaiting physical user action |
| Current-source full quality qualification | Spelling reproduction and state-based Original annotation PASS within the fixed revealed-data scope; exact observations and frozen all-row FAIL retained in1a5826e. Full-controller contextual attribution remains OPEN. v5 source agreement retains its semantic limits |
| Current external CI | No PR-triggered runs returned for fd8872f by the GitHub connector; remote main remains b5400cb; not a full workflow inventory |
| Model final release / version0.3.0 / main merge | BLOCKED by remaining gates |
