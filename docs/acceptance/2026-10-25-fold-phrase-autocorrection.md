# Autonomous phrase typing on Fold

> Historical material from 2026-10-25. The original body is retained.
> Its source, model and device claims are not fresh acceptance. Current scope
> and outstanding evidence are in the [review completion map](../plans/2026-10-27-review-completion.md).

The owner requested autonomous typing, log collection, fixes and installation. The test generates its own public phrases and injects real touchscreen events into Rune on physical SM-F966B; it does not ask the owner to type. Editor readback counters are checked after every phrase. Personal learning, touch adaptation and example collection are disabled only within the test and the complete preference map is restored afterward.

## Confirmed faults and focused change

The baseline device run retained `прийду`, `скороо`, `спосибо` in otherwise ordinary phrases. The diagnostic boundaries report `INSUFFICIENT_MARGIN` for `прийду`/`скороо` and `SCORE_TOO_LOW` for `спосибо`; the correct candidates were available. In the isolated replay, `прийду` even ranks `приеду` before `приду`. Ordinary general-search generation of `прийду` can also exhaust its state budget in the packaged-lexicon regression.

CommonConfusions V6 adds exactly three reviewed substitutions: `прийду → приду`, `спосибо → спасибо`, `скороо → скоро`. They use the existing bounded finite-source retrieval and exact target membership check. The finite-source qualification pins V6; V5 does not silently inherit qualification. Statistical models, dictionaries, search budgets and statistical confidence thresholds are unchanged. This is authored exception coverage, not a claim of improved independent statistical accuracy.

Correct target forms were checked against the packaged lexicon; [Грамота: приду](https://gramota.ru/spravka/vopros/249082) and [Грамота: скоро](https://gramota.ru/meta/skoro) support the reviewed spellings. Existing protection for ownership, editor type, language, incomplete/unverified retrieval, explicit original selection, personal rejection and exact Undo remains in the same controller path. Tests include all three mappings and explicitly exclude valid forms and unreviewed nearby spellings from this finite source.

The initial new regressions failed before the patch: no admitted `прийду → приду` candidate and exhausted general retrieval. They passed after the focused change.

## Test reliability

The first attempt stopped before typing because Android UI Automation was already registered. Subsequent exploratory runs ended after the QA field disappeared / the next Activity did not become visible; neither run is counted as a complete phrase evaluation. Cached coordinates were removed from the broad phrase characterization. The test driver now checks the `am start -W` result, drains layout work before typing and waits for a temporarily absent key only before dispatching a tap. It never retries an already dispatched gesture. Complete phrase runs are split into bounded batches with explicit offsets. A concurrent AURA physical-device QA run was subsequently identified in the app. Its initial run stopped, but a subsequent AURA cycle overlapped the retry: the missing-key observation explicitly recorded foreground `org.auraoss.android.pilot`, with no QA field or native Rune keyboard. Naming a run “exclusive” or observing no `uiautomator` process is not a cross-process device reservation. The owner subsequently explicitly authorized coordination between the chats. AURA confirmed all physical-phone ADB/UI/background controllers stopped and granted Rune the next bounded window; the final coordinated run uses that agreed queue. Rune must hand the phone back after verification and perform no subsequent device actions. Initial missing-field/key failures are retained as invalid test executions, not silently reclassified as product passes. The driver also reports foreground package, screen/focus flags and presence of the native IME on a missing-key failure, without editor contents or screenshots.

The phrase characterization reports desired-versus-observed text as data. A successful instrumentation process alone does not mean all phrases matched. Separate assertions verify each new correction and exact Undo with requested 50/100 ms pauses between taps. Existing speed, original protection and ordinary typing checks remain distinct from the phrase coverage count.

## Results

The completed baseline and coordinated repeat contain the same 15 authored phrases:

| Check | Baseline | Updated |
| --- | ---: | ---: |
| Exact phrase matches | 11/15 | 14/15 |
| Correct control phrases retained | 3/3 | 3/3 |
| Newly reviewed three error phrases corrected | 0/3 | 3/3 |

The remaining miss in this repeat is `нужен новй пароль`: the native boundary records insufficient margin among `новый`, `новой` and `ной`. It is not given a context-free mapping. This characterization is not an independent estimate of population accuracy.

An earlier interrupted probe retained `завтро` with `RESULT_NOT_READY`; both completed baseline and coordinated repeat corrected that phrase through the existing model path. This update adds no finite mapping for that spelling and does not claim model-readiness timing solved.

Final verification:

- JVM: 1,069 tests, zero failures/errors/skips. Build and Android lint passed; final test-driver lint also passed. Diagnostics Python: 64 tests and debug/release/profile packaging passed. Scoring-boundary verification and `git diff --check` passed.
- Frozen production-source replay: all 4,788 prior public boundary, Undo and hint outputs unchanged.
- Physical full regression: 8/9 passed. In the diagnostic reopen test, all three phases recorded the expected six letters, but the IME-restoration step in teardown failed once. This is retained as a failed full run, not called 9/9. A targeted repeat passed (`OK (1 test)`), including all three six-letter diagnostic phases. The repeat was explicitly started with Rune selected. Recent app exit records contained instrumentation force-stops rather than crash exits.
- Six new fast phrase cases (three rules, requested 50/100 ms pauses) passed with exact Undo. Ordinary 14-case typing, three existing fast paces, first-letter retention after empty Backspace, preview/next-word Undo, rare-word protection and the separately qualified long-word corrections passed. All asserted editor-payload read counters remained zero.
- Post-update native diagnostics confirm `AUTO_REPLACE` from `LOCAL_POLICY`, with `modelUsed=false`, for all three new rules.
- Installed APK equals the checked build, SHA-256 `1c1bcc512d55f12ea4b2870f7f4ef3765706b0c0c4963b16c832c4d42218c2bc`. Owner preference fingerprint and four personal-store fingerprints match the pre-run snapshot. Rune explicitly enabled/selected after test teardown.
- The physical-device window was handed back to AURA after verification; Rune makes no further device calls in this run.

[Aggregate evidence](2026-10-25-fold-phrase-autocorrection-evidence.json). Raw phone journals and unsuccessful-attempt outputs remain in ignored `build/fold-phrase-autocorrection/`.

## Reproducing the physical characterization

After installing the matching debug app/test APK on an explicitly selected Fold, run the existing AndroidJUnitRunner with `class=io.github.mesteriis.rune.keyboard.qa.FoldAutocorrectionInstrumentedTest#probePhrasesThroughRealTouchInput`, `allowPhysicalDevice=true`, `runeFailureArtifacts=false`, and `runePhraseOffset=0`, `runePhraseCount=3`. Repeat offsets 3, 6, 9, 12. The offsets select fixed authored phrases; they never replace input with expected output. Inspect every `matched` result as well as the instrumentation completion status. Run `reviewedPhraseFixesAtTwoPacesWithExactUndo` separately for assertions on the three new rules and their Undo.

Coordinate exclusive physical-device use with all other active QA chats before starting. A momentary foreground check or absent `uiautomator` process does not reserve a device. Retain unsuccessful runs and collect the native diagnostic archive after each bounded batch. Do not turn on diagnostic consent, export private captures to tracked files, or leave synthetic feedback in personal stores.
