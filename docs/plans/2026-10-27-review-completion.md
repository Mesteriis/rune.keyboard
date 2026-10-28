# Rune review completion map

Objective: close the complete owner-supplied 2026-10-27 review. The A/U/Q cards,
their acceptance checks and release/reproducibility work remain in scope.
This map records required proof. An item stays open until current evidence
covers the whole item; passing a narrower check closes only that check.

The owner-directed ADB Fold slice is recorded in
`docs/acceptance/2026-10-27-fold-adb-regression.md`: the updated debug build is
installed, four physical instrumentation tests pass with 15 public cases,
first-letter/Backspace and one next-word visible Undo path pass, and settings and
inspected personal stores are preserved. This does not close U1's other physical
source paths, U8/U9's broader device criteria, or release/model acceptance.

The diagnostics integration and remaining Android resource-refusal audit are
verified locally for Q3. The current fix `ff40adf` is installed on Fold through
ADB; `docs/acceptance/2026-10-28-q3-resource-fold-update.md` records four passing
physical tests / 15 exact scripted cases, retrieved journals, preserved settings
and inspected stores/model files, a successful clean-source release privacy/
footprint check, and cleanup of the task emulator. Q1's independent distribution
acceptance and the other open cards remain outstanding.

The incoming-review triage and its diagnostics-fixture repair are recorded in
`docs/acceptance/2026-10-27-review-triage.md`. Subsequent work has concentrated on
Q6. The latest Q6 receipt is
`docs/acceptance/2026-10-27-frozen-context-descendants-evidence.json`: 202 local
source-only tests pass, the lexical ledger has 121 entries, and global coverage
is explicitly incomplete. Four natural/side descendants now have verified public
captures and variant/filter lineage, adding 640 historical family exclusions.
A later source-preservation receipt,
`docs/acceptance/2026-10-27-late-training-source-closure-evidence.json`, binds
56 declared source paths across 17 late training/selection receipts (52 distinct
source payloads). All 208 source-only tests pass. This establishes direct source
identities, not transitive dependency coverage or model execution; ledger
coverage remains incomplete with 121 lexical entries.
Q9's source/JVM acceptance is verified in
`docs/acceptance/2026-10-27-q9-frozen-asset-identity.md` (nine new identity/mutation
tests; full app suite: 1,153 tests, no failures/errors/skips). U12's model and
controller acceptance is verified in
`docs/acceptance/2026-10-27-u12-personal-context-tail.md` (old-code reproduction,
six new regressions, all 1,159 app JVM tests and boundary/release privacy gates
pass). U13's night worker acceptance is verified in
`docs/acceptance/2026-10-27-u13-night-learning.md` (old APK retry, actual fixed
worker PROMOTING and durable rotation on a disposable emulator, 1,162 JVM tests,
UI/scheduler instrumentation, lint and release privacy/boundary gates pass).
U10 is verified in `docs/acceptance/2026-10-27-u10-editor-suggestion-flags.md`:
old-code regressions, 1,168 JVM tests, ten real IME/editor instrumentation cases,
release privacy/boundary/lint checks, and byte-identical 12,000-row replay
projections before/after (excluding host timings).
U7 is verified in `docs/acceptance/2026-10-27-u7-mode-and-undo-copy.md`: accurate
EN/RU source and Undo help, preserved 95% labels, four settings/setup/live-input/
accessibility instrumentation checks and debug lint/builds pass.
U1 has local acceptance in `docs/acceptance/2026-10-27-u1-visible-undo-local.md`:
schema-4 migration and next-word model/canonical Undo, 1,174 JVM tests, eight
emulator instrumentation scenarios and unchanged 12,012-row historical boundary/
Undo/admission replay. Physical Fold acceptance is still required; U1 stays open.
U2 is verified locally in `docs/acceptance/2026-10-27-u2-token-scoped-mechanics.md`: token-scoped prose protection, explicit command/marker line protection, exact refusal regressions, zero-read Undo, 1,181 JVM tests and byte-identical 12,000-row product replay with zero new aggregate false changes. Existing quality gate failures are disclosed in the receipt.
U3 is verified locally in `docs/acceptance/2026-10-27-u3-incognito.md`: explicit NPL incognito policy, zero editor reads, unchanged six personal-store roots and both diagnostic streams, 1,186 JVM tests, five emulator scenarios and byte-identical 12,000-row ordinary-product replay. Physical release acceptance remains separate.
U4 is verified locally in `docs/acceptance/2026-10-27-u4-reported-span-cleanup.md`: real old-IME word/space loss reproduced, non-text reported-span cleanup without adoption, reentry/refusal guards, 1,191 JVM tests, four emulator scenarios and byte-identical 12,000-row ordinary replay.
U5 is verified locally in `docs/acceptance/2026-10-27-u5-confirmed-words.md`: confirmed-word list/filter/removal, preserved pair/phrase evidence, capacity/error messages, 1,195 JVM tests, five guarded emulator scenarios including process restart and write-failure retry, and unchanged 12,000-row ordinary replay.
U6 has a verified registry/experiment-page slice in `docs/acceptance/2026-10-27-u6-settings-registry.md`: 18 shared feature definitions, atomic disable-all coverage, 1,199 JVM tests and eight emulator menu/tool scenarios plus a strengthened visible-target rerun. That first slice left dependencies, Switch, manual TalkBack and screenshot acceptance for the follow-up below.
The second U6 slice is in `docs/acceptance/2026-10-27-u6-switch-dependencies.md`: dependency states and RU badge, framework Switch with native node semantics, 1,202 JVM tests, 25 distinct emulator scenarios in bounded groups and updated Russian screenshots. Manual TalkBack is still required; U6 remains in progress.
U8 has selection-protocol evidence in `docs/acceptance/2026-10-27-u8-selection-prototype.md`: flags-only Shift fails to extend in the actual EditText, explicit Shift pairs extend/select across emoji and release, and three final emulator tests prove six zero payload-read counters. This is a test-only prototype; production editing behavior and the remaining U8 acceptance are not implemented.
U8 executor primitives are verified in `docs/acceptance/2026-10-27-u8-editor-commands.md`: six navigation directions and native context-menu delegation, refusal/exception cleanup, 1,208 JVM tests and six emulator scenarios. Public editing controls and ownership invalidation are not connected; the complete U8 acceptance remains outstanding.
U8 has a same-session ownership guard in `docs/acceptance/2026-10-27-u8-external-boundary-guard.md`: literal adjacent suffix until Rune whitespace, corrected caret-wait reentry, 1,218 JVM tests, eight emulator scenarios and unchanged fresh 12,000-row ordinary replay. Public UI/service wiring, app restarts and full compatibility/manual acceptance remain outstanding.
U8 public panel evidence is in `docs/acceptance/2026-10-27-u8-public-panel.md`: long-press entry, navigation/selection/native menu wiring, RAM restart guard, 1,226 JVM tests, 12 distinct emulator scenarios and unchanged 12,000-row ordinary replay. Actual multiline/preview/editor transitions, WebView/Compose/Fold and manual TalkBack remain outstanding; U8 stays open.
U8 multiline/preview follow-up is in `docs/acceptance/2026-10-27-u8-multiline-preview.md`: actual preview selection failure repaired by local view dispatch, vertical/newline selection and fresh Activity/editor behavior verified, 1,226 JVM tests and ten final emulator cases. WebView/Compose/Fold, manual TalkBack and broader lifecycle limitations remain; U8 is not closed.
U8 WebView evidence is in `docs/acceptance/2026-10-27-u8-webview.md`: offline textarea, real native menu/selection/vertical commands and post-paste correction recovery with six zero payload counters. 1,226 JVM tests and ten final emulator integration cases pass. Compose/Fold, manual TalkBack and broader lifecycle acceptance remain outstanding; U8 stays open.
U8 Compose evidence is in `docs/acceptance/2026-10-27-u8-compose.md`: independent pinned Compose QA APK, native commands/vertical selection and post-paste correction recovery with six zero payload counters. 1,226 JVM tests and thirteen final integration scenarios pass; Rune dependency graph remains unchanged. Physical Fold/manual TalkBack and broader lifecycle handling remain open; U8 is not closed.
U8 startup/lifecycle follow-up is in `docs/acceptance/2026-10-27-u8-lifecycle-start.md`: missing guard in an actual new service reproduced, numeric unknown-left startup fencing added, 1,230 JVM tests and 25 final emulator cases pass. Empty-field behavior remains; cold zero-offset/right-context, process death, Fold and TalkBack scope remain open. U8 is not closed.
U9 data foundation is in `docs/acceptance/2026-10-27-u9-emoji-catalog.md`: complete pinned Emoji/CLDR sources, reproducible 1,898-entry three-language catalog, license and preBuild/check gates. Fifteen source tests, 1,230 JVM tests and packaged-byte checks pass. The panel, glyph/recents/editor behavior and native/performance/device acceptance remain outstanding; U9 stays open.
Other cards remain open until their complete evidence is established.

## Acceptance inventory

| Card | Required behavior / acceptance evidence | State |
| --- | --- | --- |
| A1 | Narrow EN i→I rule; ES/abbreviation/identifier controls; suggestions, Undo and rejection behavior; fresh natural EN qualification. | Open |
| A2 | Word-bounded qualified prefix window, boundary-byte compatibility, hysteresis and empty-prefix suppression; native KV reuse; frozen replay parity; long-context qualification and Fold latency/deadline measurements. | Open |
| A3 | Fresh short-word holdout including lowercase names; zero new false changes and predefined useful gains; parity on other sources; Fold typo/name cases. | Open |
| A4 | Category-level period/colon controls with source/asset/corpus hashes and exit codes; Fold protected abbreviation, useful correction and exact Undo. | Open |
| U1 | Visible Undo default with compatible schema migration and explicit preference retention; model/canonical Undo survives next character without new refinement; replay and device coverage. | In progress: local acceptance verified; physical Fold pending |
| U2 | Token-scoped mechanical protection, exact refusal reasons and command/marker controls; Undo with zero reads; zero new correct/protected false changes. | Verified locally; receipt above |
| U3 | NPL incognito policy; composing/corrections with zero content reads; no mutation of six personal/diagnostic stores; JVM, instrumentation and replay. | Verified locally; receipt above |
| U4 | Reproduce shifted/changed composing ownership first; correct final text and finish behavior in simulator/qa_editor; preserve ownership safeguards; regression replay. | Verified locally; receipt above |
| U5 | Visible confirmed-word list and individual deletion; preserve pair rejections; phrase validation, capacity and restart persistence; privacy/user documentation. | Verified locally; receipt above |
| U6 | Settings registry, dependencies and Switch controls; registry/disable-list completeness; search/recreate/back, accessibility and updated screenshot/guide. | In progress: registry, dependencies, native Switch, screenshot and automated acceptance verified; manual TalkBack pending |
| U7 | Accurate mode/source and arrow/Undo descriptions; settings instrumentation, EN/RU lint and synchronized user/architecture text. | Verified locally; receipt above |
| U8 | Editing commands/layer with zero text reads; clipboard test setup; foreign-text boundary isolation; EditText/WebView/Compose and TalkBack. | In progress: editor compatibility and nonzero-left service recreation verified locally; cold zero-offset/right-context, process death, Fold and TalkBack scope outstanding |
| U9 | Emoji panel and row layout; context boundary, ZWJ/flag/modifier insertion and deletion; accessibility, opening/startup budgets, Fold displays and API 26 font. | In progress: panel/key/API26 font verified; catalog names now materialize per category after full validation; latest three-clean-AVD series has 4/12 draw starts above 50 ms (u9-emoji-deferred receipt), so no opening-speed win is established; modifier CommitText insertion/deletion verified on API26 (u9-emoji-modifier receipt); remaining cold opening, IME/PSS/presentation/Fold budgets and manual TalkBack outstanding |
| U10 | NO_SUGGESTIONS/AUTO_COMPLETE/FILTER combinations; hidden strip and no correction/model calls; unchanged search submission and frozen replay. | Verified locally; receipt above |
| U11 | Explicit experimental model status; separately calibrated in-process EN ranker; fresh family/article-separated holdout, protected forms, exact Undo, model comparison and device budgets. | Open |
| U12 | Tail-based personal phrase context with partial-token protection; >512-character session continuation and accumulated phrases. | Verified locally; receipt above |
| U13 | Reproduce charging/screen-off retry without forced Doze; policy tests; observed promotion in the night window on emulator. | Verified locally; receipt above |
| U14 | Measure expanded-strip utility first; view limits and touch invalidation; first-two replay parity, stable Fold layout and API 26 accessibility. | Open |
| U15 | Mode-key alternatives and voice command handling; popup/picker/TalkBack; Fold with/without voice IME; privacy regression. | Open |
| U16 | Packaged native symbols stripped, text/rodata parity, no local source paths, unchanged runtime build identity; negative gate and release/model/scoring smoke on required devices/APIs. | Verified native scope (native-preparation-runtime receipt): the strip-only stage retained the old identity; the separate normalized-source recipe has a new qualified identity, zero local-path findings, exact packaged/unstripped section parity and real model load/self-test/scoring on Fold and ARM64 API26/API37 (16 KiB); whole-release/distribution and x86_64 execution acceptance remain separate |
| U17 | Single-pass checksum and loading fast paths with structural/payload mutation detection; renewed source-bound replay parity; profile/PSS/startup measurements on Fold and constrained API 26. | Verified locally: u17-single-digest, u17-packaged-readers, u17-language-loading and final u17-profile-startup receipts cover the scope; startup now leaves body anchors lazy, validate retains full integrity/record checks; 1,277 JVM tests, lint/privacy gates, two fresh identical 12,000-row runs with all 69 assets bound, 40 profile starts on Fold/API26-2GiB and the updated owner's 4 physical tests/15 cases pass; temporary device/source state cleaned up |
| U18 | Optional light/system palette with contrast tests; palette/theme instrumentation; navigation/popups/strip/Shift/Monolith across API/display cases; distribution screenshots/docs. | Open |
| Q1 | Measured packaged ELF/APK size and budgets; native/privacy/runtime gates and JNI export; unchanged runtime identity; unstripped/oversized negative cases; release smoke and F-Droid evidence. | In progress: stripped payload/negative cases verified (u16-packaged-native receipt); explicit APK/component/ABI budgets and +60MB compressed-growth refusal verified (q1-apk-footprint receipt); historical recipe pins/tag and lint/source scan verified (q1-fdroid-history receipt); 24-file review data inventory, exact suppression guard and source scan verified (q1-fdroid-data receipt); live normal-Git checkpoint, dirty/cache refusal and clean-checkout release build verified (q1-clean-source receipt); exact prepared-source checkpoint, cache refusal and qualification bridge verified (q1-prepared-source receipt); native integration and renewed runtime execution qualification verified (native-preparation-runtime receipt); actual local F-Droid assembly passes and its complete unsigned APK equals the normal build under the same host/toolchain/cache; next versioned recipe, independent build-server/source-export/final-binary-scan, whole-release and distribution acceptance remain open |
| Q2 | Accurate consent/storage/source/CHANGELOG text; source enums documented, all binary assets noticed/scanner-listed, provenance/README paths tracked, persisted fields disclosed; scanner outcome. | Open |
| Q3 | Exact admission/mechanical/editor refusal diagnostics with behavioral tests and stable codes; source-bound candidate/boundary/Undo/allowed replay parity and stress analysis. | Verified locally: schema9-integration and resource-refusals receipts cover every Q3 check; 1,301 JVM tests, 67 Python checks, six current API26 diagnostics UI methods, four personal-admission methods and 101 old/new Android adapter rows pass with zero allowed changes; the 90 core sources/69 assets at that checkpoint match its complete 15,288-row replay, actual stress NOT_QUALIFIED 393 → 23; physical/update and independent distribution evidence remain separately scoped |
| Q4 | Numeric-only per-source change/Undo counters, migration, saturation, recorder API and reset tests; privacy regression; two weeks of actual owner-use observations and acceptance report. | In progress: all four source outcomes, bounded model-response timing, v3 storage/dashboard and explicit debug numeric SAF export are implemented. Source `9875aee`: 1,343 JVM tests, five actual API26 methods, profile/release privacy and release footprint pass; prior 15,288-row replay reused with all 90 sources/69 assets unchanged. Exact APK updated on Fold via ADB: four physical tests/15 matches, preferences/protected stores/model preserved. See Q4 debug-export receipt. Two actual weeks of ordinary owner use and acceptance report remain |
| Q5 | Reproducible RU ordinary-chat/orthographic corpus, clustered false-change baseline with Wilson reporting and sufficient controls; phrase/revision/Undo/case-change replay. | Open |
| Q6 | Durable consumed-data registries and shared overlap gates; historical hash/provenance recovery; independent natural qualification with exclusions surviving removal of build/; acceptance receipt binding. | In progress: Q7 adds six multilingual regression disclosure entries and two RU context/surface quarantines; all original 121 lexical entries are preserved (123 now). New unproven canonical families and prior historical gaps remain explicit; global coverage/fresh qualification is not claimed |
| Q7 | Current-product replay in CI with two identical projection hashes; threshold mutation fails with row diff; renewed baseline and measured job cost. | In progress: versioned portable driver/projection gate, permanent licensed 2,160-row inputs plus the original 12,000-row multilingual suite, separate lossless baselines and Q6 surface/context disclosures are wired after Gradle. Actual local Ubuntu24/ARM64 two-profile run: all 14,160 rows match, about 185 seconds at 2 CPU/4GiB; one-threshold CI mutant fails with 160 row diffs. Final 41 corpus commands/218 unit tests pass; observer pipeline 121 tests has one disclosed legacy conditional skip. See q7-ci-baseline receipt. Complete tools tests/heavy-dependency jobs and actual hosted Ubuntu workflow execution remain |
| Q8 | Editor-deviation simulator with predefined outcomes; qa_editor profiles and APP-001…005 compatibility/continued-correction measurements on Fold under existing device/privacy rules. | Open |
| Q9 | JVM identity tests for uncovered frozen assets and policy constants/thresholds; byte/constant mutation failures naming the artifact; included in the JVM CI gate. | Verified locally; receipt above |

## Q6 outstanding evidence

- Finish the remaining historical qualification/training provenance inventory.
  Instrumental, left-sequence, oblique, combined v11/v12 and residual group
  reuse through v14 are source/data-audited in the auxiliary-authored-history
  receipt; model execution and complete model-driver provenance are not
  established by it. The late-source archive now preserves the direct declared
  source bytes for training v4–v8 and residual v9–v14; transitive dependencies,
  historical execution and feature/model parity still need separate evidence.
  Frozen natural/side descendants are now source-capture and variant/filter
  audited; all 19 currently present right-context corpus manifests are bound.
  This scoped inventory does not establish selection or model parity.
- Keep unsupported lexical surfaces quarantined until canonical-family evidence
  exists. Prediction-only analyses do not establish canonical lemmas.
- Recover or explicitly resolve the historical role-feature source at hash
  `2442a38501946f6fcaad293a99b11d0ad785123efb1fe207b03beb5332a841d0`.
  The original left-sequence feature hash
  `82aeb37a82f7ac32aafd2f5f08eab36469ad2605b169943359db9a069726788e`
  also remains unavailable among checked copies.
- Establish provenance for the separate 120-example file; matching its manifest
  alone does not establish authorship. Keep its text/private fingerprints out
  of the public exclusions.
- Resolve the disclosed natural-v6 historical article overlaps; those existing
  rows cannot be represented as independent fresh qualification.
- Complete generator/source inventory and acceptance-template ledger binding.

## Integration and completion boundaries

Preserve the owner's selected precision profile when preparing new experiments;
existing frozen source certificates retain their bound policies until a fresh
qualification authorizes replacement. Preserve original historical generator
bytes and receipts. Q6/Q7 evidence is required before promoting changed admission.

Review section 9's remaining source/evidence integration, clean tracked-source
build/tests, release artifacts and distribution requirements alongside these
cards. Existing working changes require individual source review and validation;
bulk staging is not evidence of completion. Device/API, native, privacy,
performance and long-running observation checks must retain their own outcomes.
Missing, unrun or indirect evidence leaves the corresponding acceptance open.

Before completion, re-read the original review and audit every explicit check
against the actual source, generated artifacts, test output and external/device
state. The inventory above does not replace that requirement-by-requirement audit.
