# Fresh phrase autocorrection and valid-word suggestions

> Historical material from 2026-10-26. The original body is retained.
> Its source, model and device claims are not fresh acceptance. Current scope
> and outstanding evidence are in the [review completion map](../plans/2026-10-27-review-completion.md).

The owner requested a new autonomous phrase run, remaining autocorrection/ranking fixes and an update after checks. After AURA completed its cycle and Android MCP explicitly handed back the device, Rune ran the physical checks and installed the checked update without clearing application data. The earlier owner-requested queue was respected.

## Frozen authored inputs and observed local faults

Twenty-four new lower-case public phrases were authored before their results were observed: 18 intended typos and six unchanged controls. Their exact inputs/intentions are in `FoldAutocorrectionInstrumentedTest.probeFreshEverydayPhrasesThroughRealTouchInput`; raw host observations and input hashes are ignored under `build/fresh-phrases-20261026/`. Expected text stays outside the Kotlin product observer and never drives touchscreen input.

Production-controller replay initially matched 15/24 intended phrase-word outcomes. The first displayed correction was the intended target for 17/18 typo cases. The missing target was `нуден → нужен`: `нуден` is a dictionary-valid word, so the automatic veto is appropriate, but optional expanded suggestions did not offer any alternative.

The updated local replay matches 17/24 outcomes, preserves every prior match and all six correct controls, and puts the intended target first for all 18 typo cases. All 24 Backspace documents restore the pre-boundary document exactly. These are authored characterization counts, not an independent precision estimate or physical-device result.

## Focused changes

- CommonConfusions V7 adds the finite reviewed typo `всее → все`. Correct `все`, `всех`, `всей` remain outside that exception. Local qualification explicitly pins V7; V6 cannot silently inherit it.
- WordContextPolicy V4 adds `я уже ддмой → я уже домой`. Both preceding whole tokens are required. Bare `уже`, `стала уже`, `она уже`, punctuation/identifier fragments do not qualify this rule. Whitespace is normalized without removing punctuation; case folding applies only to the context. The rule identity is derived from the actual rule entries and separately pinned by qualification.
- With the existing optional expanded-manual-search setting enabled, dictionary-valid lower-case Russian originals of 3–12 letters may offer bounded public-dictionary neighbours. The original validity and automatic candidates stay intact. The producer trims the complete public neighbourhood to the existing seven-item display protocol; an intermediate 15-item snapshot was caught by replay and rejected before physical installation. Supplemental snapshots are manual-only, marked `PUBLIC_AUGMENTED`, carry no local/joint/recovery automatic certificate, and are validated on both baseline and recovery delivery. `нуден` offers `нужен` for explicit selection; Space retains `нуден`. The setting stays off by default and existing user settings are preserved.

No statistical score/margin threshold, dictionary protection, search-state budget or model asset is relaxed. In particular, the following authored intentions still abstain automatically:

| Typed | Authored intention | Why it remains manual |
| --- | --- | --- |
| куа | куда | Public original-word protection; intended target already first |
| поггорим | поговорим | Search budget/ambiguous candidates, including погорим and прогоним |
| нуден | нужен | Exact dictionary-valid original; now explicitly selectable |
| будкт | будет | Near-tie with будки; also будут/other inflections |
| позвоеить | позвонить | Ambiguity with позволить and incomplete extended retrieval |
| рал | рад | Public original-word protection; intended target already first |
| сттл | стол | Automatic model prefers стал; стул is also plausible |

The seven retained originals are not reported as corrected. The intended first manual suggestion improves usability while retaining the automatic veto.

## Completed local validation

- `:app:testDebugUnitTest`: 1,083 tests, zero failures/errors/skips.
- `:app:assembleDebug`, `:app:assembleDebugAndroidTest`, `:app:lintDebug`: passed.
- Diagnostics Python: 64 tests passed, including debug/release/profile packaging checks. Scoring-boundary verification and `git diff --check` passed.
- Current-source production replay over the prior 4,788 + 3,648 + 3,576 public rows: all 12,012 boundary and exact Backspace documents unchanged; zero Undo failures.
- New regressions cover two-token context boundaries, qualification drift, finite typo exceptions, opted-in/off/cancelled valid-word retrieval, preserved original certificates, both delivery stages, explicit choice/Original restoration, Space preservation, and rejected supplemental automatic certificates.

## Physical Fold results

The exact frozen 24 phrases were typed through real touchscreen keys on the installed baseline and updated APK, with a requested 100 ms pause between keys. Each phase used eight three-phrase batches; all batches completed their instrumentation/no-editor-read assertions. Expected phrase outcomes improved **15/24 → 17/24**. All six correct controls and every prior successful phrase were preserved. The two improved phrases were `я уже ддмой и жду тебя` and `сейчас всее работает хорошо`.

One initially failing phrase also acquired extra input: `ты можешь позвоеить поз, же`. Native diagnostics record comma and Space as additional `INPUT` events, rather than a spelling replacement; its underlying cause is unresolved. Three separate repeats at the same requested cadence produced the retained-original phrase `ты можешь позвоеить позже` without the extra input. The original anomalous run is preserved and remains included in the 17/24 result, never replaced by those repeats.

The first full assertion suite completed **12 methods with one failure**: the 50 ms `спосибо → спасибо` case left `спасибо` after Backspace instead of restoring `спосибо`. Subsequent tests rotated that method's detailed text events out of the bounded journal, preventing a reliable cause assignment. A focused unchanged 50/100 ms replay passed all six cases; its saved journal explicitly pairs `спосибо → спасибо` with accepted Undo back to `спосибо`.

To prevent this evidence loss, physical-test teardown now uses the existing recorder's serialized bounded export API to retain each method's journal in app-private cache before later tests can rotate it. Settings restoration remains in `finally`; there are no editor reads, screenshots or consent changes. After installing this test-only observer change, the **same full 12-method suite passed**, with the original requested typing cadence and assertions unchanged, and 12 per-method snapshots were collected privately. The initial failure is retained and is not claimed fixed or explained by the observer change.

Passing native coverage includes the two new corrections at requested 50/100 ms with exact Undo, their correct-word controls, valid-word manual expansion off/on, Space retaining `нуден`, explicit selection of `нужен`, Original restoration, the older contextual corrections, rapid short words, first-letter/empty-field handling and existing diagnostic/rescue checks. All declared editor-payload-read counters remained zero. Native records for `ддмой` use `WORD_CONTEXT`, and `всее` uses `LOCAL_POLICY`; each has its matching `EDITOR_ACCEPTED` response.

Final settings and four personal-store fingerprints match the fresh pre-test snapshot. The same checked APK was reinstalled after acceptance, its installed SHA-256 matches the build, and Rune is enabled and selected. No clear/uninstall or permission/network change was performed. The seven intended automatic abstentions listed above remain; the two intermittent episodes are explicitly retained for further observation rather than declared resolved.

The physical observer emits one `journal_snapshot` status per method. Collect `cache/fold-autocorrection-journals/` only after instrumentation finishes, into an ignored private archive (0700 parent, 0600 archive). Each method retains at most one 1 MiB metadata stream and one 4 MiB text stream through the recorder's export queue. After validating the archive, remove only the exact cache directories named by that run's statuses; do not clear application cache or diagnostics generally. Ordinary CI skips these physical tests before settings or journal mutations.
