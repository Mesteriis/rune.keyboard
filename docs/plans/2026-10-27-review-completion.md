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
U6 TalkBack follow-up: [real touchscreen traversal and activation on API 37](../acceptance/2026-10-27-u6-switch-dependencies.md#2026-11-24-talkback-settings-traversal-and-search) verify the correction and experiment dependencies, bulk disable, and Learning lab navigation. Search now focuses its selected native Switch, including a disabled off-screen result, and Back restores the query. The [speech synthesis requests](../acceptance/2026-10-27-u6-switch-dependencies.md#2026-11-24-talkback-text-submitted-to-speech-synthesis) verify names, on/off state, role, disabled status and the prerequisite. Audible rendering and the section 9 Fold run remain open.
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

Q6 model-source follow-up: [all 322 direct source references in 14 historical model records](../acceptance/2026-10-29-q6-historical-role-trainers.md) have byte-identical tracked files; transitive provenance and independent qualification remain open.

Q6 neighbor history follow-up: [15,000 source-attributed historical rows now have durable article, context and surface exclusions](../acceptance/2026-10-29-q6-neighbor-history-exclusions.md); dictionary analyses of all 2,500 target words are now retained (q6-neighbor-families); full source segments of all 2,426 articles are now excluded (q6-neighbor-article-segments); [dictionary families and exact unresolved surfaces in retained prefixes](../acceptance/2026-10-29-q6-neighbor-prefix-families.md) are also excluded; wider provenance coverage remains open.
Q6 neighbor independence: [the pinned dictionary finds one train/holdout lemma overlap](../acceptance/2026-10-29-q6-neighbor-families.md#partition-independence-recheck) despite disjoint native IDs; the lemma is already excluded from future holdouts.
Q6 observed neighbor outputs: [two identical current-controller projections are registered](../acceptance/2026-10-29-q6-neighbor-families.md#observed-output-exclusions) in both ledgers; corpus independence remains open.



Q7 API37 connected history: [seven routed scopes passed while an earlier general suite failed with 48 skips](../acceptance/2026-10-29-q7-api37-ci-nav-full.md). A [later fresh general run](../acceptance/2026-10-28-q8-editor-simulator.md#general-api-26-attempt-and-targeted-reruns) passed 321 cases with 48 skips; hosted CI remains open.

Q7 synthetic restart follow-up: [case-rejection and confirmed-word write/reload sequences](../acceptance/2026-10-29-q7-ci-synthetic-restart.md) pass on API26/API37 owned emulators and are routed for CI; hosted x86_64 remains open.

Q7 confirmed-words CI follow-up: [three synthetic-fixture scenarios are routed separately](../acceptance/2026-10-29-q7-ci-confirmed-words.md); direct API26/API37 runs pass, and the ordered process-restart fixture and Gradle/hosted execution remain open.

Q7 case-rejection CI follow-up: [two previously skipped real-IME tests now have a required synthetic-fixture route](../acceptance/2026-10-29-q7-ci-case-rejection.md); direct API26/API37 runs pass without skips, while hosted CI remains open.

Q1 current full local build: [F-Droid source export and binary scan](../acceptance/2026-10-29-q1-current-full-fdroid.md) pass on commit a5059ca3; independent build-server and release acceptance remain open.

Q1/Q7 resolver cache: [external project-cache isolation](../acceptance/2026-10-29-q1-replay-cache-isolation.md) keeps the strict source-data policy effective after the standalone Gradle resolver runs.

Q1 archive rebuild follow-up: [the verified export over a trusted checkout](../acceptance/2026-10-29-q1-fdroid-trusted-export-rebuild.md) passes the unchanged Git/qualification gates and reproduces the local APK byte for byte. Independent build-server and distribution acceptance remain open.

Q1 export guard follow-up: [the actual source tarball refuses without Git](../acceptance/2026-10-29-q1-fdroid-export-guard.md); prepared-source CLI now reports the refusal cleanly. A secure archive verification and actual archive build remain open.

Q1 source-export follow-up: [F-Droid local build with source tarball and binary scan](../acceptance/2026-10-29-q1-fdroid-source-export.md) passes at `00936a6a`; independent build-server and distribution acceptance remain open.

Q1 prepared CI candidate: [the local release gates and F-Droid binary scan](../acceptance/2026-10-29-q1-fdroid-binary-scan.md#release-scan-with-the-a2-and-editor-changes) pass on the exact unsigned APK at `75d06f6f`, including 16 KiB alignment and strict native verification. Hosted and physical acceptance remain open.

Q1 binary-scan follow-up: the [local unsigned APK scan](../acceptance/2026-10-29-q1-fdroid-binary-scan.md) returns zero F-Droid problems for the `1b3d8c33` artifact; a new release and independent build-server/distribution acceptance remain open.

Q1 current-source follow-up: [local F-Droid preparation, scanner and build](../acceptance/2026-10-29-q1-current-fdroid.md) pass for commit `1b3d8c33`; the unsigned APK matches a normal local release build byte for byte. Independent build-server, source-export, binary-scan and distribution acceptance remain open.

Hosted CI follow-up: independent-controller fixtures and two obsolete incognito
transition assertions are repaired with API26/API37 targeted evidence
([controller isolation](../acceptance/2026-10-28-hosted-ci-independent-controller.md),
[incognito tests](../acceptance/2026-10-28-hosted-ci-incognito-tests.md)).
The failed neighbor-recovery cases passed a local API26 rerun, but their
[hosted failure cause remains unproven](../acceptance/2026-10-28-hosted-ci-neighbor-rerun.md).
The [settings test driver](../acceptance/2026-10-28-hosted-ci-settings-switch.md)
now finds native accessible switches; three previously failing settings cases
pass on both API26 and API37. The [suite-size guard](../acceptance/2026-10-28-hosted-ci-suite-floor.md)
rejects grossly truncated general reports but does not prove case identities.
The [API26 general run](../acceptance/2026-10-29-android-api26-full-run.md)
had five failures under a system crash overlay; all five passed separately,
but the full run remains failed. [Historical capture sources](../acceptance/2026-10-29-q7-historical-capture-sources.md)
are restored and the scientific profile passes with one skip. A hosted CI
rerun and the other failures remain open. The [fresh local replay](../acceptance/2026-10-29-q7-current-replay.md)
matches both frozen corpora; MLX and Pymorphy gates pass without skips.

Q6 trainer follow-up: the [joint trainer](../acceptance/2026-10-28-q6-joint-trainer-audit.md)
now binds both training and calibration replay/registry inputs and labels pinned
historical reproduction; [actual historical training](../acceptance/2026-10-29-q6-joint-trainer-reproduction.md)
matches the original binary, calibration scores and thresholds. Held-source
attestation and fresh independent training remain open.

Q6 source segments: [all historical joint and follow-up source articles](../acceptance/2026-10-29-q6-joint-article-segments.md)
are now excluded at the selector-segment level. A [compact representation](../acceptance/2026-10-29-q6-compact-ledger.md)
preserves logical entries and provides headroom for subsequent exclusions.

## Acceptance inventory

Q5 source follow-up: [RuLexNorm's pinned public social-text source](../acceptance/2026-11-10-q5-rulexnorm-source-screen.md) yields eight unchanged 2–6-word Cyrillic entries under a strict in-memory screen. Its potentially sensitive comments, unproven underlying rights and annotation scope prevent treating it as a ready independent baseline; no source text was retained.
Q5 source follow-up: [Small-Life's declared 50,000 dialogue rows](../acceptance/2026-11-10-q5-small-life-source-screen.md) include 12,492 Russian General rows but only 80 distinct exact pairs and seven distinct short Cyrillic answers. Counts of unique IDs do not establish content diversity or a labelled baseline.
Q5 source follow-up: [the Russian GEC source](../acceptance/2026-11-10-q5-russian-gec-source-screen.md) has 24,998 CSV rows; removing terminal punctuation leaves 94 distinct corrected strings under the 2–6 Cyrillic-word filter. Its corrected targets and synthetic/semicrowdsourced domain do not establish a chat control baseline.

Q5 RuLexNorm follow-up: the same source contains 704 wholly unchanged annotated groups with 2,429 lowercase Cyrillic tokens. Rights, correctness, overlap and natural-chat qualification remain unverified.

Q5/A2 SAGE source screen: [four pinned social-media splits](../acceptance/2026-11-10-q5-additional-dialogue-source-screen.md#sage-social-media-partitions) supply 110 distinct short unchanged texts after normalization and zero single-token changes with an identical prefix of at least 300 characters. The independent-control and long-context requirements remain open.

Q5 RNC source follow-up: [the pinned social-media normalization dataset](../acceptance/2026-11-24-q5-rnc-normalization-screen.md) yields 712 distinct short unchanged phrases after case folding. The orthographic generator reproduces five of 59 single-final-token annotations. The source includes stylistic normalization, has no author clusters, and falls below the baseline size.

Q5 RuLexNorm provenance clarification: [the authors describe a mixed natural and synthetic dataset, and the paper and repository make different statements about its use](../acceptance/2026-11-10-q5-rulexnorm-source-screen.md#published-source-and-rights-clarification). Per-entry origin and author clustering remain unavailable in the documented two-column format; no independent baseline is claimed.

Hosted CI publication preflight (2026-11-10): the live public `origin/main`
was `2c1ff975`; local `f76936be` was 469 commits ahead, with a clean worktree
and a clean `git diff --check` against that remote. The latest hosted `ci` run
for `2c1ff975` failed. The current workflow triggers on pushes to `main` and
pull requests, not manual dispatch. A filename-only scan of changed paths in
the complete unpublished commit range found no obvious private-key or keystore
files, but it did find many retained corpus and diagnostic-related paths; this
is not a content, license, or full history disclosure audit. Do not treat this
preflight as permission to publish unreviewed data or as a hosted CI result.
Fold was not present in the contemporaneous ADB device list.

Hosted CI recheck (2026-11-24): the remote `main` ref still resolves to
`2c1ff975`. Its latest [CI run](https://github.com/Mesteriis/rune.keyboard/actions/runs/40680972358)
finished with failed Android boundary steps on API 26 and 37, and a failed
frozen multilingual replay step. The build, both Python profiles and the
Python MLX job passed. GitHub returned zero Actions runs for the exact
local review commit `b3acf3532d89fedc1abc82a46bd98318911ee3cd` and did not
resolve that commit in the public repository. The local repeat and the
publication checks remain separate acceptance work.

History secret-scan follow-up at `df700d6d`: Gitleaks 8.30.1 scanned
`origin/main..HEAD` with its default rules, a 10 MB target limit and no archive
traversal. It exited 1 with 74 generic API-key findings. One is an ordinary
navigation-receipt identifier in this document; the other 73 have the shape of
64-character hexadecimal values. A conservative local context screen found
three in explicitly named hash fields; 70 did not meet that simple criterion
and require further review. Hexadecimal shape alone does not establish that a
value is a non-secret hash. Larger targets, archived contents, private text and
licensing remain outside this result. The temporary reports were removed.

U9 cold-path follow-up: [interleaved profile builds](../acceptance/2026-10-28-u9-live-ime-trace.md#same-emulator-cold-path-comparison) compare six starts each before emoji and at `f5108055` on one API 26 emulator. The current median process-start-marker to input-view creation was lower in this small series; ranges overlap and other changes are present. Presented-frame, Fold and full startup acceptance remain open.

Q1 current clean release: [local unsigned release and native/privacy gates](../acceptance/2026-11-09-q1-current-clean-release.md) pass on `d61df14f`, with 1,401 JVM tests and strict packaged-native path checks. Hosted, signed, independent build-server and physical-device acceptance remain open.
Q1 post-corpus repeat: [clean release checks and two same-host APK builds](../acceptance/2026-11-09-q1-current-clean-release.md#repeat-after-corpus-exclusion-updates) pass at `999bb321`; [the local F-Droid source scan](../acceptance/2026-11-09-q1-current-source-scanner.md#repeat-after-corpus-exclusion-updates) has zero fatal findings and the two known warnings. Independent release/distribution remains open.


Q1 current scanner: [F-Droid 2.4.5 source scan](../acceptance/2026-11-09-q1-current-source-scanner.md) on `f3e98a7b` reports zero fatal findings and the two established warnings; two negative source injections are rejected by the combined scanner/data guard. The current checkout's existing pinned submodule is now registered, so its clean-source gate passes. Distribution and independent build-server acceptance remain open.

Q7 scientific integration: [the current scientific profile](../acceptance/2026-11-09-q7-scientific-capture-recovery.md) passes on `1eb66812`: 24 modules, 90 tests and one MLX skip; separate MLX CPU and Pymorphy gates pass 7 and 5 tests without skips. The [current controller replay](../acceptance/2026-10-29-q7-current-replay.md#current-source-repeat) matches both frozen baselines on `b7318582`. Hosted execution remains open.

A4 Fold follow-up: [private and ordinary editor boundaries plus the exact review phrase](../acceptance/2026-11-10-a4-private-boundaries.md#ordinary-editor-and-review-phrase) passed on Fold; the current 140-row, three-boundary source-bound control gate also passed. Diagnostic rotation and preserved owner backups are disclosed. Natural representativeness and control frequency remain unverified.

A4 source-frequency screen: [a pinned 92,622-article Wikipedia shard](../acceptance/2026-11-10-a4-abbreviation-frequency.md) contains raw token-dot matches for 49 of 54 disclosed abbreviation forms; meanings, representativeness and independent qualification remain unverified.

A4 source exposure: [46 sample articles reviewed by one model and the entire screened 92,622-article Wikipedia shard](../acceptance/2026-11-10-a4-abbreviation-frequency.md#whole-shard-exposure-quarantine) are excluded by article in both registries. One domain match and one uncertain reading illustrate the limits of raw frequency counts; other axes and independent qualification remain open.

Q7 current stdlib: [a clean-source repeat](../acceptance/2026-11-10-q7-current-stdlib.md) passes 207 modules and 1,005 tests after the full-shard exclusion updates. Hosted CI and scientific/Android profiles remain separate.

Q7 current scientific: [30 modules and separate live Pymorphy/MLX gates](../acceptance/2026-11-10-q7-current-scientific.md) pass after full-shard exclusion; the scientific profile has one MLX skip, independently covered by the seven-test CPU backend gate. Hosted CI remains open.

Q7 API 37 post-A4 result: [the full local workflow failed one neighbor-recovery case](../acceptance/2026-11-10-q7-api37-neighbor-failure.md); three metadata-only isolated repeats and a full local API 37 rerun pass, but do not explain the original failure. The full rerun predates the post-space diagnostic change; both targeted real-IME cases pass on current source. The original root cause, delayed-branch device observation, full current-source workflow and hosted execution remain open.

Q7 API 26 post-A4 repeat: [the complete local workflow shell](../acceptance/2026-11-10-q7-api26-post-a4-ci.md) passes at `420b4983`, including 397 general cases (59 skips) and all separate scopes. The original Logcat stream stopped early; retry is fixed and unit-tested separately. API 37 and hosted execution remain open.

Q7 current Linux replay: [both multilingual profiles](../acceptance/2026-11-10-q7-linux-x86-replay.md) passed the actual two-pass gate on emulated x86_64 with exact behavior and the existing score tolerance; the intermittent earlier failure and hosted CI remain open.

Q7 replay stability: [an injected deadline regression](../acceptance/2026-11-10-q7-recovery-deadline-replay.md) proves the real neighbor-recovery time limit can change the generation fields compared by replay. The old intermittent Linux failure remains unattributed; hosted CI remains open.

Q7 current Python integration: [clean-source stdlib inventory](../acceptance/2026-11-09-q7-current-python-inventory.md) passes 912 tests in 183 modules at `ebe2fc6e` on Python 3.12 and 3.14; eight separately run CI-helper modules pass 37 tests on both versions. Scientific backends and hosted execution remain open.
Q7 post-Taiga repeat: [the current stdlib inventory](../acceptance/2026-11-09-q7-current-python-inventory.md#repeat-after-taiga-and-neighbor-exclusions) passes in clean checkouts on Python 3.12 and 3.14; the latter reports 925 tests and no skips. Hosted and scientific execution remain separate.
Q7 post-Taiga scientific repeat: [24 modules and the separate live Pymorphy/MLX gates](../acceptance/2026-11-09-q7-scientific-capture-recovery.md#repeat-after-taiga-and-neighbor-exclusions) pass locally; the scientific profile retains one MLX skip. Hosted execution remains open.



U15 voice visibility follow-up: [Android package visibility and the silent
voice-IME fixture](../acceptance/2026-11-09-u15-voice-visibility.md) cover the
previously invisible enabled IME on API 26 and API 37. The CI fixture also
requires stale-target and next-keyboard paths on each API. Full hosted CI, actual
speech recognition, manual TalkBack and Fold remain open.

Q7/U8 process-death follow-up: [left- and right-context recovery](../acceptance/2026-11-09-q7-editing-process-death-ci.md)
is now routed for disposable-emulator CI and passes targeted API 26/API 37
runs with an independent editor. Hosted execution and physical/manual
acceptance remain open.

Q7 Compose follow-up: the [independent Compose editor route](../acceptance/2026-11-09-q7-compose-ci-route.md)
now requires all three previously skipped cases without skips; targeted API 26
and API 37 runs pass. The modified full workflow and hosted x86_64 run remain
unverified.

Q7 current API 37: [fresh boundary and restart scopes](../acceptance/2026-11-09-q7-current-api37-boundaries.md)
pass on source `16c292bd`, including all nine required reviewed-chat identities.
The general suite still skips 48 cases; hosted x86_64, the full workflow shell
and physical-device acceptance remain open.

U9 category focus: [category tabs retain their views across selection, language and privacy changes](../acceptance/2026-11-03-u9-stable-category-tabs.md); API26/API37 panel checks pass. Manual TalkBack, Fold and remaining performance acceptance remain open.

U9 frame timing: [API 37 SurfaceFlinger FrameTimeline](../acceptance/2026-11-23-u9-surfaceflinger.md) links a populated Emoji grid draw to a classified display frame at 52.147 ms after Emoji key release. An unchanged-build repeat also exceeded 50 ms on the first IME layer frame after panel construction. The lower-allocation reader still has a classified 50.750 ms populated-grid frame in the six-pair API 37 repeat. The opening budget, both Fold displays and manual TalkBack remain open.

U11 pairwise prototype: [EWT candidate ranking](../acceptance/2026-11-03-u11-ewt-pairwise-ranker.md) trained on 51 disclosed groups. It improves the nine-group development slice but ties the existing order 4/5 on five incomplete-search test groups; it is not qualified or enabled.

U11 product replay: [disclosed EWT annotations](../acceptance/2026-11-03-u11-ewt-product-replay.md) show 0/186 automatic annotated corrections in the model-free host controller, with 89 targets present in recorded alternatives; one of 165 unannotated unknown inputs changed case. This is not an independent or verified false-change estimate.

U11 control screen: [unannotated EWT tokens](../acceptance/2026-11-03-u11-ewt-control-screen.md) show that the offline edit prototype finds alternatives for 306/609 previously unseen unknown occurrences, including 198 tagged proper nouns. Missing correction annotation is not a verified control label; no product false-change rate is claimed.

U11 prototype: an [annotated EWT single-edit channel](../acceptance/2026-11-03-u11-ewt-annotated-edit-model.md) trains on 482 disclosed rows; on 29 scored unseen-target test rows it ties frequency at 29/29. It is not qualified, and the 425 public target keys are quarantined.

U11 local search: among the 165 English diagnostic inputs with wider-search state exhaustion, [the completed radius-one pool](../acceptance/2026-11-03-u11-english-local-search.md) contains the constructed target in 139, including 132 unique local alternatives. This does not bypass wider-search, admission or qualification gates.

U11 candidate feasibility: a [disclosed English source-surface screen](../acceptance/2026-11-03-u11-english-candidate-ceiling.md) finds its constructed target in the recorded alternatives with search permitting auto on 53/360 deletion/transposition inputs. Current 2,160-row product replay matches the frozen baseline; this is not natural-data qualification.

Q7 API 26 follow-up: the [complete local CI shell repeat](../acceptance/2026-11-03-q7-complete-api26-ci-repeat.md) passed after the test-driver popup fix, with all eight routed suites and four restart phases passing. The general suite includes 48 explicit skips; hosted x86_64 CI remains unverified.

A1 manual suggestion follow-up: [the owned-context guard](../acceptance/2026-11-24-a1-pronoun-boundaries.md) suppresses `I` inside apostrophe forms and identifiers. All 66 local boundary cases preserve the typed text. The GUM screen identifies ten lowercase non-pronoun occurrences before candidate boundaries. Automatic conversion, independent qualification and Fold remain open.

A1/Q7 Android follow-up: [the resident IME apostrophe regression and seven related cases](../acceptance/2026-11-24-a1-android-boundaries.md) passed on both API 26 and API 37. The new case is required by the general CI suite. The same run passed the three contextual-punctuation methods that failed in the published workflow after their fixture repair. Hosted and Fold runs remain open.

A2 source-only replay: [the exact current controller request comparison](../acceptance/2026-10-28-a2-prefix-window-component.md#2026-11-24-replay-from-source-without-model-artifacts) now runs without ignored native artifacts. All 12,000 historical inputs matched across both flag states and the separate 14,160-row frozen gate passed. Its longest request prefix was 59 bytes, leaving independent long-context scoring open.

A2 frozen archive recovery: [the verified historical scorer cache](../acceptance/2026-10-28-a2-prefix-window-component.md#2026-11-24-frozen-scorer-cache-recovery) provides exact archived responses for 1,809 of 2,004 current holdout payloads. The other 195 differ in candidate membership, and none differ in prefix. [Live native replay of all archived holdout payloads](../acceptance/2026-10-28-a2-prefix-window-component.md#2026-11-24-native-replay-of-the-complete-archived-holdout) reproduced 2,959 numeric responses and 14 error responses exactly. The fresh flag-off/flag-on comparison reproduced all 2,004 current responses, with eight historical contract errors retained. Independent long-context qualification and Fold measurements remain open.

A2 document-context source screen: [RLC-GEC and COWS-L2H](../acceptance/2026-11-24-a2-long-learner-context-screen.md) expose 271 manually annotated Russian orthography edits with matching token spans and 243 Spanish two-reference edits after at least 1,000 original characters. Human spelling labels, unchanged controls, provenance separation and English coverage are open.

A2 candidate controls: [the known-exclusion screen](../acceptance/2026-11-24-a2-long-learner-context-screen.md#candidate-controls-and-intersections-with-existing-exclusions) found 20,044 remaining Russian tokens across 700 documents and 2,159 Spanish tokens across 171 essays after at least 1,000 characters. The screen covers existing surface and context keys. Human labels, source and author separation, family exclusions and actual model-window checks remain open.

A2 English source pilot: [CPython documentation revisions](../acceptance/2026-11-24-a2-long-learner-context-screen.md#english-cpython-documentation-revisions) yielded four verified one-word edits after 1,000 raw file characters. Only one had 300 contiguous plain-text characters and none had 600. Broader English coverage remains open.

A2 retention follow-up: [the long-session controller regression](../acceptance/2026-10-28-a2-prefix-window-component.md#2026-11-24-hysteresis-across-context-retention) reproduced an early window cut after eviction and now verifies stable start across the next late-local request. 1,436 JVM tests and both frozen Q7 profiles pass. Independent scoring and live device evidence for the change remain open.

A2 native observation: an [instrumented Android scorer copy](../acceptance/2026-11-03-a2-android-observed-cache.md) retained 0, 69 and 1 tokens for the initial, extended and shifted windows on API 26 and API 37, with zero warm/cold score difference. Production JNI telemetry, independent quality and Fold remain unverified.

A2 follow-up: [Android warm/cold score parity](../acceptance/2026-11-03-a2-android-prefix-score-parity.md) passes on API 26 and API 37 for three synthetic bounded prefixes. This does not observe cache reuse or qualify long-context quality; A2 remains open.

Q7 follow-up: the complete corrected Android CI shell passed locally on a
fresh API 37 ARM64 emulator, including the general boundary suite, all seven
routed suites and all four synthetic restart phases. The workflow now rebuilds
ordinary debug APKs after qualification suites before restart checks. See
[the complete repeat](../acceptance/2026-10-29-q7-complete-api37-ci-repeat.md)
and [the APK restoration fix](../acceptance/2026-10-29-q7-restore-debug-apk.md).
The local ARM64 result does not establish a successful hosted x86_64 run; Q7
remains in progress.

Counting convention: unfinished cards are **Open + In progress**. Locally
verified cards are reported separately; nested commits/checks do not close a
whole card. The denominator remains the original 31 A/U/Q cards. Local acceptance
is not independent release/distribution acceptance.

Q1/Q2 follow-up: the [public corpus archive inventory](../acceptance/2026-10-28-q1-public-corpus-archives.md)
now covers both retained Tatoeba `.bz2` files. Current-source F-Droid preparation
and scanning pass with 31 inventory entries; release/distribution acceptance
remains open.

| Card | Required behavior / acceptance evidence | State |
| --- | --- | --- |
| A1 | Narrow EN i→I rule; ES/abbreviation/identifier controls; suggestions, Undo and rejection behavior; fresh natural EN qualification. | In progress: English `i` now offers manual-only `I` with EN/ES and live-IME checks (a1-manual-i-suggestion); automatic conversion, versioned qualification, negative controls, independent natural holdout and Fold remain |
| A2 | Word-bounded qualified prefix window, boundary-byte compatibility, hysteresis and empty-prefix suppression; native KV reuse; frozen replay parity; long-context qualification and Fold latency/deadline measurements. | In progress: prefix window and three controller paths are wired behind a default-off internal flag; opt-in JVM and API26/API37 ICU tests, disabled-path model-free replay and host-native KV observation pass (a2-prefix-window-component). Instrumented Android JNI cache reuse and three synthetic warm/cold score comparisons passed on API 26 and 37 (a2-android-observed-cache and a2-android-prefix-score-parity). Historical model-score parity, independent long-context qualification and Fold measurements remain |
| A3 | Fresh short-word holdout including lowercase names; zero new false changes and predefined useful gains; parity on other sources; Fold typo/name cases. | In progress: on the disclosed 2,924-row short-word set, 216 typo-labelled rows hit the rare-only joint stop. A diagnostic source-only mask yields 26 model winners, all rejected by the existing admission guard; 19 RIVAL_UNKNOWN winners match the intended spelling. The current rerun reproduces zero newly admitted changes across all 2,924 historical rows; all 216 probe inputs are lowercase. RNC has 265 unchanged lowercase final rare-token occurrences and no independently labelled names (a3-rare-veto-screen). The current rare veto stays in place. Fresh holdout and Fold remain |
| A4 | Category-level period/colon controls with source/asset/corpus hashes and exit codes; Fold protected abbreviation, useful correction and exact Undo. | In progress: 140 disclosed authored controls pass the source/asset-bound three-boundary gate; `инн` case veto and the real symbols-layer colon correction pass on API26/API37 (a4-inn-case-veto and a4-colon-symbols-fix). [Fold private and ordinary boundary tests, including the review phrase and exact Undo](../acceptance/2026-11-10-a4-private-boundaries.md#ordinary-editor-and-review-phrase) passed; independent natural-control qualification remains open |
| U1 | Visible Undo default with compatible schema migration and explicit preference retention; model/canonical Undo survives next character without new refinement; replay and device coverage. | In progress: local acceptance verified; physical Fold pending |
| U2 | Token-scoped mechanical protection, exact refusal reasons and command/marker controls; Undo with zero reads; zero new correct/protected false changes. | Verified locally; receipt above |
| U3 | NPL incognito policy; composing/corrections with zero content reads; no mutation of six personal/diagnostic stores; JVM, instrumentation and replay. | Verified locally; receipt above |
| U4 | Reproduce shifted/changed composing ownership first; correct final text and finish behavior in simulator/qa_editor; preserve ownership safeguards; regression replay. | Verified locally; receipt above |
| U5 | Visible confirmed-word list and individual deletion; preserve pair rejections; phrase validation, capacity and restart persistence; privacy/user documentation. | Verified locally; receipt above |
| U6 | Settings registry, dependencies and Switch controls; registry/disable-list completeness; search/recreate/back, accessibility and updated screenshot/guide. | In progress: registry, dependencies, native Switch, screenshot and automated acceptance verified; TalkBack gestures and TTS text on API 37 verified; audible rendering and section 9 Fold run pending |
| U7 | Accurate mode/source and arrow/Undo descriptions; settings instrumentation, EN/RU lint and synchronized user/architecture text. | Verified locally; receipt above |
| U8 | Editing commands/layer with zero text reads; clipboard test setup; foreign-text boundary isolation; EditText/WebView/Compose and TalkBack. | In progress: editor compatibility and service recreation with nonzero-left and zero-offset/right-context verified locally; complete nine-method editing-panel suite passes on API26 and API37 (u8-zero-offset-rebind receipt); real Rune process death with a surviving independent Compose editor passes left- and right-context cases on API26 and API37 (u8-process-death-right-context). API26 requires an explicit IME rebind, and reopening on API37 moved the caret before a Home action. Live API37 TalkBack selected an actual range and ran Cut/Paste with zero editor payload reads (u8-public-panel). Physical Fold and its TalkBack run remain |
| U9 | Emoji panel and row layout; context boundary, ZWJ/flag/modifier insertion and deletion; accessibility, opening/startup budgets, Fold displays and API 26 font. | In progress: panel/key/API26 font verified; validated glyphs filter without eagerly decoding names and parser reuses consecutive category IDs. Latest three-clean-AVD preview series passes 12/12 under 50 ms with 0.76 ms minimum margin (u9-category-id-reuse); causal speedup and physical performance are not established. Modifier CommitText insertion/deletion verified on API26; five cold profile-IME trace samples capture opening sections and PSS; a pixel-byte recheck corrected the earlier black-frame misclassification, and all five stored images show the same populated grid (u9-live-ime-trace, u9-black-frame-followup). A real debug-IME PixelCopy probe observed five positive buffers within 32–43 ms, with a negative Symbols control; this does not establish physical presentation or release performance (u9-ime-pixelcopy). A six-pair API26 cold-start comparison is recorded in u9-live-ime-trace; API37 TalkBack traversed the first grid row, wrapped to the next, returned and inserted the focused glyph (u8-public-panel). Physical presentation, device budgets and Fold TalkBack remain outstanding |
| U10 | NO_SUGGESTIONS/AUTO_COMPLETE/FILTER combinations; hidden strip and no correction/model calls; unchanged search submission and frozen replay. | Verified locally; receipt above |
| U11 | Explicit experimental model status; separately calibrated in-process EN ranker; fresh family/article-separated holdout, protected forms, exact Undo, model comparison and device budgets. | In progress: [model status and development freeze](../acceptance/2026-10-28-u11-model-status.md) documented; Q4 owner observations, EN ranker and independent qualification remain open |
| U12 | Tail-based personal phrase context with partial-token protection; >512-character session continuation and accumulated phrases. | Verified locally; receipt above |
| U13 | Reproduce charging/screen-off retry without forced Doze; policy tests; observed promotion in the night window on emulator. | Verified locally; receipt above |
| U14 | Measure expanded-strip utility first; view limits and touch invalidation; first-two replay parity, stable Fold layout and API 26 accessibility. | In progress: 12,000-row current-product replay and raw-pool upper bound in u14-candidate-pool-screen; expansion-on/off visible-strip comparison in u14-visible-modes and controller-validated hidden order in u14-hidden-order. Revision-bound single-use selection core and unchanged 12,000-row replay are in u14-expanded-core. Coordinator policy is covered in u14-expanded-coordinator; expanded UI, two-mode replay and API26/API37 tests are in u14-expanded-ui; real-IME typing outside the open row is verified in u14-expanded-input. The same-window row passes TalkBack 17 forward navigation, Back and double-tap selection in the API 37 QA editor (expanded UI receipt). Updated Fold layout and physical accessibility checks remain |
| U15 | Mode-key alternatives and voice command handling; popup/picker/TalkBack; Fold with/without voice IME; privacy regression. | In progress: next-keyboard alternate with separate accessibility action preserves U8 editing and password behavior, with local JVM/API26/API37 evidence in u15-switch-entry; voice subtype discovery and actual switching on API26/API37, plus no-voice controls, are covered in u15-voice-switch; API26/API37 voice and next-keyboard popup gestures, stale-target picker and API26 next-keyboard picker pass in u15-voice-gesture; actual TalkBack Actions on API 37 select both Next keyboard and the isolated voice target (u15-voice-visibility receipt); physical Fold and TalkBack checks remain |
| U16 | Packaged native symbols stripped, text/rodata parity, no local source paths, unchanged runtime build identity; negative gate and release/model/scoring smoke on required devices/APIs. | Verified native scope (native-preparation-runtime receipt): the strip-only stage retained the old identity; the separate normalized-source recipe has a new qualified identity, zero local-path findings, exact packaged/unstripped section parity and real model load/self-test/scoring on Fold and ARM64 API26/API37 (16 KiB); whole-release/distribution and x86_64 execution acceptance remain separate |
| U17 | Single-pass checksum and loading fast paths with structural/payload mutation detection; renewed source-bound replay parity; profile/PSS/startup measurements on Fold and constrained API 26. | Verified locally: u17-single-digest, u17-packaged-readers, u17-language-loading and final u17-profile-startup receipts cover the scope; startup now leaves body anchors lazy, validate retains full integrity/record checks; 1,277 JVM tests, lint/privacy gates, two fresh identical 12,000-row runs with all 69 assets bound, 40 profile starts on Fold/API26-2GiB and the updated owner's 4 physical tests/15 cases pass; temporary device/source state cleaned up |
| U18 | Optional light/system palette with contrast tests; palette/theme instrumentation; navigation/popups/strip/Shift/Monolith across API/display cases; distribution screenshots/docs. | In progress: independent palette, contrast tests, live IME and preview plus API26/API37 targeted checks in u18-keyboard-palette; API29/API36/API37 gesture and three-button navigation checked in u18-api29-navigation, u18-api36-navigation and u18-navigation-modes; API26 button navigation visually checked after settling in u18-api26-navigation, with one transient missing-icon capture disclosed; full nine-method theme suite passed on API26/API37 after preview integration in u18-final-theme-suite; clean-source release privacy and dependency gates passed in u18-release-boundary; actual TalkBack, Shift, candidate row and sampled contrast on Light Monolith passed on API37, and the English Fastlane screenshot hash matches (u18-keyboard-palette and u18-light-store-screenshot); physical TalkBack, visual checks on both Fold displays, other navigation configurations and distribution acceptance remain |
| Q1 | Measured packaged ELF/APK size and budgets; native/privacy/runtime gates and JNI export; unchanged runtime identity; unstripped/oversized negative cases; release smoke and F-Droid evidence. | In progress: stripped payload/negative cases verified (u16-packaged-native receipt); explicit APK/component/ABI budgets and +60MB compressed-growth refusal verified (q1-apk-footprint receipt); historical recipe pins/tag and lint/source scan verified (q1-fdroid-history receipt); 24-file review data inventory, exact suppression guard and source scan verified (q1-fdroid-data receipt); live normal-Git checkpoint, dirty/cache refusal and clean-checkout release build verified (q1-clean-source receipt); exact prepared-source checkpoint, cache refusal and qualification bridge verified (q1-prepared-source receipt); native integration and renewed runtime execution qualification verified (native-preparation-runtime receipt); actual local F-Droid assembly passes and its complete unsigned APK equals the normal build under the same host/toolchain/cache; the current 11-change prepared checkpoint including four host archives also passes direct and Gradle cache-reuse refusal probes (q1-prepared-archives receipt); minimum-class API26/2 GiB setup-screen startup and PSS measured and recorded in README (q1-minimum-device); next versioned recipe, independent build-server/source-export/final-binary-scan, whole-release and distribution acceptance remain open |
| Q2 | Accurate consent/storage/source/CHANGELOG text; source enums documented, all binary assets noticed/scanner-listed, provenance/README paths tracked, persisted fields disclosed; scanner outcome. | Verified locally: [documentation/source closure](../acceptance/2026-10-28-q2-documentation-closure.md) covers EN/RU consent/storage fields and resets, current guide/schema/model facts, all source enums/orders, Unreleased, tracked local provenance/README sources and restored historical navigation. Source 2c1ff97 passes actual pinned F-Droid preparation/scanner: 29 data entries, 11 approved changes, 7 probes, zero fatal findings; the 3-unused-scanignore negative probe confirms exact current policy while historical recipe pins remain intact. Focused JVM: 160/160; source/navigation/privacy/provenance gates pass. Independent release/distribution, hosted CI and Q6 data/model lineage remain in their own cards. |
| Q3 | Exact admission/mechanical/editor refusal diagnostics with behavioral tests and stable codes; source-bound candidate/boundary/Undo/allowed replay parity and stress analysis. | Verified locally: schema9-integration and resource-refusals receipts cover every Q3 check; 1,301 JVM tests, 67 Python checks, six current API26 diagnostics UI methods, four personal-admission methods and 101 old/new Android adapter rows pass with zero allowed changes; the 90 core sources/69 assets at that checkpoint match its complete 15,288-row replay, actual stress NOT_QUALIFIED 393 → 23; physical/update and independent distribution evidence remain separately scoped |
| Q4 | Numeric-only per-source change/Undo counters, migration, saturation, recorder API and reset tests; privacy regression; two weeks of actual owner-use observations and acceptance report. | In progress: all four source outcomes, bounded model-response timing, v3 storage/dashboard and explicit debug numeric SAF export are implemented. Source `9875aee`: 1,343 JVM tests, five actual API26 methods, profile/release privacy and release footprint pass; prior 15,288-row replay reused with all 90 sources/69 assets unchanged. Exact APK updated on Fold via ADB: four physical tests/15 matches, preferences/protected stores/model preserved. See Q4 debug-export receipt. debug numeric export navigation is now isolated on the quality dashboard and verified on API26 without widening the diagnostics boundary (q4-export-navigation-boundary receipt). Two actual weeks of ordinary owner use and acceptance report remain |
| Q5 | Reproducible RU ordinary-chat/orthographic corpus, clustered false-change baseline with Wilson reporting and sufficient controls; phrase/revision/Undo/case-change replay. | In progress: [disclosed chat-shaped baseline](../acceptance/2026-10-28-q5-chat-regression.md) has a retained CC0 source, reproducible 34,330 rows and current-product token replay; 41/9,543 unproofread source controls changed, zero prefix/Undo failures. Source errors mean that this change rate is not a false-change estimate. A separate synthetic dialogue source is screened in q5-dialog-source-screen, but is not yet used as evidence. A post-hoc audit now classifies all 30 case-only changes and retains five contextual lowercase regressions (q5-chat-case-review); pinned dictionary-only morphology labels all five as proper-only and thus cannot resolve them without context (q5-case-morphology); the already-excluded Tatoeba source contains ten lowercase occurrences and no uppercase contrasts for these exact three forms (q5-case-source); a corpus-wide screen identifies ten canonical keys with lowercase evidence, including all five reviewed errors and no 24 reviewed name occurrences (q5-lowercase-evidence); an isolated current-product replay preserved the five and left 24 named cases unchanged, but also changed one ambiguous case (q5-case-evidence-overlay); its 4,720 additional disclosed unlabeled parity inputs and eight prior controls have no non-timing observer differences (q5-case-parity); 21 disclosed Wikipedia name/place contrasts from 13 excluded articles expose loss of all 21 source-case matches, so the blanket candidate is rejected (q5-case-name-contrast); identical left context with opposed intended cases is documented and excluded from future holdouts (q5-case-collision); opt-in personal learning now persists a scoped explicit rejection of lowercase-to-titlecase changes, including real IME Undo/retype/manual selection on API26/API37 (q5-personal-case-rejection); wider chat-register evidence, full verified control labels and phrase/revision replay remain open; this previously exposed corpus is not independent qualification. |
| Q6 | Durable consumed-data registries and shared overlap gates; historical hash/provenance recovery; independent natural qualification with exclusions surviving removal of build/; acceptance receipt binding. | In progress: Q7 adds six multilingual regression disclosure entries and two RU context/surface quarantines; all original 121 lexical entries are preserved (198 at that checkpoint, including disclosed English and Russian source exclusions, historical word/epoch windows and article segments, and dictionary-only Q7 family addenda; see q6-word-epoch-article-segments and q6-q7-regression-families). the complete original v2 corpus now regenerates all 13,200 rows and its manifest byte for byte on Python 3.11/3.12 using three exact archived sources; its missing original evaluator is recovered, and the later mixed-script guard is integrated with a separate historical reproduction command (q6-v2-reproduction receipt). The Q2 source audit reconstructed neighbor frozen-tool 8d42d7e8 with exact SHA-256; the earlier corpus-generator bf2118a0 is now recovered by its original manifest hash (q6-neighbor-reproduction); all 15,000 historical neighbor rows now reproduce byte for byte using both the retained later generator and the recovered original source; the original-source run also reproduces the complete manifest object (q6-neighbor-reproduction). Historical model execution parity is not claimed. Four historical selectors project article, source window, segment and pinned dictionary families; refinement/word now select disjoint rows and meet original quotas in intercepted diagnostics, while their separate text outputs and epoch text remain blocked pending text-level checks (q6-disjoint-selector-admission); a source-bound text audit exposes historical article/family/surface collisions, cross-partition overlaps and unresolved words without qualifying a corpus (q6-text-exposure-audit). New unproven canonical families and prior historical gaps remain explicit; global coverage/fresh qualification is not claimed |
| Q7 | Current-product replay in CI with two identical projection hashes; threshold mutation fails with row diff; renewed baseline and measured job cost. | In progress: versioned portable driver/projection gate, permanent licensed 2,160-row inputs plus the original 12,000-row multilingual suite, separate lossless baselines and Q6 surface/context disclosures are wired after Gradle. Actual local Ubuntu24/ARM64 two-profile run: all 14,160 rows match, about 185 seconds at 2 CPU/4GiB; one-threshold CI mutant fails with 160 row diffs. Final 41 corpus commands/218 unit tests pass; previous observer pipeline receipt covered 121 tests with one disclosed conditional skip; the current editor-gate receipt covers 125 tests (124 pass, one conditional Kotlin-ready skip). See q7-ci-baseline receipt. Current inventory assigns all 145 tracked tools modules: 122 stdlib and 23 scientific; the latest local source-lock run covers 662 stdlib tests, while the previous scientific run covers 76 tests with one explicit MLX environment skip. The final exact-path adjustment was followed by focused tests. The original clean-checkout receipt retains 518 stdlib and 44 scientific tests, with one explicit MLX platform skip. Three original historical modules retain all ten test-method bodies and now use isolated, hash-verified reference/data/source workspaces. Original refinement/additional-epoch datasets are byte-identically reproduced and restored by a versioned attributed archive; its 230 additional-epoch articles/1,500 contexts are permanently excluded. See python-tools-tests.md and the q7-model-source-recovery receipt (71 direct project source versions; 8,555-vector numeric parity). Portable historical fixture recovery is verified in q7-portable-model-fixtures; required-backend checks now pass locally (seven original MLX CPU cases, five live Pymorphy cases, zero skips), with dedicated CI wiring and a complete hash-locked morphology closure. See q7-required-backends. review change 4 now repairs the real morphology exporter: original compilation fails on missing experiment dependencies, fixed 4,000-row exports agree across two fresh JVMs, 63 morphology tests pass and CI runs the exporter after Gradle (q7-morphology-export receipt). the historical distance-one diagnostic now validates editor/input/admission/UTF-16 edit and full Undo consistency, rejects five previously accepted real-observation corruptions, binds all 69 assets and cannot approve a new release; its exact-text ES historical gate correctly fails (q7-local-editor-gate receipt). Published main CI failed replay cache resolution and both emulator suites; fixture-scope routing, API26 clipboard cleanup and picker action are repaired locally with targeted device evidence (hosted-ci-fixture-routing). A standalone pinned toolchain resolver passes from an empty cache and both current replay corpora match (q7-replay-toolchain-provisioning). Other hosted editor failures and a rerun remain open |
| Q8 | Editor-deviation simulator with predefined outcomes; qa_editor profiles and APP-001…005 compatibility/continued-correction measurements on Fold under existing device/privacy rules. | In progress: independent five-profile simulator reproduced late-span word loss; one-shot same-session non-text cleanup fixes the supported two-phase case without restoring ownership. Nine simulator cases and all 1,352 JVM tests pass; actual two-profile 14,160-row replay matches both baselines. Committed source e2c49c4 also passes clean-checkout architecture and release/profile privacy/packaging checks offline. Receiver-side flag-only traces now calibrate four real EditText/WebView scenarios on API 26 and Fold/API 37 (eight native passes, zero skips); all 1,355 JVM tests pass. Both platforms deliver identical split/shift/no-op sequences, preserve every typed letter and correct all five consecutive WebView words. Owner settings/models and original diagnostic bytes are preserved; setup lifecycle records are disclosed. Commit ed275e5 passes clean-checkout offline release/profile privacy and packaging; both earlier replay receipts retain all bound hashes. Chrome now has two passing real-editor tests plus an independent numeric DOM gate (113 records): five corrections, exact Undo, sixth-word availability and a no-suggestions literal control. Eight oracle/server regressions are CI-wired; owner settings/data/models preserved and diagnostic rotation disclosed. A later explicitly opted-in API37 emulator run also passed both Chrome cases and the DOM gate; its initial tab-cleanup failure is disclosed in the same receipt. Full APP-001…005 display/action measurements and remaining qa_editor coverage remain (q8-chrome-editor receipt) |
| Q9 | JVM identity tests for uncovered frozen assets and policy constants/thresholds; byte/constant mutation failures naming the artifact; included in the JVM CI gate. | Verified locally; receipt above |

Q7 follow-up: the [general-suite gate](../acceptance/2026-11-03-q7-general-required-cases.md) requires eight previously failed editor, punctuation and neighbor cases to execute, in addition to the existing count floors; actual retained API 26 and API 37 reports pass. Hosted verification remains open.

Q7 general-skip follow-up: [the report gate rejects skipped identities outside its versioned 48-case inventory](../acceptance/2026-11-10-q7-known-general-skips.md); retained API 26 and API 37 reports and unexpected-skip mutations were checked. Known skips still need their separate evidence and hosted execution remains open.

Q7 Emoji route: the [owned-emulator memory check](../acceptance/2026-11-10-q7-known-general-skips.md#emoji-memory-route-and-general-opening-checks) now has an exact required case on API 26 and API 37. Each route passed locally. The general report also requires the two opening measurement checks. The current exception inventory has 59 identities and hosted execution remains open.

Q7 night learning: the [fresh-AVD route](../acceptance/2026-11-10-q7-known-general-skips.md#night-learning-fixture-evidence) requires seeding, worker promotion, rollback and Learning Lab progress in both API matrix jobs. The exact route passed locally on both APIs. Hosted execution and natural scheduler dispatch remain open.

Q7 personal-admission follow-up: the [personal-suite gate](../acceptance/2026-11-09-q7-personal-required-cases.md) requires all four admission scenarios by identity; an earlier API 26 report passes and substitution/skip probes are rejected. Current hosted execution remains open.

Q8 external-selection follow-up: [content-free session-disable diagnostics](../acceptance/2026-10-28-q8-editor-simulator.md#external-selection-diagnostics-follow-up-2026-11-09) now survive segment invalidation through a consent-bound one-shot outcome; simulator, privacy, analyzer, boundary and frozen product-replay checks pass locally. The [real-IME synthetic fixture](../acceptance/2026-10-28-q8-editor-simulator.md#real-ime-diagnostic-follow-up) passes on API 26 and 37, including a private-field negative control. Physical and hosted evidence remains open.

Q8 Backspace follow-up: [bounded timing probes](../acceptance/2026-10-28-q8-editor-simulator.md#general-api-26-attempt-and-targeted-reruns) show that activity pause precedes some accepted deletes; the observed text was stable after activity stop. Actual key detach was not observed during the listener window. The original general-suite failure and full Android run remain open.

Q7 fresh local follow-up: [API 26 boundary and restart suites](../acceptance/2026-11-09-q7-api26-boundary-repeat.md) passed at `f835c4f4`, with 306 general tests executed, 48 skipped, 19 separately routed tests and four restart phases. Complete workflow-shell, API 37 and hosted execution remain unverified at that source.

Q7 API 37 follow-up: an [interrupted general run and targeted repeats](../acceptance/2026-11-09-q7-api37-interrupted-failures.md) found 11 failures that passed separately after reinstalling the same APKs. The original sequential failure, full suite and hosted execution remain open.

Q7 API 37 repeat: [boundary and restart scopes](../acceptance/2026-11-09-q7-api37-animation-repeat.md) passed locally at `721e31b3` with CI animation scales disabled: 306 general tests executed, 48 skipped, 18 separate tests and four restart phases. The earlier failure's cause, full workflow shell and hosted execution remain open.

Q7 failure evidence: [expanded-candidate and foreign-edit fixtures](../acceptance/2026-11-09-q7-expanded-foreign-failure-captures.md) now capture before teardown on allowed emulators; five real methods and deliberate capture/denial controls were checked on API 37. The earlier sequential failure's cause remains open.

Q7 editing-panel follow-up: [the interrupted current API 37 general run and
starting-window evidence](../acceptance/2026-11-09-q7-editing-panel-occlusion.md)
record three failures and dropped touches. A fresh isolated repeat passes, but
the full CI workflow and cause of the persistent starting window remain open.
The [general report gate](../acceptance/2026-11-09-q7-editing-panel-required-cases.md)
now requires all nine panel scenarios to pass by name.

Q7 current API 37: the [complete local workflow shell](../acceptance/2026-11-09-q7-current-full-api37-ci.md)
passes at `8af345ea`, including all nine routed areas, four synthetic restart
phases, two editor process-death scopes and five voice scopes. The general
report retains 48 skips; hosted x86_64, current API 26 and the cause of the
earlier starting-window failure remain open.

Q7 current API 26: the [complete local workflow shell](../acceptance/2026-11-09-q7-current-full-api26-ci.md)
passes at `7ad41aea`, including the real picker, four synthetic restart phases,
both editor process-death scopes and five voice scopes. The general report
retains 48 skips; hosted x86_64 and the earlier starting-window cause remain open.

Q6 follow-up: [the unresolved retrieval source boundary](../acceptance/2026-11-09-q6-retrieval-suspended-source.md)
is a suspended hyphen, not a recoverable complete compound. The exact public
source and following form are quarantined; registry completeness and fresh
independent qualification remain open.
Its [historical verifier is isolated](../acceptance/2026-11-09-q6-retrieval-suspended-history-isolation.md)
from subsequent edits to five bound helpers, while the live admission gate is
checked separately. Other historical bindings remain to be audited.

Q6 consolidation: [v7 and v8 now use the shared holdout specification](../acceptance/2026-11-09-q6-v7-v8-shared-holdout.md)
with synthetic full-row parity and retained archived original sources. This does
not qualify a new independent holdout or close incomplete registry coverage.

Q6 verifier migration: the [historical neighbor segment verifier](../acceptance/2026-11-03-q6-neighbor-verifier-isolation.md) now runs with its archived guard in the isolated history runner. This removes one live-helper dependency; complete migration and independent qualification remain open.

Q6 follow-up: [partial EWT annotated-lemma exclusions](../acceptance/2026-11-03-q6-ewt-lemma-exclusions.md) register 10,485 exact vocabulary-filtered lemma keys. Unsupported shapes and out-of-vocabulary annotations remain uncovered; English independent qualification and Q6 remain open.

Q5's [isolated packed-word candidate](../acceptance/2026-10-28-q5-chat-packed-candidate.md)
reproduces all existing ranks and preserves the eight reviewed forms, but changing
the asset invalidates six existing qualification fingerprints. With those gates
unchanged, 658 of 4,720 disclosed unlabeled boundaries differ. The candidate is
not qualified or installed; this result supersedes treating the in-memory overlay
as representative of a product asset change.

U14 short-word order: [two visible corrections precede the seven-item expanded order](../acceptance/2026-10-29-u14-authored-short-hidden-order.md); the actual-IME metro selection test passes on API 26 and API 37.

Q5 short-word search: [source-bound token observations](../acceptance/2026-10-29-q5-authored-short-search.md) expose the ordinary and expanded suggestion order for three cases; all 24 observed contexts are registered.

Q5 search-completion diagnostics: [boundary records now retain local completion and counters](../acceptance/2026-10-29-q5-search-completion-diagnostics.md) while 14,160 frozen replay rows remain unchanged; admission and fresh qualification remain open.

Q5 authored deletion diagnostics: [boundary refusal attribution](../acceptance/2026-10-29-q5-authored-typo-diagnostics.md) separates length, incomplete search, valid words and ranking ambiguity; no admission policy is requalified.

Q5 source screen: [manually annotated subtitle subset](../acceptance/2026-10-29-q5-subtitle-source-screen.md) has only 67 unchanged short lowercase pairs and a cross-split duplicate under the review filter; no model scoring or publication of source text.

Q5 Undo coverage: [all 156 observed phrase corrections](../acceptance/2026-11-09-q5-phrase-boundary-undo.md) were reproduced at their own boundary and exactly undone, including 29 intermediate multiword positions. [Continuation after Undo](../acceptance/2026-11-09-q5-undo-continuation.md) also passes 123 disclosed cases through 381 following words. One real-IME continuation scenario passes API 26 and 37 and is required by CI; Fold remains open.

Q5 reviewed chat fix: [13 observed conversational forms](../acceptance/2026-11-09-q5-chat-phrase-protection.md) are now protected; full-session replay removes those 13 edits with no new edits in the disclosed sample. Two representative controls pass real-IME checks on API 26 and 37 and are required by CI. Context-dependent capitalization and independent qualification remain open.

Q5 broader phrase replay: [9,543 disclosed Tatoeba phrases](../acceptance/2026-11-09-q5-tatoeba-full-phrase-replay.md) ran in full controller sessions twice; 169 boundary changes, 33 exact final-word Undos and no observed prefix changes. Input and observed contexts are registered; verified natural controls and independent qualification remain open.

Q5 authored deletion replay: [19 disclosed synthetic phrases](../acceptance/2026-10-29-q5-authored-typo-replay.md) yield seven intended matches and seven exact Undo checks; 12 forms remain unchanged.

Q5 authored-phrase replay: [20 disclosed punctuation-stripped utterances](../acceptance/2026-10-29-q5-authored-phrase-replay.md) remained unchanged in one-session controller replay; Undo was not exercised.

Q5 reviewed-phrase follow-up: [eleven full-session reviewed controls](../acceptance/2026-10-29-q5-reviewed-phrase.md) confirm eight disclosed colloquial preservation failures and 11 exact Undo checks; all observed stage contexts are registered. Independent qualification remains open.

Q5 boundary attribution: [metadata-only per-word replay](../acceptance/2026-10-29-q5-phrase-boundary-sources.md) attributes those eight failures to three contextual, one joint-rescue and four local-policy diagnostic events. The disclosed sample cannot establish a population error rate or qualify a policy change.

Q5 follow-up: [multiword controller replay](../acceptance/2026-10-29-q5-multiword-replay.md) now runs six disclosed Russian phrases in one session each, covers revisions and exact Undo, and registers 20 stage contexts in both ledgers. Larger verified control data and full Q5 acceptance remain open.

Q7 API 26 follow-up: [all seven routed scopes via direct instrumentation](../acceptance/2026-10-29-q7-api26-direct-suites.md) completed without failures; the general run includes 48 skips. API 37, Gradle-connected routing and hosted CI remain open.

Q7 CI report follow-up: [JUnit testcase and scope verification](../acceptance/2026-10-29-q7-android-report-integrity.md) rejects fabricated aggregate counts, inconsistent statuses and misrouted special suites. A full connected/hosted rerun remains open.

Q5 distance hypothesis: [a disclosed recorded-choice screen](../acceptance/2026-10-29-q5-distance-screen.md) isolates 91 synthetic one-operation mistakes and three reviewed controls with higher-distance selected candidates; it does not test multi-error gains or a modified policy.

Q5 multi-operation contrast: [1,800 disclosed historical rows](../acceptance/2026-10-29-q5-multiedit-distance.md) include 281 exact targets selected at distance greater than one. A blanket distance veto would lose these selected corrections; source-prefix input deviations and remaining disclosure work are explicit.

Q7 API 37 editor test follow-up: [the reproduced symbols tap failure and reordered test](../acceptance/2026-10-29-q7-editor-boundary-api37.md) have three targeted API 37 passes and one API 26 pass. The original full run remains failed; fresh full and hosted runs are pending.

Q7 API 37 general rerun: [304 executed and 48 skipped without failures](../acceptance/2026-10-29-q7-api37-general-rerun.md) on the earlier APK; later source changes and hosted CI still require verification.

Q7 API 37 general result: [the old-APK run completed with six failures](../acceptance/2026-10-29-q7-api37-general-result.md); targeted reruns do not establish a full-suite pass.

Q7 API 37 composing follow-up: [five suite-only input failures passed isolated reruns](../acceptance/2026-10-29-q7-api37-compose-isolation.md); the cause and a full-suite pass remain unproven.

Q5 packed candidate follow-up: [multi-operation comparison](../acceptance/2026-10-29-q5-packed-multiedit-comparison.md) exposes 476 lost and one gained synthetic target match with unchanged invalidated qualification gates; three newly exposed output contexts are registered.

Q5 report integrity: the [v2 chat reporter](../acceptance/2026-11-09-q5-undo-report-v2.md) checks the claimed Undo against actual editor snapshots and rejects missing or contradictory evidence; the historical reporter and its receipts are preserved. Independent chat qualification remains open.

Q5 replay follow-up: [the original 34,330 disclosed chat rows](../acceptance/2026-11-09-q5-chat-undo-replay.md) regenerated byte for byte from their historical ledger and were replayed through the current controller; v2 verified exact text Undo on all 16,819 changed boundaries. Unproofread controls and independent qualification remain open.

Q5 current-controller follow-up: [the disclosed 34,330 rows and v3 source/cluster-bound report](../acceptance/2026-11-10-q5-cluster-report-integrity.md#current-controller-replay-with-v3-report) show 33 changed unproofread controls and zero text Undo failures across 16,811 changes. Natural-chat qualification and device acceptance remain open.

Q5 control follow-up: [the 9,543 controls were replayed and matched against the earlier per-case reviews](../acceptance/2026-11-10-q5-current-control-review.md): 30 identical case-only changes and three previously reviewed possible source typos; all eight colloquial preservation cases remain unchanged. Five lowercase-context cases and independent qualification remain open.

Q5 personal-case follow-up: [real-IME tests now cover Undo learning for the three reviewed lowercase forms](../acceptance/2026-10-28-q5-personal-case-rejection.md#reviewed-forms-through-the-real-ime) on API 26 and 37. Learning must be enabled, and the first automatic case change still occurs; natural context qualification and Fold evidence remain open.

Q5 reviewed protection: [seven exact chat forms](../acceptance/2026-11-09-q5-curated-chat-protection.md) are vetoed for automatic substitution, including compact admission; eight disclosed controls are preserved and frozen replay matches. Independent natural controls, broader family coverage and physical acceptance remain open.

Q5 real-IME follow-up: [reviewed phrase controls and manual selection](../acceptance/2026-11-09-q5-reviewed-chat-real-ime.md) cover all seven protected forms. Pre-fix negative controls demonstrate the original substitutions; the previously lost `бобо` proposal is again selectable without automatic replacement on API 26 and 37. Nine identities are required by the general Android CI report gate; hosted and Fold results remain open.

Q7 current stdlib repeat: [202 modules and 987 tests](../acceptance/2026-11-09-q7-current-python-inventory.md#current-stdlib-inventory-after-v6-target-recovery) passed locally at `7676bc24` without skips. Scientific, Android and hosted execution remain separate.

Q7 current scientific repeat: [30 modules and 123 tests](../acceptance/2026-11-09-q7-current-python-inventory.md#current-scientific-profile-in-a-temporary-clone) passed locally at `91a8e343` with one skip; hosted Linux and Android remain unverified.

U14 physical candidate-view follow-up: [two isolated view tests pass on the unfolded Fold](../acceptance/2026-10-28-u14-expanded-ui.md#fold-candidate-view-follow-up--2026-11-10), with IME settings, diagnostics and preferences unchanged. Real-IME Fold layout and manual accessibility remain open.

U14 real-IME fixture: [explicit Fold opt-in and personal-store checks](../acceptance/2026-10-28-u14-expanded-ui.md#real-ime-physical-fixture-preparation--2026-11-10) are implemented; all three scenarios pass on API 37. A physical run with host diagnostic backup and manual accessibility are still required.

U14 Fold real-IME follow-up: [all three expanded-candidate scenarios passed](../acceptance/2026-10-28-u14-expanded-ui.md#fold-real-ime-expanded-candidates--2026-11-10); system settings, preferences and non-diagnostic stores matched. Diagnostic rotation displaced one original journal, preserved in a private owner backup. Installed app source identity, other display configurations and manual TalkBack remain open.

U14 diagnostic retention: [a private test fixture and an enabled-diagnostics regression](../acceptance/2026-10-28-u14-expanded-ui.md#private-physical-fixture-and-diagnostic-retention) passed targeted API 37 checks; the Russian expanded-order assertion remains ordinary-only, and the revised physical fixture still needs Fold validation and a host-side backup.

U14 Fold diagnostic retention: [both private expanded-candidate scenarios passed](../acceptance/2026-10-28-u14-expanded-ui.md#fold-private-fixture-retention-check) with exact post-run owner-store and IME-setting comparison; the original test APK was restored. The earlier displaced journal remains in the private backup; manual accessibility and the other display configuration remain open.

U14 live TalkBack: [the expanded-row traversal trace](../acceptance/2026-10-28-u14-expanded-ui.md#2026-11-24-live-talkback-traversal-of-the-expanded-row) verifies touch exploration and selection on API 37 and reproduces the sequential swipe gap. Popup experiments did not reliably preserve outside double-tap selection, so they were reverted. A single-window accessibility path remains open.

U9 private deletion regression: [real-IME API 37 tests reproduce partial deletion of ZWJ and modifier emoji](../acceptance/2026-10-27-u9-emoji-panel.md#private-field-complex-emoji-deletion-gap). Ordinary-field deletion passes; a no-editor-read ownership-safe fix remains required.

U9 private emoji deletion: [owned composing-span fix](../acceptance/2026-10-27-u9-emoji-panel.md#private-field-owned-emoji-deletion-fix) passes API 26/API 37 and five physical Fold cases without payload reads; the updated APK is installed and owner data matched. Other display configurations, nonconforming editors and manual TalkBack remain open.

U9/Q8 editor-change follow-up: [three private emoji scenarios](../acceptance/2026-10-27-u9-emoji-panel.md#external-editor-changes-after-private-emoji-insertion) pass API 26, API 37 and Fold with zero payload reads and preserved owner stores. Silent editor changes, third-party coverage and hosted CI remain open.

U9 private WebView follow-up: [emoji deletion and continuation](../acceptance/2026-10-27-u9-emoji-panel.md#private-webview-emoji-deletion) pass API 26/37 and Fold with zero Rune payload reads. An initial Fold teardown failed on appended session records and changed WebView preferences; the revised repeat preserved owner-state snapshots. Third-party apps and hosted CI remain open.

U9 private Compose follow-up: [emoji deletion and continuation](../acceptance/2026-10-27-u9-emoji-panel.md#private-compose-emoji-deletion) pass API 26/37 and Fold in an independent Compose QA editor, with zero payload reads. The first Fold attempt appended diagnostic setup events and retains a recovery archive; the revised repeat preserved the owner snapshot. Physical tile touch, other apps and hosted CI remain open.

Q6 corpus recovery: [the complete v3 and v4 historical corpus bytes](../acceptance/2026-10-27-early-ru-source-recovery.md#complete-retained-v3v4-corpus-bytes) are retained in two verified compact archives, including multilingual spelling, punctuation and protected-token files. They remain disclosed, not fresh qualification; per-row attribution and available-v6 remain open.

Q6 control protection: [654 dictionary-unsupported early RU target surfaces](../acceptance/2026-11-10-q6-early-unknown-control-surfaces.md) are now source-bound in the control registry, including 645 previously absent exact keys; no family or independent qualification is inferred.

Q6 control importer: [punctuation and protected historical components](../acceptance/2026-10-27-early-ru-source-recovery.md#punctuation-and-protected-control-importer-integration) now consume the retained v3/v4 archives and reconstruct all 18 existing registry entries with identical keys; independent attribution and qualification remain open.

Q6 historical controls: [v2–v4 disclosed inputs](../acceptance/2026-11-10-q6-historical-qualification-control-inputs.md) now contribute 30,600 exact spelling contexts and 30,997 additional multilingual surface keys without altering punctuation article coverage. Source attribution and independent qualification remain open.

Q6 attribution follow-up: [v2–v4 source notices and maps](../../tools/typing_experiments/historical-qualification-v3-v4/NOTICE.md) now locate candidate articles for all 34,200 Wikipedia-derived rows. Across 25,630 metadata records, all 25,013 distinct language-qualified article identities agree on title and URL. Wikimedia's terms list the article URL as an attribution method. The Parquet schemas omit revision IDs. Article-specific attribution conditions, the distribution license and the wider publication review remain open.

## Q6 outstanding evidence

Q6 rejected conversation v1: [the restored preparer](../acceptance/2026-10-27-unmanifested-conversation-audit.md#exact-replay-and-control-exclusions-for-the-rejected-corpus) regenerated all 29,162 original rows and reproduced the split-overlap rejection. The control ledger now carries both categories of context and surface keys plus 5,414 source-sentence keys. Independent qualification remains open.

Q6 recovered corpus control coverage: [the verified projection](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#control-exclusions-for-the-three-recovered-corpora) covers 49,002 exact historical rows across Supervised Conversation v2, Context Feature and Available Clean v6. It adds 18,596 context, 7,643 surface and 4,267 source keys. The independent qualification gate remains open.

Q6 Joint control coverage: [the projection of nine exact row files](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#joint-and-diagnostic-rare-ranking-control-coverage) covers 54,364 historical inputs across the three Joint corpora and Diagnostic Rare Ranking. It adds 54,364 context, 47,449 surface and 5,047 source keys. The lexical article and context keys were already covered. Full-source sentence provenance and independent qualification remain open.


Q6 final available-clean v6: [the full parent replay and restored corpus](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-24-byte-exact-final-available-clean-v6) match the original plan and all four JSONL/TSV hashes for 15,655 rows. The original plan verifies the parent context digest and clean preparer. Article-revision attribution, distribution rights and independent quality qualification remain open. The historical entries below retain the status at the time of each check.

Q6 v6 exclusions: [both restored partitions](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#exact-v6-exclusion-ledger-entries) reproduce their exact article, family, sentence and context key sets in the ledger. Global freshness coverage remains incomplete.

Q6 v6 overlap by row: [the restored partitions and 239-entry ledger](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#exact-v6-rows-affected-by-article-overlap) identify 690 calibration and 710 holdout rows in the spelling-or-neighbor article union. The broader registry finds 1,469 and 1,402 rows respectively. Independent qualification remains open.

Q6 v6 revision attribution: [the content pilot](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#first-historical-revision-content-witnesses) found byte-exact full-article versions for 32 sampled pages after rerunning the published cleaner. Sixteen pages have multiple matches in the tested revision window. The exact dump revision identities and passage-level licensing remain open.

Q6 first-shard revision witnesses: [the complete `0011.parquet` check](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#full-revision-content-check-for-shard-0011) found exact full-text matches for all 355 mapped pages, covering 919 calibration and 773 holdout rows. The other nine shards and original dump revision identities remain open.

Q6 second-shard revision witnesses: [the complete `0012.parquet` check](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#complete-revision-content-check-for-shard-0012) found exact matches for all 292 pages. Both shards together cover 647 pages and 3,086 v6 rows. The shared command supports each remaining pinned shard.

Q6 third-shard revision witnesses: [the `0013.parquet` audit](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#revision-content-check-for-shard-0013) found exact matches for 324 of 327 pages. Three missing calibration articles account for 15 rows. The offline checker accounts for all 974 indexed pages across the first three shards.

Q6 fourth-shard witnesses: [the `0014.parquet` audit](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#revision-content-check-for-shard-0014) found exact matches for 344 of 345 pages. The first four reports and both exact corpus files give full-text witnesses for 1,315 pages and 6,291 rows. Four missing pages account for 19 rows.

Q6 fifth-shard witnesses: [the `0015.parquet` audit](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#revision-content-check-for-shard-0015) found exact matches for 332 of 335 pages. Across five shards, 1,647 pages and 7,903 rows have by-date witnesses. Seven unavailable IDs affect 34 rows. A separate Wayback capture confirms the complete normalized source window for the four missing holdout rows from 0014.

Q6 sixth-shard witnesses: [the `0016.parquet` audit](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#revision-content-check-for-shard-0016) found full-text matches for 364 of 366 pages. Across six shards, 2,011 pages and 9,648 rows have by-date witnesses. Nine unavailable IDs affect 44 rows.

Q6 seventh-shard witnesses: [the `0017.parquet` audit and extended history check](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#revision-content-check-for-shard-0017) found by-date full-text matches for 350 of 354 pages. Across seven shards, 2,361 pages and 11,306 rows have by-date witnesses. Thirteen unavailable IDs affect 64 rows.

Q6 eighth-shard witnesses: [the `0018.parquet` audit](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#revision-content-check-for-shard-0018) found by-date full-text matches for 340 of 343 pages. Across eight shards, 2,701 pages and 12,934 rows have by-date witnesses. Sixteen missing pages affect 78 rows.

Q6 ninth-shard witnesses: [the `0019.parquet` audit](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#revision-content-check-for-shard-0019) found by-date full-text matches for 338 of 342 pages. Across nine shards, 3,039 pages and 14,573 rows have by-date witnesses. Twenty missing pages affect 97 rows. The final shard covers 985 rows.

Q6 all ten shards: [the complete v6 revision-content audit](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#revision-content-check-for-shard-0020) finds by-date full-text witnesses for 3,239 of 3,265 pages and 15,529 of 15,655 rows. The live API lacks 26 original pages covering 126 rows. Original dump identities, passage-level attribution, distribution review and independent qualification remain open.

Q6 v6 archive and translation follow-up: [all recorded historical translation-notice pages](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#revision-content-check-for-shard-0020) have receiving-article full-text witnesses, covering 2,190 rows. Archived source windows independently cover 47 of the 126 rows whose pages are absent from the live API. Seventy-nine rows lack either form of complete text evidence.

Q6 ancestry exclusions: [six exact recovered payloads](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#recovered-ancestry-exclusions) brought the ledger to 235 entries.

Q6 Rare Ranking exclusions: [verified historical source windows and dictionary analyses](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#diagnostic-rare-ranking-source-windows-and-family-exclusions) cover both exact partitions and bring the ledger to 239 entries.

Q6 role model: [the original v6 model and exact supervised family entry](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-23-earlier-v6-preparation-chain) passed the current JVM parity and identity check. The v5 model and full training replay remain open.

Q6 ancestry follow-up: [the original noun-case plans and audits](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-23-exact-noun-case-ancestry) match five historical hashes. The existing contrast generator also reproduces all 1,140 original authored training rows. The natural noun-case payload remains open.

Q6 authored noun-case follow-up: the reproduced training source is bound to 25 canonical family keys and 576 new context exclusions. The scientific CI route regenerates the entries and checks the original payload hash.

Q6 grammar contrast follow-up: [both authored corpora](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-23-exact-grammar-contrast-inputs) match their original hashes and contribute 412 new context exclusions. Scientific CI also checks these registrations.

Q6 noun-case regression follow-up: [the broad-v2 and instrumental results](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-23-broad-and-instrumental-noun-case-inputs) match both original result digests. The logged commands recover their selection plans. The manifests and row files remain open.

Q6 focused Tatoeba follow-up: [the grammar-focused plan](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-24-focused-tatoeba-plans-and-availability) matches the original policy digest, and the original availability output is retained for both the grammar and right-context-focused-v2 selections.

Q6 Tatoeba manifest follow-up: [the original supervised-v2, grammar-focused and noun-case-v3 manifests](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-24-original-tatoeba-exclusion-manifests) match three original file hashes. The noun-case v3 exclusion map also matches its independent 56-entry digest.

Q6 Tatoeba CC0 follow-up: [the exact 23,077-row split and train-only counts](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#byte-exact-cc0-split-and-training-counts) reproduce both original hashes from the pinned public archive without scoring. The separate detailed export and its derived payloads remain open.

Q6 Tatoeba conversation follow-up: [the original context-feature CC0 corpus](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#exact-cc0-context-feature-conversation-corpus) reproduces both original row hashes and the manifest. The 4,444 rows carry packed family IDs. The later supervised and detailed-export payloads remain open.

Q6 supervised conversation v2 follow-up: [the original builder and all 28,903 CC0-derived rows](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#exact-supervised-conversation-v2-corpus) match the historical digests, including the three original partitions and manifest. The detailed-export cohorts remain open.

Q6 detailed Tatoeba follow-up: [five captured preparers](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#detailed-export-preparers-and-family-representation) cover thirteen original corpus paths and identify the packed family representation. Three source hashes match the historical manifests. The corpus bytes remain open.

Q6 early Wikipedia Context Feature follow-up: [both original row files](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#exact-early-wikipedia-context-feature-rows) reproduce all 9,469 rows. The captured preparer is retained. The original Context Feature manifest matches its historical hash and binds 28 verified input files. [Word Context and Word Context Extra](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#exact-early-wikipedia-word-context-corpora) now match all four original row hashes and both manifest hashes.

Q6 Word Context training-count follow-up: [the archived counter and binary packer](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#historical-word-context-training-count-sources) reproduce both original output hashes from nine verified Wikipedia shards and 23 verified row inputs. The historical ranking experiment remains rejected.

Q6 role-training ancestry: [both v5/v6 plans and frozen model bindings](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-23-earlier-v6-preparation-chain) match the four original digests and confirm 38 declared training families with the same recorded v5/v6 group, vector and candidate-selection inputs. Three later cohort bindings and the final v6 JSONL remain open.

Q6 role-training candidate replay: [the historical production controller](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-24-historical-v5v6-candidate-pool-replay) regenerated all 9,094 groups and 134,459 candidates from the byte-exact authored v5 rows. The resulting JSONL matches the original shared v5/v6 digest. [Both refits](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-24-byte-exact-v5v6-refits) reproduced the original model weights and the shared vectors byte for byte. The historical observations, selection receipt and independent qualification remain open.

Q6 role-training authored manifests: [both v4 and v5 manifests](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-24-historical-v5v6-candidate-pool-replay) now match the original receipt digests after restoring the original dictionary installation receipt and generator path key.

Q6 candidate-pool reproducibility: [the recovery command](../../tools/typing_experiments/recover_role_training_groups.py) reproduced the original shared groups from a clean checkout without pre-existing build outputs or chat history. It checks both archived authored corpora and the resulting groups against their original digests.

Q6 training reproducibility: [the two-fit command](../../tools/typing_experiments/refit_historical_role_models.py) ran from a clean checkout with supplied, digest-verified count tables and recovered groups. Both weights and the vector archive matched their original bytes. The command refused a modified count table before fitting.

Q6 training import provenance: [the exact v5/v6 refit](../acceptance/2026-10-29-q6-historical-role-trainers.md#runtime-imports-in-the-byte-exact-v5v6-refit) records and verifies nine and two project modules against the historical Git tree, including the v5 morphology ranker omitted from the direct bindings. Both weights and the vector archive still match. Original preamble imports and other model records remain open.

Q6/Q7 role replay in hosted CI: [the workflow step](../../.github/workflows/ci.yml) reproduced the historical group digest in a local depth-one checkout after fetching the pinned revision. It uploads the numeric receipt. Hosted execution remains open.

Q6 v6 family follow-up: [the declared-family audit](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-23-confirmed-historical-family-exposure) confirms exposure for 2,603 contexts and verifies both candidate TSV projections. Testing the instrumental possibilities alone produced no exact JSONL match. Historical declared families and JSONL-only fields remain open.

Q6 refinement family follow-up: [the exact archived partitions and their concatenation](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#refinement-archive-families) bind eight original paths in each of three plans. The v6 audit now confirms prior exposure for 2,732 contexts. The full JSONL digests remain open.

Q6 legacy spelling follow-up: [the exact v6–v12 spelling rows](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#exact-legacy-spelling-v6v12-rows) match all seven original digests and raise the confirmed family-exposure total to 2,797 contexts. Reliable Side v5 and the final v6 JSONL payloads remain open.

Q6 Reliable Side v5 follow-up: [all 1,690 original contexts and the availability report](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#exact-reliable-side-v5-contexts) match their historical digests. The recovered contexts complete the 17,886-article exclusion input for sentence-corpus-v6. The sentence-corpus-v6 and final v6 payloads remain open.

Q6 sentence-corpus-v6 follow-up: [all 2,068 original contexts and the availability report](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#exact-sentence-corpus-v6-contexts) match their historical digests. All twelve context and additional article payloads are now exact, and the successor index contains all 19,954 excluded articles. The final v6 JSONL digests remain open.

Q6 v6 Side-input follow-up: [Side and Fresh Side v4/v5](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-23-byte-exact-side-and-fresh-side-inputs) now match all twelve historical payload hashes. The original Side and Fresh Side v5 plans and manifests also match, with 92 and 38 recorded exclusion families respectively. The three failed additional cohorts and the final v6 JSONL remain open.

Q6 v6 exclusion-input follow-up: [the exact Natural Frozen input](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-23-byte-exact-natural-frozen-input) recovers the original plan, manifest and 3,200 variants in four files. Its two JSONL files are part of the v6 family-exposure inputs. Other exclusion inputs and the v6 JSONL remain open.

Q6 v6 source-input follow-up: [all seven early Wikipedia context pools](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-23-byte-exact-early-wikipedia-context-pools) now match the original row digests for 1,204 contexts. Three later aggregate availability reports also match their original hashes. Their row files, the v6 plan and the two final v6 JSONL files remain open.

Q6 v6 preparation follow-up: [the earlier preparation chain](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-23-earlier-v6-preparation-chain) restores one source against its original SHA-256 and six logged source captures, including the missing fresh-matched-v5 preparer. The historical exposure calculation distinguishes declared dictionary lemmas from the broad-v2 corpus's packed numeric family IDs.

Q6 v6 parent selection: [the exact parent plan](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-24-byte-exact-v6-parent-selection-plan) binds ten public shards and 76 exclusion and context inputs. Five earlier selection plans match recorded hashes, including the first Wikipedia and focused Tatoeba plans. Five outstanding payloads and the final available-clean plan and JSONL remain open.

Q6 Fresh Matched v5: [all 45 original context rows](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-24-byte-exact-fresh-matched-v5-context-input) match the v6 parent plan. The two other additional cohort payloads and both noun-case payloads remain open.

Q6 reliable Side ancestry: [the reconstructed Diagnostic Rare Ranking manifest](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-24-diagnostic-rare-ranking-provenance) binds both rare-ranking payload hashes. Existing verified sources account for 15,188 of the 16,152 recorded blocked article identities. The rare-ranking bytes and the unaccounted article identities remain open.

Q6 rare-ranking ancestry: [both original first-letter holdouts](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-24-diagnostic-rare-ranking-provenance) match their protocols and payload digests. Together with verified Joint article keys they reproduce all 7,521 recorded rare-ranking article exclusions. Earlier Joint declared families and the rare-ranking payloads remain open.

Q6 Joint and Rare Ranking: [all nine original payloads](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-24-exact-joint-and-diagnostic-rare-ranking-payloads) match their digests. Their 964 recovered Rare Ranking article keys complete the 16,152-key Reliable Side input. Reliable Side v5 and the final v6 JSONL payloads remain open.

Q6 publication follow-up: [the v6 calibration source screen](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-23-v6-calibration-publication-screen) found 14 unavailable source pages, one current copyright warning and 240 translated-article notices. Attribution and distribution rights for the exact archive remain open.

Q6 holdout publication follow-up: [the snapshot map and current article screen](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-24-v6-holdout-article-availability) identify all 1,614 source pages and 266 current translation notices. Historical revisions, passage-level attribution and distribution rights remain open.

Q6 holdout historical notices: [the discussion-revision screen](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-24-historical-holdout-translation-notices) projects 251 notices and records verification outcomes for their 41 distinct numeric revision references. Removed notices, exact excerpt revisions and distribution rights remain open.

Q6 holdout follow-up: [the source index and JSONL field check](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-23-holdout-source-index-and-jsonl-field-check) bind all 1,630 holdout groups to their registry entries and validate every variant against the exact TSV. The [two excluded context anchors](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-23-source-anchors-for-the-two-excluded-contexts) restore the pre-exclusion group, family and cue-type counts. Both complete JSONL hashes and the parent context digest remain open.

[The registered available-v6 article identities](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#all-registered-v6-source-article-identities)
now resolve to 3,265 page IDs in ten pinned public shards, with source-only
rechecking and the existing 140/144 historical article intersections mapped to
their shards. Original corpus rows, the historical plan, article revisions,
complete registry coverage and independent qualification remain open.

[The v6 registered source contexts](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#source-context-anchors-for-registered-v6-keys)
now have candidates in the pinned public articles: 3,277 unique same-partition
locations, 14 ambiguous keys and one additional cross-partition candidate.
These are source anchors only; the original typo rows and selection remain open.

[Registered v6 target-key candidates](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#target-key-candidates-from-source-anchors) map 6,576 distinct keys to source anchors; six have multiple candidates and 2,488 remain unmatched. Historical rows, errors, labels and independent qualification remain open.

[Exact v6 calibration TSV](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#all-remaining-target-keys-and-byte-exact-calibration-tsv) matches the original manifest for all 7,905 rows. The [exact holdout TSV](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#2026-11-23-byte-exact-holdout-tsv-recovery) matches the manifest for all 7,750 rows and is retained locally. Rival associations cover all remaining registered target keys. The [calibration source index](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#calibration-tsv-source-index-and-jsonl-reconstruction-probe) links all TSV context groups to their registered articles, sentences and families. The [calibration attribution map](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#calibration-article-urls-and-plan-input-gaps) binds all 1,651 article titles and URLs to the same public source snapshot. Both original JSONL files, the plan, publication rights and independent qualification remain open.

[The maintained v7–v12 builder](../acceptance/2026-10-28-q6-collector-registry-gates.md#source-bound-future-v7v12-rows) now attaches source article/segment/context and dictionary families to future rows, detects canonical-family overlap and binds the inputs. Current incomplete registry coverage still blocks collection; full provenance and independent qualification remain open.

[The v6 builder](../acceptance/2026-10-28-q6-base-collector-gates.md#source-bound-v6-follow-up) now uses the same source and family checks, and the shared exclusion reader rejects duplicate paths. Independent collection is still blocked by incomplete coverage.

[English UniMorph exact-form exclusions](../acceptance/2026-11-10-q6-english-unimorph-surfaces.md)
add 22,647 source-attested form keys beyond the preceding lexical/EWT keys;
English family completeness and independent qualification remain open.

[Word-ranking synthetic-label compatibility](../acceptance/2026-10-28-q6-word-history-families.md)
reproduces all 9,000 disclosed row identities, splits, edit cohorts, operations
and typed forms with the bound selector, pinned vocabulary and a hash-verified
helper candidate. The original manifest did not bind that helper; historical
execution, full source lineage and independent natural qualification remain open.

[Bound Parquet preflight v2](../acceptance/2026-11-09-q6-bound-parquet-reader.md)
removes the injectable decoder from this diagnostic and binds selected runtime
files and all recorded PyArrow package files; it has fixture, no-build and full
pinned-source decoding evidence for the earlier reader version, plus
a three-article end-to-end probe with real ledgers and dictionary. Full
decoder supply-chain attestation, registry coverage, source labels, collector
integration and independent qualification remain open.

[Taiga dev dictionary and surface exclusions](../acceptance/2026-10-28-a2-taiga-source-screen.md#dictionary-and-surface-exclusions) quarantine 4,528 dictionary families and 6,185 exact public fragments; the [within-sentence context addendum](../acceptance/2026-10-28-a2-taiga-source-screen.md#within-sentence-source-context-exclusions) protects the source contexts; the annotated-lemma addendum adds 2,242 previously unblocked exact lemmas and 17 dictionary families. Document identity, cross-sentence contexts and global qualification remain open.

[English Tatoeba exact surfaces](../acceptance/2026-11-09-q6-tatoeba-english-surfaces.md) add 26,735 exact keys outside the EWT fixture to the strict family preflight (26,324 were not already in the prior control surface keys); English morphology, provenance completeness and independent qualification remain open.

[Surface exclusion binding v2](../acceptance/2026-11-09-q6-surface-binding-v2.md) carries the mandatory surface fixture and helper hashes through preparation, training and evaluation; historical ledger-only verification remains separate. Coverage and independent qualification remain open.

[Full-frequency English EWT lemmas](../acceptance/2026-11-05-q6-ewt-packaged-lemmas.md) add 845 exact exclusions. The lexical registry now has 211 entries; both lexical and control coverage remain incomplete. The selector text diagnostic and live row guard reject internally apostrophe-joined source fragments; the original guard remains available to isolated historical verifiers. The coverage and text-admission migration remains open.

The same EWT receipt records a separate exact token-surface exclusion fixture,
enforced for English `new-families` proposals. It is not a complete morphology
or a replacement for the unresolved registry and qualification requirements.

[Packaged English EWT lemmas](../acceptance/2026-11-05-q6-ewt-packaged-lemmas.md) quarantine 850 additional exact public dictionary lemma keys; English family coverage and qualification remain incomplete.

[Selector row source checks](../acceptance/2026-11-05-q6-retrieval-row-source.md) now verify source article, window, token boundary and dictionary analyses; 1,790 reconstructed disclosed retrieval rows match, while 10 partial tokens are refused. Source-label and decoder attestation, coverage migration and independent qualification remain open.

[Selector text preflight v1](../acceptance/2026-11-03-q6-selector-text-preflight.md) adds a source-lock-bound diagnostic for full text and both control registries; publication remains blocked and integration and complete coverage remain open.

[Neighbor prefix compounds](../acceptance/2026-11-03-q6-neighbor-prefix-compounds.md) conservatively exclude 232 complete source-attested forms and 262 additional lexical contexts; independent qualification remains open.

[EWT control-source exclusions](../acceptance/2026-11-03-q6-ewt-control-source.md) mirror all 1,174 disclosed document keys into a source-only control entry, with old verifier compatibility. English family qualification and global coverage remain open.

[English source overlap](../acceptance/2026-11-03-q6-english-source-overlap.md) is now detected for disclosed Tatoeba/EWT article and sentence identities, including source-backed protected controls. English family qualification and global coverage remain unsupported; the EWT control identity is now covered by the follow-up below.

[Truncated text completions](../acceptance/2026-11-03-q6-truncated-text-completions.md) recover all 24 cut-word source occurrences in the three retained text corpora, adding 19 exact forms and one dictionary family; four source heads remain exact-only. Independent qualification and other provenance remain open.

[Additional-epoch full source-token boundaries](../acceptance/2026-11-03-q6-epoch-text-source-boundaries.md) exclude 167 historical forms and 262 contexts, including 105 newly excluded forms. Unknown families, historical provenance and independent qualification remain open.

[Refinement full source-token boundaries](../acceptance/2026-11-03-q6-refinement-text-source-boundaries.md) exclude 1,370 historical forms and 2,606 contexts, including 1,291 newly excluded forms. Unknown families, historical provenance and independent qualification remain open.

[Control source-identity guard](../acceptance/2026-11-03-q6-control-article-overlap.md) now rejects disclosed articles or Tatoeba sentences even when both word and context differ. The registry remains incomplete; the historical named-regression check runs with its archived helper.

[Historical text verifier isolation](../acceptance/2026-11-03-q6-historical-text-verifier-isolation.md) runs both source-token registration checks with hash-verified archived control and selector helpers, keeping their original ledger bindings intact. The future coverage schema, checked-text admission and other historical bindings remain open.

[Freshness migration blockers](../acceptance/2026-11-03-q6-freshness-migration-blockers.md): the current control schema cannot represent complete coverage, nonempty new selector texts are refused, and in-place guard edits invalidate bound historical checks. A versioned, evidence-preserving migration is required before fresh qualification.

Q6 all-text follow-up: [258 full historical source-token surfaces and 384 contexts](../acceptance/2026-11-03-q6-all-text-source-boundaries.md) are excluded, including 161 surfaces beyond the preceding shared-fragment audit. Unknown families and independent qualification remain open.

The [shared historical text source-token audit](../acceptance/2026-11-03-q6-shared-text-source-boundaries.md) adds exact exclusions for 97 previously unblocked full source surfaces and 174 contexts behind disclosed shared unknown fragments; canonical families and global qualification remain open.

The [empty-prefix current-controller probe](../acceptance/2026-10-29-a2-empty-controller.md) discloses and protects 42 observed candidate contexts; it formed no model request for the tested token and does not qualify A2.

The [A2 empty-prefix scorer controls](../acceptance/2026-10-29-a2-empty-prefix-scorer.md) are disclosed in both applicable ledgers; one synthetic blank-prefix request produced scores and remains a qualification counterexample.

The [authored phrase deletion inputs](../acceptance/2026-10-29-q5-authored-typo-inputs.md) register 19 deterministic synthetic typo phrases and their intended original words before replay.

The [authored dialogue phrase inputs](../acceptance/2026-10-29-q5-authored-phrase-inputs.md) protect 80 normalized token contexts before controller replay; punctuation is intentionally omitted and this is not a natural holdout.

The [authored dialogue source](../acceptance/2026-10-29-q5-authored-dialogue-source.md) is retained with attribution and 262 token contexts protected in both ledgers before replay; this small scripted set does not qualify Q5 or a natural holdout.

The [original source-context audit](../acceptance/2026-10-29-q6-original-text-context-audit.md) maps emitted words to original article prefixes and detects registry and cross-partition collisions. It remains diagnostic and does not qualify an independent corpus.

The [cleaned text-context audit](../acceptance/2026-10-29-q6-text-context-audit.md) detects registry and cross-partition context reuse in separately emitted training fragments. Original article context coverage and the independent text gate remain open.

The [retrieval boundary audit](../acceptance/2026-10-29-q6-retrieval-boundaries.md) quarantines nine complete hyphenated source tokens; one suspended hyphen remains explicitly unresolved.

The [refinement and epoch boundary audit](../acceptance/2026-10-29-q6-refinement-epoch-boundaries.md) traces and quarantines 75 complete hyphenated source tokens. This is historical disclosure, not new qualification.

The [historical retrieval disclosure](../acceptance/2026-10-29-q6-retrieval-history.md) restores 1,800 source-bound rows and quarantines 341 source articles in both registries. This is exposed historical data, not independent qualification; global coverage remains open.

The [historical source-boundary audit and selector guard](../acceptance/2026-10-29-q6-wordrank-source-boundaries.md) quarantines 52 full source forms and prevents four independent selectors from admitting partial tokens. Historical data parity is preserved; fresh qualification remains open.

The [word-ranking source-token audit](../acceptance/2026-10-29-q6-wordrank-hyphen-origins.md) traces all five occurrences of the three unknown historical targets to hyphenated source compounds and quarantines full forms without guessing head lemmas. Other canonical-family and provenance gaps remain open.

The [word-ranking replay disclosure](../acceptance/2026-10-29-q6-wordrank-replay-disclosure.md) adds both control and lexical exclusions for 3,419 previously exposed input/target/output contexts; global completeness remains open.

The [no-build gate regression](../acceptance/2026-10-29-q6-no-build-gate.md) runs the real two-registry preparation and receipt verification in an isolated checkout without `build/`; historical provenance completeness and fresh natural-data qualification remain open.

The [refinement source-article addenda](../acceptance/2026-10-29-q6-refinement-article-segments.md) protect selector segments from all 1,158 manifest articles using the pinned public shard, without ledger bindings to ignored build files. Global provenance and independent qualification remain open.

The [refinement text addenda](../acceptance/2026-10-29-q6-refinement-text-families.md) bind 1,069 archived text fragments to historical parents and retain their segments, dictionary families and exact unknowns. Complete articles, unsupported canonical identities and global coverage remain open.

The [word/epoch text-family addenda](../acceptance/2026-10-29-q6-word-epoch-text-families.md) protect dictionary analyses and exact unknown surfaces in 630 archived text fragments. Complete articles, unresolved canonical families and global registry coverage remain open.

The [selector prior-input gate](../acceptance/2026-10-29-q6-selector-prior-drift.md) extends pre-publication drift checks to word-ranking and additional-epoch prior graphs; the unchecked-text barrier remains active.

The [retrieval prior-input drift gate](../acceptance/2026-10-29-q6-retrieval-prior-drift.md) rechecks all 25 consumed prior/source-helper inputs before output; independent registry coverage and other collector paths remain open.

The [retrieval real-prior diagnostic](../acceptance/2026-10-29-q6-retrieval-real-prior.md) replaces the earlier stub with three checked historical prior datasets in one local intercepted run. A [portable fixture](../acceptance/2026-10-29-q6-retrieval-portable-prior.md) now restores the prior-data reader inputs in an isolated workspace without owner build files; the [historical retrieval reproduction command](../acceptance/2026-10-29-q6-retrieval-portable-reproduction.md) now reproduces the original rows byte for byte. Complete registries and independent qualification remain outstanding.

- Joint corpus privacy/provenance admission: independent joint preparers now
  declare `containsPersonalMessages=false` after verifying the pinned public
  source shards and public exclusion manifests; source locks, frequency and
  morphology inputs are hash-bound and rechecked before publication. Historical
  reproduction remains disclosed without this declaration. Their source locks are
  supplied under `source_root`; the source lock is now checked against retained
  public shard hashes and the pinned Wikipedia revision. Additional exclusion
  inputs are now manifest-bound and rechecked before publication; independent
  collection additionally requires every manifest/split pair in the permanent
  ledger and must match one of the three audited public historical manifest
  identities. Other sets require a separate provenance audit. Complete registry
  coverage and an actual fresh independent corpus remain outstanding.
  An isolated synthetic test exercises the primary joint collector through
  serialization and refuses source mutation before output; its registry guard,
  dictionary and source inputs are test doubles, so it grants no qualification.
- [Joint calibrators](../acceptance/2026-10-28-q6-joint-calibration.md):
  all three gate data roles; source/follow-up now recompute bound actual scores
  instead of trusting a stale cache. The shared replay capture validates resources,
  IDs and corpus/model/parent edges. Native six-row replay rejects 14 input mutations
  and mid-calculation drift; the full pinned rescue recipe matches its published
  114/0 numeric result without requalifying its ancestry. 660 stdlib / 76 scientific
  tests pass (one MLX skip). Training, fresh role alignment and full Q6 closure remain.
- [Joint editor evaluation](../acceptance/2026-10-28-q6-joint-evaluation.md):
  both evaluators now gate data roles and verify actual UTF-16/editor flags,
  complete schema-2 replay resources/sources, opaque input IDs, model/threshold/
  short-policy/corpus edges and exclusive reports. Original numerical criteria
  remain separate. Actual two-mode replay binds 188 files; 18 isolated mutations
  and mid-evaluation drift are refused. 651 stdlib / 76 scientific tests pass
  (one MLX skip). Existing baseline capitalization and one original typing-context
  deviation are disclosed. Calibrators/training and full Q6 lineage remain open.
- [Manual retrieval evaluation](../acceptance/2026-10-28-q6-retrieval-evaluation.md):
  current evaluator is registry-gated, disclosed reports cannot qualify and all
  export/source/model inputs are bound. Missing experiment dependencies in the
  real exporter are repaired; two fresh JVM runs agree excluding timing. Current
  numerical replay rejects 90 isolated input mutations and mid-scoring drift.
  638 stdlib / 76 scientific tests pass (one MLX skip). Native observer compilation
  is CI-wired, not hosted-verified. No APK changes; Q6's other gaps remain.
- [Word-ranking evaluation](../acceptance/2026-10-28-q6-word-evaluation.md):
  disclosed numerical gains cannot grant independent acceptance. Four dataset/
  export graphs, both dev groups, weights/code/registries and typed cohort
  denominators are bound. A current real JVM capture of four original word rows
  drives the numerical smoke; all 232 distinct input mutations and a second
  disclosure are rejected. 631 stdlib / 75 scientific tests pass (one MLX skip);
  no APK changes. Other drivers, historical gaps and fresh qualification remain.
- [Additional-epoch evaluation](../acceptance/2026-10-28-q6-extra-epoch-evaluation.md):
  disclosed numerical gates no longer grant acceptance; selection/dev reports,
  weights, three dataset/export graphs, code and registries are bound. A
  controlled real-driver smoke passes with packaged files unchanged; 623 stdlib,
  74 scientific (one MLX skip) and 41 CI tools tests pass. Word-ranking and other
  drivers, complete history/families and fresh qualification remain outstanding.
- [Refinement legacy snapshot](../acceptance/2026-10-28-q6-refinement-legacy-binding.md):
  corpus/export rows and checked generator dependencies are now bound before
  evaluation and rechecked before export. Actual graph: 4,000 export rows /
  3,400 source matches / 39 generator sources; bounded numerical smoke and
  legacy drift refusal pass with packaged files unchanged. 617 stdlib tests,
  73 scientific tests (one MLX skip) and 41 CI tools tests pass. Other drivers,
  historical provenance and fresh independent qualification remain open.
- [Refinement evaluation receipt](../acceptance/2026-10-28-q6-refinement-evaluation.md):
  main data/observations/export graph, weights/code/registries and recorded
  metrics are bound and consumed by promotion. Permanent bounded real-driver
  smoke passes with packaged files unchanged; 615 stdlib and 73 scientific
  tests pass (one explicit MLX skip). The latest follow-up binds the legacy graph;
  other drivers and independent fresh qualification remain outstanding.
- [Refinement promotion admission](../acceptance/2026-10-28-q6-refinement-promotion.md):
  default packaging now requires permanent registry coverage and a bound
  independent-data evaluation. Disclosed review export is isolated under build;
  609 stdlib tests and a controlled six-file/four-parity-row export pass, with
  packaged files unchanged. The evaluation receipt producer and other promotion
  paths still need integration; no fresh model qualification is claimed.
- [Training/evaluation collector gates](../acceptance/2026-10-28-q6-training-collector-gates.md):
  refinement, word-ranking, epoch and retrieval now join the guard. All 13
  maintained CLI commands refuse incomplete coverage; original source/data
  identities are retained through exact archive lookup. 603 stdlib tests and
  72 scientific tests pass (one explicit MLX skip). Evaluation/promotion drivers
  and other entry points still require scope checks.
- [Base collector gates](../acceptance/2026-10-28-q6-base-collector-gates.md):
  direct v6 and original joint prepare paths now join the permanent-registry
  guard; all nine current spelling/joint collector CLIs refuse incomplete
  coverage. Original source bytes and finite row parity are retained; 599
  stdlib tests pass. Refinement, word-ranking, epoch and retrieval preparers
  still need their own scope audit.
- [Collector registry gates](../acceptance/2026-10-28-q6-collector-registry-gates.md):
  current v7–v12 and joint follow-up commands now refuse incomplete permanent
  registries before reading corpus inputs. Historical reproduction is explicit,
  marked disclosed/non-independent, and original source bytes are preserved.
  Seven real CLI refusals and 598 stdlib tests pass; other historical builders
  and full natural/data/model qualification remain outstanding.
- [Named regression replay](../acceptance/2026-10-28-q6-named-regression.md):
  all 56 disclosed cases pass current JVM exact-output/control/Undo checks.
  Historical finite-only qualification rejects the current general-local
  configuration; no new independent qualification is claimed.
- [Durable named exclusions](../acceptance/2026-10-28-q6-named-exclusions.md):
  56 disclosed standalone cases, three new source-bound entries; all original
  24 control entries preserved. Exact and changed-context surface reuse is
  blocked. Global control coverage remains incomplete.
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
- [Joint public source windows](../acceptance/2026-10-28-q6-joint-source-windows.md):
  44,816 historical rows are source-matched; seven durable source-only addenda
  preserve 5,387 partition-window keys. Original parent gaps and incomplete
  global coverage remain disclosed.
- [Joint dictionary-family coverage](../acceptance/2026-10-28-q6-joint-family-closure.md):
  all 44,816 historical joint rows map to registered dictionary-family keys;
  the 5,385 previously unresolved rows are protected `@` controls whose source
  words are resolved. This does not establish global family coverage.
- [Word-ranking family quarantine](../acceptance/2026-10-28-q6-word-history-families.md):
  the 9,000-row public historical corpus adds 615 previously unblocked dictionary
  family keys and two previously unblocked exact unknown surfaces. Three unknown
  forms still have no verified canonical family; global coverage remains open.
- [Additional-epoch test families](../acceptance/2026-10-28-q6-epoch-history-families.md):
  all 1,500 disclosed test targets resolve to 832 dictionary families, including
  two previously absent from new-family exclusions. They are not labeled as
  supervised training; full source sentences and global coverage remain open.
- [Refinement exclusion audit](../acceptance/2026-10-28-q6-refinement-coverage.md):
  all 7,500 archived train/dev/test rows have covered article and target-context
  keys, applicable dictionary-family exclusions and exact quarantine of one
  unresolved training surface. It does not establish model execution or full
  source sentences.
- Joint collectors use native numeric morphology family IDs, whereas the
  lexical registry uses Pymorph lemmas. Numeric IDs now fail the registry
  identity gate rather than being hashed as lemmas. The independent collector
  path now projects every selected target to all pinned dictionary analyses,
  rejects unresolved targets and cross-split lemma overlap, persists these
  analyses for downstream calibration/evaluation gates, and binds dictionary
  and helper identities. A local audit of the three retained joint corpora
  covered 25,647 / 9,584 / 9,585 rows without unresolved targets or cross-split
  lemma overlap. Historical reproduction remains disclosed. This projection
  does not establish complete registry coverage or recover missing historical
  sentence identities. New independent joint proposals now capture the existing
  source-window hash directly from the public article before typo generation;
  they reject cross-split window reuse. This is a bounded source window, not a
  claim of full-sentence recovery, and does not qualify a model on its own.
- [Both previously missing historical feature sources are restored](../acceptance/2026-10-29-q6-recovered-feature-sources.md) from local creation and patch records and match their pinned hashes. Historical execution, model parity and other transitive source gaps remain open.
- Establish provenance for the separate 120-example file; its [local creation record](../acceptance/2026-10-29-q6-authored-file-creation.md) now reproduces the 120 rows byte for byte without executing historical code, but does not establish the origin of its literal inputs. Keep its text/private fingerprints out of the public exclusions.
- Resolve the disclosed natural-v6 historical article overlaps; those existing
  rows cannot be represented as independent fresh qualification. The tracked
  spelling-plus-neighbor article-key union now exposes 140 calibration and 144
  holdout collisions (18 and 13 additional to spelling-only); see
  [ledger scope](../../tools/typing_experiments/HOLDOUT_LEDGER.md). The exact
  [row projection](../acceptance/2026-11-10-q6-available-v6-metadata-recovery.md#exact-v6-rows-affected-by-article-overlap)
  now counts the affected v6 rows. A replacement independent corpus remains open. The
  neighbor side of those collisions maps to 180 and 150 retained public neighbor
  rows respectively; exact target-context keys do not overlap. The preceding
  reliable-side-v5, sentence-corpus-v6 and sentence-pairs-v2-v6 source scripts
  are restored byte for byte against original evidence in the
  [frozen source catalogue](../../tools/typing_experiments/frozen_sources/README.md).
  The two later available-v6 preparation sources have also been reconstructed
  from creation records, but lack independent source-hash attestation; see
  [provenance sources](../../tools/typing_experiments/historical_provenance_sources/README.md).
  This does not restore available-clean-v6 data or its full lineage.
- [Acceptance-template registry binding](../acceptance/2026-10-28-q6-acceptance-registry-binding.md)
  is verified: exact snapshots plus canonical entry digests for both registries,
  blocked real-proposal receipt and omission-mutation failures. Complete the
  remaining generator/source inventory and independent fresh qualification.

## Integration and completion boundaries

Q7 Android 37 general: [candidate 687361c8](../acceptance/2026-10-28-q7-ci-baseline.md#candidate-687361c8-api-37-general-boundary) matched all 400 discovered identities and passed the five required expanded-candidate cases. It recorded 341 passes, the exact 59 known skips and zero errors. The [supplementary routes](../acceptance/2026-10-28-q7-ci-baseline.md#candidate-687361c8-api-37-supplementary-scopes) passed locally, including the Chrome DOM oracle. Hosted execution remains open.

Q7 Android 26 refresh: [the full local wrapper on candidate 75d06f6f](../acceptance/2026-10-28-q7-ci-baseline.md#candidate-75d06f6f-api-26-general-boundary) passed all 11 boundary scopes and all four supplementary runners. The general report matched all 399 discovered cases, with 340 passes and the 59 known skips. The [next candidate](../acceptance/2026-11-10-publication-text-screen.md#candidate-with-expanded-suggestion-accessibility-and-the-u14-ci-gate) adds the U14 implementation and required CI cases. Its full local API 37 and hosted runs remain open.

Q7 skip follow-up: [the current route coverage audit](../acceptance/2026-11-10-q7-known-general-skips.md#current-route-coverage-for-the-59-known-skip-identities) accounts for 27 distinct opt-in cases across the API 26/37 CI routes. Another 29 known skip identities require physical Fold scenarios and three require an installed real model fixture.

Q7 scientific follow-up: [the current clean scientific repeat](../acceptance/2026-10-28-q7-ci-baseline.md#current-clean-scientific-and-mlx-repeat) passed fixture restoration, 123 scientific tests and six live Pymorphy checks. The single scientific MLX skip passed in the separate seven-test CPU gate. Hosted execution remains open.

Q7 stdlib follow-up: [the current clean profile repeat](../acceptance/2026-10-28-q7-ci-baseline.md#current-clean-stdlib-repeat) passed 1,048 isolated tests in 210 modules and all local stdlib shell steps from CI. Hosted execution remains open.

Q7 clean stdlib repeat: [candidate source `7ec3b332`](../acceptance/2026-10-28-q7-ci-baseline.md#clean-stdlib-run-through-the-joint-control-recovery) passed 1,106 tests in 211 modules after updating the spelling coverage fixture for the Joint control exclusions. Hosted execution remains open.

Q7 stdlib corpus-recovery follow-up: [the clean checkout at `84618831`](../acceptance/2026-10-28-q7-ci-baseline.md#clean-stdlib-repeat-through-the-supervised-v2-recovery) passed 1,074 tests in 210 modules after resolving the `stdlib` matrix expression locally. Hosted execution remains open.

Publication follow-up: [the 18-commit delta through the Android report gate](../acceptance/2026-11-10-publication-text-screen.md#delta-through-the-android-full-report-gate) accounts for each new scanner location against the historical holdout index or a verified dependency digest. Earlier history findings and distribution rights remain open.

Publication follow-up: [the ten-commit delta through the API 26 supplementary routes](../acceptance/2026-11-10-publication-text-screen.md#delta-through-the-api-26-supplementary-routes) passed the bounded Git patch scan and a direct scan of all four entries appended to the oversized holdout ledger. Both authored registration checks reproduced those entries.

Publication follow-up: [the eight-commit delta through the API 37 QA editor change](../acceptance/2026-11-10-publication-text-screen.md#delta-through-the-api-37-qa-editor-change) accounts for both Gitleaks locations against the exact file from the pinned Pymorphy install.

Publication follow-up: [the 15-commit delta through Joint and Rare Ranking recovery](../acceptance/2026-11-10-publication-text-screen.md#delta-through-joint-and-rare-ranking-recovery) resolves the single Gitleaks location to the independently verified article exclusion index digest. Earlier history findings and distribution rights remain open.

Publication follow-up: [the five-commit delta through Reliable Side v5 and night learning](../acceptance/2026-11-10-publication-text-screen.md#delta-through-reliable-side-v5-and-the-night-learning-runs) resolves the single Gitleaks location to the verified 17,886-article exclusion index digest. Earlier history findings and distribution rights remain open.

Q7 general-suite follow-up: [the discovery and JUnit identity gate](../acceptance/2026-10-28-hosted-ci-suite-floor.md#general-suite-discovery-and-report-identity) compares the complete runtime-discovered case list with the fresh report. Local API 26 and API 37 listing parity and both omission/substitution rejection probes passed. Full execution and hosted CI remain open.

Q7 API 26 connected follow-up: [all eleven boundary scopes](../acceptance/2026-10-28-hosted-ci-suite-floor.md#api-26-connected-boundary-run) passed locally. The general scope reported all 398 discovered identities, with 339 passes and exactly the 59 known skips. The API 37 boundary run and hosted execution remain open.

Q7 API 26 additional routes: [the restart, editing process-death and voice runners](../acceptance/2026-10-28-hosted-ci-suite-floor.md#api-26-restart-process-death-and-voice-routes) passed locally after rebuilding the ordinary APKs. The separate night-learning workload requires a fresh AVD.

Q7 API 37 follow-up: [System UI blocked the late punctuation inputs](../acceptance/2026-10-28-hosted-ci-suite-floor.md#api-37-interruption-after-a-blocked-input-window) during an interrupted general run. The debug QA theme eliminated the starting window over 12 repeated launches. Five of six targeted tests passed. One setup failure, four earlier scoring failures, and the full run remain open.

Q7 API 37 general repeat: [JUnit matched all 398 discovered identities](../acceptance/2026-10-28-hosted-ci-suite-floor.md#api-37-general-repeat-with-the-debug-preview-disabled). All nine earlier failures passed in the repeat. The general route recorded 339 passes, 58 known skips and one editor startup timeout. The startup patch, remaining device scopes and hosted CI have separate acceptance checks.

Q7 API 37 editor startup: [the patched QA editor](../acceptance/2026-10-28-hosted-ci-suite-floor.md#api-37-debug-editor-startup-fix) passed its default-profile check and all three opt-in repeats. The nine other boundary scopes and the restart, process-death, voice and Chrome routes also passed on the previous build. A full repeat with the patch and hosted acceptance remain open.

Q7 API 37 connected repeat: [ten boundary scopes with the startup patch](../acceptance/2026-10-28-hosted-ci-suite-floor.md#api-37-connected-scopes-with-the-startup-fix) passed across the general invocation and a separate Compose repeat after installing its fixture. General JUnit matched all 398 identities, with 339 passes and 59 known skips. The fresh night-learning route, a single complete invocation and hosted CI remain open.

Q7 night-learning follow-up: [the exact CI night-learning command](../acceptance/2026-10-27-u13-night-learning.md#complete-local-ci-runner-on-fresh-api-26-and-api-37-avds) passed four instrumentation cases each on fresh API 26 and API 37 emulators. Hosted CI and natural scheduler dispatch remain open.

Q7/Q8 Chrome follow-up: [the API 37 Chrome route](../acceptance/2026-10-28-q8-chrome-editor.md#api-37-emulator-ci-route) adds both real textarea cases and the numeric DOM verdict to emulator CI. Local ARM64 checks pass. Hosted execution and the full Fold application matrix remain open.

U6 TalkBack follow-up: [language-order buttons](../acceptance/2026-10-27-u6-switch-dependencies.md#2026-11-23-talkback-language-order-actions) expose distinct localized names. Actual TalkBack touch focus and double-tap activation were verified on API 37. All six settings tests pass on API 26 and API 37. Other settings screens and Fold remain open.

U8/U9/U15 TalkBack follow-up: [the API 37 live keyboard check](../acceptance/2026-10-27-u8-public-panel.md#2026-11-23-talkback-menu-editing-and-emoji) verified the new Edit menu action, Copy and Paste, Emoji insertion and deletion, and Next keyboard switching from Rune to Gboard. Twelve instrumented methods passed on each of API 26 and API 37. The physical Fold checks remain open.

Q1 independent environment follow-up: [the pinned Linux and macOS release comparison](../acceptance/2026-10-29-q1-fdroid-binary-scan.md#2026-11-23-independent-linux-release-comparison) passed the release, privacy, footprint, strict native and scanner checks on both APKs. The 127 equal ZIP entries and two native ELF metadata differences establish the scope of the cross-platform mismatch. The actual remote F-Droid job, signed distribution and Fold smoke remain open.

Q1 public release follow-up: [the downloaded v0.4.1 release](../acceptance/2026-10-29-q1-fdroid-binary-scan.md#2026-11-24-published-apk-baseline) passes signature and 16 KiB alignment checks. Both Rune native binaries still contain debug sections and the footprint gate rejects the APK. Public v0.4.2 distribution and F-Droid acceptance remain open.

Q7 current host evidence: [clean-checkout JVM, Python and replay results](../acceptance/2026-10-28-q7-ci-baseline.md#2026-11-23-clean-host-replay-and-unit-tests) verify both exact baseline projections and the 160-row threshold rejection. Hosted CI on the current source remains open.

Q8 Fold application coverage: [the APP-001–005 matrix](../acceptance/2026-09-01-z-fold-rune-0.1-rc.md#q8-application-matrix-status--2026-11-24) binds the available Chrome and Termux observations to the original scenarios. Gmail was disabled and Samsung Notes was absent at their last inspections. The remaining app and display cells have separate acceptance criteria.

Q7 current candidate: [fresh import of `75d06f6f`](../acceptance/2026-11-10-publication-text-screen.md#candidate-with-a2-retention-and-editor-settling-fixes) verifies the A2 retention and editor fixture fixes with all four exclusions retained. Forty Python checks and both frozen profiles pass. The [API 26 interruption and recovery](../acceptance/2026-10-28-q7-ci-baseline.md#candidate-123d0a52-api-26-run-interrupted-by-the-local-timeout) account for the partial general result and successful night rerun, with both listed methods passing separately on API 26 and API 37 after the fixture fix.

Q7 refreshed candidate: [the imported local candidate `123d0a52`](../acceptance/2026-11-10-publication-text-screen.md#2026-11-24-candidate-with-current-android-review-fixes) includes the current A1 and U6 Android sources. The clean repository retained all four publication exclusions. 38 runner tests and both frozen replay profiles passed. [The exact-revision JVM and targeted Android checks](../acceptance/2026-10-28-q7-ci-baseline.md#2026-11-24-jvm-and-android-checks-on-candidate-123d0a52) added 1,434 JVM passes and 13 instrumentation passes each on API 26 and API 37. The full Android boundary runs on this revision and hosted execution remain open.

Q7 candidate fixture replay: [the corrected stdlib profile and cold v3/v4 restoration](../acceptance/2026-10-28-q7-ci-baseline.md#recovered-v6-registry-and-cold-fixture-replay) passed locally with the expanded v6 registry. Hosted execution remains open.

Q7 candidate API 37 follow-up: [all five separate CI commands](../acceptance/2026-10-28-q7-ci-baseline.md#api-37-follow-up-suites-on-the-v6-candidate) passed on fresh local ARM64 emulators. The general boundary run and hosted execution remain open.

Q7 candidate API 26 follow-up: [all four CI follow-up commands](../acceptance/2026-10-28-q7-ci-baseline.md#api-26-follow-up-suites-on-the-v6-candidate) passed on fresh local ARM64 emulators, including the fallback IME process-death route.

Q7 exact model: [the v6 candidate](../acceptance/2026-10-28-q7-ci-baseline.md#exact-rune-text-scoring-on-isolated-candidate-builds) passed bounded scoring on both APIs and private Binder on API 26. The API 37 Binder repeat timed out after canceling the preceding request. Its repeatability and the installed-model typing path remain open.

Q7 fresh API 26 general: [the JUnit report](../acceptance/2026-10-28-q7-ci-baseline.md#fresh-api-26-general-boundary-report) matched all 398 discovered identities, with 339 passes and exactly the 59 known skips.

Q7 fresh API 26 boundary: [all eleven scopes](../acceptance/2026-10-28-q7-ci-baseline.md#fresh-api-26-general-boundary-report) passed in one invocation, including 24 passing cases in the ten opt-in scopes.

Q7 fresh API 37 boundary: [all ten connected scopes](../acceptance/2026-10-28-q7-ci-baseline.md#fresh-api-37-general-boundary-report) passed in one invocation. The general report matched all 398 discovered identities with 339 passes and exactly the 59 known skips. The nine opt-in scopes added 23 passes. The release-native Binder repeat and hosted execution have separate checks.

Q7 API 37 Binder: [four traced repetitions](../acceptance/2026-10-28-q7-ci-baseline.md#api-37-binder-request-trace) scored the first successor successfully. One later request returned `UNAVAILABLE` before queue entry. The earlier successor timeout remains open.

Q7 Binder refill: [the extended trace and corrected test](../acceptance/2026-10-28-q7-ci-baseline.md#api-37-binder-request-trace) verified the warm-budget cause and exercised a 32.5-second refill on API 26. Two API 37 repeats reproduced the independent first-successor timeout.

Q7 Binder deadline: [a buffered API 37 trace](../acceptance/2026-10-28-q7-ci-baseline.md#first-successor-timeout-traced-to-the-shared-wall-deadline) reproduced the successor timeout at the shared cold preparation and scoring deadline. Real-model acceptance remains open.

Q7 release-native Binder: [six API 37 process starts](../acceptance/2026-10-28-q7-ci-baseline.md#release-native-binder-fixture) used the exact published model and the native binaries from the release build. Five passed, and one timed out awaiting the first successor. Cold Binder repeatability remains open.

Q7 first-score phase trace: [six further release-native runs](../acceptance/2026-10-28-q7-ci-baseline.md#first-score-phase-timing-with-release-native-libraries) reproduced the first timeout. Native model load took 357 ms and the first scorer call took 2,636 ms before cancellation. The other five runs passed. The native context/decode split and cold-path repeatability remain open.

Q7 native phase split: [the standalone Android scoring benchmark](../acceptance/2026-10-28-q7-ci-baseline.md#standalone-android-split-of-context-creation-and-scoring) found the first slowdown inside the scalar scoring call. Context creation took at most 4.2 ms and the first score in the first process took 11.1 s. All 60 direct scores preserved exact within-process parity. The cause of the anomalous cold interval and end-to-end repeatability remain open.

Q7 fresh emulator comparison: [three API 37 AVDs](../acceptance/2026-10-28-q7-ci-baseline.md#fresh-emulator-timing-comparison) put the first native score over ten seconds at 13 seconds guest uptime and at 99 ms at 74 seconds uptime.

Q7 settled Binder: [all six process starts](../acceptance/2026-10-28-q7-ci-baseline.md#release-native-binder-in-a-settled-guest) passed on an isolated API 37 emulator with the release-native libraries and exact model. First-successor latency was 343–419 ms; the earlier startup-load failures, physical-device cold path, and hosted verification retain separate outcomes.

Q1 release payload parity: [the two review revisions](../acceptance/2026-10-29-q1-fdroid-binary-scan.md#apk-parity-across-review-only-commits) differ in the packaged Git stamp and ZIP offsets. All 128 other ZIP payloads match byte for byte.

Q1 current U14 candidate: [the unsigned APK at 687361c8](../acceptance/2026-10-29-q1-fdroid-binary-scan.md#release-scan-with-the-same-window-u14-row) passed the release gates, strict native validation, 16 KiB alignment and the offline F-Droid scan. The hosted build-server result, signed distribution and Fold smoke test remain open.

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

Q6 edit-count follow-up: the [shared word/retrieval input validator](../acceptance/2026-10-28-q6-retrieval-evaluation.md#edit-count-validation-follow-up-2026-11-09) now rejects typo rows whose claimed count differs from the original generator's edit distance, and both receipts bind that function's source. Historical word and retrieval rows match; context labels and independent qualification remain unproven.
