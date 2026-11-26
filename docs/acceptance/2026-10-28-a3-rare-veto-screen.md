# A3: short-word rare-veto screen

The 8,557-row historical joint holdout at
`build/joint-correction-20261025/corpus/holdout.jsonl` has SHA-256
`03e32ae46a61dd3c5ee0f84a308b9b2d79bf17f7c18de78442d2284738e8084d`.
Applying the original evaluator's `len(typed) <= 4` band yields exactly 2,924
rows: 2,183 typo-labelled rows and 741 controls. This is a previously revealed
set, not a fresh qualification corpus. The selected file SHA-256 is
`d5624cd7ed0e276bdbd55471370efd177e7b9b549497abfcc16b9dde034ba356`.

Two current-product, model-free host replays completed deterministically. Their
source/asset-bound receipt is `build/review-a3-short-current-20261028/receipt.json`
(SHA-256 `a10c38e26efd0e919ba83b33f78e87d6241aaa773eadc0377b9801b21d2fe37c`).
On typo-labelled rows, joint search returned `VALID_WORD` 348 times, `COMPLETE`
1,728 times and `UNAVAILABLE` 107 times. On controls it returned `VALID_WORD`
159 times and `UNAVAILABLE` 582 times.

For the 348 typo-labelled `VALID_WORD` rows, the replay's original morphology
lookup was available in every case. Decoding the packaged `RUNERAR1` asset
(SHA-256 `434b462d4edb0165946568dfdf2a6729ff8b2590fead1fe815d3912817837b6e`,
internal digest checked, 288,246 unique entries) and comparing exact folded
originals gave 216 present only in rare, 40 present only in morphology, and 92
present in both. This identifies 216 rows on which that particular joint search
test is stopped by rare membership with morphology absent. It does not establish
that rare membership is the only product-wide veto, that a complete candidate
pool exists, or that any desired replacement passes the frozen joint model.

The 216 are an upper bound for further investigation, not predicted gains.
## Controlled observer experiment

`current_product_replay.py --a3-rare-probe` now adds a diagnostic-only probe:
for the precise `VALID_WORD`, rare-present and morphology-absent cases it masks
only the original's rare membership, rebuilds the joint pool, and applies the
frozen joint model and thresholds, followed by the existing public and morphology
admission checks. The real controller receives the original unmodified assets
and decisions. Removing the new probe field from the observations yields exact
non-timing parity with the earlier current-product replay on all 2,924 rows.
Two probe runs agreed; the source/asset-bound receipt is
`build/review-a3-rare-probe-20261028/receipt.json`, SHA-256
`b00ad5586991f3793271968c82db18df485ef95a7de4fc57abe60ec5706daf42`.

All 216 eligible rows were typo-labelled; none of the 741 controls entered this
probe. A complete pool was found for 195, and 21 were unavailable. The model
rejected 169 complete pools for insufficient margin and selected a winner on 26.
Existing admission rejected all 26: 22 for `RIVAL_UNKNOWN`, two for
`WINNER_AMBIGUOUS`, and two for `TARGET_UNKNOWN`. Nineteen of the rejected
`RIVAL_UNKNOWN` winners matched the expected spelling. No new correction is
established by this experiment. The results are disclosed-data diagnostics,
not evidence that relaxing morphology or other admission rules is safe; a
fresh holdout with lowercase names remains required.

## Unknown rivals in the observer

The probe now records plausible rivals lacking a single known morphology lemma,
and whether each rival occurred in the complete model pool. All 22
`RIVAL_UNKNOWN` rows had at least one such rival; in every row all identified
unknown rivals were already present in the model pool. Every row had at least
one absent morphology entry, and 17 also had at least one present but
lemma-ambiguous rival. The probe reproduces the guard's cost band; it does not
infer a lemma from the model score.

Of these 22 model winners, 19 match the historical expected spelling and three
do not (19/22 = 86.36% descriptive point precision). This is an offline
counterfactual before subsequent controller/editor checks, with no independent
controls for this subset; it is not a tested replacement policy or a precision
claim for natural typing. It does not justify bypassing `RIVAL_UNKNOWN`, even
when the competitor was scored. The two deterministic replays retained identical
pre-existing observation fields after removing the added rival details. Receipt:
`build/review-a3-rival-diagnostic-20261028/receipt.json`, SHA-256
`d1b03e65890546bd1df47d22ae5a152841402d3a7299e75fc4884f2febb2ef08`.

## Lowercase evidence sidecar screen

The same three pinned public Wikipedia shards used for the rare-word supplement
were scanned for standalone lowercase Cyrillic forms of 3–4 code points. The
extractor excludes spans touching Unicode word characters or hyphens; it records
document counts and requires at least one occurrence. It also rejects a match
adjacent to a Unicode combining mark. Across 277,866 documents it found 14,516
distinct forms. The development-only `words.tsv` SHA-256 is
`0371518ac794c9dbd37d58a4a7123a6a8bf1d4fe57c803264d85a08d4ef9d8ce`;
source and runtime bindings are in
`build/review-a3-lowercase-sidecar-grapheme-20261028/receipt.json`.
An independent second run produced the same file hash; boundary-unit tests and
the versioned test-inventory check passed.
An initial broader boundary expression counted Cyrillic fragments next to Latin
or digits; that 20,632-form output is superseded. The next version retained
18,405 forms but also allowed a boundary inside a combining sequence; it too is
superseded and its prior reported row counts must not be used as current results.

Among the 216 disclosed rare-only typo rows, 76 originals occur in the sidecar
and 140 do not. For the latter, the diagnostic model selected 19 winners, of
which 15 match the expected spelling and four do not; existing admission vetoed
all 19. Seventeen of these were `RIVAL_UNKNOWN` (15 matching, two not). These
are observer results before later controller/editor checks, not accepted edits.
Lowercase occurrence is neither proof of common-word status nor proof that a
non-occurring form is not a name. This disclosed screening cannot qualify or
package the sidecar, relax admission, or replace a fresh named-control holdout.

The previously disclosed Q5 name/place contrasts contain 18 short-name rows;
all 18 forms occur in this sidecar, and none reaches the rare-only diagnostic
probe because an earlier valid-word condition stops it. The 18 examples are
clustered, previously exposed, and cannot measure name safety for other forms.
The two-run controller receipt is
`build/review-a3-name-contrast-20261028/receipt.json`; it used the ordinary
product data and the source-only rare probe, not the sidecar in the controller.

## Canonical-case key overlap

The frozen `ru.case` asset contains 615 lowercase Cyrillic keys of length 3–4
whose canonical-case entries have the enabled flag. Of those, 551 also appear in
the frozen rare asset; 364 of those 551 have no entry in this lowercase evidence
sidecar. Separately, 192 of the 615 occur in the sidecar. This is a key overlap,
not a count of names, proposed corrections, or false changes: other dictionary,
canonical-case, model and admission gates may still preserve those forms.
It demonstrates that absence from the sidecar does not alone establish that a
form cannot be a name or another case-sensitive word.

`a3_case_sidecar_audit.py` verifies the packaged asset hashes and the sidecar
receipt before calculating these counts. Its aggregate-only report is
`build/review-a3-case-sidecar-audit-20261028/report.json`; it does not expose
word lists or qualify the proposed sidecar. The small disclosed 18-row name
contrast above and this wider static inventory do not replace a fresh named
control set with actual typing and editor outcomes.

The 364 short case keys present in rare and absent from lowercase evidence were
replayed in two synthetic contexts, as 728 unlabelled inputs. All 728 were
already recognized as valid words by the baseline generator, so the A3 rare-only
probe was never entered. Both runs were deterministic. This tests the current
host cascade for these keys, not whether each key is a name, whether changing
case would match a person's intent, or how a different rare-veto intervention
would affect real text. The inputs and their case-insensitive surfaces are now
registered in `control-ledger.json` as disclosed regressions; they are not
fresh holdout data. The reproducible generator is `a3_case_control_inputs.py`;
its output rows SHA-256 is
`237b2f832d13d0feeda7238ef41c2ff8ec7b952597e6aea59b0bbef5f01a03a5`.
Replay receipt: `build/review-a3-case-controls-replay-20261028/receipt.json`.

## Short rare keys outside lowercase evidence

The frozen rare asset contains 10,120 standalone 3–4-letter forms absent from
the diagnostic lowercase sidecar. A host probe using the actual validated
packed dictionary and morphology readers checked every form: 780 are present in
the main dictionary, 2,359 in morphology, and 7,708 absent from both (the first
two counts can overlap). Every rare lookup succeeded and confirmed membership.
This establishes the size of a potentially affected surface, not the number of
names, emitted candidates, actual replacements, or errors: the probe did not
run a controller or model and has no intended-text labels. Other protections
and case rules may still apply.

The reproducible `a3_rare_membership_probe.py` and `A3RareMembershipProbe.kt`
bind the input sidecar, frozen assets and source files; the final receipt is
`build/review-a3-rare-membership-final-20261028/receipt.json`. A selection test
checks the short-Cyrillic and absent-sidecar restrictions. Neither this static
inventory nor the 364 case-key replay qualifies changing the veto.

## Disclosed Taiga PROPN contrasts

The already-exposed UD Russian Taiga 2.18 development partition supplies 24
unambiguously aligned, title-case 3–4-letter PROPN occurrences (12 distinct
lowercased surfaces) that are in `ru.rare` and absent from the lowercase
sidecar. The source annotations are a mixture of automatic processing and manual
review; a PROPN tag and source capitalization are not a verified label for what
a user intended when typing lowercase. Context is clipped to 128 characters;
two inputs have empty prefixes. No annotation or expected target is sent to the
controller. The disclosed input surfaces and context keys are registered in
`control-ledger.json`, and the source sentences were already quarantined in the
holdout ledger. This is not an independent holdout.

The current host controller was replayed twice with the diagnostic rare mask.
Twenty-two rows did not reach the rare-only probe; two reached it, produced
complete pools and the frozen model abstained on insufficient margin in both.
The two probed rows have distinct surfaces. This small clustered sample did not
produce a hypothetical model winner, but does not establish zero false changes
for names or actual Android behavior. The input generator is
`tools/typing_experiments/a3_taiga_propn_screen.py`; rows SHA-256 is
`1983076cc5fa171271fea276beaa66254bd9bf84f38f71067b71426d10100021` and the
replay receipt is `build/review-a3-taiga-propn-replay-20261028/receipt.json`.

## Current controller repeat on the recovered original holdout

The original 8,557-row Joint holdout recovered by the archived native
morphology selectors matched its original SHA-256. Applying the historical
length filter and serialization reproduced the exact 2,924-row A3 input
digest recorded above. On source revision `f87d4d8a`, the ordinary and
source-mask configurations each agreed across two JVM processes. Every
ordinary controller field was byte-identical across configurations after
removing the diagnostic `a3RareProbe` field.

All 216 eligible rows were lowercase Russian typo-labelled inputs. The
mask produced 195 complete pools and 26 winners. Nineteen matched the
expected spelling, and seven did not. The existing admission guard
rejected every winner, with 22 `RIVAL_UNKNOWN`, two `WINNER_AMBIGUOUS`
and two `TARGET_UNKNOWN`. None of the 741 controls entered the probe.
The tested source-only change yields zero accepted corrections on this
disclosed sample. The current product keeps its existing veto.

| Configuration | Projection SHA-256 | Receipt SHA-256 |
| --- | --- | --- |
| Ordinary | `92aea6ea2bb087602a34b2709237d2b80abeb54606590159e036604a5171b346` | `31f72f121e1655936518d992a5e45e323ef8974a2f9aa67143064d239e3c2ec7` |
| Source rare mask | `4948f9d6ac14f28fa2d3c9c6e9a9c15e44ff99229e3b60fd599458780957fefb` | `09bb3dfdd0c1c0605f8ee712433bebbff916ef77eaa2c60c0447a3a84d6dc6e4` |

## Lowercase controls available in RNC normalization

The [pinned RNC scan](2026-11-24-q5-rnc-normalization-screen.md)
was repeated in memory for A3. It counted aligned original and annotated
tokens where the original has exactly 3–4 lowercase Russian Cyrillic
letters. The screen distinguished exact unchanged tokens from edits
changing only the initial capitalization. The existing packed readers
checked each original against the verified `ru.rare` and enabled
`ru.case` keys.

| Aligned source tokens | Occurrences | Distinct surfaces |
| --- | ---: | ---: |
| Unchanged lowercase | 2,027 | 520 |
| Unchanged lowercase found in `ru.rare` | 1,898 | 442 |
| Unchanged lowercase final token | 302 | 192 |
| Unchanged lowercase final token found in `ru.rare` | 265 | 160 |
| Initial capitalization changed by the annotation | 65 | 41 |

Zero unchanged or capitalization-edited rows matched an enabled
`ru.case` key. The capitalization edits were all nonfinal. The release
does not label proper names, so the lookup counts provide no independently
adjudicated lowercase name controls. The aggregate SHA-256 was
`2a402be37035088306cd4b91ea703a84d41552a775d152b5d8c06b3eefeadf5a`.
The screen retained zero source texts or row identities. Temporary replay
outputs were removed. Independent qualification and Fold acceptance remain
open.
