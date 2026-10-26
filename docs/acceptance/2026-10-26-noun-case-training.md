# Noun-case training and frozen independent corpus

On 2026-10-26 a new authored noun-case training slice was added after
[the infinitive revision integration](2026-10-26-infinitive-revision-integration.md).
The experimental weights now put `фотографию` above `фотографией` for the
previously disclosed `Том показал мне фотографие` training example.
This is a training diagnostic, not independent qualification or changed editor behavior.
[Evidence hashes and counts](2026-10-26-noun-case-training-evidence.json) accompany this record.

## Cause and training change

Both intended and competing forms were already retrieved. The old 146-feature
scorer sees the accusative verb cue and accusative support for `фотографию`,
yet scores it 0.579070 against 0.621967 for `фотографией`. Candidate retrieval
and the cue extractor therefore do not explain this particular miss.
The old authored object slice had only 90 typo groups across eight noun families.

`noun_case_contrast_corpus.py` adds 24 different dictionary-verified noun paradigms
and six opposing accusative/instrumental context pairs. Corruptions are selected
by static keyboard geometry and dictionary unknownness, without model scores.
Both correct forms remain retention controls in every context, including a
grammatically disagreeing context. The earlier eight noun paradigms and the
five disclosed failure targets are absent from this added authored set.

All 1,140 rows completed the production Kotlin candidate replay. The existing
strict group selector accepted all 564 typo and 576 retention groups. Both noun
forms were genuinely present in each typo pool; no candidate was inserted to
satisfy a label. All 564 authored edit-cost pairs matched production metadata
exactly at `(1.0, 1.0)`. No duplicate training tuples or IDs were added.

The full 20,750-group preceding mix was retained, yielding 21,890 groups /
248,796 candidate rows. Frozen base vectors are hash-verified and remain
byte-for-byte numerically identical in the concatenated matrix. Training keeps
146 features, 128 depth-five trees, learning rate 0.05, seed 25102026 and
PairLogitPairwise. The new 22,036-byte experimental binary SHA256 is
`c848b1cac54515382287325343a863e4e8713ca7a628e3336806b74ccd64de42`.

| Training slice | Groups | Prior secondary weights: target first | New weights: target first |
| --- | ---: | ---: | ---: |
| Frozen broad mix | 19,802 | 18,809 | 18,842 |
| Earlier typo contrasts | 540 | 433 | 449 |
| Earlier retention contrasts | 408 | 405 | 406 |
| New noun typo contrasts | 564 | 389 | 532 |
| New noun retention contrasts | 576 | 528 | 564 |

The comparator here is the preceding `20409f…` secondary model, not a projection
of the installed layered controller. The new weights also lose 68 formerly
correct broad raw winners and two earlier typo winners, despite improving totals.
There is no qualification for replacing any installed weights globally.

The disclosed photo training row now scores `фотографию` at 0.672892 against
`фотографией` at 0.556319. All three disclosed infinitive training winners stay
correct. `виновн` still ranks `виновен` ahead of `виновны`: its missing following
subject/right context is outside this training slice.

## Independent corpus preparation

`noun_case_focus_forms.py` derives a source cohort from natural lowercase nouns
ending in `у/ю`. It requires dictionary-unambiguous singular accusative and
instrumental forms of a single identical lemma, and an unknown shared corruption
with equal edit cost. Known intermediate words, unsupported forms, mixed analyses
and competing dictionary spellings are refused. This helper does not establish
candidate retrieval or automatic admission.

The final corpus is frozen under `build/noun-case-focus-v3-20261026/` before any
independent evaluation scoring: 1,000 contexts / 4,000 inputs in each partition,
157 calibration families and 168 holdout families, with family separation.
Each context has one typo, two correctly spelled form controls, and one protected
`@` token: 6,000 controls total. Source/context and full normalized sentence hash
exclusions cover earlier training/evaluation material, all authored templates,
authored contrast families, and the disclosed failure families. The separate
audit confirms zero overlaps on these recorded dimensions. Contributor independence
is not claimed. Source attribution/license remains Tatoeba CC-BY-2.0-FR; this is
synthetic corruption in natural text, not observed human typing.

The first availability plan required 1,000 contexts per partition with at most
24 per family. It stopped at 863/967 before scoring. A second plan raised the
cap to 64, retained the same seed/volume/quality requirements and required at
least 100 families per partition. Its unscored corpus was superseded by v3 to
explicitly exclude all disclosed failure families. All earlier plans/artifacts
remain retained. No threshold, label or sample was changed in response to an
evaluation model score; no independent model score was consumed in this slice.

The subsequent qualification must compare revisions against the actual installed
contextual-plus-infinitive controller, require at least 100 additional correct
changes, 97.5% calibration and 95% held-out precision, zero previous-correct losses
and zero control changes. Holdout scoring remains prohibited until calibration
passes; broad regression, Kotlin/controller qualification and device tests remain
required before deployment.

## Checks and status

All 23 tests passed:

```sh
PYTHONPATH=tools/typing_experiments python3 -m unittest \
  test_noun_case_contrast_corpus test_noun_case_focus_forms \
  test_grammar_contrast_corpus test_grammar_training_groups
build/typing-ranker-v2-venv/bin/python \
  tools/typing_experiments/noun_case_contrast_corpus.py --output build/new-noun-corpus
```

Tests cover opposing targets for the same unknown spelling, unduplicated correct
controls, deterministic identities, disclosed/prior form exclusions, dictionary
case/lemma failures, mixed/homonymous analyses and dictionary-known corruptions.
The scalar decoder and vectorized scores agree exactly on 128 sampled vectors
per model. `git diff --check` passed. Android build/device checks were not rerun:
application sources and packaged assets did not change, and no phone command was
performed in this experimental slice. The last verified installed Rune build
remains the preceding integration milestone; these new weights are unqualified
and remain ignored local artifacts.
