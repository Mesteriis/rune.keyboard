# Authored grammar contrasts: training diagnostic

The installed contextual model still misselects grammatical forms. The five
disclosed target forms are already retrieved; existing soft infinitive/case
features do not consistently outweigh spelling similarity. This diagnostic adds
generic opposing contexts before further fitting, rather than special rules for
those five words.

`tools/typing_experiments/grammar_contrast_corpus.py` generates **630 training-only
rows in 35 paradigm families**: 20 infinitive/second-person verb pairs, seven
singular/plural short-adjective pairs and eight accusative/instrumental noun
pairs. All five disclosed failure paradigms are excluded. These are authored
templates, not harvested messages or sentences. Dictionary-only Pymorphy analyses
validate that both forms share a lemma and the intended grammatical attributes.
The pinned dictionary dependency is the existing `tools/morphology/requirements.lock`.

Each family has an unknown-to-that-dictionary one-edit corruption shared by both
forms, three preceding contexts for each intended form, and both already-correct
forms as retention controls at every context. A grammatically disagreeing but
correctly spelled word remains a retention control: these examples train
spelling correction without granting permission to rewrite valid words.

Reproduce in a new output directory using the existing environment containing
the pinned morphology dependencies:

```sh
python tools/typing_experiments/grammar_contrast_corpus.py --output build/grammar-contrast-new
PYTHONPATH=tools/typing_experiments python3 -m unittest test_grammar_contrast_corpus test_grammar_context_features
```

The generator refuses an existing output directory, binds its source/corpus/
dictionary hashes in a manifest, and does not use model scores for selection.
Two complete generations produced byte-identical JSONL. **11 unit tests passed**
(five new corpus tests and six existing grammar-feature tests).

## Current controller result

The hash-verified Kotlin harness from the installed integration (`e7397be`) ran
all 630 rows in `contextual-production` mode. Only IDs, the `train` partition,
language, prefix and typed text entered the harness; intended forms remained in
the Python join. This was a desktop controller replay, not another Fold test.

| Contrast | Typo rows | Correct | Unchanged | Wrong | Both forms retrieved |
| --- | ---: | ---: | ---: | ---: | ---: |
| Infinitive / finite | 120 | 13 | 104 | 3 | 120 |
| Singular / plural predicate | 42 | 0 | 42 | 0 | 42 |
| Accusative / instrumental | 48 | 9 | 30 | 9 | 42 |

All **420 correct-word controls stayed unchanged**. All **630 exact boundary
Undo checks passed**. These synthetic training diagnostics establish neither
independent precision nor qualification at the owner's 95% gate.

The six noun cases without joint candidates use `копие`. Pymorphy's restricted
dictionary adapter returned no analysis, but the production lexicon reports
`VALID_WORD`, `isValidWord=true`, `prohibitsAutoReplace=true`. Therefore these six
rows must be excluded from correction fitting; they demonstrate a dictionary
coverage mismatch, not a candidate retrieval defect. Do not weaken original-word
protection to make the synthetic labels pass. Future training selection must
require an unknown, complete production pool containing the intended form and
keep already-correct retention groups separate.

The aggregate JSON receipt records corpus, generator and observation hashes.
Local manifests and observations are under ignored `build/grammar-contrasts-20261026/`.
No weights, thresholds, application assets or installed APK changed in this slice.
The next fit must combine these contrasts with the broad existing training mix,
freeze its selection, and reserve fresh non-overlapping evaluation contexts and
families. This authored set must never be called independent evaluation data.
